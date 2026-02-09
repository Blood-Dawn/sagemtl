"""
Tests for translator module.
"""

import sys
import types

import pytest
from sagemtl_desktop.core.translator import Translator, MissingTranslatorError


class TestTranslator:
    """Test cases for Translator class"""

    def test_detect_language_chinese(self):
        """Test auto-detection of Chinese text"""
        translator = Translator()
        text = "这是一个测试文件。修真者的道心非常重要。"
        detected = translator.detect_language(text)
        assert detected == "zh"

    def test_detect_language_japanese(self):
        """Test auto-detection of Japanese text"""
        translator = Translator()
        text = "これはテストです。"
        detected = translator.detect_language(text)
        assert detected == "ja"

    def test_detect_language_korean(self):
        """Test auto-detection of Korean text"""
        translator = Translator()
        text = "이것은 테스트입니다."
        detected = translator.detect_language(text)
        assert detected == "ko"

    def test_detect_language_english(self):
        """Test auto-detection defaults to English for Latin text"""
        translator = Translator()
        text = "This is a test file."
        detected = translator.detect_language(text)
        assert detected == "en"

    def test_auto_lang_detects_and_translates(self):
        """Test that source_lang='auto' triggers detection"""
        translator = Translator()

        # Skip if Argos not available
        if not translator.is_available():
            pytest.skip("Argos Translate not installed")

        text = "这是测试"
        logs = []

        def log_cb(level, msg):
            logs.append((level, msg))

        # This should detect zh and attempt zh→en translation
        # Will raise MissingTranslatorError if model not installed
        try:
            translator.translate(text, "auto", "en", log_callback=log_cb)
        except MissingTranslatorError:
            # Expected if model not installed
            pass

        # Check that detection happened
        assert any("Auto-detected" in msg for level, msg in logs)

    def test_missing_model_raises_error_with_install_instructions(self, caplog):
        """Test that missing model raises MissingTranslatorError with instructions"""
        translator = Translator()

        # Skip if Argos not available
        if not translator.is_available():
            pytest.skip("Argos Translate not installed")

        # Try to use a language pair that definitely doesn't exist
        with pytest.raises(MissingTranslatorError) as exc_info:
            translator.translate("test", "xx", "yy")

        error = exc_info.value
        assert "xx → yy" in str(error)
        assert "install" in str(error).lower()
        assert "python -c" in str(error)

    def test_chunker_splits_long_text(self):
        """Test that long text is split into chunks"""
        translator = Translator()

        # Create long text (over 500 chars)
        sentence = "This is a test sentence. "
        long_text = sentence * 30  # ~750 chars

        chunks = translator._split_into_sentences(long_text, max_length=500)

        assert len(chunks) > 1
        assert all(len(chunk) <= 500 or chunk.endswith('.') for chunk in chunks)

    def test_chunker_preserves_order(self):
        """Test that chunked text can be rejoined in correct order"""
        translator = Translator()

        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = translator._split_into_sentences(text)

        # Rejoin and check
        rejoined = "".join(chunks)
        # Should contain all sentences
        assert "First" in rejoined
        assert "Second" in rejoined
        assert "Third" in rejoined
        assert "Fourth" in rejoined
        assert rejoined == text

    def test_translation_memory_cache_reuses_chunk_results(self, monkeypatch):
        """Repeated chunks should hit in-memory cache instead of re-translating."""
        translator = Translator()
        translator._argos_available = True
        translator.clear_translation_cache()

        calls = {"count": 0}

        class FakeTranslation:
            @staticmethod
            def translate(chunk):
                calls["count"] += 1
                return f"T:{chunk}"

        fake_translate_mod = types.ModuleType("argostranslate.translate")
        fake_translate_mod.get_translation_from_codes = lambda source, target: FakeTranslation()

        fake_package_mod = types.ModuleType("argostranslate.package")
        fake_package_mod.get_installed_packages = lambda: []

        fake_argos_mod = types.ModuleType("argostranslate")
        fake_argos_mod.translate = fake_translate_mod
        fake_argos_mod.package = fake_package_mod

        monkeypatch.setitem(sys.modules, "argostranslate", fake_argos_mod)
        monkeypatch.setitem(sys.modules, "argostranslate.translate", fake_translate_mod)
        monkeypatch.setitem(sys.modules, "argostranslate.package", fake_package_mod)

        repeated_sentence = ("A" * 300) + ". "
        text = repeated_sentence * 4
        result = translator.translate(text, "en", "fr", max_chunk_size=350)

        assert result
        assert calls["count"] == 1
        stats = translator.get_translation_cache_stats()
        assert stats["entries"] == 1
        assert stats["hits"] >= 3

    def test_echo_backend_passthrough(self):
        """Echo backend should return source text unchanged."""
        translator = Translator()
        translator.set_active_backend("echo")

        text = "Echo backend test."
        translated = translator.translate(text, "en", "fr")

        assert translated == text
        assert translator.is_available("echo")

    def test_googletrans_backend_translate(self, monkeypatch):
        """googletrans backend should work when optional dependency is available."""
        translator = Translator()
        translator.clear_translation_cache()

        calls = []

        class FakeGoogleResponse:
            def __init__(self, text):
                self.text = text

        class FakeGoogleTranslator:
            def translate(self, chunk, src="auto", dest="en"):
                calls.append((chunk, src, dest))
                return FakeGoogleResponse(f"G:{chunk}")

        fake_google_module = types.ModuleType("googletrans")
        fake_google_module.Translator = lambda: FakeGoogleTranslator()
        monkeypatch.setitem(sys.modules, "googletrans", fake_google_module)

        result = translator.translate(
            "One sentence. Two sentence.",
            "en",
            "es",
            backend="googletrans",
            max_chunk_size=20,
        )

        assert result.startswith("G:")
        assert calls
        assert all(call[2] == "es" for call in calls)

    def test_chunker_preserves_cjk_punctuation_and_newlines(self):
        """Chunker should preserve CJK punctuation and newline boundaries."""
        translator = Translator()
        text = ("第一句。第二句！\n第三句？\n\n第四句，還有第五句。") * 8

        chunks = translator._split_into_sentences(text, max_length=10, source_lang="zh")

        assert len(chunks) > 1
        assert "".join(chunks) == text

    def test_chunker_hard_splits_long_unbroken_text(self):
        """Long unbroken text should still be chunked to bounded sizes."""
        translator = Translator()
        text = "A" * 1200

        chunks = translator._split_into_sentences(text, max_length=250, source_lang="en")

        assert "".join(chunks) == text
        assert all(len(chunk) <= 250 for chunk in chunks)
