import asyncio
import json
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup

from sagemtl.crawl.novel_crawler import NovelCrawler


URL = "https://www.fanmtl.com/novel/survival-for-all-practice-a-hundred-times-faster-at-the-beginning.html"


def _diagnose_connectivity(url: str) -> tuple[bool, str]:
    """Return (status, reason) for reaching the target site."""
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return False, f"Invalid URL: {url}"

    try:
        socket.gethostbyname(hostname)
    except socket.gaierror as exc:
        return False, f"DNS lookup failed for {hostname}: {exc}"  # pragma: no cover

    try:
        response = httpx.get(
            url,
            timeout=10.0,
            headers={
                "User-Agent": "SageMTL-IntegrationTest/1.0 (+https://github.com/Blood-Dawn/sagemtl)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # HTTP reached but returned error code
        return False, f"Site responded with HTTP {exc.response.status_code}: {exc.response.reason_phrase}"
    except httpx.RequestError as exc:
        return False, f"Failed to reach site: {exc}"

    return True, "OK"


def _resolve_start_chapter_url(toc_url: str) -> tuple[bool, str, str]:
    """Return (status, reason, chapter_url)."""
    try:
        response = httpx.get(
            toc_url,
            timeout=10.0,
            headers={
                "User-Agent": "SageMTL-IntegrationTest/1.0 (+https://github.com/Blood-Dawn/sagemtl)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
    except httpx.RequestError as exc:
        return False, f"Failed to load TOC page: {exc}", ""

    soup = BeautifulSoup(response.text, "html.parser")
    base = httpx.URL(response.request.url)

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        if not href or href.startswith("#"):
            continue

        lower_href = href.lower()
        if "chapter" in lower_href or "episode" in lower_href:
            chapter_url = str(base.join(href))
            return True, "OK", chapter_url

    return False, "Could not locate first chapter link on TOC page", ""


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

    chapter_ok, chapter_reason, start_chapter_url = _resolve_start_chapter_url(URL)
    if not chapter_ok:
        pytest.skip(chapter_reason)

    crawler = NovelCrawler()

    # Crawl up to 10 chapters (crawler should handle range limits)
    novel_info = asyncio.run(
        crawler.crawl_novel(
            start_url=start_chapter_url,
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
