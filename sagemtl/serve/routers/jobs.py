"""Jobs API router - Job management with WebSocket progress streaming."""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from sagemtl.jobs.store import get_job_store

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    created_at: str
    updated_at: str
    meta: dict[str, object]
    result: Optional[dict[str, object]] = None
    error: Optional[str] = None
    log: list[str]
    log_path: Optional[str] = None
    progress: Optional[float] = None


@router.get("", response_model=list[JobResponse])
def list_jobs() -> list[JobResponse]:
    """List all jobs with full details."""
    store = get_job_store()
    jobs = []

    for job in store.list():
        jobs.append(
            JobResponse(
                id=job.id,
                type=job.type,
                status=job.status,
                created_at=job.created_at,
                updated_at=job.updated_at,
                meta=job.meta,
                result=job.result,
                error=job.error,
                log=job.log,
                log_path=job.log_path,
                progress=job.meta.get("progress") if hasattr(job, "meta") else None,
            )
        )

    return jobs


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    """Get detailed information about a specific job."""
    store = get_job_store()
    job = store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return JobResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        meta=job.meta,
        result=job.result,
        error=job.error,
        log=job.log,
        log_path=job.log_path,
        progress=job.meta.get("progress") if hasattr(job, "meta") else None,
    )


@router.delete("/{job_id}")
def cancel_job(job_id: str) -> dict[str, str]:
    """Cancel a running or queued job."""
    store = get_job_store()
    job = store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job.status in ("queued", "running"):
        job.status = "cancelled"
        job.error = "Cancelled by user"
        store.upsert(job)

    return {"status": "cancelled", "job_id": job_id}


@router.get("/{job_id}/log", response_model=dict[str, str])
def get_job_log(job_id: str) -> dict[str, str]:
    """Get the log file content for a job."""
    from pathlib import Path

    store = get_job_store()
    job = store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if not job.log_path:
        # If no log file exists, return the in-memory log
        return {"log": "\n".join(job.log), "source": "memory"}

    try:
        log_file = Path(job.log_path)
        if not log_file.exists():
            # Fallback to in-memory log
            return {"log": "\n".join(job.log), "source": "memory"}

        log_content = log_file.read_text(encoding="utf-8")
        return {"log": log_content, "source": "file", "path": str(log_file)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {exc}")


@router.websocket("/ws/{job_id}")
async def job_progress_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.

    Client receives JSON messages with job status:
    {
        "type": "progress",
        "job_id": "...",
        "status": "running",
        "progress": 0.5,
        "message": "Processing...",
        "updated_at": "..."
    }

    When job completes:
    {
        "type": "complete",
        "job_id": "...",
        "status": "done",
        "result": {...}
    }
    """
    await websocket.accept()

    store = get_job_store()
    last_status = None
    last_updated = None

    try:
        while True:
            job = store.get(job_id)

            if not job:
                await websocket.send_json({"type": "error", "message": f"Job '{job_id}' not found"})
                break

            # Send update if status changed or job updated
            if job.status != last_status or job.updated_at != last_updated:
                if job.status in ("done", "failed", "cancelled"):
                    # Job completed
                    await websocket.send_json(
                        {
                            "type": "complete",
                            "job_id": job.id,
                            "status": job.status,
                            "result": job.result,
                            "error": job.error,
                            "updated_at": job.updated_at,
                        }
                    )
                    break
                else:
                    # Job still running
                    await websocket.send_json(
                        {
                            "type": "progress",
                            "job_id": job.id,
                            "status": job.status,
                            "progress": job.meta.get("progress", 0.0),
                            "message": job.log[-1] if job.log else "",
                            "updated_at": job.updated_at,
                        }
                    )

                last_status = job.status
                last_updated = job.updated_at

            # Poll every 500ms
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@router.post("/{job_id}/retry")
def retry_job(job_id: str) -> dict[str, str]:
    """Retry a failed job (re-queues with same parameters)."""
    store = get_job_store()
    job = store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=400, detail=f"Can only retry failed/cancelled jobs. Current status: {job.status}"
        )

    # Re-queue the job
    if job.type == "translate":
        from sagemtl.translate import TranslationRequest, get_translation_queue

        queue = get_translation_queue()
        payload = job.payload

        request = TranslationRequest(
            text=str(payload.get("text", "")),
            src_lang=str(payload.get("src_lang", "en")),
            tgt_lang=str(payload.get("tgt_lang", "fr")),
            provider_name=str(payload.get("provider")),
            glossary_path=payload.get("glossary"),
            meta=job.meta,
        )

        new_job = queue.enqueue(request)
        return {"status": "retried", "new_job_id": new_job.id}

    raise HTTPException(status_code=400, detail=f"Cannot retry job of type '{job.type}'")


@router.delete("")
def purge_jobs(keep_running: bool = True) -> dict[str, int]:
    """
    Purge completed jobs from storage.

    By default, keeps queued/running jobs. Set keep_running=false to purge all.
    """
    store = get_job_store()
    statuses = {"queued", "running"} if keep_running else set()
    removed = store.purge(statuses=statuses)

    return {"purged": len(removed)}
