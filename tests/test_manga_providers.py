"""Phase 3 unit tests: cloud provider orchestration (no API key needed)."""

from __future__ import annotations

import json

import pytest

from sagemtl_desktop.core.manga import providers
from sagemtl_desktop.core.manga.models import TextRegion


def _regions(n):
    return [TextRegion(box=(0, 0, 10, 10), source_text=f"src{i}") for i in range(n)]


def _json(items):
    return json.dumps({"translations": items})


# ---------------------------------------------------------------------------
# prompt + parsing
# ---------------------------------------------------------------------------


def test_build_glossary_block():
    from sagemtl_desktop.core.glossary_manager import GlossaryTerm

    block = providers.build_glossary_block(
        [GlossaryTerm(source="A", target="B", category="Character"), ("C", "D")]
    )
    assert "A -> B (Character)" in block
    assert "C -> D" in block


def test_build_messages_has_appendix_c_shape():
    system, user, payload = providers.build_messages(
        _regions(2), "ja", "en", "A -> B", "previously: stuff happened"
    )
    assert "localizer" in system and "ja" in system and "en" in system
    assert "A -> B" in user
    assert "previously: stuff happened" in user
    assert '"translations"' in user
    assert payload == [{"id": 0, "text": "src0"}, {"id": 1, "text": "src1"}]


def test_parse_translations_wellformed():
    raw = _json([{"id": 0, "text": "a"}, {"id": 1, "text": "b"}])
    assert providers.parse_translations(raw, 2) == ["a", "b"]


def test_parse_translations_reorders_by_id():
    raw = _json([{"id": 1, "text": "b"}, {"id": 0, "text": "a"}])
    assert providers.parse_translations(raw, 2) == ["a", "b"]


def test_parse_translations_missing_and_extra():
    raw = _json([{"id": 0, "text": "a"}, {"id": 5, "text": "ignored"}])
    assert providers.parse_translations(raw, 2) == ["a", ""]


def test_parse_translations_markdown_fenced():
    raw = "```json\n" + _json([{"id": 0, "text": "x"}]) + "\n```"
    assert providers.parse_translations(raw, 1) == ["x"]


def test_parse_translations_non_json_returns_blanks():
    assert providers.parse_translations("not json at all", 2) == ["", ""]


# ---------------------------------------------------------------------------
# orchestration (mocked complete_fn, no key)
# ---------------------------------------------------------------------------


def test_translate_page_happy_path():
    captured = {}

    def complete(system, user, image):
        captured["system"] = system
        captured["user"] = user
        captured["image"] = image
        return _json([{"id": 0, "text": "A"}, {"id": 1, "text": "B"}])

    provider = providers.BaseCloudProvider("m", "KEY", complete_fn=complete)
    out = provider.translate_page(b"IMG", _regions(2), [], "en", "")
    assert out == ["A", "B"]
    assert captured["image"] == b"IMG"  # image forwarded by default


def test_allow_image_false_sends_no_image():
    seen = {}

    def complete(system, user, image):
        seen["image"] = image
        return _json([{"id": 0, "text": "A"}])

    provider = providers.BaseCloudProvider("m", "KEY", allow_image=False, complete_fn=complete)
    provider.translate_page(b"IMG", _regions(1), [], "en", "")
    assert seen["image"] is None


def test_retry_then_success_with_backoff():
    calls = {"n": 0}
    slept = []

    def complete(system, user, image):
        calls["n"] += 1
        if calls["n"] < 3:
            raise providers.TransientError("429 rate limit")
        return _json([{"id": 0, "text": "ok"}])

    provider = providers.BaseCloudProvider(
        "m", "KEY", max_retries=4, base_delay=1.0, complete_fn=complete, sleep=slept.append
    )
    out = provider.translate_page(b"", _regions(1), [], "en", "")
    assert out == ["ok"]
    assert calls["n"] == 3
    assert slept == [1.0, 2.0]  # exponential backoff between the 2 failures


def test_retry_exhausted_raises_transient():
    def complete(system, user, image):
        raise providers.TransientError("429")

    provider = providers.BaseCloudProvider(
        "m", "KEY", max_retries=2, base_delay=0.0, complete_fn=complete, sleep=lambda d: None
    )
    with pytest.raises(providers.TransientError):
        provider.translate_page(b"", _regions(1), [], "en", "")


def test_cost_ceiling_blocks_before_call():
    called = {"n": 0}

    def complete(system, user, image):
        called["n"] += 1
        return _json([{"id": 0, "text": "x"}])

    tracker = providers.CostTracker(ceiling_usd=0.0)
    provider = providers.BaseCloudProvider(
        "m", "KEY", cost_tracker=tracker, usd_per_call=0.5, complete_fn=complete
    )
    with pytest.raises(providers.CostCeilingExceeded):
        provider.translate_page(b"", _regions(1), [], "en", "")
    assert called["n"] == 0  # never called the model


def test_cost_accumulates_until_ceiling():
    tracker = providers.CostTracker(ceiling_usd=1.0)
    provider = providers.BaseCloudProvider(
        "m", "KEY", cost_tracker=tracker, usd_per_call=0.4,
        complete_fn=lambda s, u, i: _json([{"id": 0, "text": "x"}]),
    )
    provider.translate_page(b"", _regions(1), [], "en", "")
    provider.translate_page(b"", _regions(1), [], "en", "")
    assert tracker.spent_usd == pytest.approx(0.8)
    with pytest.raises(providers.CostCeilingExceeded):
        provider.translate_page(b"", _regions(1), [], "en", "")


def test_glossary_block_appears_in_prompt():
    from sagemtl_desktop.core.glossary_manager import GlossaryTerm

    seen = {}
    provider = providers.BaseCloudProvider(
        "m", "KEY",
        complete_fn=lambda s, u, i: seen.update(user=u) or _json([{"id": 0, "text": "x"}]),
    )
    provider.translate_page(b"", _regions(1), [GlossaryTerm(source="X", target="Y")], "en", "")
    assert "X -> Y" in seen["user"]


# ---------------------------------------------------------------------------
# factory + key handling
# ---------------------------------------------------------------------------


def test_build_provider_factory():
    assert isinstance(
        providers.build_provider("anthropic", "claude-x", "ANTHROPIC_API_KEY"),
        providers.AnthropicProvider,
    )
    assert isinstance(
        providers.build_provider("openai", "gpt-x", "OPENAI_API_KEY"), providers.OpenAIProvider
    )
    assert isinstance(
        providers.build_provider("google", "gemini-x", "GOOGLE_API_KEY"), providers.GoogleProvider
    )
    with pytest.raises(providers.CloudError):
        providers.build_provider("nope", "m", "K")


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("SAGEMTL_TEST_KEY_UNSET", raising=False)
    provider = providers.AnthropicProvider("claude-x", "SAGEMTL_TEST_KEY_UNSET")
    with pytest.raises(providers.MissingApiKeyError):
        provider._api_key()


def test_empty_regions_returns_empty():
    provider = providers.BaseCloudProvider("m", "KEY", complete_fn=lambda s, u, i: "{}")
    assert provider.translate_page(b"", [], [], "en", "") == []


# ---------------------------------------------------------------------------
# _map_transient: the production trigger that turns SDK 429s into retries
# ---------------------------------------------------------------------------


def test_map_transient_status_429():
    class RateErr(Exception):
        status_code = 429

    assert isinstance(providers._map_transient(RateErr("boom")), providers.TransientError)


def test_map_transient_message_rate_limit():
    mapped = providers._map_transient(Exception("Error 429: rate limit exceeded"))
    assert isinstance(mapped, providers.TransientError)
    mapped2 = providers._map_transient(Exception("Rate Limit hit, slow down"))
    assert isinstance(mapped2, providers.TransientError)


def test_map_transient_passes_through_non_transient():
    class AuthErr(Exception):
        status_code = 401

    err = AuthErr("invalid api key")
    # A non-transient error must be returned unchanged (so it is NOT retried).
    assert providers._map_transient(err) is err
