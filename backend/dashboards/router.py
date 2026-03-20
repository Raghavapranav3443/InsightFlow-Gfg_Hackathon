"""
dashboards/router.py
──────────────────────────────────────────────────────────────────────────────
Dashboard management endpoints: list, create, get, delete, share, public view.
All routes (except /share/{token}) require authentication.
Ownership is verified in the service layer — 404 for not-found OR not-owned
(never confirm existence of another user's resource with 403).
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from auth.models import User
from core.database import get_db
from core.exceptions import NotFoundError
from dashboards import service as dashboard_service
from datasets.models import DashboardResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/dashboards", tags=["dashboards"])


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateDashboardRequest(BaseModel):
    dataset_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    prompt: str | None = None
    result_json: dict[str, Any]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[DashboardResponse])
async def list_dashboards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DashboardResponse]:
    """Return all dashboards owned by the current user."""
    return await dashboard_service.list_dashboards(db, current_user.id)


@router.post("", status_code=201, response_model=DashboardResponse)
async def create_dashboard(
    req: CreateDashboardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Save a new dashboard."""
    dashboard = await dashboard_service.create_dashboard(
        db=db,
        user_id=current_user.id,
        dataset_id=req.dataset_id,
        name=req.name,
        prompt=req.prompt,
        result_json=req.result_json,
    )
    return DashboardResponse.model_validate(dashboard)


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Get a single dashboard by ID (ownership-checked)."""
    dashboard = await dashboard_service.get_dashboard(db, dashboard_id, current_user.id)
    if not dashboard:
        raise NotFoundError("Dashboard not found.")
    return DashboardResponse.model_validate(dashboard)


@router.delete("/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a dashboard."""
    if not await dashboard_service.delete_dashboard(db, dashboard_id, current_user.id):
        raise NotFoundError("Dashboard not found.")


@router.post("/{dashboard_id}/share")
async def share_dashboard(
    dashboard_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a public share token for a dashboard."""
    token = await dashboard_service.generate_share_token(db, dashboard_id, current_user.id)
    if not token:
        raise NotFoundError("Dashboard not found.")
    return {"share_token": token, "share_url": f"/share/{token}"}


@router.delete("/{dashboard_id}/share")
async def unshare_dashboard(
    dashboard_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke public sharing for a dashboard."""
    if not await dashboard_service.unshare_dashboard(db, dashboard_id, current_user.id):
        raise NotFoundError("Dashboard not found.")


# ── Public endpoint (no auth) ────────────────────────────────────────────────

share_router = APIRouter(tags=["sharing"])


@share_router.get("/share/{token}", response_model=DashboardResponse)
async def get_shared_dashboard(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """
    Public read-only view of a shared dashboard.
    No authentication required — anyone with the token can view.
    """
    dashboard = await dashboard_service.get_dashboard_by_share_token(db, token)
    if not dashboard:
        raise NotFoundError("Shared dashboard not found or is no longer public.")
    return DashboardResponse.model_validate(dashboard)
