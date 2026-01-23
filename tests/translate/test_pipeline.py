"""Tests for the translation pipeline module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from sagemtl.translate.pipeline import (
    TranslationPipeline,
    TranslationConfig,
    TranslationProgress,
    translate_text,
)
from sagemtl.translate.providers import TranslationResult


class TestTranslationConfig:
    """Test TranslationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TranslationConfig()
        assert config.provider_name == "echo"
        assert config.source_lang == "zh"
        assert config.target_lang == "en"
        assert config.glossary_path is None
        assert config.use_glossary_db is True
        assert config.novel_id is None
        assert config.max_chars_per_chunk == 4000
        assert config.preserve_whitespace is True
        assert config.preserve_paragraphs is True
        assert len(config.protected_patterns) == 4

    def test_custom_config(self):
        """Test custom configuration."""
        config = TranslationConfig(
            provider_name="argos",
            source_lang="ja",
            target_lang="fr",
            glossary_path="/path/to/glossary.csv",
            use_glossary_db=False,
            novel_id="novel-123",
            max_chars_per_chunk=2000,
        )
        assert config.provider_name == "argos"
        assert config.source_lang == "ja"
        assert config.target_lang == "fr"
        assert config.glossary_path == "/path/to/glossary.csv"
        assert config.use_glossary_db is False
        assert config.novel_id == "novel-123"
        assert config.max_chars_per_chunk == 2000


class TestTranslationProgress:
    """Test TranslationProgress dataclass."""

    def test_default_progress(self):
        """Test default progress values."""
        progress = TranslationProgress()
        assert progress.total_chunks == 0
        assert progress.completed_chunks == 0
        assert progress.total_chars == 0
        assert progress.translated_chars == 0
        assert progress.current_chunk is None
        assert progress.errors == []

    def test_percent_complete_zero(self):
        """Test percent complete with no chunks."""
        progress = TranslationProgress()
        assert progress.percent_complete == 0.0

    def test_percent_complete_partial(self):
        """Test percent complete with partial progress."""
        progress = TranslationProgress(
            total_chunks=10,
            completed_chunks=5,
        )
        assert progress.percent_complete == 50.0

    def test_percent_complete_full(self):
        """Test percent complete when done."""
        progress = TranslationProgress(
            total_chunks=10,
            completed_chunks=10,
        )
        assert progress.percent_complete == 100.0


class TestTranslationPipeline:
    """Test TranslationPipeline class."""

    def test_init_with_echo_provider(self):
        """Test initialization with echo provider."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)
        assert pipeline.config == config
        assert pipeline._provider is not None

    def test_protect_text(self):
        """Test protected text extraction."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        text = "Hello [name] and <b>world</b>"
        protected, placeholders = pipeline._protect_text(text)

        assert "[name]" not in protected
        assert "<b>" not in protected
        assert "</b>" not in protected
        # [name], <b>, and </b> are all matched separately
        assert len(placeholders) == 3

    def test_restore_protected(self):
        """Test restoration of protected content."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        placeholders = {
            "__PROTECTED_0__": "[name]",
            "__PROTECTED_1__": "<b>",
        }
        text = "Hello __PROTECTED_0__ and __PROTECTED_1__world"

        restored = pipeline._restore_protected(text, placeholders)

        assert "[name]" in restored
        assert "<b>" in restored

    def test_split_into_chunks_small(self):
        """Test that small text is not split."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
            max_chars_per_chunk=100,
        )
        pipeline = TranslationPipeline(config)

        text = "Short text"
        chunks = pipeline._split_into_chunks(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_into_chunks_large(self):
        """Test that large text is split."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
            max_chars_per_chunk=50,
        )
        pipeline = TranslationPipeline(config)

        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph."
        chunks = pipeline._split_into_chunks(text)

        assert len(chunks) > 1

    def test_split_by_sentences(self):
        """Test splitting by sentences."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        text = "First sentence. Second sentence! Third sentence?"
        chunks = pipeline._split_by_sentences(text, 30)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_translate_empty_text(self):
        """Test translation of empty text."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        result = await pipeline.translate("")

        assert result.translated_text == ""
        assert result.source_text == ""

    @pytest.mark.asyncio
    async def test_translate_whitespace_only(self):
        """Test translation of whitespace-only text."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        result = await pipeline.translate("   ")

        assert result.translated_text == "   "

    @pytest.mark.asyncio
    async def test_translate_with_echo_provider(self):
        """Test translation with echo provider (returns same text)."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        text = "Hello world"
        result = await pipeline.translate(text)

        assert result.source_text == text
        assert result.translated_text == text
        assert result.provider == "echo"

    @pytest.mark.asyncio
    async def test_translate_with_progress_callback(self):
        """Test translation with progress callback."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        progress_updates = []

        def callback(progress):
            progress_updates.append(progress.percent_complete)

        text = "Hello world"
        await pipeline.translate(text, progress_callback=callback)

        assert len(progress_updates) > 0
        assert progress_updates[-1] == 100.0

    @pytest.mark.asyncio
    async def test_translate_batch(self):
        """Test batch translation."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        texts = ["Hello", "World", "Test"]
        results = await pipeline.translate_batch(texts)

        assert len(results) == 3
        assert results[0].translated_text == "Hello"
        assert results[1].translated_text == "World"
        assert results[2].translated_text == "Test"

    @pytest.mark.asyncio
    async def test_translate_stream(self):
        """Test streaming translation."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
            max_chars_per_chunk=50,
        )
        pipeline = TranslationPipeline(config)

        text = "First chunk here.\n\nSecond chunk here."
        chunks = []

        async for chunk in pipeline.translate_stream(text):
            chunks.append(chunk)

        assert len(chunks) >= 1

    def test_add_glossary_term(self):
        """Test adding a glossary term."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        pipeline.add_glossary_term("source", "target", persist=False)

        glossary = pipeline.get_glossary_dict()
        assert "source" in glossary
        assert glossary["source"] == "target"

    def test_get_glossary_dict(self):
        """Test getting glossary as dictionary."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        pipeline.add_glossary_term("term1", "translation1", persist=False)
        pipeline.add_glossary_term("term2", "translation2", persist=False)

        glossary = pipeline.get_glossary_dict()

        assert len(glossary) == 2
        assert glossary["term1"] == "translation1"
        assert glossary["term2"] == "translation2"


class TestTranslateTextFunction:
    """Test the convenience translate_text function."""

    @pytest.mark.asyncio
    async def test_translate_text_basic(self):
        """Test basic translation."""
        result = await translate_text("Hello", provider_name="echo")
        assert result == "Hello"

    @pytest.mark.asyncio
    async def test_translate_text_with_languages(self):
        """Test translation with language specification."""
        result = await translate_text(
            "Test",
            source_lang="en",
            target_lang="fr",
            provider_name="echo",
        )
        assert result == "Test"


class TestProtectedPatterns:
    """Test protected pattern handling."""

    def test_url_protection(self):
        """Test that URLs are protected."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        text = "Visit https://example.com for more info"
        protected, placeholders = pipeline._protect_text(text)

        assert "https://example.com" not in protected
        assert any("https://example.com" in v for v in placeholders.values())

    def test_html_tag_protection(self):
        """Test that HTML tags are protected."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        text = "This is <strong>bold</strong> text"
        protected, placeholders = pipeline._protect_text(text)

        assert "<strong>" not in protected
        assert "</strong>" not in protected

    def test_square_bracket_protection(self):
        """Test that square brackets are protected."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        text = "The [character name] said hello"
        protected, placeholders = pipeline._protect_text(text)

        assert "[character name]" not in protected

    def test_curly_bracket_protection(self):
        """Test that curly brackets are protected."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
        )
        pipeline = TranslationPipeline(config)

        text = "Template {variable} here"
        protected, placeholders = pipeline._protect_text(text)

        assert "{variable}" not in protected

    def test_no_protected_patterns(self):
        """Test with no protected patterns."""
        config = TranslationConfig(
            provider_name="echo",
            use_glossary_db=False,
            protected_patterns=[],
        )
        pipeline = TranslationPipeline(config)

        text = "Visit https://example.com"
        protected, placeholders = pipeline._protect_text(text)

        assert protected == text
        assert len(placeholders) == 0
