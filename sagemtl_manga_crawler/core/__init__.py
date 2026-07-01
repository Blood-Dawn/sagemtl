"""Core plumbing for the manga crawler (source base, registry, fetch, models).

Dependency-light: re-exports only the crawler dataclasses so importing this
package does not pull in httpx or any source modules.
"""

from __future__ import annotations

from .models import ChapterRef, PageImage, SeriesResult

__all__ = ["ChapterRef", "PageImage", "SeriesResult"]
