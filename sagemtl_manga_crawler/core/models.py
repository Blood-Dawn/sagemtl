"""Manga crawler data models (spec 9.1).

Dependency-light dataclasses shared by every source plugin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SeriesResult:
    """A series hit from a source search."""

    title: str
    url: str
    source: str
    cover: Optional[str] = None


@dataclass
class ChapterRef:
    """A reference to one chapter within a series."""

    id: str
    number: str
    title: str
    url: str
    lang: str


@dataclass
class PageImage:
    """A single page image to download (referer set for hotlink protection)."""

    index: int
    url: str
    referer: Optional[str] = None
    headers: dict = field(default_factory=dict)
