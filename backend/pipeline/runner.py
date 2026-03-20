"""
pipeline/runner.py
──────────────────────────────────────────────────────────────────────────────
Orchestrates the two-stage pipeline and streams progress via SSE.
Events emitted:
  - init
  - stage1_start
  - stage1_done
  - sql_exec_start
  - sql_exec_done
  - stage2_start
  - stage2_done
  - insight_start
  - complete
  - error
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal

import structlog

from datasets.models import Dataset, QueryHistory
from pipeline.executor import execute_sql, validate_sql
from pipeline.insight import generate_insight
from pipeline.postprocessor import post_process_chart
from pipeline.stage1_sql import run_stage1
from pipeline.stage2_viz import infer_viz

logger = structlog.get_logger()


async def run_pipeline_sse(
    prompt: str,
    dataset: Dataset,
    schema_context: str,
    table_name: str,
    user_id: uuid.UUID,
    last_contexts: List[Dict[str, Any]] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Generator that yields JSON-encoded Server-Sent Events (SSE).

    Args:
        table_name: The ACTUAL SQLite table name (from schema_json, always "data").
                    Used for SQL validation and LLM prompt generation.
                    NOT dataset.name (which is a user-facing label).
        user_id:    Authenticated user's ID — used to persist query history.
    """

    def _event(event: str, data: Dict[str, Any] | None = None) -> str:
        payload = {"event": event}
        if data:
            payload.update(data)
        return f"data: {json.dumps(payload)}\n\n"

    try:
        yield _event("init", {"message": "Initializing query pipeline..."})
        await asyncio.sleep(0.1)

        # ── Stage 1: SQL Generation ──────────────────────────────────────────
        yield _event("stage1_start", {"message": "Generating SQL (Stage 1)..."})
        
        stage1 = await run_stage1(
            schema_context=schema_context,
            user_prompt=prompt,
            table_name=table_name,
            dataset_id=str(dataset.id),
            last_contexts=last_contexts,
        )

        if stage1.get("cannot_answer"):
            yield _event("error", {"message": stage1.get("reason", "Cannot answer.")})
            return

        if stage1.get("clarification_needed"):
            yield _event("clarify", {"message": stage1.get("clarification_prompt", "Please clarify.")})
            return

        charts_specs = stage1.get("charts", [])
        kpis_specs = stage1.get("kpis", [])

        if not charts_specs and not kpis_specs:
            yield _event("error", {"message": "No queries generated. Please rephrase."})
            return

        yield _event("stage1_done", {"message": "SQL generated successfully."})

        # ── Execute SQL ──────────────────────────────────────────────────────
        yield _event("sql_exec_start", {"message": "Executing SQL queries safely..."})

        chart_results = []
        for spec in charts_specs:
            sql = spec.get("sql", "").strip()
            title = spec.get("title", "Untitled")
            if not sql:
                continue

            try:
                validate_sql(sql, table_name)
                rows = await execute_sql(sql, dataset.db_path)
            except Exception as e:
                logger.warning("sql_execution_failed", title=title, sql=sql, error=str(e))
                chart_results.append({
                    "title": title, "sql": sql, "rows": [],
                    "warning": f"Query execution failed: {e}",
                    "type": "bar", "x_col": "", "y_cols": [], "color_col": None,
                })
                continue

            # Stage 2: Viz Inference
            yield _event("stage2_start", {"message": f"Inferring visualization for '{title}'..."})
            viz = infer_viz(rows)
            
            raw_spec = {
                "title": title,
                "sql": sql,
                "type": viz["type"],
                "x_col": viz["x_col"],
                "y_cols": viz["y_cols"],
                "color_col": viz["color_col"],
            }
            
            # Post-processing (pivoting, truncation, forecasting, correlation)
            final_spec = post_process_chart(raw_spec, rows)
            chart_results.append(final_spec)

        kpi_results = []
        for kspec in kpis_specs:
            sql = kspec.get("sql", "").strip()
            label = kspec.get("label", "")
            fmt = kspec.get("format", "number")
            value = None
            if sql:
                try:
                    validate_sql(sql, table_name)
                    rows = await execute_sql(sql, dataset.db_path)
                    if rows and len(rows) > 0:
                        first_val = list(rows[0].values())[0]
                        value = str(first_val)
                except Exception as e:
                    logger.warning("sql_execution_failed_kpi", label=label, error=str(e))
            
            kpi_results.append({
                "label": label, "value": value, "format": fmt, "sql": sql
            })

        yield _event("sql_exec_done", {"message": "SQL execution and visualization complete."})

        # ── Insight Generation ───────────────────────────────────────────────
        yield _event("insight_start", {"message": "Generating business insights..."})
        
        schema_cols = []
        if dataset.schema_json and "columns" in dataset.schema_json:
            schema_cols = [c["safe_name"] for c in dataset.schema_json["columns"] if "safe_name" in c]

        insight_data = await generate_insight(
            user_prompt=prompt,
            chart_results=chart_results,
            schema_columns=schema_cols,
            dataset_id=str(dataset.id),
            pii_detected=dataset.pii_detected,
        )

        yield _event("insight_done", {"message": "Insights generated."})

        # ── Final Payload ────────────────────────────────────────────────────
        final_payload = {
            "charts": chart_results,
            "kpis": kpi_results,
            "insight": insight_data.get("insight", ""),
            "brief_insights": insight_data.get("brief_insights", []),
            "suggestions": insight_data.get("suggestions", []),
        }

        yield _event("complete", final_payload)

        # ── Persist to query_history ──────────────────────────────────────────
        try:
            history_entry = QueryHistory(
                id=uuid.uuid4(),
                user_id=user_id,
                dataset_id=dataset.id,
                prompt=prompt,
                result_json=final_payload,
            )
            async with AsyncSessionLocal() as session:
                session.add(history_entry)
                await session.commit()
            logger.info("query_history_saved", history_id=str(history_entry.id))
        except Exception as persist_err:
            logger.warning("query_history_save_failed", error=str(persist_err))
            # Don't fail the SSE stream — the user already got their results

    except Exception as e:
        logger.exception("pipeline_error_sse", error=str(e))
        yield _event("error", {"message": f"An unexpected error occurred: {e}"})
