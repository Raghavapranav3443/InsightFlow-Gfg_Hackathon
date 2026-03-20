"""
auth/service.py
──────────────────────────────────────────────────────────────────────────────
JWT creation/validation, bcrypt hashing, Google OAuth token exchange.
All auth business logic lives here — router only calls these functions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import get_settings
from core.redis import redis_exists, redis_set

logger = structlog.get_logger()
cfg = get_settings()

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(plaintext: str) -> str:
    return pwd_ctx.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    return pwd_ctx.verify(plaintext, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    """Create a short-lived JWT access token (15 min default)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, cfg.SECRET_KEY, algorithm=cfg.ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, uuid.UUID, datetime]:
    """
    Create a long-lived refresh token.
    Returns (token_str, jti, expires_at) so the caller can persist jti to DB.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=cfg.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = uuid.uuid4()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(jti),
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, cfg.SECRET_KEY, algorithm=cfg.ALGORITHM)
    return token, jti, expire


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access token.
    Raises JWTError on failure.
    """
    payload = jwt.decode(token, cfg.SECRET_KEY, algorithms=[cfg.ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a refresh token.
    Raises JWTError on failure.
    """
    payload = jwt.decode(token, cfg.SECRET_KEY, algorithms=[cfg.ALGORITHM])
    if payload.get("type") != "refresh":
        raise JWTError("Not a refresh token")
    return payload


async def is_token_revoked(jti: str) -> bool:
    """Check if a refresh token JTI is in the Redis revocation list."""
    return await redis_exists(f"revoked_token:{jti}")


async def revoke_token(jti: str, ttl_seconds: int = 60 * 60 * 24 * 8) -> None:
    """Add a JTI to the Redis revocation list (TTL = refresh token lifetime + 1 day)."""
    await redis_set(f"revoked_token:{jti}", "1", ttl_seconds=ttl_seconds)
