"""Backwards compatible wrapper around :mod:`sagemtl.clean.pipeline`."""

from __future__ import annotations

from typing import Any, Dict

from .pipeline import CleanOptions, CleanResult, clean_text as _clean_text

__all__ = ["CleanOptions", "CleanResult", "clean_text", "clean_text_with_meta"]


def clean_text(text: str, *, options: CleanOptions | None = None) -> str:
    """Return only the cleaned text for legacy callers."""

    return _clean_text(text, options=options).text


def clean_text_with_meta(
    text: str,
    *,
    options: CleanOptions | None = None,
    meta: Dict[str, Any] | None = None,
) -> CleanResult:
    """Expose the :class:`CleanResult` object for callers that need metadata."""

    return _clean_text(text, options=options, meta=meta)
