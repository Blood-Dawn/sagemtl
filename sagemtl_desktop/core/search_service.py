"""
Search orchestration helpers for novel lookup.
"""

from __future__ import annotations

import asyncio
import re
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

    @staticmethod
    def _normalize_title_key(title: str) -> str:
        """Normalize a title to a stable grouping key."""
        cleaned = re.sub(r"[^\w]+", " ", (title or "").strip().lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _normalize_url_key(url: str) -> str:
        return (url or "").strip().rstrip("/").lower()

    @classmethod
    def group_results(cls, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group flat per-site search results by novel title (or explicit group key).

        Output group schema:
        - title: display title
        - group_key: normalized grouping key
        - sources: list of per-site rows
        - site_count: number of unique source URLs
        - chapter_count_summary: string summary for known chapter counts
        """
        groups_by_key: dict[str, dict[str, Any]] = {}
        seen_urls_by_group: dict[str, set[str]] = {}
        ordered_group_keys: list[str] = []

        for row in results or []:
            title = str(row.get("title") or "").strip()
            url = str(row.get("url") or "").strip()
            if not title or not url:
                continue

            explicit_group_key = str(
                row.get("group_key") or row.get("group_title") or ""
            ).strip()
            group_key = cls._normalize_title_key(explicit_group_key or title)
            if not group_key:
                group_key = f"url:{cls._normalize_url_key(url)}"

            if group_key not in groups_by_key:
                groups_by_key[group_key] = {
                    "title": str(row.get("group_title") or title).strip() or title,
                    "group_key": group_key,
                    "sources": [],
                    "site_count": 0,
                    "chapter_count_summary": "Unknown",
                }
                seen_urls_by_group[group_key] = set()
                ordered_group_keys.append(group_key)

            url_key = cls._normalize_url_key(url)
            if not url_key or url_key in seen_urls_by_group[group_key]:
                continue

            seen_urls_by_group[group_key].add(url_key)
            groups_by_key[group_key]["sources"].append(dict(row))

        grouped_results = [groups_by_key[key] for key in ordered_group_keys]
        cls.refresh_group_summaries(grouped_results)
        return grouped_results

    @staticmethod
    def _chapter_count_summary(sources: List[Dict[str, Any]]) -> str:
        known_counts = sorted(
            {
                int(value)
                for value in (source.get("chapter_count") for source in sources or [])
                if isinstance(value, int) and value >= 0
            }
        )
        if not known_counts:
            return "Unknown"
        if len(known_counts) == 1:
            return str(known_counts[0])
        return f"{known_counts[0]}-{known_counts[-1]}"

    @classmethod
    def refresh_group_summaries(cls, grouped_results: List[Dict[str, Any]]) -> None:
        """Refresh derived group fields after source-level chapter updates."""
        for group in grouped_results or []:
            sources = group.get("sources") or []
            group["site_count"] = len(sources)
            group["chapter_count_summary"] = cls._chapter_count_summary(sources)

    @staticmethod
    def select_prefetch_rows(results: List[Dict[str, Any]], top_n: int) -> List[int]:
        """
        Select row indexes for chapter-count prefetch from top results.

        Unknown counts are selected in original order up to `top_n`.
        """
        if top_n <= 0:
            return []

        selected_rows: list[int] = []
        for index, row in enumerate(results or []):
            chapter_count = row.get("chapter_count")
            url = str(row.get("url") or "").strip()
            if not url:
                continue
            if isinstance(chapter_count, int) and chapter_count >= 0:
                continue
            selected_rows.append(index)
            if len(selected_rows) >= top_n:
                break
        return selected_rows
