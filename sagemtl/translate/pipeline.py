"""
Translation pipeline that integrates providers, glossary, and text processing.

This module provides a high-level interface for translating text with:
- Multi-provider support (Argos, Google, DeepL, Azure)
- Glossary protection and application
- Batch processing
- Progress callbacks
- Text chunking for large content
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import (
    AsyncIterator, Callable, Dict, List, Optional, Tuple, Union
)
from pathlib import Path

from .providers import (
    TranslationProvider,
    TranslationResult,
    ProviderRegistry,
    EchoProvider,
    get_provider,
    NotConfigured,
)
from .glossary import GlossaryEntry, apply_glossary, load_glossary
from .glossary_db import GlossaryDB, get_glossary_db

logger = logging.getLogger(__name__)


@dataclass
class TranslationConfig:
    """Configuration for translation pipeline."""
    provider_name: str = "echo"
    source_lang: str = "zh"
    target_lang: str = "en"
    # Glossary settings
    glossary_path: Optional[str] = None
    use_glossary_db: bool = True
    novel_id: Optional[str] = None
    # Processing settings
    max_chars_per_chunk: int = 4000
    preserve_whitespace: bool = True
    preserve_paragraphs: bool = True
    # Protected patterns (won't be translated)
    protected_patterns: List[str] = field(default_factory=lambda: [
        r'\[.*?\]',  # Square brackets
        r'\{.*?\}',  # Curly brackets
        r'<.*?>',    # HTML tags
        r'https?://\S+',  # URLs
    ])


@dataclass
class TranslationProgress:
    """Progress tracking for translation."""
    total_chunks: int = 0
    completed_chunks: int = 0
    total_chars: int = 0
    translated_chars: int = 0
    current_chunk: Optional[str] = None
    errors: List[Tuple[int, str]] = field(default_factory=list)

    @property
    def percent_complete(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.completed_chunks / self.total_chunks) * 100


class TranslationPipeline:
    """
    High-level translation pipeline with glossary support.

    Example:
        pipeline = TranslationPipeline(TranslationConfig(
            provider_name="argos",
            source_lang="zh",
            target_lang="en",
            use_glossary_db=True,
            novel_id="my-novel-123"
        ))

        result = await pipeline.translate("这是一个测试")
        print(result.translated_text)
    """

    def __init__(self, config: TranslationConfig):
        self.config = config
        self._provider: Optional[TranslationProvider] = None
        self._glossary_entries: List[GlossaryEntry] = []
        self._glossary_db: Optional[GlossaryDB] = None
        self._protected_pattern: Optional[re.Pattern] = None
        self._init_pipeline()

    def _init_pipeline(self):
        """Initialize pipeline components."""
        # Initialize provider
        self._provider = get_provider(self.config.provider_name)

        # Compile protected patterns
        if self.config.protected_patterns:
            combined = '|'.join(f'({p})' for p in self.config.protected_patterns)
            self._protected_pattern = re.compile(combined)

        # Load glossary
        self._load_glossary()

    def _load_glossary(self):
        """Load glossary entries from file and/or database."""
        self._glossary_entries = []

        # Load from file if specified
        if self.config.glossary_path:
            file_entries = load_glossary(self.config.glossary_path)
            self._glossary_entries.extend(file_entries)

        # Load from database if enabled
        if self.config.use_glossary_db:
            try:
                self._glossary_db = get_glossary_db()
                db_entries = self._glossary_db.get_all_entries(
                    novel_id=self.config.novel_id
                )
                # Convert to simple GlossaryEntry
                for e in db_entries:
                    self._glossary_entries.append(GlossaryEntry(
                        source=e.source,
                        target=e.target,
                        case_sensitive=e.case_sensitive,
                        word_boundary=e.word_boundary,
                        notes=e.notes,
                    ))
            except Exception as e:
                logger.warning(f"Failed to load glossary from database: {e}")

    def _protect_text(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Replace protected patterns with placeholders.

        Args:
            text: Original text

        Returns:
            Tuple of (modified text, placeholder mapping)
        """
        if not self._protected_pattern:
            return text, {}

        placeholders: Dict[str, str] = {}
        counter = 0

        def replace(match):
            nonlocal counter
            placeholder = f"__PROTECTED_{counter}__"
            placeholders[placeholder] = match.group(0)
            counter += 1
            return placeholder

        protected_text = self._protected_pattern.sub(replace, text)
        return protected_text, placeholders

    def _restore_protected(self, text: str, placeholders: Dict[str, str]) -> str:
        """Restore protected content from placeholders."""
        result = text
        for placeholder, original in placeholders.items():
            result = result.replace(placeholder, original)
        return result

    def _protect_glossary(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Protect glossary terms before translation.

        This replaces source terms with placeholders so they're not translated,
        then restores them with target terms after translation.

        Args:
            text: Original text

        Returns:
            Tuple of (modified text, term mapping)
        """
        term_mapping: Dict[str, str] = {}
        result = text
        counter = 0

        # Sort by length (longer first) to avoid partial matches
        sorted_entries = sorted(
            self._glossary_entries,
            key=lambda e: len(e.source),
            reverse=True
        )

        for entry in sorted_entries:
            if not entry.source or not entry.target:
                continue

            if entry.word_boundary:
                pattern = r'\b' + re.escape(entry.source) + r'\b'
            else:
                pattern = re.escape(entry.source)

            flags = 0 if entry.case_sensitive else re.IGNORECASE

            # Find all matches
            for match in re.finditer(pattern, result, flags):
                placeholder = f"__TERM_{counter}__"
                term_mapping[placeholder] = entry.target
                counter += 1

            # Replace with placeholders
            if entry.word_boundary:
                result = re.sub(pattern, f"__TERM_{counter - 1}__", result, flags=flags)
            else:
                if entry.case_sensitive:
                    result = result.replace(entry.source, f"__TERM_{counter - 1}__", 1)
                else:
                    result = re.sub(pattern, f"__TERM_{counter - 1}__", result, count=1, flags=flags)

        return result, term_mapping

    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks for translation.

        Respects paragraph boundaries when possible.
        """
        max_chars = self.config.max_chars_per_chunk

        if len(text) <= max_chars:
            return [text]

        chunks = []

        if self.config.preserve_paragraphs:
            # Split by paragraphs first
            paragraphs = re.split(r'\n\s*\n', text)
            current_chunk = ""

            for para in paragraphs:
                if len(current_chunk) + len(para) + 2 <= max_chars:
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    # If single paragraph is too long, split by sentences
                    if len(para) > max_chars:
                        chunks.extend(self._split_by_sentences(para, max_chars))
                        current_chunk = ""
                    else:
                        current_chunk = para

            if current_chunk:
                chunks.append(current_chunk)
        else:
            chunks = self._split_by_sentences(text, max_chars)

        return chunks

    def _split_by_sentences(self, text: str, max_chars: int) -> List[str]:
        """Split text by sentences."""
        # Common sentence endings
        sentence_pattern = r'([。！？.!?])\s*'
        sentences = re.split(sentence_pattern, text)

        # Recombine sentences with their punctuation
        combined = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                combined.append(sentences[i] + sentences[i + 1])
            else:
                combined.append(sentences[i])
        if len(sentences) % 2 == 1 and sentences[-1]:
            combined.append(sentences[-1])

        # Group into chunks
        chunks = []
        current_chunk = ""

        for sentence in combined:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If single sentence is too long, just include it
                if len(sentence) > max_chars:
                    chunks.append(sentence)
                    current_chunk = ""
                else:
                    current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def translate(
        self,
        text: str,
        progress_callback: Optional[Callable[[TranslationProgress], None]] = None,
    ) -> TranslationResult:
        """
        Translate text using the configured pipeline.

        Args:
            text: Text to translate
            progress_callback: Optional callback for progress updates

        Returns:
            TranslationResult with translated text
        """
        if not text.strip():
            return TranslationResult(
                source_text=text,
                translated_text=text,
                source_language=self.config.source_lang,
                target_language=self.config.target_lang,
                provider=self.config.provider_name,
            )

        # Check provider availability
        if not self._provider or not self._provider.is_available():
            raise NotConfigured(f"Provider '{self.config.provider_name}' is not available")

        # Split into chunks
        chunks = self._split_into_chunks(text)

        progress = TranslationProgress(
            total_chunks=len(chunks),
            total_chars=len(text),
        )

        translated_chunks = []

        for i, chunk in enumerate(chunks):
            progress.current_chunk = chunk[:50] + "..." if len(chunk) > 50 else chunk

            try:
                # Protect patterns
                protected_chunk, pattern_placeholders = self._protect_text(chunk)

                # Translate
                result = await self._provider.translate(
                    protected_chunk,
                    self.config.source_lang,
                    self.config.target_lang,
                )

                translated = result.translated_text

                # Restore protected patterns
                translated = self._restore_protected(translated, pattern_placeholders)

                # Apply glossary post-processing
                if self._glossary_entries:
                    translated = apply_glossary(translated, self._glossary_entries)

                translated_chunks.append(translated)
                progress.translated_chars += len(translated)

            except Exception as e:
                logger.error(f"Translation error on chunk {i}: {e}")
                progress.errors.append((i, str(e)))
                # Keep original on error
                translated_chunks.append(chunk)

            progress.completed_chunks += 1

            if progress_callback:
                progress_callback(progress)

        # Combine chunks
        if self.config.preserve_paragraphs:
            final_text = "\n\n".join(translated_chunks)
        else:
            final_text = "".join(translated_chunks)

        return TranslationResult(
            source_text=text,
            translated_text=final_text,
            source_language=self.config.source_lang,
            target_language=self.config.target_lang,
            provider=self.config.provider_name,
        )

    async def translate_batch(
        self,
        texts: List[str],
        progress_callback: Optional[Callable[[TranslationProgress], None]] = None,
    ) -> List[TranslationResult]:
        """
        Translate multiple texts.

        Args:
            texts: List of texts to translate
            progress_callback: Optional callback for progress updates

        Returns:
            List of TranslationResult objects
        """
        results = []

        total_chars = sum(len(t) for t in texts)
        progress = TranslationProgress(
            total_chunks=len(texts),
            total_chars=total_chars,
        )

        for i, text in enumerate(texts):
            result = await self.translate(text)
            results.append(result)

            progress.completed_chunks += 1
            progress.translated_chars += len(result.translated_text)

            if progress_callback:
                progress_callback(progress)

        return results

    async def translate_stream(
        self,
        text: str,
    ) -> AsyncIterator[str]:
        """
        Stream translation output chunk by chunk.

        Args:
            text: Text to translate

        Yields:
            Translated chunks as they complete
        """
        chunks = self._split_into_chunks(text)

        for chunk in chunks:
            # Protect patterns
            protected_chunk, pattern_placeholders = self._protect_text(chunk)

            # Translate
            result = await self._provider.translate(
                protected_chunk,
                self.config.source_lang,
                self.config.target_lang,
            )

            translated = result.translated_text

            # Restore protected patterns
            translated = self._restore_protected(translated, pattern_placeholders)

            # Apply glossary
            if self._glossary_entries:
                translated = apply_glossary(translated, self._glossary_entries)

            yield translated

    def add_glossary_term(
        self,
        source: str,
        target: str,
        category: str = "general",
        persist: bool = True,
    ):
        """
        Add a glossary term to the pipeline.

        Args:
            source: Source term
            target: Target translation
            category: Category for organization
            persist: Save to database
        """
        entry = GlossaryEntry(source=source, target=target)
        self._glossary_entries.append(entry)

        if persist and self._glossary_db:
            from .glossary_db import GlossaryEntryDB
            db_entry = GlossaryEntryDB(
                source=source,
                target=target,
                category=category,
                novel_id=self.config.novel_id,
            )
            self._glossary_db.add_entry(db_entry)

    def get_glossary_dict(self) -> Dict[str, str]:
        """Get glossary as a simple dictionary."""
        return {e.source: e.target for e in self._glossary_entries}


# Convenience function for quick translation
async def translate_text(
    text: str,
    source_lang: str = "zh",
    target_lang: str = "en",
    provider_name: str = "echo",
    glossary_path: Optional[str] = None,
) -> str:
    """
    Quick translation function.

    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        provider_name: Translation provider
        glossary_path: Optional path to glossary file

    Returns:
        Translated text
    """
    config = TranslationConfig(
        provider_name=provider_name,
        source_lang=source_lang,
        target_lang=target_lang,
        glossary_path=glossary_path,
        use_glossary_db=False,
    )

    pipeline = TranslationPipeline(config)
    result = await pipeline.translate(text)
    return result.translated_text
