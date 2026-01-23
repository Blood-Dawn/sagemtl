# Translation Pipeline Specification

## Overview

The translation pipeline converts raw machine-translated text or foreign-language text into clean, readable English. It supports both real-time (streaming) and batch translation modes. A critical feature is the glossary system that maintains consistent terminology across translations.

---

## Architecture

### Pipeline Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Translation Pipeline                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   │
│  │  Raw Text   │──►│ Pre-Process │──►│  Translate  │──►│Post-Process │   │
│  │  (Foreign)  │   │ • Clean     │   │ • Argos     │   │ • Glossary  │   │
│  └─────────────┘   │ • Glossary  │   │ • Google    │   │ • Format    │   │
│                    │   Protect   │   │ • DeepL     │   │ • Polish    │   │
│                    └─────────────┘   │ • Azure     │   └──────┬──────┘   │
│                                      └─────────────┘          │          │
│                                                               ▼          │
│                                                      ┌─────────────┐     │
│                                                      │Clean English│     │
│                                                      └─────────────┘     │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Translation Module                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │ ProviderRegistry │    │  TranslationJob  │                       │
│  │ (Plugin System)  │    │  (Queue/Batch)   │                       │
│  └────────┬─────────┘    └──────────────────┘                       │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                   Translation Providers                   │       │
│  ├──────────────┬──────────────┬──────────────┬─────────────┤       │
│  │ ArgosProvider│GoogleProvider│DeepLProvider │AzureProvider│       │
│  │ (Offline)    │ (Cloud API)  │ (Cloud API)  │(Cloud API)  │       │
│  └──────────────┴──────────────┴──────────────┴─────────────┘       │
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │   GlossaryDB     │    │  AutoGlossary    │                       │
│  │   (SQLite)       │    │  (NER + Freq)    │                       │
│  └──────────────────┘    └──────────────────┘                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Translation Provider Protocol

```python
# Location: sagemtl/translate/providers.py

from typing import Protocol, Optional, List, Dict, AsyncIterator
from dataclasses import dataclass
from enum import Enum

class LanguageCode(str, Enum):
    """Supported language codes."""
    CHINESE_SIMPLIFIED = "zh"
    CHINESE_TRADITIONAL = "zh-TW"
    JAPANESE = "ja"
    KOREAN = "ko"
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    RUSSIAN = "ru"


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    confidence: Optional[float] = None
    alternatives: Optional[List[str]] = None


@dataclass
class ProviderCapabilities:
    """Capabilities of a translation provider."""
    max_chars_per_request: int
    supports_batch: bool
    supports_glossary: bool
    supports_formality: bool
    supported_languages: List[str]
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_month: Optional[int] = None


class TranslationProvider(Protocol):
    """Protocol for translation providers."""

    # Provider identification
    name: str
    is_online: bool  # True for API-based, False for offline

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        ...

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        """Translate a single text string."""
        ...

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """Translate multiple texts in a batch."""
        ...

    async def translate_stream(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> AsyncIterator[str]:
        """Stream translation output (if supported)."""
        ...

    def is_available(self) -> bool:
        """Check if provider is available (API key configured, models loaded, etc.)."""
        ...

    async def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        ...
```

### 2. Provider Registry

```python
# Location: sagemtl/translate/provider_registry.py

from typing import Dict, Optional, Type, List
import logging

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for translation providers."""

    _providers: Dict[str, Type[TranslationProvider]] = {}
    _instances: Dict[str, TranslationProvider] = {}
    _default_provider: Optional[str] = None

    @classmethod
    def register(cls, name: str, provider_class: Type[TranslationProvider]):
        """Register a provider class."""
        cls._providers[name] = provider_class

    @classmethod
    def get_provider(cls, name: str) -> Optional[TranslationProvider]:
        """Get a provider instance by name."""
        if name not in cls._instances:
            if name not in cls._providers:
                return None
            cls._instances[name] = cls._providers[name]()
        return cls._instances[name]

    @classmethod
    def get_default(cls) -> Optional[TranslationProvider]:
        """Get the default provider."""
        if cls._default_provider:
            return cls.get_provider(cls._default_provider)
        # Fall back to first available
        for name in cls._providers:
            provider = cls.get_provider(name)
            if provider and provider.is_available():
                return provider
        return None

    @classmethod
    def set_default(cls, name: str):
        """Set the default provider."""
        cls._default_provider = name

    @classmethod
    def list_providers(cls) -> List[Dict]:
        """List all registered providers with their status."""
        result = []
        for name, provider_class in cls._providers.items():
            provider = cls.get_provider(name)
            result.append({
                'name': name,
                'is_online': provider_class.is_online if hasattr(provider_class, 'is_online') else True,
                'is_available': provider.is_available() if provider else False,
                'capabilities': provider.capabilities if provider else None,
            })
        return result
```

### 3. Argos Provider (Offline)

```python
# Location: sagemtl/translate/argos_provider.py

import argostranslate.package
import argostranslate.translate
from typing import List, Dict, Optional, AsyncIterator
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ArgosProvider:
    """Offline translation using Argos Translate."""

    name = "argos"
    is_online = False

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._installed_packages = set()
        self._refresh_packages()

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            max_chars_per_request=10000,  # Soft limit for memory
            supports_batch=True,
            supports_glossary=False,  # We handle via pre/post processing
            supports_formality=False,
            supported_languages=self._get_supported_languages(),
            rate_limit_per_minute=None,  # No rate limit for offline
        )

    def _refresh_packages(self):
        """Refresh list of installed language packages."""
        argostranslate.package.update_package_index()
        installed = argostranslate.package.get_installed_packages()
        self._installed_packages = {
            (pkg.from_code, pkg.to_code) for pkg in installed
        }

    def _get_supported_languages(self) -> List[str]:
        """Get list of languages we can translate."""
        languages = set()
        for from_code, to_code in self._installed_packages:
            languages.add(from_code)
            languages.add(to_code)
        return list(languages)

    def is_available(self) -> bool:
        """Check if Argos is available with at least one language pair."""
        return len(self._installed_packages) > 0

    async def ensure_language_pair(self, source: str, target: str) -> bool:
        """Ensure the language pair is installed, download if needed."""
        if (source, target) in self._installed_packages:
            return True

        # Try to download
        try:
            argostranslate.package.update_package_index()
            available = argostranslate.package.get_available_packages()

            package = next(
                (p for p in available
                 if p.from_code == source and p.to_code == target),
                None
            )

            if package:
                argostranslate.package.install_from_path(package.download())
                self._refresh_packages()
                return True

        except Exception as e:
            logger.error(f"Failed to install language pair {source}->{target}: {e}")

        return False

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        """Translate text using Argos."""
        # Ensure language pair is available
        if not await self.ensure_language_pair(source_lang, target_lang):
            raise ValueError(f"Language pair {source_lang}->{target_lang} not available")

        # Run translation in thread pool (Argos is synchronous)
        loop = asyncio.get_event_loop()
        translated = await loop.run_in_executor(
            self._executor,
            self._translate_sync,
            text, source_lang, target_lang
        )

        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            provider=self.name,
        )

    def _translate_sync(self, text: str, source: str, target: str) -> str:
        """Synchronous translation (runs in thread pool)."""
        return argostranslate.translate.translate(text, source, target)

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """Translate multiple texts."""
        # For Argos, we translate one at a time but concurrently
        tasks = [
            self.translate(text, source_lang, target_lang, glossary)
            for text in texts
        ]
        return await asyncio.gather(*tasks)

    async def translate_stream(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> AsyncIterator[str]:
        """Argos doesn't support streaming, so we yield the full result."""
        result = await self.translate(text, source_lang, target_lang)
        yield result.translated_text


# Register provider
ProviderRegistry.register("argos", ArgosProvider)
```

### 4. Google Cloud Translation Provider

```python
# Location: sagemtl/translate/google_provider.py

from google.cloud import translate_v3 as translate
from typing import List, Dict, Optional, AsyncIterator
import os
import asyncio

class GoogleTranslateProvider:
    """Translation using Google Cloud Translation API v3."""

    name = "google"
    is_online = True

    def __init__(self):
        self._client = None
        self._project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY")
        self._location = "global"
        self._glossary_id = None

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            max_chars_per_request=5000,
            supports_batch=True,
            supports_glossary=True,  # Google supports glossaries!
            supports_formality=False,
            supported_languages=self._get_supported_languages(),
            rate_limit_per_minute=600000,  # 600k chars/min
            rate_limit_per_month=500000,   # 500k chars free tier
        )

    def _get_client(self):
        if not self._client:
            self._client = translate.TranslationServiceClient()
        return self._client

    def _get_supported_languages(self) -> List[str]:
        # Google supports 130+ languages
        return ["zh", "zh-TW", "ja", "ko", "en", "es", "fr", "de", "ru", "pt", "it", "ar"]

    def is_available(self) -> bool:
        """Check if Google API is configured."""
        return bool(self._project_id or self._api_key)

    async def upload_glossary(
        self,
        glossary_entries: Dict[str, str],
        source_lang: str,
        target_lang: str,
        glossary_name: str = "sagemtl-glossary",
    ):
        """Upload a glossary to Google Cloud for consistent translations."""
        client = self._get_client()
        parent = f"projects/{self._project_id}/locations/{self._location}"

        # Create glossary CSV in memory
        import io
        csv_content = io.StringIO()
        csv_content.write(f"{source_lang},{target_lang}\n")
        for source, target in glossary_entries.items():
            csv_content.write(f"{source},{target}\n")

        # This is simplified - real implementation would use GCS bucket
        # For now, we'll use inline glossary in translate requests

        self._glossary_id = glossary_name

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        """Translate using Google Cloud API."""
        client = self._get_client()
        parent = f"projects/{self._project_id}/locations/{self._location}"

        request = translate.TranslateTextRequest(
            parent=parent,
            contents=[text],
            source_language_code=source_lang,
            target_language_code=target_lang,
            mime_type="text/plain",
        )

        # Add glossary if configured
        if self._glossary_id:
            glossary_path = f"{parent}/glossaries/{self._glossary_id}"
            request.glossary_config = translate.TranslateTextGlossaryConfig(
                glossary=glossary_path
            )

        # Run in thread pool (client is synchronous)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            client.translate_text,
            request
        )

        translated = response.translations[0].translated_text

        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            provider=self.name,
        )

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """Translate multiple texts in a single API call."""
        client = self._get_client()
        parent = f"projects/{self._project_id}/locations/{self._location}"

        request = translate.TranslateTextRequest(
            parent=parent,
            contents=texts,
            source_language_code=source_lang,
            target_language_code=target_lang,
            mime_type="text/plain",
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            client.translate_text,
            request
        )

        return [
            TranslationResult(
                source_text=texts[i],
                translated_text=t.translated_text,
                source_language=source_lang,
                target_language=target_lang,
                provider=self.name,
            )
            for i, t in enumerate(response.translations)
        ]

    async def translate_stream(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> AsyncIterator[str]:
        """Google doesn't support streaming, yield full result."""
        result = await self.translate(text, source_lang, target_lang)
        yield result.translated_text


# Register provider
ProviderRegistry.register("google", GoogleTranslateProvider)
```

### 5. DeepL Provider

```python
# Location: sagemtl/translate/deepl_provider.py

import deepl
from typing import List, Dict, Optional, AsyncIterator
import os
import asyncio

class DeepLProvider:
    """Translation using DeepL API."""

    name = "deepl"
    is_online = True

    def __init__(self):
        self._api_key = os.environ.get("DEEPL_API_KEY")
        self._translator = None

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            max_chars_per_request=50000,
            supports_batch=True,
            supports_glossary=True,  # DeepL Pro supports glossaries
            supports_formality=True,  # DeepL supports formal/informal
            supported_languages=["zh", "ja", "ko", "en", "de", "fr", "es", "it", "pt", "ru", "pl", "nl"],
            rate_limit_per_minute=None,
            rate_limit_per_month=500000,  # Free tier limit
        )

    def _get_translator(self):
        if not self._translator and self._api_key:
            self._translator = deepl.Translator(self._api_key)
        return self._translator

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _convert_lang_code(self, code: str) -> str:
        """Convert our language codes to DeepL format."""
        mapping = {
            "zh": "ZH",
            "zh-TW": "ZH",
            "ja": "JA",
            "ko": "KO",
            "en": "EN-US",
            "de": "DE",
            "fr": "FR",
            "es": "ES",
        }
        return mapping.get(code, code.upper())

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        """Translate using DeepL."""
        translator = self._get_translator()
        if not translator:
            raise ValueError("DeepL API key not configured")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: translator.translate_text(
                text,
                source_lang=self._convert_lang_code(source_lang),
                target_lang=self._convert_lang_code(target_lang),
            )
        )

        return TranslationResult(
            source_text=text,
            translated_text=result.text,
            source_language=source_lang,
            target_language=target_lang,
            provider=self.name,
        )

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """Translate multiple texts."""
        translator = self._get_translator()
        if not translator:
            raise ValueError("DeepL API key not configured")

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: translator.translate_text(
                texts,
                source_lang=self._convert_lang_code(source_lang),
                target_lang=self._convert_lang_code(target_lang),
            )
        )

        return [
            TranslationResult(
                source_text=texts[i],
                translated_text=r.text,
                source_language=source_lang,
                target_language=target_lang,
                provider=self.name,
            )
            for i, r in enumerate(results)
        ]

    async def translate_stream(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> AsyncIterator[str]:
        result = await self.translate(text, source_lang, target_lang)
        yield result.translated_text


# Register provider
ProviderRegistry.register("deepl", DeepLProvider)
```

---

## Glossary System

### Database Schema

```sql
-- Location: ~/.sagemtl/glossary.db

-- Novels table for organizing glossaries
CREATE TABLE novels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    source_url TEXT,
    source_language TEXT DEFAULT 'zh',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Per-novel glossary entries
CREATE TABLE glossary_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL,
    source_term TEXT NOT NULL,
    target_term TEXT NOT NULL,
    term_type TEXT,  -- character, item, location, technique, title, etc.
    notes TEXT,
    confidence REAL DEFAULT 1.0,  -- 0.0 to 1.0
    auto_generated BOOLEAN DEFAULT FALSE,
    frequency INTEGER DEFAULT 0,  -- How often this term appears
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id),
    UNIQUE(novel_id, source_term)
);

-- Global glossary (applied to all novels)
CREATE TABLE global_glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_term TEXT NOT NULL UNIQUE,
    target_term TEXT NOT NULL,
    term_type TEXT,
    notes TEXT,
    category TEXT,  -- cultivation, wuxia, xianxia, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance
CREATE INDEX idx_glossary_novel ON glossary_entries(novel_id);
CREATE INDEX idx_glossary_source ON glossary_entries(source_term);
CREATE INDEX idx_glossary_type ON glossary_entries(term_type);
CREATE INDEX idx_global_source ON global_glossary(source_term);
CREATE INDEX idx_global_category ON global_glossary(category);
```

### Glossary Database Manager

```python
# Location: sagemtl/translate/glossary_db.py

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from contextlib import contextmanager
import json

@dataclass
class GlossaryEntry:
    """A single glossary entry."""
    id: Optional[int] = None
    novel_id: Optional[int] = None
    source_term: str = ""
    target_term: str = ""
    term_type: Optional[str] = None  # character, item, location, technique
    notes: Optional[str] = None
    confidence: float = 1.0
    auto_generated: bool = False
    frequency: int = 0


class GlossaryDB:
    """SQLite-based glossary storage."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".sagemtl" / "glossary.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS novels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT,
                    source_url TEXT,
                    source_language TEXT DEFAULT 'zh',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS glossary_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    novel_id INTEGER NOT NULL,
                    source_term TEXT NOT NULL,
                    target_term TEXT NOT NULL,
                    term_type TEXT,
                    notes TEXT,
                    confidence REAL DEFAULT 1.0,
                    auto_generated BOOLEAN DEFAULT FALSE,
                    frequency INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (novel_id) REFERENCES novels(id),
                    UNIQUE(novel_id, source_term)
                );

                CREATE TABLE IF NOT EXISTS global_glossary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_term TEXT NOT NULL UNIQUE,
                    target_term TEXT NOT NULL,
                    term_type TEXT,
                    notes TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_glossary_novel
                    ON glossary_entries(novel_id);
                CREATE INDEX IF NOT EXISTS idx_glossary_source
                    ON glossary_entries(source_term);
            """)

    # --- Novel Management ---

    def create_novel(self, title: str, author: Optional[str] = None,
                     source_url: Optional[str] = None,
                     source_language: str = "zh") -> int:
        """Create a new novel entry, return its ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO novels (title, author, source_url, source_language)
                   VALUES (?, ?, ?, ?)""",
                (title, author, source_url, source_language)
            )
            return cursor.lastrowid

    def get_novel(self, novel_id: int) -> Optional[Dict]:
        """Get novel by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM novels WHERE id = ?", (novel_id,)
            ).fetchone()
            return dict(row) if row else None

    def find_novel_by_title(self, title: str) -> Optional[int]:
        """Find novel ID by title."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM novels WHERE title = ?", (title,)
            ).fetchone()
            return row['id'] if row else None

    # --- Glossary Entries ---

    def add_entry(self, novel_id: int, entry: GlossaryEntry) -> int:
        """Add a glossary entry."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO glossary_entries
                   (novel_id, source_term, target_term, term_type, notes,
                    confidence, auto_generated, frequency)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (novel_id, entry.source_term, entry.target_term, entry.term_type,
                 entry.notes, entry.confidence, entry.auto_generated, entry.frequency)
            )
            return cursor.lastrowid

    def add_entries_batch(self, novel_id: int, entries: List[GlossaryEntry]):
        """Add multiple entries at once."""
        with self._get_connection() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO glossary_entries
                   (novel_id, source_term, target_term, term_type, notes,
                    confidence, auto_generated, frequency)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [(novel_id, e.source_term, e.target_term, e.term_type,
                  e.notes, e.confidence, e.auto_generated, e.frequency)
                 for e in entries]
            )

    def get_entries(self, novel_id: int,
                    include_auto: bool = True) -> List[GlossaryEntry]:
        """Get all entries for a novel."""
        with self._get_connection() as conn:
            query = "SELECT * FROM glossary_entries WHERE novel_id = ?"
            if not include_auto:
                query += " AND auto_generated = FALSE"
            query += " ORDER BY frequency DESC, source_term"

            rows = conn.execute(query, (novel_id,)).fetchall()
            return [GlossaryEntry(**dict(row)) for row in rows]

    def get_glossary_dict(self, novel_id: int,
                          include_global: bool = True) -> Dict[str, str]:
        """Get glossary as a simple dict for translation."""
        glossary = {}

        # Add novel-specific entries
        for entry in self.get_entries(novel_id):
            glossary[entry.source_term] = entry.target_term

        # Add global entries (lower priority)
        if include_global:
            for entry in self.get_global_entries():
                if entry.source_term not in glossary:
                    glossary[entry.source_term] = entry.target_term

        return glossary

    def update_entry(self, entry_id: int, **kwargs):
        """Update a glossary entry."""
        valid_fields = {'target_term', 'term_type', 'notes', 'confidence', 'frequency'}
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}

        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [entry_id]

        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE glossary_entries SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )

    def delete_entry(self, entry_id: int):
        """Delete a glossary entry."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM glossary_entries WHERE id = ?", (entry_id,))

    # --- Global Glossary ---

    def add_global_entry(self, entry: GlossaryEntry, category: str = "general"):
        """Add a global glossary entry."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO global_glossary
                   (source_term, target_term, term_type, notes, category)
                   VALUES (?, ?, ?, ?, ?)""",
                (entry.source_term, entry.target_term, entry.term_type,
                 entry.notes, category)
            )

    def get_global_entries(self, category: Optional[str] = None) -> List[GlossaryEntry]:
        """Get global glossary entries."""
        with self._get_connection() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM global_glossary WHERE category = ?",
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM global_glossary").fetchall()

            return [GlossaryEntry(
                source_term=row['source_term'],
                target_term=row['target_term'],
                term_type=row['term_type'],
                notes=row['notes'],
            ) for row in rows]

    # --- Import/Export ---

    def export_to_csv(self, novel_id: int, output_path: Path):
        """Export glossary to CSV."""
        import csv
        entries = self.get_entries(novel_id)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['source', 'target', 'type', 'notes'])
            for entry in entries:
                writer.writerow([
                    entry.source_term,
                    entry.target_term,
                    entry.term_type or '',
                    entry.notes or ''
                ])

    def import_from_csv(self, novel_id: int, input_path: Path):
        """Import glossary from CSV."""
        import csv
        entries = []

        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(GlossaryEntry(
                    source_term=row.get('source', row.get('source_term', '')),
                    target_term=row.get('target', row.get('target_term', '')),
                    term_type=row.get('type', row.get('term_type')),
                    notes=row.get('notes'),
                ))

        self.add_entries_batch(novel_id, entries)

    def export_to_json(self, novel_id: int, output_path: Path):
        """Export glossary to JSON."""
        entries = self.get_entries(novel_id)
        data = [
            {
                'source': e.source_term,
                'target': e.target_term,
                'type': e.term_type,
                'notes': e.notes,
                'confidence': e.confidence,
            }
            for e in entries
        ]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_from_json(self, novel_id: int, input_path: Path):
        """Import glossary from JSON."""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        entries = [
            GlossaryEntry(
                source_term=item.get('source', item.get('source_term', '')),
                target_term=item.get('target', item.get('target_term', '')),
                term_type=item.get('type'),
                notes=item.get('notes'),
                confidence=item.get('confidence', 1.0),
            )
            for item in data
        ]

        self.add_entries_batch(novel_id, entries)
```

### Auto-Glossary Generator

```python
# Location: sagemtl/translate/auto_glossary.py

from typing import List, Dict, Tuple
from collections import Counter
import re
from dataclasses import dataclass

@dataclass
class GlossarySuggestion:
    """A suggested glossary entry."""
    source_term: str
    suggested_target: str
    term_type: str
    confidence: float
    frequency: int
    context_examples: List[str]


class AutoGlossaryGenerator:
    """Automatically generate glossary suggestions from text."""

    # Common patterns for Chinese/Japanese names
    NAME_PATTERNS = [
        r'[\u4e00-\u9fff]{2,4}',  # Chinese characters (2-4)
        r'[\u3040-\u309f\u30a0-\u30ff]{2,6}',  # Japanese hiragana/katakana
    ]

    # Common cultivation/wuxia terms
    COMMON_TERMS = {
        '灵石': ('Spirit Stone', 'item'),
        '丹药': ('Pill', 'item'),
        '阵法': ('Formation', 'technique'),
        '武技': ('Martial Art', 'technique'),
        '功法': ('Cultivation Method', 'technique'),
        '境界': ('Realm', 'rank'),
        '内力': ('Inner Force', 'power'),
        '真气': ('True Qi', 'power'),
        '剑气': ('Sword Qi', 'power'),
        '宗门': ('Sect', 'organization'),
        '长老': ('Elder', 'title'),
        '掌门': ('Sect Master', 'title'),
        '弟子': ('Disciple', 'title'),
    }

    def __init__(self):
        pass

    def analyze_text(self, text: str) -> List[GlossarySuggestion]:
        """Analyze text and generate glossary suggestions."""
        suggestions = []

        # Find potential names (capitalized in MTL or Chinese characters)
        names = self._extract_names(text)
        for name, frequency, examples in names:
            suggestions.append(GlossarySuggestion(
                source_term=name,
                suggested_target=name,  # Keep as-is for names
                term_type='character',
                confidence=0.7,
                frequency=frequency,
                context_examples=examples[:3],
            ))

        # Find common cultivation terms
        terms = self._find_common_terms(text)
        for term, (translation, term_type), frequency, examples in terms:
            suggestions.append(GlossarySuggestion(
                source_term=term,
                suggested_target=translation,
                term_type=term_type,
                confidence=0.9,  # Higher confidence for known terms
                frequency=frequency,
                context_examples=examples[:3],
            ))

        # Find repeated unusual words (potential terms)
        repeated = self._find_repeated_terms(text)
        for term, frequency, examples in repeated:
            if not any(s.source_term == term for s in suggestions):
                suggestions.append(GlossarySuggestion(
                    source_term=term,
                    suggested_target='',  # Unknown translation
                    term_type='unknown',
                    confidence=0.5,
                    frequency=frequency,
                    context_examples=examples[:3],
                ))

        # Sort by frequency
        suggestions.sort(key=lambda x: -x.frequency)

        return suggestions

    def _extract_names(self, text: str) -> List[Tuple[str, int, List[str]]]:
        """Extract potential character names."""
        results = []

        # Find capitalized words that might be names
        # Pattern: Two or more capitalized words together (e.g., "Xiao Ming")
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        matches = re.findall(name_pattern, text)
        counter = Counter(matches)

        for name, count in counter.most_common(50):
            if count >= 3:  # Must appear at least 3 times
                # Find context examples
                examples = self._find_context(text, name)
                results.append((name, count, examples))

        return results

    def _find_common_terms(self, text: str) -> List[Tuple[str, Tuple[str, str], int, List[str]]]:
        """Find known cultivation/wuxia terms."""
        results = []

        for term, (translation, term_type) in self.COMMON_TERMS.items():
            count = text.count(term)
            if count > 0:
                examples = self._find_context(text, term)
                results.append((term, (translation, term_type), count, examples))

        return results

    def _find_repeated_terms(self, text: str, min_freq: int = 5) -> List[Tuple[str, int, List[str]]]:
        """Find repeated unusual words that might be terms."""
        results = []

        # Find words that repeat but aren't common English
        word_pattern = r'\b([A-Za-z]{4,})\b'
        matches = re.findall(word_pattern, text)
        counter = Counter(matches)

        # Filter common English words
        common_words = {'that', 'this', 'with', 'have', 'from', 'they', 'been',
                       'were', 'said', 'each', 'which', 'their', 'will', 'would',
                       'could', 'about', 'there', 'these', 'other', 'into', 'more'}

        for word, count in counter.most_common(100):
            if count >= min_freq and word.lower() not in common_words:
                # Check if it looks like a proper noun or term
                if word[0].isupper() or word.isupper():
                    examples = self._find_context(text, word)
                    results.append((word, count, examples))

        return results

    def _find_context(self, text: str, term: str, window: int = 50) -> List[str]:
        """Find context examples for a term."""
        examples = []
        start = 0

        while True:
            idx = text.find(term, start)
            if idx == -1:
                break

            # Extract surrounding context
            ctx_start = max(0, idx - window)
            ctx_end = min(len(text), idx + len(term) + window)
            context = text[ctx_start:ctx_end].strip()

            # Clean up context
            context = ' '.join(context.split())
            if context:
                examples.append(context)

            start = idx + 1

            if len(examples) >= 5:
                break

        return examples
```

---

## Translation Pipeline

### Pre/Post Processing

```python
# Location: sagemtl/translate/pipeline.py

from typing import Optional, Dict, List
import re

class TranslationPipeline:
    """Complete translation pipeline with pre/post processing."""

    def __init__(
        self,
        provider: TranslationProvider,
        glossary_db: GlossaryDB,
        novel_id: int,
    ):
        self.provider = provider
        self.glossary_db = glossary_db
        self.novel_id = novel_id
        self._glossary_dict = None
        self._placeholders: Dict[str, str] = {}

    @property
    def glossary(self) -> Dict[str, str]:
        """Lazy-load glossary dict."""
        if self._glossary_dict is None:
            self._glossary_dict = self.glossary_db.get_glossary_dict(
                self.novel_id,
                include_global=True
            )
        return self._glossary_dict

    def refresh_glossary(self):
        """Refresh the glossary from database."""
        self._glossary_dict = None

    async def translate(
        self,
        text: str,
        source_lang: str = "zh",
        target_lang: str = "en",
    ) -> str:
        """Translate text through the full pipeline."""
        # Pre-processing
        processed_text = self._pre_process(text)

        # Protect glossary terms
        protected_text = self._protect_glossary_terms(processed_text)

        # Translate
        result = await self.provider.translate(
            protected_text,
            source_lang,
            target_lang,
            glossary=self.glossary if self.provider.capabilities.supports_glossary else None
        )

        # Restore protected terms
        restored_text = self._restore_protected_terms(result.translated_text)

        # Post-processing
        final_text = self._post_process(restored_text)

        return final_text

    async def translate_chapters(
        self,
        chapters: List[str],
        source_lang: str = "zh",
        target_lang: str = "en",
        progress_callback=None,
    ) -> List[str]:
        """Translate multiple chapters with progress tracking."""
        results = []

        for i, chapter in enumerate(chapters):
            translated = await self.translate(chapter, source_lang, target_lang)
            results.append(translated)

            if progress_callback:
                progress_callback(i + 1, len(chapters))

        return results

    def _pre_process(self, text: str) -> str:
        """Pre-process text before translation."""
        # Normalize whitespace
        text = ' '.join(text.split())

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Normalize dashes
        text = text.replace('—', '--').replace('–', '-')

        return text

    def _protect_glossary_terms(self, text: str) -> str:
        """Replace glossary terms with placeholders."""
        self._placeholders = {}

        # Sort by length (longer first) to avoid partial replacements
        sorted_terms = sorted(self.glossary.keys(), key=len, reverse=True)

        for i, term in enumerate(sorted_terms):
            placeholder = f"__TERM_{i:04d}__"
            if term in text:
                self._placeholders[placeholder] = self.glossary[term]
                text = text.replace(term, placeholder)

        return text

    def _restore_protected_terms(self, text: str) -> str:
        """Restore protected terms with their translations."""
        for placeholder, translation in self._placeholders.items():
            text = text.replace(placeholder, translation)
        return text

    def _post_process(self, text: str) -> str:
        """Post-process translated text."""
        # Fix common MTL issues

        # Fix double spaces
        text = re.sub(r' +', ' ', text)

        # Fix punctuation spacing
        text = re.sub(r' ([.,!?;:])', r'\1', text)

        # Capitalize after periods
        text = re.sub(r'(?<=\. )([a-z])', lambda m: m.group(1).upper(), text)

        # Fix quotes
        text = text.replace(' "', '"').replace('" ', '" ')

        return text.strip()
```

---

## Configuration

```toml
# config.toml - Translation section

[translation]
# Default provider
default_provider = "argos"  # argos, google, deepl, azure

# Language settings
source_language = "zh"
target_language = "en"

# Processing
chunk_size = 4000          # Max characters per translation call
batch_size = 10            # Chapters per batch

# Glossary
auto_generate_glossary = true
min_term_frequency = 3
include_global_glossary = true

# API keys (can also be set via environment variables)
# google_api_key = ""
# deepl_api_key = ""
# azure_api_key = ""

[translation.argos]
# Argos-specific settings
max_concurrent = 2
download_models_on_start = true

[translation.google]
# Google-specific settings
project_id = ""
location = "global"
use_glossary_api = true

[translation.deepl]
# DeepL-specific settings
formality = "default"  # default, more, less
```

---

## Error Handling

```python
class TranslationError(Exception):
    """Base exception for translation errors."""
    pass

class ProviderNotAvailableError(TranslationError):
    """Provider is not available (API key missing, etc.)."""
    pass

class LanguageNotSupportedError(TranslationError):
    """Language pair not supported by provider."""
    pass

class RateLimitError(TranslationError):
    """Rate limit exceeded."""
    pass

class QuotaExceededError(TranslationError):
    """Monthly/daily quota exceeded."""
    pass

class GlossaryError(TranslationError):
    """Error with glossary operations."""
    pass
```

---

## Testing

```python
# Location: tests/test_translation_pipeline.py

import pytest
import asyncio
from sagemtl.translate import ProviderRegistry, ArgosProvider
from sagemtl.translate.glossary_db import GlossaryDB, GlossaryEntry
from sagemtl.translate.pipeline import TranslationPipeline

@pytest.fixture
def glossary_db(tmp_path):
    return GlossaryDB(tmp_path / "test_glossary.db")

@pytest.fixture
def novel_id(glossary_db):
    return glossary_db.create_novel("Test Novel")

@pytest.mark.asyncio
async def test_argos_basic_translation():
    """Test basic Argos translation."""
    provider = ArgosProvider()
    if not provider.is_available():
        pytest.skip("Argos not available")

    result = await provider.translate(
        "你好世界",
        source_lang="zh",
        target_lang="en"
    )

    assert result.translated_text
    assert "hello" in result.translated_text.lower() or "world" in result.translated_text.lower()

@pytest.mark.asyncio
async def test_glossary_protection(glossary_db, novel_id):
    """Test that glossary terms are protected during translation."""
    # Add glossary entry
    glossary_db.add_entry(novel_id, GlossaryEntry(
        source_term="灵石",
        target_term="Spirit Stone",
    ))

    provider = ArgosProvider()
    if not provider.is_available():
        pytest.skip("Argos not available")

    pipeline = TranslationPipeline(provider, glossary_db, novel_id)

    result = await pipeline.translate("他需要更多灵石")

    assert "Spirit Stone" in result

def test_glossary_import_export(glossary_db, novel_id, tmp_path):
    """Test glossary CSV import/export."""
    # Add entries
    glossary_db.add_entry(novel_id, GlossaryEntry(
        source_term="Test",
        target_term="测试",
        term_type="test"
    ))

    # Export
    csv_path = tmp_path / "export.csv"
    glossary_db.export_to_csv(novel_id, csv_path)

    # Create new novel and import
    novel_id_2 = glossary_db.create_novel("Test Novel 2")
    glossary_db.import_from_csv(novel_id_2, csv_path)

    entries = glossary_db.get_entries(novel_id_2)
    assert len(entries) == 1
    assert entries[0].source_term == "Test"
```
