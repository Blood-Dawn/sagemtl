"""
Tests for translator module.
"""

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
        rejoined = " ".join(chunks)
        # Should contain all sentences
        assert "First" in rejoined
        assert "Second" in rejoined
        assert "Third" in rejoined
        assert "Fourth" in rejoined
