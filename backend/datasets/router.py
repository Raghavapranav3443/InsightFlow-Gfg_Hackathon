"""
datasets/router.py
──────────────────────────────────────────────────────────────────────────────
Dataset management endpoints: list, upload CSV, get schema, preview, delete.
All routes require authentication. Ownership is verified for every resource.
"""
from __future__ import annotations

import asyncio
import secrets
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from auth.models import User
from core.config import get_settings
from core.database import get_db
from core.exceptions import DatasetError, NotFoundError, ValidationError
from datasets.models import Dataset, DatasetResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/datasets", tags=["datasets"])
cfg = get_settings()


def _db_path_for_dataset(user_id: str, dataset_id: str) -> Path:
    """Canonical path for a user's SQLite database file."""
    base = Path(cfg.DATA_DIR).resolve()
    return base / str(user_id) / "datasets" / str(dataset_id) / "data.db"


@router.get("", response_model=list[DatasetResponse])
async def list_datasets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DatasetResponse]:
    """Return all datasets owned by the current user."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == current_user.id)
        .order_by(Dataset.created_at.desc())
    )
    datasets = result.scalars().all()
    return [DatasetResponse.model_validate(d) for d in datasets]


@router.post("", status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload a CSV file as a new dataset.
    Runs ingestion in a thread pool to avoid blocking the event loop.
    """
    from datasets.ingest.parser import ingest_csv_to_sqlite

    # ── Limits ────────────────────────────────────────────────────────────────
    existing = await db.execute(
        select(Dataset).where(Dataset.user_id == current_user.id)
    )
    if len(existing.scalars().all()) >= cfg.MAX_DATASETS_PER_USER:
        raise DatasetError(
            f"Dataset limit reached ({cfg.MAX_DATASETS_PER_USER}). "
            "Delete an existing dataset to upload a new one."
        )

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise ValidationError("Only .csv files are accepted.")

    content = await file.read()
    if len(content) > cfg.max_csv_bytes:
        raise ValidationError(f"File too large. Maximum: {cfg.MAX_CSV_SIZE_MB}MB.")

    # ── Create dataset record ─────────────────────────────────────────────────
    dataset_id = uuid.uuid4()
    db_path = _db_path_for_dataset(str(current_user.id), str(dataset_id))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    dataset_name = name.strip() or Path(file.filename).stem

    dataset = Dataset(
        id=dataset_id,
        user_id=current_user.id,
        name=dataset_name,
        original_filename=file.filename,
        db_path=str(db_path),
    )
    db.add(dataset)
    await db.flush()  # get ID before ingestion

    # ── Ingest CSV → SQLite in thread pool ───────────────────────────────────
    try:
        schema_info = await asyncio.to_thread(
            ingest_csv_to_sqlite,
            content,
            str(db_path),
        )
    except Exception as exc:
        logger.error("ingest_failed", error=str(exc), dataset_id=str(dataset_id))
        raise DatasetError(f"CSV import failed: {exc}")

    dataset.row_count = schema_info.get("row_count")
    dataset.col_count = schema_info.get("col_count")
    dataset.size_bytes = len(content)
    dataset.schema_json = schema_info
    dataset.pii_detected = schema_info.get("pii_detected", False)

    logger.info(
        "dataset_uploaded",
        user_id=str(current_user.id),
        dataset_id=str(dataset_id),
        rows=dataset.row_count,
        cols=dataset.col_count,
    )

    return {
        "id": str(dataset.id),
        "name": dataset.name,
        "row_count": dataset.row_count,
        "col_count": dataset.col_count,
        "pii_detected": dataset.pii_detected,
        "schema": schema_info,
    }


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """Get dataset metadata + schema."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == current_user.id,  # ownership check
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise NotFoundError("Dataset not found.")
    return DatasetResponse.model_validate(dataset)


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete a dataset and all associated data."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == current_user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise NotFoundError("Dataset not found.")

    db_path = Path(dataset.db_path)
    await db.delete(dataset)

    # Remove SQLite files from disk in a thread pool (blocking I/O must not run on event loop)
    def _remove_files() -> None:
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass
        # Remove parent directory if empty
        try:
            db_path.parent.rmdir()
        except OSError:
            pass

    await asyncio.to_thread(_remove_files)
    logger.info("dataset_deleted", user_id=str(current_user.id), dataset_id=str(dataset_id))
