"""
datasets/models.py
──────────────────────────────────────────────────────────────────────────────
SQLAlchemy ORM models for datasets, dashboards, and query history.
Pydantic response schemas are also defined here.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

JSONVariant = JSON().with_variant(JSONB, "postgresql")
UUIDVariant = Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql")

from core.database import Base


# ── SQLAlchemy ORM models ─────────────────────────────────────────────────────

class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDVariant, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDVariant, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    col_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    db_path: Mapped[str] = mapped_column(Text, nullable=False)
    schema_json: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    pii_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDVariant, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDVariant, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUIDVariant, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    share_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class QueryHistory(Base):
    __tablename__ = "query_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDVariant, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDVariant, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUIDVariant, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    is_favorited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


# ── Pydantic response schemas ──────────────────────────────────────────────────

class DatasetResponse(BaseModel):
    id: str
    name: str
    original_filename: str | None
    row_count: int | None
    col_count: int | None
    size_bytes: int | None
    pii_detected: bool
    created_at: datetime
    schema_json: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    id: str
    dataset_id: str
    name: str
    prompt: str | None
    result_json: dict[str, Any]
    is_public: bool
    share_token: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryItemResponse(BaseModel):
    id: str
    prompt: str
    result_json: dict[str, Any] | None
    is_favorited: bool
    created_at: datetime

    model_config = {"from_attributes": True}
