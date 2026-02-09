"""Regression tests for grouped search UX helpers."""

from __future__ import annotations

from sagemtl_desktop.core.search_service import SearchService


def test_group_results_merges_same_novel_across_sites():
    title = "In the universe online game, I can specify the drop"
    results = [
        {
            "title": title,
            "url": "https://site-a.example/books/drop-system",
            "site": "site-a.example",
        },
        {
            "title": title,
            "url": "https://site-b.example/novel/drop-system",
            "site": "site-b.example",
        },
        {
            # Duplicate trailing slash variant should be deduplicated.
            "title": title,
            "url": "https://site-a.example/books/drop-system/",
            "site": "site-a.example",
        },
    ]

    grouped = SearchService.group_results(results)

    assert len(grouped) == 1
    assert grouped[0]["title"] == title
    assert grouped[0]["site_count"] == 2
    assert grouped[0]["chapter_count_summary"] == "Unknown"
    assert [row["site"] for row in grouped[0]["sources"]] == [
        "site-a.example",
        "site-b.example",
    ]


def test_group_results_uses_explicit_group_key_when_titles_vary():
    group_key = "in-universe-online-drop-system"
    results = [
        {
            "title": "In the universe online game, I can specify the drop",
            "group_key": group_key,
            "url": "https://site-a.example/books/drop-system",
            "site": "site-a.example",
        },
        {
            "title": "In The Universe Online Game I Can Specify The Drop [MTL]",
            "group_key": group_key,
            "url": "https://site-b.example/novel/drop-system",
            "site": "site-b.example",
        },
        {
            "title": "Another novel title",
            "url": "https://site-c.example/novel/other",
            "site": "site-c.example",
        },
    ]

    grouped = SearchService.group_results(results)

    assert len(grouped) == 2
    assert grouped[0]["site_count"] == 2
    assert grouped[0]["chapter_count_summary"] == "Unknown"
    assert grouped[1]["title"] == "Another novel title"


def test_refresh_group_summaries_builds_chapter_range_summary():
    grouped = [
        {
            "title": "In the universe online game, I can specify the drop",
            "sources": [
                {"url": "https://site-a.example/books/drop-system", "chapter_count": 220},
                {"url": "https://site-b.example/novel/drop-system", "chapter_count": 230},
                {"url": "https://site-c.example/novel/drop-system", "chapter_count": None},
            ],
        }
    ]

    SearchService.refresh_group_summaries(grouped)

    assert grouped[0]["site_count"] == 3
    assert grouped[0]["chapter_count_summary"] == "220-230"


def test_select_prefetch_rows_uses_top_unknown_rows_only():
    results = [
        {"url": "https://site-a.example/novel/a", "chapter_count": 180},
        {"url": "https://site-b.example/novel/b", "chapter_count": None},
        {"url": "https://site-c.example/novel/c"},
        {"url": "", "chapter_count": None},  # Invalid source row.
        {"url": "https://site-d.example/novel/d", "chapter_count": 90},
        {"url": "https://site-e.example/novel/e", "chapter_count": -1},
    ]

    rows = SearchService.select_prefetch_rows(results, top_n=3)

    assert rows == [1, 2, 5]
