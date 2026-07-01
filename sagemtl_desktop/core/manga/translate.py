"""Stage 3: translation (offline-first, optional cloud).

Offline (no API key required):
    - m2m100 (facebook/m2m100_1.2B): direct CJK->EN, coherent, the default fallback.
    - Argos (reuses the app's Translator): lightest, lowest quality.
    - llama.cpp GGUF (Sugoi / X-ALMA): best offline quality, optional/heavy.

Glossary handling reuses ``GlossaryManager`` keyed by ``series_id`` (== novel_id):
for sentence-level engines the glossary is applied to the source *before*
translation (so the target rendering of a name passes through verbatim) and to the
output *after* (the novel path's pre/post pattern, spec 6.3); for LLM engines the
glossary is injected as a prompt block.

Cloud translation (page image + whole-page context) lives in :mod:`providers` and
is delegated to here when a provider is supplied. All heavy imports (transformers,
torch, llama_cpp) are lazy. See ``MANGA_MODULE_BUILD_SPEC.md`` section 6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional, Sequence

from .models import TextRegion
from .ocr import detect_script, normalize_lang

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .providers import CloudTranslator

__all__ = [
    "run",
    "build_engine",
    "TranslateEngine",
    "ArgosEngine",
    "M2M100Engine",
    "LlamaCppEngine",
    "build_llm_prompt",
    "parse_numbered",
    "glossary_block",
]

LogCb = Optional[Callable[[str], None]]
_M2M_LANGS = {"ja", "ko", "zh", "en"}


# ---------------------------------------------------------------------------
# Glossary helpers (reuse GlossaryManager)
# ---------------------------------------------------------------------------


def _apply_glossary(text: str, glossary, series_id: str) -> str:
    if not text or glossary is None or not hasattr(glossary, "apply_glossary"):
        return text
    return glossary.apply_glossary(text, novel_id=series_id or None)


def _glossary_terms(glossary, series_id: str) -> list:
    if glossary is None:
        return []
    terms: list = []
    if series_id and hasattr(glossary, "get_novel_terms"):
        terms.extend(glossary.get_novel_terms(series_id))
    if hasattr(glossary, "get_global_terms"):
        terms.extend(glossary.get_global_terms())
    return terms


def glossary_block(glossary, series_id: str = "") -> str:
    """Render a glossary block ('source -> target (category)') for LLM prompts."""

    lines = []
    for term in _glossary_terms(glossary, series_id):
        line = f"{term.source} -> {term.target}"
        category = getattr(term, "category", "")
        if category:
            line += f" ({category})"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------


class TranslateEngine:
    """Base translation engine."""

    name = "base"
    is_llm = False

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:  # sentence-level
        raise NotImplementedError

    def translate_block(
        self, texts: Sequence[str], src_lang: str, tgt_lang: str, glossary_text: str = ""
    ) -> list[str]:  # LLM, whole-page context
        raise NotImplementedError


def _m2m_lang(lang: str) -> str:
    norm = normalize_lang(lang)
    return norm if norm in _M2M_LANGS else "ja"


class M2M100Engine(TranslateEngine):
    """Direct CJK->EN via facebook/m2m100_1.2B (transformers)."""

    name = "m2m100"
    is_llm = False

    def __init__(self, model_id: str = "facebook/m2m100_1.2B", device: str = "auto", max_length: int = 256) -> None:
        self.model_id = model_id
        self.device = device
        self.max_length = max_length
        self._tok = None
        self._model = None

    def _ensure(self):
        if self._model is None:
            from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

            self._tok = M2M100Tokenizer.from_pretrained(self.model_id)
            self._model = M2M100ForConditionalGeneration.from_pretrained(self.model_id)
        return self._tok, self._model

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        if not text.strip():
            return ""
        tok, model = self._ensure()
        tok.src_lang = _m2m_lang(src_lang)
        encoded = tok(text, return_tensors="pt")
        generated = model.generate(
            **encoded,
            forced_bos_token_id=tok.get_lang_id(_m2m_lang(tgt_lang)),
            max_length=self.max_length,
        )
        return tok.batch_decode(generated, skip_special_tokens=True)[0].strip()


class ArgosEngine(TranslateEngine):
    """Lightest offline engine: reuses the app's Argos-backed Translator."""

    name = "argos"
    is_llm = False

    def __init__(self) -> None:
        self._translator = None

    def _ensure(self):
        if self._translator is None:
            from sagemtl_desktop.core.translator import Translator

            self._translator = Translator()
        return self._translator

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        if not text.strip():
            return ""
        return self._ensure().translate(
            text, source_lang=src_lang or "auto", target_lang=tgt_lang or "en", backend="argos"
        ).strip()


def build_llm_prompt(texts: Sequence[str], src_lang: str, tgt_lang: str, glossary_text: str = "") -> str:
    """Build a numbered-lines prompt for a local LLM translator (Sugoi/X-ALMA)."""

    lines = [
        f"You are a professional manga localizer translating {src_lang} to {tgt_lang}.",
        "Preserve tone, honorifics, and each speaker's voice. Use the glossary exactly.",
    ]
    if glossary_text:
        lines.append("\nGLOSSARY (use these renderings verbatim):")
        lines.append(glossary_text)
    lines.append("\nTranslate each numbered line. Return one numbered line per input, same numbers.\n")
    for i, text in enumerate(texts):
        lines.append(f"{i + 1}. {text}")
    lines.append("\nTranslations:")
    return "\n".join(lines)


def parse_numbered(raw: str, count: int) -> list[str]:
    """Parse '1. text' numbered output into a list aligned to ``count`` items."""

    import re

    out: dict[int, str] = {}
    for match in re.finditer(r"^\s*(\d+)[.)]\s*(.+?)\s*$", raw or "", re.MULTILINE):
        idx = int(match.group(1)) - 1
        if 0 <= idx < count and idx not in out:
            out[idx] = match.group(2).strip()
    return [out.get(i, "") for i in range(count)]


class LlamaCppEngine(TranslateEngine):
    """Best offline quality via a GGUF model (Sugoi / X-ALMA) through llama.cpp.

    Optional and heavy; ``translate_block`` degrades to empty strings if llama.cpp
    or the model is unavailable, so it never crashes the offline path.
    """

    name = "llamacpp"
    is_llm = True

    def __init__(self, model_key: str = "mt_sugoi", device: str = "auto", n_ctx: int = 4096) -> None:
        self.model_key = model_key
        self.device = device
        self.n_ctx = n_ctx
        self._llm = None

    def _ensure(self):
        if self._llm is None:
            from llama_cpp import Llama

            from . import model_registry

            path = model_registry.ensure(self.model_key)
            self._llm = Llama(model_path=str(path), n_ctx=self.n_ctx, verbose=False)
        return self._llm

    def _generate(self, prompt: str) -> str:
        llm = self._ensure()
        result = llm(prompt, max_tokens=self.n_ctx // 2, temperature=0.2, stop=["\n\n\n"])
        return result["choices"][0]["text"]

    def translate_block(
        self, texts: Sequence[str], src_lang: str, tgt_lang: str, glossary_text: str = ""
    ) -> list[str]:
        texts = list(texts)
        try:
            prompt = build_llm_prompt(texts, src_lang, tgt_lang, glossary_text)
            return parse_numbered(self._generate(prompt), len(texts))
        except Exception:
            return ["" for _ in texts]


def _engine_key(model_id: str) -> str:
    value = (model_id or "").lower()
    if "m2m100" in value:
        return "m2m100"
    if value == "argos" or "argos" in value:
        return "argos"
    if "gguf" in value or "sugoi" in value:
        return "llamacpp"
    return ""


def build_engine(config=None, *, offline_engine: Optional[TranslateEngine] = None) -> TranslateEngine:
    """Construct the offline engine from config (defaults to m2m100)."""

    if offline_engine is not None:
        return offline_engine
    model_id = getattr(config, "offline_mt_model", "") if config else ""
    device = getattr(config, "device", "auto") if config else "auto"
    key = _engine_key(model_id)
    if key == "argos":
        return ArgosEngine()
    if key == "llamacpp":
        return LlamaCppEngine(device=device)
    # m2m100 is the default wired engine; heavy LLM defaults (e.g. X-ALMA-13B) are
    # not auto-downloaded here -- select 'sugoi'/GGUF for the llama.cpp path.
    return M2M100Engine(device=device)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _resolve_src_lang(region: TextRegion, source_lang: str) -> str:
    if region.lang:
        return normalize_lang(region.lang) or "ja"
    norm = normalize_lang(source_lang)
    if norm and source_lang != "auto":
        return norm
    return detect_script(region.source_text) or "ja"


def _fit_length(values: list[str], n: int) -> list[str]:
    values = list(values)
    if len(values) < n:
        values.extend([""] * (n - len(values)))
    return values[:n]


def _translate_offline(regions, source_lang, target_lang, glossary, series_id, engine, log_cb, cache=None):
    tgt = normalize_lang(target_lang) or (target_lang or "en")
    if getattr(engine, "is_llm", False):
        block = glossary_block(glossary, series_id)
        src = _resolve_src_lang(regions[0], source_lang) if regions else "ja"
        raw = engine.translate_block([r.source_text for r in regions], src, tgt, block)
        return [_apply_glossary(t, glossary, series_id) for t in _fit_length(raw, len(regions))]

    results: list[str] = []
    for region in regions:
        if not region.source_text.strip():
            results.append("")
            continue
        src = _resolve_src_lang(region, source_lang)
        # glossary pre-substitution is part of the key, so a glossary change yields
        # a different key (cache stays consistent); post-substitution is re-applied.
        pre = _apply_glossary(region.source_text, glossary, series_id)
        key = f"{src}>{tgt}:{pre}" if cache is not None else None
        raw = cache.get(key) if key is not None else None
        if raw is None:
            raw = engine.translate(pre, src, tgt)
            if key is not None:
                cache[key] = raw
        results.append(_apply_glossary(raw, glossary, series_id))
    return results


def run(
    regions: Sequence[TextRegion],
    page_png: bytes = b"",
    source_lang: str = "auto",
    target_lang: str = "en",
    glossary=None,
    mode: str = "hybrid",
    rolling_summary: str = "",
    *,
    series_id: str = "",
    config=None,
    offline_engine: Optional[TranslateEngine] = None,
    provider: "Optional[CloudTranslator]" = None,
    cache: Optional[dict] = None,
    log_cb: LogCb = None,
) -> list[TextRegion]:
    """Fill ``target_text`` for each region.

    Cloud is used when ``mode`` is 'cloud' (or 'hybrid' with a ``provider``); the
    provider receives the page image and the glossary terms. Otherwise the offline
    engine (``offline_engine`` or one built from ``config``) is used with the
    glossary applied pre/post.
    """

    region_list = list(regions)
    if not region_list:
        return region_list

    use_cloud = provider is not None and mode in ("cloud", "hybrid")
    if use_cloud:
        terms = _glossary_terms(glossary, series_id)
        raw = provider.translate_page(page_png, region_list, terms, target_lang, rolling_summary)
        results = _fit_length([str(t) for t in raw], len(region_list))
        results = [_apply_glossary(t, glossary, series_id) for t in results]
    else:
        engine = build_engine(config, offline_engine=offline_engine)
        results = _translate_offline(
            region_list, source_lang, target_lang, glossary, series_id, engine, log_cb, cache=cache
        )

    for region, text in zip(region_list, results):
        region.target_text = (text or "").strip()
        if log_cb:
            log_cb(
                f"[translate] cls={region.cls} mode={mode} "
                f"src_chars={len(region.source_text)} tgt_chars={len(region.target_text)}"
            )
    return region_list
