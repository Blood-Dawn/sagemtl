"""Translation provider abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class NotConfigured(RuntimeError):
    """Raised when a requested provider is not available."""


class TranslationProvider(Protocol):
    def name(self) -> str: ...

    def translate(self, text: str, *, src: str, tgt: str) -> str: ...


@dataclass(slots=True)
class EchoProvider:
    """Default provider that simply echoes the input text."""

    provider_name: str = "echo"

    def name(self) -> str:
        return self.provider_name

    def translate(self, text: str, *, src: str, tgt: str) -> str:
        return text


@dataclass(slots=True)
class UnconfiguredProvider:
    provider_name: str

    def name(self) -> str:  # pragma: no cover - trivial
        return self.provider_name

    def translate(self, text: str, *, src: str, tgt: str) -> str:
        raise NotConfigured(f"Provider '{self.provider_name}' is not configured")


def get_provider(name: str | None) -> TranslationProvider:
    if not name or name == "echo":
        return EchoProvider()
    if name in {"ctranslate2", "hf-pipeline", "hf", "ctranslate"}:
        raise NotConfigured(f"Provider '{name}' is not configured")
    return EchoProvider(provider_name=name)
