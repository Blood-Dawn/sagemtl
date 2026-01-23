"""Translation service with multi-provider support and glossary management."""

from .queue import TranslationQueue, TranslationRequest, get_translation_queue
from .providers import (
    NotConfigured,
    TranslationProvider,
    TranslationResult,
    ProviderCapabilities,
    ProviderRegistry,
    EchoProvider,
    ArgosProvider,
    GoogleTranslateProvider,
    DeepLProvider,
    AzureTranslateProvider,
    get_provider,
    list_available_providers,
    translate,
    LanguageCode,
)
from .glossary import GlossaryEntry, load_glossary, save_glossary, apply_glossary
from .glossary_db import GlossaryDB, GlossaryEntryDB, get_glossary_db
from .pipeline import (
    TranslationPipeline,
    TranslationConfig,
    TranslationProgress,
    translate_text,
)

__all__ = [
    # Queue
    "TranslationQueue",
    "TranslationRequest",
    "get_translation_queue",
    # Providers
    "NotConfigured",
    "TranslationProvider",
    "TranslationResult",
    "ProviderCapabilities",
    "ProviderRegistry",
    "EchoProvider",
    "ArgosProvider",
    "GoogleTranslateProvider",
    "DeepLProvider",
    "AzureTranslateProvider",
    "get_provider",
    "list_available_providers",
    "translate",
    "LanguageCode",
    # Glossary
    "GlossaryEntry",
    "load_glossary",
    "save_glossary",
    "apply_glossary",
    "GlossaryDB",
    "GlossaryEntryDB",
    "get_glossary_db",
    # Pipeline
    "TranslationPipeline",
    "TranslationConfig",
    "TranslationProgress",
    "translate_text",
]
