"""Compose API router - unified Clean + Translate + Glossary pipeline."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sagemtl.clean.pipeline import CleanOptions, clean_text
from sagemtl.clean.text_normalize import NormalizeOptions
from sagemtl.translate import TranslationRequest, get_translation_queue, NotConfigured
from sagemtl.translate.glossary import apply_glossary, load_glossary

router = APIRouter(prefix="/api/compose", tags=["compose"])


class ComposeCleanOptions(BaseModel):
    """Enhanced clean options with glossary support."""

    smart_quotes: bool = True
    em_dash: bool = True
    minus_sign: bool = True
    nbsp_to_space: bool = True
    zero_width: bool = True
    collapse_blank_lines: bool = True
    ensure_trailing_lf: bool = True
    trim_trailing_spaces: bool = True
    unicode_nfkc: bool = True
    normalize_eol: str = "lf"  # lf, crlf, or preserve
    apply_glossary: bool = False
    glossary_path: Optional[str] = None


class ComposeCleanRequest(BaseModel):
    text: str
    options: ComposeCleanOptions = Field(default_factory=ComposeCleanOptions)


class ComposeCleanResponse(BaseModel):
    text: str
    meta: dict[str, object]
    glossary_applied: bool = False


@router.post("/clean", response_model=ComposeCleanResponse)
def compose_clean(payload: ComposeCleanRequest) -> ComposeCleanResponse:
    """
    Clean text with enhanced options including glossary support.

    This is the unified clean endpoint for the Compose screen.
    """
    options = NormalizeOptions(
        smart_quotes=payload.options.smart_quotes,
        em_dash=payload.options.em_dash,
        minus_sign=payload.options.minus_sign,
        nbsp_to_space=payload.options.nbsp_to_space,
        zero_width=payload.options.zero_width,
        collapse_blank_lines=payload.options.collapse_blank_lines,
        ensure_trailing_lf=payload.options.ensure_trailing_lf,
    )

    result = clean_text(payload.text, options=CleanOptions(normalize=options))
    cleaned_text = result.text
    glossary_applied = False

    # Apply glossary if requested
    if payload.options.apply_glossary and payload.options.glossary_path:
        glossary_entries = load_glossary(payload.options.glossary_path)
        if glossary_entries:
            cleaned_text = apply_glossary(cleaned_text, glossary_entries)
            glossary_applied = True

    return ComposeCleanResponse(text=cleaned_text, meta=result.meta, glossary_applied=glossary_applied)


class ComposeTranslateRequest(BaseModel):
    text: str
    src_lang: str = "auto"
    tgt_lang: str = "en"
    provider: Optional[str] = None
    glossary_path: Optional[str] = None
    apply_glossary_pre: bool = False
    apply_glossary_post: bool = True
    dataset_id: Optional[str] = None
    save_to_dataset: bool = False


class ComposeTranslateResponse(BaseModel):
    job_id: str
    status: str


@router.post("/translate", response_model=ComposeTranslateResponse)
def compose_translate(payload: ComposeTranslateRequest) -> ComposeTranslateResponse:
    """
    Queue a translation job with optional glossary pre/post-processing.

    Returns job_id for tracking via WebSocket or polling.
    """
    # Apply pre-translation glossary if requested
    text_to_translate = payload.text
    if payload.apply_glossary_pre and payload.glossary_path:
        glossary_entries = load_glossary(payload.glossary_path)
        if glossary_entries:
            text_to_translate = apply_glossary(text_to_translate, glossary_entries)

    queue = get_translation_queue()
    request = TranslationRequest(
        text=text_to_translate,
        src_lang=payload.src_lang,
        tgt_lang=payload.tgt_lang,
        provider_name=payload.provider,
        glossary_path=payload.glossary_path if payload.apply_glossary_post else None,
        meta={
            "dataset_id": payload.dataset_id,
            "save_to_dataset": payload.save_to_dataset,
            "apply_glossary_post": payload.apply_glossary_post,
        },
    )

    try:
        job = queue.enqueue(request)
    except NotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ComposeTranslateResponse(job_id=job.id, status=job.status)


class ComposePipelineRequest(BaseModel):
    """Full pipeline: Import → Clean → Translate → Glossary → Save."""

    source_text: str
    dataset_id: Optional[str] = None
    clean_options: ComposeCleanOptions = Field(default_factory=ComposeCleanOptions)
    src_lang: str = "auto"
    tgt_lang: str = "en"
    provider: Optional[str] = None
    glossary_path: Optional[str] = None
    save_to_dataset: bool = True


class ComposePipelineResponse(BaseModel):
    clean_job_id: Optional[str] = None
    translate_job_id: str
    status: str
    message: str


@router.post("/pipeline", response_model=ComposePipelineResponse)
def compose_pipeline(payload: ComposePipelineRequest) -> ComposePipelineResponse:
    """
    Execute the full Compose pipeline:
    1. Clean text
    2. Apply pre-translate glossary
    3. Queue translation job
    4. Result will have post-translate glossary applied by worker
    5. Save to dataset (if requested)

    Returns the translation job_id for tracking.
    """
    # Step 1: Clean
    clean_result = compose_clean(ComposeCleanRequest(text=payload.source_text, options=payload.clean_options))

    # Step 2 & 3: Translate (with glossary)
    translate_result = compose_translate(
        ComposeTranslateRequest(
            text=clean_result.text,
            src_lang=payload.src_lang,
            tgt_lang=payload.tgt_lang,
            provider=payload.provider,
            glossary_path=payload.glossary_path,
            apply_glossary_pre=False,
            apply_glossary_post=True,
            dataset_id=payload.dataset_id,
            save_to_dataset=payload.save_to_dataset,
        )
    )

    return ComposePipelineResponse(
        translate_job_id=translate_result.job_id,
        status="queued",
        message="Pipeline queued successfully. Track via /api/jobs/{job_id}",
    )
