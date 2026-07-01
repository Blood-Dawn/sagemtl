"""Cloud vision-LLM translation providers.

Each provider sends one page image plus the detected source text, a glossary
block, and a short rolling summary, and asks for one translated string per region
as JSON (spec Appendix C). Whole-page context fixes dropped pronouns, honorifics,
gendered voice, and name/term consistency; quality peaks at one page of context,
so it is one page per call plus a rolling summary, never a whole volume.

The orchestration (prompt build, JSON-per-region parse, exponential backoff on
transient/429 errors, per-chapter cost ceiling, image-disabled fallback) lives in
``BaseCloudProvider`` and is fully testable without an API key by injecting a
``complete_fn``. Concrete providers add a lazy SDK call. API keys are read from the
environment variable named in config; they are never stored. See spec section 6.1.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Callable, Optional, Protocol, Sequence, runtime_checkable

from .models import TextRegion

__all__ = [
    "CloudError",
    "CostCeilingExceeded",
    "TransientError",
    "MissingApiKeyError",
    "CostTracker",
    "CloudTranslator",
    "BaseCloudProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "OpenAIProvider",
    "build_provider",
    "build_glossary_block",
    "build_messages",
    "parse_translations",
]


class CloudError(Exception):
    """Base error for cloud translation."""


class CostCeilingExceeded(CloudError):
    """Raised when a call would exceed the per-chapter cost ceiling."""


class TransientError(CloudError):
    """Retryable error (e.g. HTTP 429 / rate limit / transient server error)."""


class MissingApiKeyError(CloudError):
    """Raised when the configured API key environment variable is unset."""


@dataclass
class CostTracker:
    """Tracks spend against a per-chapter ceiling (USD). ceiling < 0 == unlimited."""

    ceiling_usd: float
    spent_usd: float = 0.0

    def would_exceed(self, add_usd: float) -> bool:
        if self.ceiling_usd < 0:
            return False
        return (self.spent_usd + max(0.0, add_usd)) > self.ceiling_usd

    def add(self, usd: float) -> None:
        self.spent_usd += max(0.0, usd)


@runtime_checkable
class CloudTranslator(Protocol):
    def translate_page(
        self,
        page_png: bytes,
        regions: Sequence[TextRegion],
        glossary: Sequence,
        target_lang: str,
        rolling_summary: str,
    ) -> list[str]:
        ...


# ---------------------------------------------------------------------------
# Prompt construction (spec Appendix C)
# ---------------------------------------------------------------------------


def build_glossary_block(glossary: Sequence) -> str:
    """Render glossary terms as 'source -> target (category)' lines."""

    lines = []
    for term in glossary or []:
        source = getattr(term, "source", None)
        target = getattr(term, "target", None)
        if source is None and isinstance(term, (list, tuple)) and len(term) >= 2:
            source, target = term[0], term[1]
        if not source:
            continue
        line = f"{source} -> {target}"
        category = getattr(term, "category", "")
        if category:
            line += f" ({category})"
        lines.append(line)
    return "\n".join(lines)


def build_messages(
    regions: Sequence[TextRegion],
    source_lang: str,
    target_lang: str,
    glossary_text: str,
    rolling_summary: str,
) -> tuple[str, str, list[dict]]:
    """Return (system_prompt, user_prompt, regions_payload) per spec Appendix C."""

    payload = [{"id": i, "text": r.source_text} for i, r in enumerate(regions)]
    system = (
        f"You are a professional manga/manhwa/manhua localizer translating "
        f"{source_lang} to {target_lang}. Preserve tone, register, honorifics, and "
        f"each character's distinct voice. Keep onomatopoeia natural for "
        f"{target_lang}. Use the glossary exactly. Return only JSON."
    )
    parts = []
    if glossary_text:
        parts.append("GLOSSARY (use these renderings verbatim):\n" + glossary_text)
    if rolling_summary:
        parts.append("RECENT CONTEXT (previous page, summary):\n" + rolling_summary)
    parts.append(
        "Here is one manga page and the detected text regions in reading order:\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    parts.append(
        "Translate each region using the whole-page image for context (who is "
        "speaking, panel, gender). Return: "
        '{"translations":[{"id":0,"text":"..."}, ...]} with one entry per region '
        "id, same order."
    )
    return system, "\n\n".join(parts), payload


def parse_translations(raw, count: int) -> list[str]:
    """Parse a JSON-per-region response into a list of ``count`` strings."""

    data = raw
    if isinstance(raw, str):
        data = _extract_json(raw)
    if not isinstance(data, dict):
        return [""] * count

    items = data.get("translations")
    out = [""] * count
    if isinstance(items, list):
        for i, item in enumerate(items):
            if isinstance(item, dict):
                idx = item.get("id", i)
                text = item.get("text", "")
            else:
                idx, text = i, item
            try:
                idx = int(idx)
            except (TypeError, ValueError):
                idx = i
            if 0 <= idx < count:
                out[idx] = str(text)
    return out


def _extract_json(raw: str):
    raw = raw.strip()
    # Strip markdown code fences if present.
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        pass
    # Fall back to the first {...} object in the text.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (ValueError, TypeError):
            return None
    return None


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class BaseCloudProvider:
    """Shared orchestration: prompt, retry/backoff, cost ceiling, parsing."""

    name = "base"

    def __init__(
        self,
        model: str,
        api_key_env: str = "",
        *,
        source_lang: str = "ja",
        max_retries: int = 4,
        base_delay: float = 1.0,
        allow_image: bool = True,
        cost_tracker: Optional[CostTracker] = None,
        usd_per_call: float = 0.0,
        complete_fn: Optional[Callable[[str, str, Optional[bytes]], str]] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model
        self.api_key_env = api_key_env
        self.source_lang = source_lang
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.allow_image = allow_image
        self.cost_tracker = cost_tracker
        self.usd_per_call = usd_per_call
        self._complete_fn = complete_fn
        self._sleep = sleep

    def _api_key(self) -> str:
        key = os.environ.get(self.api_key_env, "") if self.api_key_env else ""
        if not key:
            raise MissingApiKeyError(
                f"API key env var {self.api_key_env!r} is not set."
            )
        return key

    def _complete(self, system: str, user: str, page_png: Optional[bytes]) -> str:
        """Provider-specific call. Base supports an injected ``complete_fn``."""

        if self._complete_fn is not None:
            return self._complete_fn(system, user, page_png)
        raise NotImplementedError("BaseCloudProvider has no SDK; provide complete_fn or use a subclass.")

    def _complete_with_retry(self, system: str, user: str, page_png: Optional[bytes]) -> str:
        delay = self.base_delay
        last: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._complete(system, user, page_png)
            except TransientError as exc:
                last = exc
                if attempt >= self.max_retries:
                    break
                self._sleep(delay)
                delay *= 2
        raise last if last is not None else CloudError("retry loop exhausted")

    def translate_page(
        self,
        page_png: bytes,
        regions: Sequence[TextRegion],
        glossary: Sequence,
        target_lang: str,
        rolling_summary: str,
    ) -> list[str]:
        regions = list(regions)
        if not regions:
            return []
        if self.cost_tracker is not None and self.cost_tracker.would_exceed(self.usd_per_call):
            raise CostCeilingExceeded(
                f"per-chapter cost ceiling reached (spent={self.cost_tracker.spent_usd:.4f}, "
                f"ceiling={self.cost_tracker.ceiling_usd:.4f})"
            )

        block = build_glossary_block(glossary)
        system, user, _ = build_messages(
            regions, self.source_lang, target_lang, block, rolling_summary
        )
        image = page_png if self.allow_image else None
        raw = self._complete_with_retry(system, user, image)

        if self.cost_tracker is not None:
            self.cost_tracker.add(self.usd_per_call)
        return parse_translations(raw, len(regions))


def _image_block_b64(page_png: bytes) -> str:
    import base64

    return base64.b64encode(page_png).decode("ascii")


class AnthropicProvider(BaseCloudProvider):
    name = "anthropic"

    def _complete(self, system: str, user: str, page_png: Optional[bytes]) -> str:
        if self._complete_fn is not None:
            return self._complete_fn(system, user, page_png)
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dep
            raise CloudError("anthropic SDK not installed") from exc

        client = anthropic.Anthropic(api_key=self._api_key())
        content: list = [{"type": "text", "text": user}]
        if page_png:
            content.insert(
                0,
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": _image_block_b64(page_png),
                    },
                },
            )
        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": content}],
            )
        except Exception as exc:  # pragma: no cover - network
            raise _map_transient(exc)
        return "".join(part.text for part in message.content if getattr(part, "type", "") == "text")


class OpenAIProvider(BaseCloudProvider):
    name = "openai"

    def _complete(self, system: str, user: str, page_png: Optional[bytes]) -> str:
        if self._complete_fn is not None:
            return self._complete_fn(system, user, page_png)
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dep
            raise CloudError("openai SDK not installed") from exc

        client = OpenAI(api_key=self._api_key())
        user_content: list = [{"type": "text", "text": user}]
        if page_png:
            url = "data:image/png;base64," + _image_block_b64(page_png)
            user_content.append({"type": "image_url", "image_url": {"url": url}})
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover - network
            raise _map_transient(exc)
        return resp.choices[0].message.content or ""


class GoogleProvider(BaseCloudProvider):
    name = "google"

    def _complete(self, system: str, user: str, page_png: Optional[bytes]) -> str:
        if self._complete_fn is not None:
            return self._complete_fn(system, user, page_png)
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - optional dep
            raise CloudError("google-genai SDK not installed") from exc

        client = genai.Client(api_key=self._api_key())
        parts: list = [user]
        if page_png:
            parts.append(types.Part.from_bytes(data=page_png, mime_type="image/png"))
        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=parts,
                config=types.GenerateContentConfig(system_instruction=system),
            )
        except Exception as exc:  # pragma: no cover - network
            raise _map_transient(exc)
        return resp.text or ""


def _map_transient(exc: Exception) -> Exception:
    """Map an SDK error to TransientError on 429 / rate-limit, else return as-is."""

    text = f"{type(exc).__name__}: {exc}".lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    rate_limited = ("rate" in text and "limit" in text)
    if status == 429 or "429" in text or rate_limited:
        return TransientError(str(exc))
    return exc


_PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "google": GoogleProvider,
}


def build_provider(provider: str, model: str, api_key_env: str, **kwargs) -> CloudTranslator:
    """Construct a configured cloud provider by name."""

    name = (provider or "").strip().lower()
    if name not in _PROVIDERS:
        raise CloudError(f"Unknown cloud provider {provider!r}. Known: {', '.join(sorted(_PROVIDERS))}")
    return _PROVIDERS[name](model=model, api_key_env=api_key_env, **kwargs)
