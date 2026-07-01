"""SageMTL manga crawler.

A sibling to ``sagemtl_crawler`` for page-image sources. A manga chapter is an
ordered list of page-image URLs (not an HTML body), so the core method is
``fetch_page_list`` rather than ``download_chapter``. The MangaDex official-API
source is the flagship legal default. Implemented across Phase 7.

See ``MANGA_MODULE_BUILD_SPEC.md`` section 9.
"""

from __future__ import annotations
