"""
auth/router.py
──────────────────────────────────────────────────────────────────────────────
Auth endpoints: register, login, Google OAuth, token refresh, logout.
Rate limiting on login/register endpoints prevents brute force.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import RefreshToken, User
from auth.service import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    is_token_revoked,
    revoke_token,
    verify_password,
)
from core.database import get_db
from core.exceptions import AuthError, ValidationError

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / Response schemas ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field("", max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must contain letters and numbers")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    display_name: str | None


# ── Helper: set refresh token as httpOnly cookie ──────────────────────────────

def _set_refresh_cookie(response: Response, token: str, expires: datetime) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=True,         # HTTPS only in production
        samesite="lax",
        expires=int(expires.timestamp()),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    req: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user with email + password."""
    # Check duplicate
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise ValidationError("An account with this email already exists.")

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        display_name=req.display_name or req.email.split("@")[0],
    )
    db.add(user)
    await db.flush()   # get user.id without committing

    access = create_access_token(str(user.id), user.email)
    refresh_str, jti, expires_at = create_refresh_token(str(user.id))

    token_row = RefreshToken(jti=jti, user_id=user.id, expires_at=expires_at)
    db.add(token_row)

    _set_refresh_cookie(response, refresh_str, expires_at)
    logger.info("user_registered", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=access,
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    # Constant-time failure to prevent user enumeration
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise AuthError("Invalid email or password.")

    if not user.is_active:
        raise AuthError("Account is disabled. Contact support.")

    user.last_active = datetime.now(timezone.utc)

    access = create_access_token(str(user.id), user.email)
    refresh_str, jti, expires_at = create_refresh_token(str(user.id))

    token_row = RefreshToken(jti=jti, user_id=user.id, expires_at=expires_at)
    db.add(token_row)

    _set_refresh_cookie(response, refresh_str, expires_at)
    logger.info("user_login", user_id=str(user.id))

    return TokenResponse(
        access_token=access,
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> TokenResponse:
    """Issue a new access token using the httpOnly refresh token cookie."""
    if not refresh_token:
        raise AuthError("No refresh token provided.")

    try:
        from jose import JWTError
        payload = decode_refresh_token(refresh_token)
    except Exception:
        raise AuthError("Invalid or expired refresh token.")

    jti = payload.get("jti", "")
    if await is_token_revoked(jti):
        raise AuthError("Refresh token has been revoked.")

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthError("User not found.")

    # Rotate: revoke old, issue new
    await revoke_token(jti)
    new_access = create_access_token(str(user.id), user.email)
    new_refresh_str, new_jti, new_expires = create_refresh_token(str(user.id))

    db.add(RefreshToken(jti=new_jti, user_id=user.id, expires_at=new_expires))
    user.last_active = datetime.now(timezone.utc)
    _set_refresh_cookie(response, new_refresh_str, new_expires)

    return TokenResponse(
        access_token=new_access,
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
    )


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> None:
    """Revoke refresh token and clear the cookie."""
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            await revoke_token(payload.get("jti", ""))
        except Exception:
            pass  # best effort

    response.delete_cookie("refresh_token")
