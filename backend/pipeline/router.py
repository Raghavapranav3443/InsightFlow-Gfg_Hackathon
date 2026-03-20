"""
pipeline/router.py
──────────────────────────────────────────────────────────────────────────────
Pipeline API endpoints.
Provides the SSE streaming endpoint for executing natural language queries.
"""
from __future__ import annotations

import itertools
import uuid

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from auth.dependencies import get_current_user
from auth.models import User
from core.database import get_db
from core.exceptions import NotFoundError, ValidationError
from datasets.models import Dataset
from pipeline.runner import run_pipeline_sse

logger = structlog.get_logger()
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class QueryRequest(BaseModel):
    dataset_id: uuid.UUID
    prompt: str = Field(..., min_length=1, max_length=500)


@router.post("/query")
async def execute_query(
    req: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """
    Execute a natural language query against a dataset and stream progress via SSE.
    """
    prompt = req.prompt.strip()
    if not prompt:
        raise ValidationError("Prompt cannot be empty.")

    # 1. Fetch dataset and verify ownership
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == req.dataset_id,
            Dataset.user_id == current_user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise NotFoundError("Dataset not found or access denied.")

    if not dataset.schema_json:
        raise ValidationError("Dataset schema not found. Re-upload required.")

    # 2. Resolve the ACTUAL SQLite table name from the ingest schema.
    #    The ingest pipeline always writes to a table called "data" (see parser.py:222).
    #    We MUST use this canonical name — NOT dataset.name (which is a user-facing label).
    #    Using dataset.name would cause validate_sql() to reject every LLM-generated query
    #    because the LLM correctly targets FROM "data" but the validator expected a different name.
    table_name: str = dataset.schema_json.get("table_name", "data")

    # 3. Build schema string context for LLM
    cols = dataset.schema_json.get("columns", [])

    schema_lines = [f"TABLE SCHEMA FOR '{table_name}':"]
    for c in cols:
        name = c.get("safe_name", "")
        dtype = c.get("sql_type", c.get("inferred_type", "TEXT"))
        role = c.get("role", "")
        sample_vals = c.get("samples", c.get("sample_values", []))
        sample_str = str(sample_vals)
        sample = "".join(itertools.islice(sample_str, 50))
        if len(sample_str) > 50:
            sample += "..."
        bucket = c.get("bucket_sql")
        line = f" - {name} ({dtype}, {role}) | sample: {sample}"
        if bucket:
            line += f" | bucket_sql: {bucket}"
        schema_lines.append(line)

    schema_context = "\n".join(schema_lines)

    logger.info("pipeline_query_start", user_id=str(current_user.id), dataset_id=str(dataset.id))

    # 4. Stream pipeline execution via SSE
    return EventSourceResponse(
        run_pipeline_sse(
            prompt=prompt,
            dataset=dataset,
            schema_context=schema_context,
            table_name=table_name,
            user_id=current_user.id,
            last_contexts=None,  # Chat history can be injected here later
        )
    )
