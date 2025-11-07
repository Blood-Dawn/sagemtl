"""Crawl API router - Chapter extraction and novel crawling."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sagemtl.clean.text_normalize import NormalizeOptions
from sagemtl.crawl.http import fetch_text
from sagemtl.crawl.pipeline import CrawlOptions, crawl_html
from sagemtl.crawl.novel_crawler import NovelCrawler
from sagemtl.crawl.lncrawl_adapter import (
    is_lncrawl_available,
    fetch_novel,
    check_url_support,
)
from sagemtl.jobs.store import JobRecord, get_job_store

router = APIRouter(prefix="/api/crawl", tags=["crawl"])


class CrawlChapterRequest(BaseModel):
    """Request for crawling chapters from a novel website."""
    start_url: str
    depth: int = 1
    max_chapters: Optional[int] = None
    allow_selectors: List[str] = Field(default_factory=lambda: ["article", "main", ".chapter-content"])
    block_selectors: List[str] = Field(default_factory=lambda: [".sidebar", ".footer", ".navigation", ".ads"])
    render_js: bool = False
    dataset_name: Optional[str] = None
    novel_title: Optional[str] = None


class CrawlChapterResponse(BaseModel):
    job_id: str
    status: str
    message: str


class CrawlResult(BaseModel):
    source: str
    meta: dict[str, object]
    blocks: list[dict[str, object]]


def extract_chapters_from_blocks(blocks: list[dict]) -> list[dict[str, str]]:
    """Extract chapter text from crawl blocks."""
    chapters = []
    current_chapter = {"title": "", "text": "", "order": 0}

    for block in blocks:
        text = block.get("text", "")
        if not text.strip():
            continue

        # Simple heuristic: first block is title if it's short
        if not current_chapter["title"] and len(text) < 200:
            current_chapter["title"] = text.strip()
        else:
            current_chapter["text"] += text + "\n\n"

    if current_chapter["text"]:
        chapters.append(current_chapter)

    return chapters


def save_chapters_to_dataset(dataset_name: str, chapters: list[dict[str, str]], novel_title: str = "") -> Path:
    """Save extracted chapters to a dataset directory."""
    import os
    from sagemtl.serve.routers.datasets import get_data_dir

    data_dir = get_data_dir() / dataset_name
    files_dir = data_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    # Save chapters
    for idx, chapter in enumerate(chapters, start=1):
        chapter_file = files_dir / f"ch{idx:04d}.txt"
        content = f"# {chapter.get('title', f'Chapter {idx}')}\n\n{chapter['text']}"
        chapter_file.write_text(content, encoding="utf-8", newline="\n")

    # Save metadata
    meta = {
        "type": "novel",
        "title": novel_title or dataset_name,
        "chapter_count": len(chapters),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "size_bytes": sum((files_dir / f"ch{i:04d}.txt").stat().st_size for i in range(1, len(chapters) + 1)),
        "items_count": len(chapters),
    }

    meta_file = data_dir / "meta.json"
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return data_dir


async def crawl_chapters_worker(job_id: str, request: CrawlChapterRequest):
    """Background worker to crawl chapters."""
    store = get_job_store()
    job = store.get(job_id)

    if not job:
        return

    try:
        job.status = "running"
        store.upsert(job)

        # Fetch and parse the page
        html = fetch_text(request.start_url)

        options = CrawlOptions(
            depth=request.depth,
            render_js=request.render_js,
            allow_selectors=request.allow_selectors,
            block_selectors=request.block_selectors,
            normalize=NormalizeOptions(ensure_trailing_lf=False),
        )

        result = crawl_html(html, source=request.start_url, options=options)

        # Extract chapters
        blocks = [
            {
                "order": block.order,
                "text": block.text,
                "css_path": block.css_path,
                "xpath": block.xpath,
                "lang": block.lang,
            }
            for block in result.blocks
        ]

        chapters = extract_chapters_from_blocks(blocks)

        # Limit chapters if requested
        if request.max_chapters:
            chapters = chapters[:request.max_chapters]

        # Generate dataset name
        dataset_name = request.dataset_name or f"novel-{uuid.uuid4().hex[:8]}"

        # Save to dataset
        data_dir = save_chapters_to_dataset(
            dataset_name,
            chapters,
            request.novel_title or dataset_name
        )

        # Update job
        job.status = "done"
        job.result = {
            "dataset_id": dataset_name,
            "dataset_path": str(data_dir),
            "chapters_extracted": len(chapters),
            "source_url": request.start_url,
        }
        job.log.append(f"Extracted {len(chapters)} chapters to dataset '{dataset_name}'")
        store.upsert(job)

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.log.append(f"Error: {exc}")
        store.upsert(job)


@router.post("/run", response_model=CrawlChapterResponse)
async def crawl_chapters(request: CrawlChapterRequest) -> CrawlChapterResponse:
    """
    Crawl chapters from a novel website and save as a dataset.

    This creates a background job that:
    1. Fetches the page(s)
    2. Extracts chapter content
    3. Saves chapters as {ch0001}.txt, {ch0002}.txt, etc.
    4. Creates a novel-type dataset

    Track progress via WebSocket: /ws/jobs/{job_id}
    """
    # Create job
    job_id = str(uuid.uuid4())
    store = get_job_store()

    job = JobRecord(
        id=job_id,
        type="crawl",
        status="queued",
        meta={"start_url": request.start_url, "novel_title": request.novel_title},
        payload={
            "start_url": request.start_url,
            "depth": request.depth,
            "max_chapters": request.max_chapters,
            "dataset_name": request.dataset_name,
        },
    )

    store.upsert(job)

    # Start background task
    asyncio.create_task(crawl_chapters_worker(job_id, request))

    return CrawlChapterResponse(
        job_id=job_id,
        status="queued",
        message=f"Crawl job queued. Track at /api/jobs/{job_id}"
    )


class ExtractRequest(BaseModel):
    """Request for synchronous HTML extraction."""
    html: Optional[str] = None
    url: Optional[str] = None
    allow_selectors: List[str] = Field(default_factory=list)
    block_selectors: List[str] = Field(default_factory=list)


@router.post("/extract", response_model=CrawlResult)
def extract_html(request: ExtractRequest) -> CrawlResult:
    """
    Extract content from HTML (synchronous, for quick testing).

    Provide either 'html' or 'url'.
    """
    if bool(request.html) == bool(request.url):
        raise HTTPException(status_code=400, detail="Provide exactly one of 'html' or 'url'")

    if request.url:
        html = fetch_text(request.url)
        source = request.url
    else:
        html = request.html or ""
        source = "inline"

    options = CrawlOptions(
        depth=0,
        render_js=False,
        allow_selectors=request.allow_selectors,
        block_selectors=request.block_selectors,
        normalize=NormalizeOptions(ensure_trailing_lf=False),
    )

    result = crawl_html(html, source=source, options=options)

    blocks = [
        {
            "order": block.order,
            "text": block.text,
            "css_path": block.css_path,
            "xpath": block.xpath,
            "lang": block.lang,
        }
        for block in result.blocks
    ]

    return CrawlResult(source=source, meta=result.meta, blocks=blocks)


class NovelCrawlRequest(BaseModel):
    """Request for novel chapter crawling with automatic pattern detection."""
    start_url: str
    start_chapter: int = 1
    end_chapter: int = 10
    allow_selectors: List[str] = Field(default_factory=lambda: ["article", "main", ".chapter-content", ".chapter"])
    block_selectors: List[str] = Field(default_factory=lambda: ["nav", "footer", ".sidebar", ".ads", ".navigation"])
    dataset_name: Optional[str] = None
    max_concurrent: int = Field(default=3, ge=1, le=10)


async def novel_crawl_worker(job_id: str, request: NovelCrawlRequest):
    """Background worker for novel crawling with pattern detection."""
    store = get_job_store()
    job = store.get(job_id)

    if not job:
        return

    try:
        import time
        from sagemtl.serve.routers.datasets import get_data_dir

        start_time = time.time()
        job.status = "running"
        job.meta["start_time"] = start_time
        store.upsert(job)
        store.append_log(job_id, f"Starting novel crawl from {request.start_url}")

        data_dir = get_data_dir()

        # Check if URL is supported by LNCrawl
        is_supported, source_name = check_url_support(request.start_url)

        if is_supported and is_lncrawl_available():
            # Use LNCrawl for supported sites
            store.append_log(job_id, f"URL supported by lightnovel-crawler ({source_name})")
            store.append_log(job_id, f"Using lightnovel-crawler to fetch chapters {request.start_chapter}-{request.end_chapter}")

            novel_dataset = fetch_novel(
                url=request.start_url,
                output_dir=data_dir,
                dataset_name=request.dataset_name,
                start_chapter=request.start_chapter,
                end_chapter=request.end_chapter,
                format="txt",
            )

            dataset_name = novel_dataset.id
            dataset_path = novel_dataset.path
            total_words = novel_dataset.total_words
            chapter_count = novel_dataset.chapter_count
            novel_title = novel_dataset.name
            novel_author = novel_dataset.author
            cover_url = novel_dataset.cover_url

        else:
            # Fall back to built-in crawler
            if is_lncrawl_available():
                store.append_log(job_id, "URL not supported by lightnovel-crawler, using built-in crawler")
            else:
                store.append_log(job_id, "lightnovel-crawler not installed, using built-in crawler")

            crawler = NovelCrawler(max_concurrent=request.max_concurrent)

            store.append_log(job_id, f"Detecting chapter pattern and crawling chapters {request.start_chapter}-{request.end_chapter}")
            novel_info = crawler.crawl_novel(
                start_url=request.start_url,
                start_chapter=request.start_chapter,
                end_chapter=request.end_chapter,
                allow_selectors=request.allow_selectors,
                block_selectors=request.block_selectors,
                dataset_name=request.dataset_name,
            )

            dataset_path = crawler.save_to_dataset(novel_info, data_dir, format="txt")
            dataset_name = dataset_path.name
            total_words = sum(ch.word_count for ch in novel_info.chapters)
            chapter_count = len(novel_info.chapters)
            novel_title = novel_info.title
            novel_author = novel_info.author
            cover_url = novel_info.cover_url

        # Calculate metrics
        end_time = time.time()
        runtime_ms = (end_time - start_time) * 1000

        # Update job with success
        job.status = "done"
        job.result = {
            "dataset_id": dataset_name,
            "dataset_path": str(dataset_path),
            "novel_title": novel_title,
            "author": novel_author,
            "chapters_extracted": chapter_count,
            "total_words": total_words,
            "cover_url": cover_url,
        }
        job.meta["runtime_ms"] = round(runtime_ms, 2)
        job.meta["chapters_extracted"] = chapter_count
        job.meta["total_words"] = total_words

        store.append_log(job_id, f"✓ Crawled {chapter_count} chapters ({total_words:,} words)")
        store.append_log(job_id, f"✓ Saved to dataset: {dataset_name}")
        store.append_log(job_id, f"✓ Completed in {runtime_ms:.0f}ms")
        store.upsert(job)

    except Exception as exc:
        import time
        end_time = time.time()
        runtime_ms = (end_time - start_time) * 1000
        job.status = "failed"
        job.error = str(exc)
        job.meta["runtime_ms"] = round(runtime_ms, 2)
        store.append_log(job_id, f"✗ Error: {exc}")
        store.upsert(job)


@router.post("/novel", response_model=CrawlChapterResponse)
async def crawl_novel(request: NovelCrawlRequest) -> CrawlChapterResponse:
    """
    Crawl a novel with automatic chapter pattern detection.

    This endpoint:
    1. Detects chapter URL patterns automatically
    2. Crawls multiple chapters sequentially
    3. Extracts chapter titles and content
    4. Saves as a novel-type dataset with metadata
    5. Returns job ID for tracking

    The crawler supports common patterns like:
    - /chapter-1, /chapter-2, ...
    - /1/, /2/, ...
    - /ch1/, /ch2/, ...
    - /1.html, /2.html, ...

    Track progress via WebSocket: /api/jobs/ws/{job_id}
    """
    # Create job
    job_id = str(uuid.uuid4())
    store = get_job_store()

    job = JobRecord(
        id=job_id,
        type="novel_crawl",
        status="queued",
        meta={
            "start_url": request.start_url,
            "start_chapter": request.start_chapter,
            "end_chapter": request.end_chapter,
            "expected_chapters": request.end_chapter - request.start_chapter + 1,
        },
        payload={
            "start_url": request.start_url,
            "start_chapter": request.start_chapter,
            "end_chapter": request.end_chapter,
            "dataset_name": request.dataset_name,
        },
    )

    store.upsert(job)
    store.append_log(job_id, f"Novel crawl job queued")

    # Start background task
    asyncio.create_task(novel_crawl_worker(job_id, request))

    return CrawlChapterResponse(
        job_id=job_id,
        status="queued",
        message=f"Novel crawl job queued. Expected to crawl {request.end_chapter - request.start_chapter + 1} chapters. Track at /api/jobs/{job_id}"
    )
