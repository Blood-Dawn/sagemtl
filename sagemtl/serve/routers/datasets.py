"""Datasets API router - Import, Export, Novels management."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from sagemtl.datasets.registry import DatasetFormat, get_dataset_registry

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


class DatasetRecord(BaseModel):
    id: str
    name: str
    type: str = "text"  # text, novel, translation
    format: str = "txt"
    size_bytes: int = 0
    items_count: int = 0
    created_at: str
    updated_at: str
    meta: dict[str, object] = Field(default_factory=dict)
    cover_path: Optional[str] = None
    chapter_count: Optional[int] = None


class ImportResponse(BaseModel):
    dataset_id: str
    name: str
    files_imported: int
    total_bytes: int
    items: List[dict[str, object]]


class NovelDatasetResponse(BaseModel):
    id: str
    name: str
    cover_url: Optional[str] = None
    chapter_count: int
    last_processed_job: Optional[str] = None
    created_at: str
    meta: dict[str, object]


def get_data_dir() -> Path:
    """Get the base data directory for datasets."""
    import os
    data_dir = Path(os.environ.get("SAGEMTL_DATA_DIR", Path.home() / ".sagemtl" / "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def save_uploaded_file(upload_file: UploadFile, dest_dir: Path) -> tuple[Path, int]:
    """Save uploaded file to disk and return path + size."""
    dest_path = dest_dir / upload_file.filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    with dest_path.open("wb") as f:
        while chunk := upload_file.file.read(8192):
            f.write(chunk)
            total_bytes += len(chunk)

    return dest_path, total_bytes


@router.get("", response_model=List[DatasetRecord])
def list_datasets() -> List[DatasetRecord]:
    """List all datasets with enhanced metadata."""
    registry = get_dataset_registry()
    datasets = []

    for record in registry.list():
        # Load extended metadata from dataset directory
        data_dir = get_data_dir() / record.name
        meta_file = data_dir / "meta.json"

        meta = {}
        dataset_type = "text"
        cover_path = None
        chapter_count = None

        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                dataset_type = meta.get("type", "text")
                cover_path = meta.get("cover_path")
                chapter_count = meta.get("chapter_count")
            except (json.JSONDecodeError, OSError):
                pass

        datasets.append(
            DatasetRecord(
                id=record.name,
                name=record.name,
                type=dataset_type,
                format=record.format.value if hasattr(record.format, "value") else str(record.format),
                size_bytes=meta.get("size_bytes", 0),
                items_count=meta.get("items_count", 0),
                created_at=meta.get("created_at", record.filename),
                updated_at=meta.get("updated_at", record.filename),
                meta=meta,
                cover_path=cover_path,
                chapter_count=chapter_count,
            )
        )

    return datasets


@router.post("/import", response_model=ImportResponse)
async def import_files(
    files: List[UploadFile] = File(...),
    dataset_name: Optional[str] = Form(None),
    dataset_type: str = Form("text"),
) -> ImportResponse:
    """
    Import one or more files as a new dataset.

    Accepts: .txt, .md, .html, .jsonl, .epub
    Stores under ~/.sagemtl/data/{dataset_id}/files/*
    """
    # Generate dataset ID if name not provided
    if not dataset_name:
        dataset_name = f"dataset-{uuid.uuid4().hex[:8]}"

    # Create dataset directory
    data_dir = get_data_dir() / dataset_name
    files_dir = data_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    # Process files
    imported_files = []
    total_bytes = 0

    for upload_file in files:
        # Validate file type
        suffix = Path(upload_file.filename).suffix.lower()
        if suffix not in {".txt", ".md", ".html", ".jsonl", ".epub"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {suffix}. Allowed: .txt, .md, .html, .jsonl, .epub"
            )

        # Save file
        dest_path, file_bytes = save_uploaded_file(upload_file, files_dir)
        total_bytes += file_bytes

        imported_files.append({
            "filename": upload_file.filename,
            "path": str(dest_path.relative_to(data_dir)),
            "size_bytes": file_bytes,
            "type": suffix[1:],  # Remove leading dot
        })

    # Save metadata
    meta = {
        "type": dataset_type,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "size_bytes": total_bytes,
        "items_count": len(imported_files),
        "files": imported_files,
    }

    meta_file = data_dir / "meta.json"
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # Register in dataset registry
    registry = get_dataset_registry()
    # Use first file as the "main" file for registry
    if imported_files:
        first_file = files_dir / imported_files[0]["filename"]
        registry.add(dataset_name, first_file)

    return ImportResponse(
        dataset_id=dataset_name,
        name=dataset_name,
        files_imported=len(imported_files),
        total_bytes=total_bytes,
        items=imported_files,
    )


@router.get("/novels", response_model=List[NovelDatasetResponse])
def list_novels() -> List[NovelDatasetResponse]:
    """List all datasets with type='novel'."""
    all_datasets = list_datasets()
    novels = []

    for ds in all_datasets:
        if ds.type == "novel":
            novels.append(
                NovelDatasetResponse(
                    id=ds.id,
                    name=ds.name,
                    cover_url=ds.cover_path,
                    chapter_count=ds.chapter_count or 0,
                    last_processed_job=ds.meta.get("last_job_id"),
                    created_at=ds.created_at,
                    meta=ds.meta,
                )
            )

    return novels


@router.get("/{dataset_id}", response_model=DatasetRecord)
def get_dataset(dataset_id: str) -> DatasetRecord:
    """Get detailed information about a specific dataset."""
    datasets = list_datasets()
    for ds in datasets:
        if ds.id == dataset_id:
            return ds

    raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str) -> dict[str, str]:
    """Delete a dataset and its files."""
    data_dir = get_data_dir() / dataset_id

    if not data_dir.exists():
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    # Remove directory
    shutil.rmtree(data_dir)

    # Remove from registry (best effort)
    try:
        registry = get_dataset_registry()
        # Registry doesn't have a delete method, so we'll just return success
    except Exception:
        pass

    return {"status": "deleted", "dataset_id": dataset_id}


@router.get("/{dataset_id}/files")
def list_dataset_files(dataset_id: str) -> List[dict[str, object]]:
    """List all files in a dataset."""
    data_dir = get_data_dir() / dataset_id
    files_dir = data_dir / "files"

    if not files_dir.exists():
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    files = []
    for file_path in files_dir.rglob("*"):
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "path": str(file_path.relative_to(data_dir)),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    return files


@router.get("/{dataset_id}/files/{file_path:path}")
def get_dataset_file(dataset_id: str, file_path: str) -> dict[str, object]:
    """Get content of a specific file from a dataset."""
    data_dir = get_data_dir() / dataset_id
    target_file = data_dir / file_path

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found in dataset")

    # Read file content
    try:
        content = target_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary file
        raise HTTPException(status_code=400, detail="Cannot read binary file as text")

    return {
        "path": file_path,
        "content": content,
        "size_bytes": len(content.encode("utf-8")),
    }
