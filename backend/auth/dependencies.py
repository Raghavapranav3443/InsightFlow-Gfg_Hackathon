"""
auth/dependencies.py
──────────────────────────────────────────────────────────────────────────────
FastAPI dependencies for authentication.
Every protected route uses `current_user: User = Depends(get_current_user)`.
"""
from __future__ import annotations

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User
from auth.service import decode_access_token
from core.database import get_db
from core.exceptions import AuthError

logger = structlog.get_logger()
security = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate Bearer JWT and return the authenticated User.
    Raises AuthError(401) if token is missing, invalid, or expired.
    Raises AuthError(401) if user not found or deactivated.
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload["sub"]
    except (JWTError, KeyError) as exc:
        logger.warning("invalid_access_token", error=str(exc))
        raise AuthError("Invalid or expired token. Please log in again.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise AuthError("User account not found or deactivated.")

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Like get_current_user but returns None if no auth header is present.
    Used for endpoints that support both authenticated and anonymous access
    (e.g., public shared dashboards).
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except AuthError:
        return None
