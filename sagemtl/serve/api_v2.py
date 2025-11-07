"""Enhanced FastAPI application with modular routers and WebSocket support."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sagemtl.serve.routers import compose_router, datasets_router, crawl_router, jobs_router, settings_router

# Create app
app = FastAPI(
    title="SageMTL API",
    version="2.0",
    description="Complete machine translation toolchain with Import → Process → Export workflow",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(compose_router)
app.include_router(datasets_router)
app.include_router(crawl_router)
app.include_router(jobs_router)
app.include_router(settings_router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "SageMTL API",
        "version": "2.0",
        "docs": "/docs",
        "endpoints": {
            "compose": "/api/compose/*",
            "datasets": "/api/datasets/*",
            "crawl": "/api/crawl/*",
            "jobs": "/api/jobs/*",
            "settings": "/api/settings/*",
        },
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Legacy endpoints for backward compatibility
from sagemtl.clean.pipeline import CleanOptions, clean_text
from sagemtl.clean.text_normalize import NormalizeOptions
from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi import HTTPException


class LegacyCleanRequest(BaseModel):
    text: str
    options: dict = Field(default_factory=dict)


class LegacyCleanResponse(BaseModel):
    text: str
    meta: dict[str, object]


@app.post("/clean", response_model=LegacyCleanResponse, tags=["legacy"])
def legacy_clean(payload: LegacyCleanRequest) -> LegacyCleanResponse:
    """Legacy clean endpoint (for backward compatibility)."""
    options = NormalizeOptions(
        smart_quotes=payload.options.get("smart_quotes", True),
        em_dash=payload.options.get("em_dash", True),
        minus_sign=payload.options.get("minus_sign", True),
        nbsp_to_space=payload.options.get("nbsp_to_space", True),
        zero_width=payload.options.get("zero_width", True),
        collapse_blank_lines=payload.options.get("collapse_blank_lines", True),
        ensure_trailing_lf=payload.options.get("ensure_trailing_lf", True),
    )

    result = clean_text(payload.text, options=CleanOptions(normalize=options))
    return LegacyCleanResponse(text=result.text, meta=result.meta)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
