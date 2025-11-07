"""Settings API router - Configuration management."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sagemtl.config import load_config, save_config, update_config, Settings as AppSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    newline_mode: str
    clean_input_path: str
    clean_output_path: str | None
    crawl_glob: str
    crawl_outdir: str
    crawl_jsonl: bool
    thread_count: int


class SettingsUpdateRequest(BaseModel):
    newline_mode: str | None = None
    clean_input_path: str | None = None
    clean_output_path: str | None = None
    crawl_glob: str | None = None
    crawl_outdir: str | None = None
    crawl_jsonl: bool | None = None
    thread_count: int | None = None


@router.get("", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    """Get current application settings from config.toml."""
    config = load_config()
    return SettingsResponse(
        newline_mode=config.newline_mode,
        clean_input_path=config.clean_input_path,
        clean_output_path=config.clean_output_path,
        crawl_glob=config.crawl_glob,
        crawl_outdir=config.crawl_outdir,
        crawl_jsonl=config.crawl_jsonl,
        thread_count=config.thread_count,
    )


@router.put("", response_model=SettingsResponse)
def update_settings(request: SettingsUpdateRequest) -> SettingsResponse:
    """Update application settings and persist to config.toml."""
    # Build updates dict from non-None fields
    updates: Dict[str, Any] = {}

    if request.newline_mode is not None:
        updates["newline_mode"] = request.newline_mode
    if request.clean_input_path is not None:
        updates["clean_input_path"] = request.clean_input_path
    if request.clean_output_path is not None:
        updates["clean_output_path"] = request.clean_output_path
    if request.crawl_glob is not None:
        updates["crawl_glob"] = request.crawl_glob
    if request.crawl_outdir is not None:
        updates["crawl_outdir"] = request.crawl_outdir
    if request.crawl_jsonl is not None:
        updates["crawl_jsonl"] = request.crawl_jsonl
    if request.thread_count is not None:
        updates["thread_count"] = request.thread_count

    try:
        new_config = update_config(updates)
        return SettingsResponse(
            newline_mode=new_config.newline_mode,
            clean_input_path=new_config.clean_input_path,
            clean_output_path=new_config.clean_output_path,
            crawl_glob=new_config.crawl_glob,
            crawl_outdir=new_config.crawl_outdir,
            crawl_jsonl=new_config.crawl_jsonl,
            thread_count=new_config.thread_count,
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/reset")
def reset_settings() -> dict[str, str]:
    """Reset settings to defaults."""
    try:
        default_settings = AppSettings()
        save_config(default_settings)
        return {"status": "reset", "message": "Settings reset to defaults"}
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reset settings: {exc}")
