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
