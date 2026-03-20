"""
pipeline/history.py
──────────────────────────────────────────────────────────────────────────────
Query history endpoints: list, favorite toggle, delete.
All routes require authentication and operate on the current user's history.
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from auth.models import User
from core.database import get_db
from core.exceptions import NotFoundError
from datasets.models import HistoryItemResponse, QueryHistory

logger = structlog.get_logger()
router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryItemResponse])
async def list_history(
    dataset_id: uuid.UUID | None = Query(None, description="Filter by dataset"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[HistoryItemResponse]:
    """
    Return query history for the current user, newest first.
    Optionally filter by dataset_id.
    """
    stmt = (
        select(QueryHistory)
        .where(QueryHistory.user_id == current_user.id)
        .order_by(QueryHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if dataset_id:
        stmt = stmt.where(QueryHistory.dataset_id == dataset_id)

    result = await db.execute(stmt)
    return [HistoryItemResponse.model_validate(h) for h in result.scalars().all()]


@router.patch("/{history_id}/favorite")
async def toggle_favorite(
    history_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Toggle the favorite status of a history entry."""
    result = await db.execute(
        select(QueryHistory).where(
            QueryHistory.id == history_id,
            QueryHistory.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise NotFoundError("History entry not found.")

    entry.is_favorited = not entry.is_favorited
    await db.flush()

    logger.info(
        "history_favorite_toggled",
        history_id=str(history_id),
        is_favorited=entry.is_favorited,
    )
    return {"id": str(entry.id), "is_favorited": entry.is_favorited}


@router.delete("/{history_id}")
async def delete_history_entry(
    history_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a single history entry."""
    result = await db.execute(
        select(QueryHistory).where(
            QueryHistory.id == history_id,
            QueryHistory.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise NotFoundError("History entry not found.")

    await db.delete(entry)
    logger.info("history_entry_deleted", history_id=str(history_id))
