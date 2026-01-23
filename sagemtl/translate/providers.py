"""
Translation provider abstractions and implementations.

Supports multiple translation backends:
- Echo (passthrough for testing)
- Argos Translate (offline, open source)
- Google Cloud Translation (API)
- DeepL (API)
- Azure Cognitive Services (API)
"""

from __future__ import annotations

import asyncio
import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Dict, List, Optional, Type, AsyncIterator, Protocol, Any,
    runtime_checkable
)
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class NotConfigured(RuntimeError):
    """Raised when a requested provider is not available."""


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
    PORTUGUESE = "pt"
    ITALIAN = "it"
    ARABIC = "ar"
    VIETNAMESE = "vi"
    THAI = "th"
    INDONESIAN = "id"


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
    tokens_used: Optional[int] = None
    cost: Optional[float] = None


@dataclass
class ProviderCapabilities:
    """Capabilities of a translation provider."""
    max_chars_per_request: int
    supports_batch: bool
    supports_glossary: bool
    supports_formality: bool
    supported_languages: List[str]
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    is_offline: bool = False


@runtime_checkable
class TranslationProvider(Protocol):
    """Protocol for translation providers."""

    name: str
    is_online: bool

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        ...

    def is_available(self) -> bool:
        """Check if provider is available."""
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


class BaseTranslationProvider(ABC):
    """Base class for translation providers."""

    name: str = "base"
    is_online: bool = True

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        """Translate a single text string."""
        pass

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """Default batch implementation - translate one at a time."""
        results = []
        for text in texts:
            result = await self.translate(text, source_lang, target_lang, glossary)
            results.append(result)
        return results

    async def translate_stream(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> AsyncIterator[str]:
        """Stream translation output (default: yield full result)."""
        result = await self.translate(text, source_lang, target_lang)
        yield result.translated_text


# ============================================================================
# Echo Provider (Testing/Passthrough)
# ============================================================================

@dataclass(slots=True)
class EchoProvider:
    """Default provider that simply echoes the input text."""

    provider_name: str = "echo"
    name: str = field(default="echo", init=False)
    is_online: bool = field(default=False, init=False)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            max_chars_per_request=1_000_000,
            supports_batch=True,
            supports_glossary=False,
            supports_formality=False,
            supported_languages=[lc.value for lc in LanguageCode],
            is_offline=True,
        )

    def is_available(self) -> bool:
        return True

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        return TranslationResult(
            source_text=text,
            translated_text=text,
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
        return [
            await self.translate(text, source_lang, target_lang, glossary)
            for text in texts
        ]

    # Backwards compatibility with old sync interface
    def translate_sync(self, text: str, *, src: str, tgt: str) -> str:
        return text


# ============================================================================
# Unconfigured Provider (Placeholder)
# ============================================================================

@dataclass(slots=True)
class UnconfiguredProvider:
    """Placeholder for providers that aren't configured."""

    provider_name: str
    name: str = field(default="unconfigured", init=False)
    is_online: bool = field(default=True, init=False)

    def __post_init__(self):
        self.name = self.provider_name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            max_chars_per_request=0,
            supports_batch=False,
            supports_glossary=False,
            supports_formality=False,
            supported_languages=[],
        )

    def is_available(self) -> bool:
        return False

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        raise NotConfigured(f"Provider '{self.provider_name}' is not configured")

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        raise NotConfigured(f"Provider '{self.provider_name}' is not configured")

    # Backwards compatibility with old sync interface
    def translate_sync(self, text: str, *, src: str, tgt: str) -> str:
        raise NotConfigured(f"Provider '{self.provider_name}' is not configured")


# ============================================================================
# Argos Provider (Offline)
# ============================================================================

class ArgosProvider(BaseTranslationProvider):
    """Offline translation using Argos Translate."""

    name = "argos"
    is_online = False

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._installed_packages: set = set()
        self._argos_available = False
        self._init_argos()

    def _init_argos(self):
        """Initialize Argos Translate."""
        try:
            import argostranslate.package
            import argostranslate.translate
            self._argos_available = True
            self._refresh_packages()
        except ImportError:
            logger.debug("argostranslate not installed. Argos provider unavailable.")
            self._argos_available = False

    def _refresh_packages(self):
        """Refresh list of installed language packages."""
        if not self._argos_available:
            return

        try:
            import argostranslate.package
            installed = argostranslate.package.get_installed_packages()
            self._installed_packages = {
                (pkg.from_code, pkg.to_code) for pkg in installed
            }
        except Exception as e:
            logger.error(f"Failed to refresh Argos packages: {e}")

    def _get_supported_languages(self) -> List[str]:
        """Get list of languages we can translate."""
        languages = set()
        for from_code, to_code in self._installed_packages:
            languages.add(from_code)
            languages.add(to_code)
        return list(languages)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            max_chars_per_request=10000,
            supports_batch=True,
            supports_glossary=False,
            supports_formality=False,
            supported_languages=self._get_supported_languages(),
            is_offline=True,
        )

    def is_available(self) -> bool:
        return self._argos_available and len(self._installed_packages) > 0

    async def ensure_language_pair(self, source: str, target: str) -> bool:
        """Ensure the language pair is installed, download if needed."""
        if not self._argos_available:
            return False

        if (source, target) in self._installed_packages:
            return True

        try:
            import argostranslate.package

            argostranslate.package.update_package_index()
            available = argostranslate.package.get_available_packages()

            package = next(
                (p for p in available
                 if p.from_code == source and p.to_code == target),
                None
            )

            if package:
                logger.info(f"Downloading Argos language package: {source} -> {target}")
                download_path = package.download()
                argostranslate.package.install_from_path(download_path)
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
        if not self._argos_available:
            raise NotConfigured("Argos Translate is not installed")

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
        import argostranslate.translate
        return argostranslate.translate.translate(text, source, target)

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """Translate multiple texts concurrently."""
        tasks = [
            self.translate(text, source_lang, target_lang, glossary)
            for text in texts
        ]
        return await asyncio.gather(*tasks)


# ============================================================================
# Google Cloud Translation Provider
# ============================================================================

class GoogleTranslateProvider(BaseTranslationProvider):
    """Translation using Google Cloud Translation API."""

    name = "google"
    is_online = True

    def __init__(self):
        self._client = None
        self._api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY")
        self._project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._google_available = False
        self._use_v3 = False
        self._init_google()

    def _init_google(self):
        """Initialize Google Cloud Translation."""
        # Try v3 API first, then fall back to basic v2
        try:
            from google.cloud import translate_v3 as translate
            self._google_available = True
            self._use_v3 = True
        except ImportError:
            try:
                from google.cloud import translate_v2 as translate
                self._google_available = True
                self._use_v3 = False
            except ImportError:
                # Can still use REST API directly
                if self._api_key:
                    self._google_available = True
                    self._use_v3 = False
                else:
                    logger.debug("google-cloud-translate not installed and no API key. Google provider unavailable.")
                    self._google_available = False

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            max_chars_per_request=5000,
            supports_batch=True,
            supports_glossary=True,
            supports_formality=False,
            supported_languages=["zh", "zh-TW", "ja", "ko", "en", "es", "fr", "de", "ru", "pt", "it", "ar", "vi", "th", "id"],
            rate_limit_per_minute=600000,
            rate_limit_per_day=500000,
        )

    def is_available(self) -> bool:
        return self._google_available and (self._api_key or self._project_id)

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        """Translate using Google Cloud API."""
        if not self.is_available():
            raise NotConfigured("Google Translate is not configured")

        loop = asyncio.get_event_loop()

        if self._api_key and not self._project_id:
            # Use REST API with API key
            translated = await loop.run_in_executor(
                None,
                self._translate_rest,
                text, source_lang, target_lang
            )
        else:
            # Use client library
            translated = await loop.run_in_executor(
                None,
                self._translate_client,
                text, source_lang, target_lang
            )

        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            provider=self.name,
        )

    def _translate_rest(self, text: str, source: str, target: str) -> str:
        """Translate using REST API with API key."""
        import requests

        url = "https://translation.googleapis.com/language/translate/v2"
        params = {
            "key": self._api_key,
            "q": text,
            "source": source,
            "target": target,
            "format": "text",
        }

        response = requests.post(url, params=params)
        response.raise_for_status()
        data = response.json()

        return data["data"]["translations"][0]["translatedText"]

    def _translate_client(self, text: str, source: str, target: str) -> str:
        """Translate using Google Cloud client library."""
        if self._use_v3:
            from google.cloud import translate_v3 as translate

            if not self._client:
                self._client = translate.TranslationServiceClient()

            parent = f"projects/{self._project_id}/locations/global"
            response = self._client.translate_text(
                parent=parent,
                contents=[text],
                source_language_code=source,
                target_language_code=target,
                mime_type="text/plain",
            )
            return response.translations[0].translated_text
        else:
            from google.cloud import translate_v2 as translate

            if not self._client:
                self._client = translate.Client()

            result = self._client.translate(
                text,
                source_language=source,
                target_language=target,
            )
            return result["translatedText"]

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """Translate multiple texts."""
        # Google v3 supports batch in single call
        if self._use_v3 and self._project_id:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._translate_batch_v3,
                texts, source_lang, target_lang
            )
            return [
                TranslationResult(
                    source_text=src,
                    translated_text=tgt,
                    source_language=source_lang,
                    target_language=target_lang,
                    provider=self.name,
                )
                for src, tgt in zip(texts, results)
            ]
        else:
            # Fall back to sequential
            return await super().translate_batch(texts, source_lang, target_lang, glossary)

    def _translate_batch_v3(self, texts: List[str], source: str, target: str) -> List[str]:
        """Batch translate using v3 API."""
        from google.cloud import translate_v3 as translate

        if not self._client:
            self._client = translate.TranslationServiceClient()

        parent = f"projects/{self._project_id}/locations/global"
        response = self._client.translate_text(
            parent=parent,
            contents=texts,
            source_language_code=source,
            target_language_code=target,
            mime_type="text/plain",
        )
        return [t.translated_text for t in response.translations]


# ============================================================================
# DeepL Provider
# ============================================================================

class DeepLProvider(BaseTranslationProvider):
    """Translation using DeepL API."""

    name = "deepl"
    is_online = True

    def __init__(self):
        self._api_key = os.environ.get("DEEPL_API_KEY")
        self._deepl_available = False
        self._translator = None
        self._init_deepl()

    def _init_deepl(self):
        """Initialize DeepL."""
        try:
            import deepl
            self._deepl_available = True
            if self._api_key:
                self._translator = deepl.Translator(self._api_key)
        except ImportError:
            # Can still use REST API directly
            if self._api_key:
                self._deepl_available = True
            else:
                logger.debug("deepl library not installed and no API key. DeepL provider unavailable.")
                self._deepl_available = False

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            max_chars_per_request=128000,  # DeepL has generous limits
            supports_batch=True,
            supports_glossary=True,
            supports_formality=True,  # DeepL supports formal/informal
            supported_languages=["zh", "ja", "ko", "en", "es", "fr", "de", "ru", "pt", "it", "nl", "pl"],
            rate_limit_per_minute=None,
            rate_limit_per_day=500000,  # Free tier
        )

    def is_available(self) -> bool:
        return self._deepl_available and bool(self._api_key)

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        """Translate using DeepL API."""
        if not self.is_available():
            raise NotConfigured("DeepL is not configured")

        loop = asyncio.get_event_loop()

        # Map language codes (DeepL uses different format)
        deepl_source = self._map_language_code(source_lang)
        deepl_target = self._map_language_code(target_lang, is_target=True)

        if self._translator:
            translated = await loop.run_in_executor(
                None,
                self._translate_lib,
                text, deepl_source, deepl_target
            )
        else:
            translated = await loop.run_in_executor(
                None,
                self._translate_rest,
                text, deepl_source, deepl_target
            )

        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            provider=self.name,
        )

    def _map_language_code(self, code: str, is_target: bool = False) -> str:
        """Map standard language codes to DeepL format."""
        code = code.upper()
        # DeepL uses different codes for some languages
        mapping = {
            "ZH": "ZH",
            "ZH-TW": "ZH",  # DeepL doesn't distinguish
            "EN": "EN-US" if is_target else "EN",
            "PT": "PT-BR" if is_target else "PT",
        }
        return mapping.get(code, code)

    def _translate_lib(self, text: str, source: str, target: str) -> str:
        """Translate using DeepL library."""
        result = self._translator.translate_text(
            text,
            source_lang=source if source else None,
            target_lang=target,
        )
        return result.text

    def _translate_rest(self, text: str, source: str, target: str) -> str:
        """Translate using DeepL REST API."""
        import requests

        # Determine API endpoint (free vs pro)
        if self._api_key.endswith(":fx"):
            url = "https://api-free.deepl.com/v2/translate"
        else:
            url = "https://api.deepl.com/v2/translate"

        data = {
            "auth_key": self._api_key,
            "text": text,
            "target_lang": target,
        }
        if source:
            data["source_lang"] = source

        response = requests.post(url, data=data)
        response.raise_for_status()
        result = response.json()

        return result["translations"][0]["text"]

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """Translate multiple texts."""
        if self._translator:
            loop = asyncio.get_event_loop()
            deepl_source = self._map_language_code(source_lang)
            deepl_target = self._map_language_code(target_lang, is_target=True)

            results = await loop.run_in_executor(
                None,
                self._translate_batch_lib,
                texts, deepl_source, deepl_target
            )
            return [
                TranslationResult(
                    source_text=src,
                    translated_text=tgt,
                    source_language=source_lang,
                    target_language=target_lang,
                    provider=self.name,
                )
                for src, tgt in zip(texts, results)
            ]
        else:
            return await super().translate_batch(texts, source_lang, target_lang, glossary)

    def _translate_batch_lib(self, texts: List[str], source: str, target: str) -> List[str]:
        """Batch translate using DeepL library."""
        results = self._translator.translate_text(
            texts,
            source_lang=source if source else None,
            target_lang=target,
        )
        return [r.text for r in results]


# ============================================================================
# Azure Cognitive Services Provider
# ============================================================================

class AzureTranslateProvider(BaseTranslationProvider):
    """Translation using Azure Cognitive Services Translator."""

    name = "azure"
    is_online = True

    def __init__(self):
        self._api_key = os.environ.get("AZURE_TRANSLATOR_KEY")
        self._region = os.environ.get("AZURE_TRANSLATOR_REGION", "global")
        self._endpoint = os.environ.get(
            "AZURE_TRANSLATOR_ENDPOINT",
            "https://api.cognitive.microsofttranslator.com"
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            max_chars_per_request=50000,
            supports_batch=True,
            supports_glossary=True,
            supports_formality=False,
            supported_languages=["zh-Hans", "zh-Hant", "ja", "ko", "en", "es", "fr", "de", "ru", "pt", "it", "ar", "vi", "th", "id"],
            rate_limit_per_minute=2000000,
            rate_limit_per_day=2000000,
        )

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> TranslationResult:
        """Translate using Azure Translator API."""
        if not self.is_available():
            raise NotConfigured("Azure Translator is not configured")

        loop = asyncio.get_event_loop()

        # Map language codes for Azure
        azure_source = self._map_language_code(source_lang)
        azure_target = self._map_language_code(target_lang)

        translated = await loop.run_in_executor(
            None,
            self._translate_rest,
            text, azure_source, azure_target
        )

        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            provider=self.name,
        )

    def _map_language_code(self, code: str) -> str:
        """Map standard language codes to Azure format."""
        mapping = {
            "zh": "zh-Hans",
            "zh-TW": "zh-Hant",
        }
        return mapping.get(code, code)

    def _translate_rest(self, text: str, source: str, target: str) -> str:
        """Translate using Azure REST API."""
        import requests
        import uuid

        url = f"{self._endpoint}/translate"

        params = {
            "api-version": "3.0",
            "from": source,
            "to": target,
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Ocp-Apim-Subscription-Region": self._region,
            "Content-type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }

        body = [{"text": text}]

        response = requests.post(url, params=params, headers=headers, json=body)
        response.raise_for_status()
        result = response.json()

        return result[0]["translations"][0]["text"]

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """Translate multiple texts in a single API call."""
        if not self.is_available():
            raise NotConfigured("Azure Translator is not configured")

        loop = asyncio.get_event_loop()

        azure_source = self._map_language_code(source_lang)
        azure_target = self._map_language_code(target_lang)

        results = await loop.run_in_executor(
            None,
            self._translate_batch_rest,
            texts, azure_source, azure_target
        )

        return [
            TranslationResult(
                source_text=src,
                translated_text=tgt,
                source_language=source_lang,
                target_language=target_lang,
                provider=self.name,
            )
            for src, tgt in zip(texts, results)
        ]

    def _translate_batch_rest(self, texts: List[str], source: str, target: str) -> List[str]:
        """Batch translate using Azure REST API."""
        import requests
        import uuid

        url = f"{self._endpoint}/translate"

        params = {
            "api-version": "3.0",
            "from": source,
            "to": target,
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Ocp-Apim-Subscription-Region": self._region,
            "Content-type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }

        body = [{"text": text} for text in texts]

        response = requests.post(url, params=params, headers=headers, json=body)
        response.raise_for_status()
        result = response.json()

        return [item["translations"][0]["text"] for item in result]


# ============================================================================
# Provider Registry
# ============================================================================

class ProviderRegistry:
    """Registry for translation providers."""

    _providers: Dict[str, Type] = {}
    _instances: Dict[str, Any] = {}
    _default_provider: Optional[str] = None

    @classmethod
    def register(cls, name: str, provider_class: Type):
        """Register a provider class."""
        cls._providers[name] = provider_class

    @classmethod
    def get_provider(cls, name: str) -> Optional[Any]:
        """Get a provider instance by name."""
        if name not in cls._instances:
            if name not in cls._providers:
                return None
            try:
                cls._instances[name] = cls._providers[name]()
            except Exception as e:
                logger.error(f"Failed to instantiate provider {name}: {e}")
                return None
        return cls._instances[name]

    @classmethod
    def get_default(cls) -> Optional[Any]:
        """Get the default provider."""
        if cls._default_provider:
            provider = cls.get_provider(cls._default_provider)
            if provider and provider.is_available():
                return provider

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
    def list_providers(cls) -> List[Dict[str, Any]]:
        """List all registered providers with their status."""
        result = []
        for name in cls._providers:
            provider = cls.get_provider(name)
            if provider:
                result.append({
                    'name': name,
                    'is_online': provider.is_online,
                    'is_available': provider.is_available(),
                    'capabilities': provider.capabilities,
                })
            else:
                result.append({
                    'name': name,
                    'is_online': True,
                    'is_available': False,
                    'capabilities': None,
                })
        return result

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names."""
        available = []
        for name in cls._providers:
            provider = cls.get_provider(name)
            if provider and provider.is_available():
                available.append(name)
        return available


# Register providers
ProviderRegistry.register("echo", EchoProvider)
ProviderRegistry.register("argos", ArgosProvider)
ProviderRegistry.register("google", GoogleTranslateProvider)
ProviderRegistry.register("deepl", DeepLProvider)
ProviderRegistry.register("azure", AzureTranslateProvider)


# ============================================================================
# Convenience Functions
# ============================================================================

def get_provider(name: str | None) -> Any:
    """Get a translation provider by name."""
    if not name or name == "echo":
        return EchoProvider()

    provider = ProviderRegistry.get_provider(name)
    if provider and provider.is_available():
        return provider

    # Check for old provider names
    if name in {"ctranslate2", "hf-pipeline", "hf", "ctranslate"}:
        raise NotConfigured(f"Provider '{name}' is not configured")

    # Return unconfigured placeholder
    return UnconfiguredProvider(provider_name=name)


def list_available_providers() -> List[str]:
    """List names of available providers."""
    return ProviderRegistry.get_available_providers()


async def translate(
    text: str,
    source_lang: str = "zh",
    target_lang: str = "en",
    provider_name: Optional[str] = None,
    glossary: Optional[Dict[str, str]] = None,
) -> TranslationResult:
    """Translate text using the specified or default provider."""
    if provider_name:
        provider = get_provider(provider_name)
    else:
        provider = ProviderRegistry.get_default() or EchoProvider()

    return await provider.translate(text, source_lang, target_lang, glossary)
