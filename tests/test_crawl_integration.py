import asyncio
import json
from pathlib import Path

import httpx
import pytest

from sagemtl.crawl.novel_crawler import NovelCrawler


URL = "https://www.fanmtl.com/novel/survival-for-all-practice-a-hundred-times-faster-at-the-beginning.html"


def _diagnose_connectivity(url: str) -> tuple[bool, str]:
    """Return (status, reason)."""
    import socket

    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2).close()
    except OSError as exc:
        return False, f"No internet connectivity (DNS probe failed: {exc})"

    try:
        response = httpx.get(url, timeout=5.0, headers={"User-Agent": "SageMTL-Test/1.0"})
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # HTTP reached but returned error code
        return False, f"Site responded with HTTP {exc.response.status_code}: {exc.response.reason_phrase}"
    except httpx.RequestError as exc:
        return False, f"Failed to reach site: {exc}"

    return True, "OK"


def _assert_txt_export(dataset_dir: Path) -> None:
    files_dir = dataset_dir / "files"
    first_chapter = next(files_dir.glob("chapter-*.txt"))
    content = first_chapter.read_text(encoding="utf-8")
    assert len(content.strip()) > 100


def _assert_md_export(dataset_dir: Path) -> None:
    files_dir = dataset_dir / "files"
    first_chapter = next(files_dir.glob("chapter-*.md"))
    content = first_chapter.read_text(encoding="utf-8")
    assert content.startswith("# ")


def _assert_jsonl_export(dataset_dir: Path) -> None:
    files_dir = dataset_dir / "files"
    first_chapter = next(files_dir.glob("chapter-*.jsonl"))
    content = first_chapter.read_text(encoding="utf-8")
    obj = json.loads(content.strip())
    assert "title" in obj and "content" in obj


def _assert_json_export(dataset_dir: Path) -> None:
    files_dir = dataset_dir / "files"
    first_chapter = next(files_dir.glob("chapter-*.json"))
    data = json.loads(first_chapter.read_text(encoding="utf-8"))
    assert data["chapter"] >= 1


def _assert_web_export(dataset_dir: Path) -> None:
    files_dir = dataset_dir / "files"
    first_chapter = next(files_dir.glob("chapter-*.web"))
    content = first_chapter.read_text(encoding="utf-8")
    assert "<html" in content.lower()


def _assert_epub_export(dataset_dir: Path) -> None:
    files_dir = dataset_dir / "files"
    assert any(path.suffix == ".epub" for path in files_dir.iterdir())


def test_crawl_and_export_all_formats(tmp_path: Path):
    """Integration test: crawl example URL, fetch first 10 chapters, and export to multiple formats."""

    ok, reason = _diagnose_connectivity(URL)
    if not ok:
        pytest.skip(reason)

    crawler = NovelCrawler()

    # Crawl up to 10 chapters (crawler should handle range limits)
    novel_info = asyncio.run(
        crawler.crawl_novel(
            start_url=URL,
            start_chapter=1,
            end_chapter=10,
            dataset_name="integration_test_novel",
        )
    )

    assert novel_info is not None
    assert len(novel_info.chapters) >= 1

    # Create exports matching the desktop application's options
    format_assertions = {
        "txt": _assert_txt_export,
        "md": _assert_md_export,
        "jsonl": _assert_jsonl_export,
        "json": _assert_json_export,
        "web": _assert_web_export,
    }

    for export_format, assertion in format_assertions.items():
        base_dir = tmp_path / export_format
        dataset_dir = crawler.save_to_dataset(novel_info, base_dir, export_format)
        assertion(dataset_dir)

    # EPUB export is optional (depends on ebooklib)
    try:
        epub_dir = crawler.save_to_dataset(novel_info, tmp_path / "epub", "epub")
    except RuntimeError as exc:
        pytest.skip(f"EPUB export not available: {exc}")
    else:
        _assert_epub_export(epub_dir)
