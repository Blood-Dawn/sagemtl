"""FastAPI bridge exposing the CLI pipelines over HTTP."""

from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sagemtl.clean.pipeline import CleanOptions, clean_text
from sagemtl.clean.text_normalize import NormalizeOptions
from sagemtl.crawl.pipeline import CrawlOptions, crawl_html
from sagemtl.crawl.http import fetch_text
from sagemtl.datasets.registry import get_dataset_registry
from sagemtl.translate import NotConfigured, TranslationRequest, get_translation_queue

app = FastAPI(title="SageMTL API", version="0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NormalizePayload(BaseModel):
    smart_quotes: bool = True
    em_dash: bool = True
    minus_sign: bool = True
    nbsp_to_space: bool = True
    zero_width: bool = True
    collapse_blank_lines: bool = True
    ensure_trailing_lf: bool = True

    def to_options(self) -> NormalizeOptions:
        return NormalizeOptions(
            smart_quotes=self.smart_quotes,
            em_dash=self.em_dash,
            minus_sign=self.minus_sign,
            nbsp_to_space=self.nbsp_to_space,
            zero_width=self.zero_width,
            collapse_blank_lines=self.collapse_blank_lines,
            ensure_trailing_lf=self.ensure_trailing_lf,
        )


class CleanRequest(BaseModel):
    text: str
    options: NormalizePayload = Field(default_factory=NormalizePayload)


class CleanResponse(BaseModel):
    text: str
    meta: dict[str, object]


@app.post("/clean", response_model=CleanResponse)
def post_clean(payload: CleanRequest) -> CleanResponse:
    result = clean_text(
        payload.text, options=CleanOptions(normalize=payload.options.to_options())
    )
    return CleanResponse(text=result.text, meta=result.meta)


class CrawlRequest(BaseModel):
    html: Optional[str] = None
    url: Optional[str] = None
    options: NormalizePayload = Field(
        default_factory=lambda: NormalizePayload(ensure_trailing_lf=False)
    )
    allow_selectors: List[str] = Field(default_factory=list)
    block_selectors: List[str] = Field(default_factory=list)
    depth: int = 0
    render_js: bool = False


class CrawlResponse(BaseModel):
    source: str
    meta: dict[str, object]
    blocks: list[dict[str, object]]


@app.post("/crawl", response_model=CrawlResponse)
def post_crawl(payload: CrawlRequest) -> CrawlResponse:
    if bool(payload.html) == bool(payload.url):
        raise HTTPException(
            status_code=400, detail="Provide exactly one of 'html' or 'url'."
        )
    if payload.url:
        html = fetch_text(payload.url)
        source = payload.url
    else:
        html = payload.html or ""
        source = "inline"
    options = CrawlOptions(
        depth=payload.depth,
        render_js=payload.render_js,
        allow_selectors=payload.allow_selectors,
        block_selectors=payload.block_selectors,
        normalize=payload.options.to_options(),
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
    return CrawlResponse(source=source, meta=result.meta, blocks=blocks)


class TranslateRequest(BaseModel):
    text: str
    src_lang: str = "en"
    tgt_lang: str = "fr"
    provider: Optional[str] = None
    glossary: Optional[str] = None
    meta: dict[str, object] = Field(default_factory=dict)


class TranslateResponse(BaseModel):
    id: str
    status: str
    result: Optional[dict[str, object]] = None
    error: Optional[str] = None


@app.post("/translate", response_model=TranslateResponse)
def post_translate(payload: TranslateRequest) -> TranslateResponse:
    queue = get_translation_queue()
    request = TranslationRequest(
        text=payload.text,
        src_lang=payload.src_lang,
        tgt_lang=payload.tgt_lang,
        provider_name=payload.provider,
        glossary_path=payload.glossary,
        meta=payload.meta,
    )
    try:
        job = queue.enqueue(request)
    except NotConfigured as exc:  # pragma: no cover - handled via provider
        raise HTTPException(status_code=400, detail=str(exc))
    return TranslateResponse(id=job.id, status=job.status)


@app.get("/jobs")
def get_jobs() -> list[dict[str, object]]:
    queue = get_translation_queue()
    return [job.to_dict() for job in queue.list_jobs()]


@app.get("/datasets")
def get_datasets() -> list[dict[str, object]]:
    registry = get_dataset_registry()
    return [record.to_dict() for record in registry.list()]
