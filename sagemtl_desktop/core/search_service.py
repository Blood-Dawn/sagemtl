"""
Search orchestration helpers for novel lookup.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List


class SearchService:
    """Runs crawler search calls with consistent progress/log handling."""

    @staticmethod
    def run_search_sync(
        crawler,
        novel_name: str,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        """
        Execute async crawler search from a worker thread.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                crawler.search_novel_by_name(novel_name, progress_callback)
            )
        finally:
            loop.close()
