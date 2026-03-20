"""
dashboards/service.py
──────────────────────────────────────────────────────────────────────────────
Business logic for dashboard CRUD and sharing.
All ownership checks are performed at the service layer — routers delegate here.
"""
from __future__ import annotations

import secrets
import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datasets.models import Dashboard, DashboardResponse

logger = structlog.get_logger()


async def list_dashboards(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[DashboardResponse]:
    """Return all dashboards owned by the user, newest first."""
    result = await db.execute(
        select(Dashboard)
        .where(Dashboard.user_id == user_id)
        .order_by(Dashboard.updated_at.desc())
    )
    return [DashboardResponse.model_validate(d) for d in result.scalars().all()]


async def create_dashboard(
    db: AsyncSession,
    user_id: uuid.UUID,
    dataset_id: uuid.UUID,
    name: str,
    prompt: str | None,
    result_json: dict[str, Any],
) -> Dashboard:
    """Create and persist a new dashboard."""
    dashboard = Dashboard(
        id=uuid.uuid4(),
        user_id=user_id,
        dataset_id=dataset_id,
        name=name.strip(),
        prompt=prompt,
        result_json=result_json,
    )
    db.add(dashboard)
    await db.flush()
    logger.info("dashboard_created", dashboard_id=str(dashboard.id), user_id=str(user_id))
    return dashboard


async def get_dashboard(
    db: AsyncSession,
    dashboard_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Dashboard | None:
    """Fetch a dashboard by ID, returns None if not found or not owned."""
    result = await db.execute(
        select(Dashboard).where(
            Dashboard.id == dashboard_id,
            Dashboard.user_id == owner_id,
        )
    )
    return result.scalar_one_or_none()


async def get_dashboard_by_share_token(
    db: AsyncSession,
    token: str,
) -> Dashboard | None:
    """Fetch a public dashboard by its share token. No ownership check — public access."""
    result = await db.execute(
        select(Dashboard).where(
            Dashboard.share_token == token,
            Dashboard.is_public == True,  # noqa: E712 — SQLAlchemy requires == for filters
        )
    )
    return result.scalar_one_or_none()


async def delete_dashboard(
    db: AsyncSession,
    dashboard_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> bool:
    """Delete a dashboard. Returns True if found and deleted, False otherwise."""
    dashboard = await get_dashboard(db, dashboard_id, owner_id)
    if not dashboard:
        return False
    await db.delete(dashboard)
    logger.info("dashboard_deleted", dashboard_id=str(dashboard_id), user_id=str(owner_id))
    return True


async def generate_share_token(
    db: AsyncSession,
    dashboard_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> str | None:
    """
    Generate a unique share token and mark the dashboard as public.
    Returns the token, or None if dashboard not found.
    """
    dashboard = await get_dashboard(db, dashboard_id, owner_id)
    if not dashboard:
        return None

    if not dashboard.share_token:
        dashboard.share_token = secrets.token_urlsafe(32)
    dashboard.is_public = True
    await db.flush()
    logger.info(
        "dashboard_shared",
        dashboard_id=str(dashboard_id),
        share_token=dashboard.share_token[:8] + "...",
    )
    return dashboard.share_token


async def unshare_dashboard(
    db: AsyncSession,
    dashboard_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> bool:
    """Revoke public sharing for a dashboard."""
    dashboard = await get_dashboard(db, dashboard_id, owner_id)
    if not dashboard:
        return False
    dashboard.is_public = False
    dashboard.share_token = None
    await db.flush()
    logger.info("dashboard_unshared", dashboard_id=str(dashboard_id))
    return True
