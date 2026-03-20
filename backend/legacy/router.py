"""
legacy/router.py
──────────────────────────────────────────────────────────────────────────────
Session-based legacy endpoints for the v1 frontend.
Uses an in-memory session store keyed by X-Session-ID header.
Delegates all heavy lifting to the v2 modules.
"""
from __future__ import annotations

import asyncio
import itertools
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, File, Header, Request, UploadFile
from fastapi.responses import JSONResponse

from core.config import get_settings
from datasets.ingest.parser import ingest_csv_to_sqlite
from pipeline.executor import execute_sql, validate_sql
from pipeline.insight import generate_insight
from pipeline.postprocessor import post_process_chart
from pipeline.stage1_sql import run_stage1
from pipeline.stage2_viz import infer_viz

logger = structlog.get_logger()
router = APIRouter(tags=["legacy"])
cfg = get_settings()


# ── In-memory session store ───────────────────────────────────────────────────
# Each session holds: db_path, schema, history, overview, dataset_name
# Bounded to MAX_SESSIONS to prevent unbounded memory growth.
import time

_sessions: Dict[str, Dict[str, Any]] = {}
_MAX_SESSIONS = 500  # hard cap — oldest sessions evicted when full


def _evict_oldest() -> None:
    """Evict the oldest session when the store is at capacity."""
    if len(_sessions) < _MAX_SESSIONS:
        return
    oldest_key = min(_sessions, key=lambda k: _sessions[k].get("_last_accessed", 0))
    del _sessions[oldest_key]


def _get_session(session_id: str) -> Dict[str, Any] | None:
    sess = _sessions.get(session_id)
    if sess:
        sess["_last_accessed"] = time.monotonic()
    return sess


def _create_session(session_id: str) -> Dict[str, Any]:
    _evict_oldest()
    _sessions[session_id] = {
        "db_path": None,
        "schema": None,
        "history": [],
        "overview": None,
        "dataset_name": None,
        "_last_accessed": time.monotonic(),
    }
    return _sessions[session_id]


def _ensure_session(session_id: str) -> Dict[str, Any]:
    return _get_session(session_id) or _create_session(session_id)


def _db_path_for_session(session_id: str) -> Path:
    base = Path(cfg.DATA_DIR).resolve()
    return base / "sessions" / session_id / "data.db"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_schema_context(schema: dict) -> str:
    table_name = schema.get("table_name", "data")
    cols = schema.get("columns", [])
    lines = [f"TABLE SCHEMA FOR '{table_name}':"]
    for c in cols:
        name = c.get("safe_name", "")
        dtype = c.get("sql_type", "TEXT")
        role = c.get("role", "")
        sample_vals = c.get("samples", [])
        sample = str(sample_vals)[:50]
        if len(str(sample_vals)) > 50:
            sample += "..."
        bucket = c.get("bucket_sql")
        line = f" - {name} ({dtype}, {role}) | sample: {sample}"
        if bucket:
            line += f" | bucket_sql: {bucket}"
        lines.append(line)
    return "\n".join(lines)


# ── Upload CSV ────────────────────────────────────────────────────────────────

@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    if not x_session_id:
        return JSONResponse(status_code=400, content={"detail": "X-Session-ID header required"})

    session = _ensure_session(x_session_id)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        return JSONResponse(status_code=400, content={"detail": "Only .csv files are accepted."})

    content = await file.read()
    if len(content) > cfg.max_csv_bytes:
        return JSONResponse(status_code=400, content={"detail": f"File too large. Maximum: {cfg.MAX_CSV_SIZE_MB}MB."})

    db_path = _db_path_for_session(x_session_id)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        schema_info = await asyncio.to_thread(ingest_csv_to_sqlite, content, str(db_path))
    except Exception as exc:
        logger.error("legacy_ingest_failed", error=str(exc))
        return JSONResponse(status_code=400, content={"detail": f"CSV import failed: {exc}"})

    dataset_name = Path(file.filename).stem
    schema_info["dataset_name"] = dataset_name
    session["db_path"] = str(db_path)
    session["schema"] = schema_info
    session["dataset_name"] = dataset_name
    session["history"] = []
    session["overview"] = None

    logger.info("legacy_csv_uploaded", session_id=x_session_id, rows=schema_info.get("row_count"))
    return JSONResponse(content={"status": "ok", "rows": schema_info.get("row_count"), "cols": schema_info.get("col_count")})


# ── Preload sample dataset ────────────────────────────────────────────────────

@router.post("/preload")
async def preload_dataset(
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    if not x_session_id:
        return JSONResponse(status_code=400, content={"detail": "X-Session-ID header required"})

    session = _ensure_session(x_session_id)

    # Find sample CSV
    sample_paths = [
        Path(__file__).parent.parent / "data" / "Customer_Behaviour__Online_vs_Offline_.csv",
        Path(cfg.DATA_DIR).parent / "Customer_Behaviour__Online_vs_Offline_.csv",
    ]
    # Also check project root data directory
    sample_paths.append(Path(__file__).parent.parent.parent / "data" / "Customer_Behaviour__Online_vs_Offline_.csv")

    sample_csv = None
    for p in sample_paths:
        if p.exists():
            sample_csv = p
            break

    if not sample_csv:
        return JSONResponse(status_code=404, content={"detail": "Sample dataset not found. Upload a CSV instead."})

    content = sample_csv.read_bytes()
    db_path = _db_path_for_session(x_session_id)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        schema_info = await asyncio.to_thread(ingest_csv_to_sqlite, content, str(db_path))
    except Exception as exc:
        logger.error("legacy_preload_failed", error=str(exc))
        return JSONResponse(status_code=400, content={"detail": f"Preload failed: {exc}"})

    schema_info["dataset_name"] = "Customer Behaviour (GFG)"
    session["db_path"] = str(db_path)
    session["schema"] = schema_info
    session["dataset_name"] = "Customer Behaviour (GFG)"
    session["history"] = []
    session["overview"] = None

    logger.info("legacy_preload_ok", session_id=x_session_id, rows=schema_info.get("row_count"))
    return JSONResponse(content={"status": "ok", "rows": schema_info.get("row_count")})


# ── Get schema ────────────────────────────────────────────────────────────────

@router.get("/schema")
async def get_schema(
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    if not x_session_id:
        return JSONResponse(status_code=400, content={"detail": "X-Session-ID header required"})

    session = _get_session(x_session_id)
    if not session or not session.get("schema"):
        return JSONResponse(status_code=404, content={"detail": "Session not found or no dataset loaded."})

    return JSONResponse(content=session["schema"])


# ── Query (NL → SQL → chart) ─────────────────────────────────────────────────

@router.post("/query")
async def query(
    request: Request,
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    if not x_session_id:
        return JSONResponse(status_code=400, content={"detail": "X-Session-ID header required"})

    session = _get_session(x_session_id)
    if not session or not session.get("schema") or not session.get("db_path"):
        return JSONResponse(status_code=404, content={"detail": "No dataset loaded. Upload or preload first."})

    body = await request.json()
    prompt = body.get("prompt", "").strip()
    if not prompt:
        return JSONResponse(status_code=400, content={"detail": "Prompt is required."})

    schema = session["schema"]
    db_path = session["db_path"]
    table_name = schema.get("table_name", "data")
    schema_context = _build_schema_context(schema)

    # Build last_contexts from history
    last_contexts = None
    if session.get("history"):
        last_contexts = []
        for h in session["history"][-3:]:
            charts = h.get("result", {}).get("charts", [])
            if charts:
                last_contexts.append({
                    "prompt": h.get("prompt", ""),
                    "sql": charts[0].get("sql", ""),
                    "columns": list(charts[0].get("rows", [{}])[0].keys()) if charts[0].get("rows") else [],
                })

    try:
        # Stage 1: SQL Generation
        stage1 = await run_stage1(
            schema_context=schema_context,
            user_prompt=prompt,
            table_name=table_name,
            dataset_id=x_session_id,
            last_contexts=last_contexts,
        )

        if stage1.get("cannot_answer"):
            result = {"cannot_answer": True, "reason": stage1.get("reason", "Cannot answer.")}
            session["history"].append({"prompt": prompt, "result": result})
            return JSONResponse(content=result)

        if stage1.get("clarification_needed"):
            result = {
                "clarification_needed": True,
                "clarification_prompt": stage1.get("clarification_prompt", "Please clarify."),
            }
            return JSONResponse(content=result)

        charts_specs = stage1.get("charts", [])
        kpis_specs = stage1.get("kpis", [])

        if not charts_specs and not kpis_specs:
            return JSONResponse(content={"cannot_answer": True, "reason": "No queries generated. Please rephrase."})

        # Execute SQL and build charts
        chart_results = []
        for spec in charts_specs:
            sql = spec.get("sql", "").strip()
            title = spec.get("title", "Untitled")
            if not sql:
                continue
            try:
                validate_sql(sql, table_name)
                rows = await execute_sql(sql, db_path)
            except Exception as e:
                logger.warning("legacy_sql_fail", title=title, error=str(e))
                chart_results.append({
                    "title": title, "sql": sql, "rows": [],
                    "warning": f"Query execution failed: {e}",
                    "type": "bar", "x_col": "", "y_cols": [], "color_col": None,
                })
                continue

            viz = infer_viz(rows)
            raw_spec = {
                "title": title, "sql": sql,
                "type": viz["type"], "x_col": viz["x_col"],
                "y_cols": viz["y_cols"], "color_col": viz["color_col"],
            }
            final_spec = post_process_chart(raw_spec, rows)
            chart_results.append(final_spec)

        # Execute KPIs
        kpi_results = []
        for kspec in kpis_specs:
            sql = kspec.get("sql", "").strip()
            label = kspec.get("label", "")
            fmt = kspec.get("format", "number")
            value = None
            if sql:
                try:
                    validate_sql(sql, table_name)
                    rows = await execute_sql(sql, db_path)
                    if rows and len(rows) > 0:
                        value = str(list(rows[0].values())[0])
                except Exception as e:
                    logger.warning("legacy_kpi_fail", label=label, error=str(e))
            kpi_results.append({"label": label, "value": value, "format": fmt, "sql": sql})

        # Insight generation
        schema_cols = [c["safe_name"] for c in schema.get("columns", []) if "safe_name" in c]
        pii_detected = schema.get("pii_detected", False)

        insight_data = await generate_insight(
            user_prompt=prompt,
            chart_results=chart_results,
            schema_columns=schema_cols,
            dataset_id=x_session_id,
            pii_detected=pii_detected,
        )

        provider = stage1.get("provider_used", "")
        result = {
            "charts": chart_results,
            "kpis": kpi_results,
            "insight": insight_data.get("insight", ""),
            "brief_insights": insight_data.get("brief_insights", []),
            "suggestions": insight_data.get("suggestions", []),
            "provider": provider,
        }

        session["history"].append({"prompt": prompt, "result": result})
        return JSONResponse(content=result)

    except Exception as e:
        logger.exception("legacy_query_error", error=str(e))
        return JSONResponse(status_code=500, content={"detail": f"Query failed: {e}"})


# ── Refine ────────────────────────────────────────────────────────────────────

@router.post("/refine")
async def refine(
    request: Request,
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    """Refine a previous query by combining with a follow-up message."""
    body = await request.json()
    message = body.get("message", "").strip()
    original = body.get("original_prompt", "").strip()
    combined = f"{original}. Additionally: {message}" if original else message

    # Delegate to query() logic directly — avoid mutating private request internals
    session = _get_session(x_session_id)
    if not session or not session.get("schema") or not session.get("db_path"):
        return JSONResponse(status_code=404, content={"detail": "No dataset loaded. Upload or preload first."})

    # Reuse all the query logic by forwarding a synthetic re-entry
    # Build a fresh minimal fake request body just for the combined prompt
    from starlette.datastructures import Headers
    from io import BytesIO
    import json as _json
    fake_body = _json.dumps({"prompt": combined}).encode()
    scope = dict(request.scope)
    synthetic_request = Request(scope, receive=lambda: None)
    synthetic_request._body = fake_body  # type: ignore[attr-defined]  # starlette internal, stable since v0.13

    return await query(synthetic_request, x_session_id)


# ── Overview ──────────────────────────────────────────────────────────────────

@router.post("/overview")
async def overview(
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    if not x_session_id:
        return JSONResponse(status_code=400, content={"detail": "X-Session-ID header required"})

    session = _get_session(x_session_id)
    if not session or not session.get("schema"):
        return JSONResponse(status_code=404, content={"detail": "No dataset loaded."})

    if session.get("overview"):
        return JSONResponse(content=session["overview"])

    schema = session["schema"]
    from llm.providers import call_llm
    from llm.sanitizer import SYSTEM_INJECTION_GUARD

    col_info = []
    for c in schema.get("columns", [])[:20]:
        col_info.append(f"  - {c['safe_name']} ({c['sql_type']}, {c['role']}, {c['nunique']} unique)")

    prompt = f"""{SYSTEM_INJECTION_GUARD}

You are analyzing a dataset called "{session.get('dataset_name', 'Dataset')}".
It has {schema.get('row_count', 0)} rows and {schema.get('col_count', 0)} columns.

Columns:
{chr(10).join(col_info)}

Provide a JSON response:
{{
  "summary": "2-3 sentence overview of what this dataset contains",
  "expert_note": "One insightful observation about the data structure",
  "column_groups": [
    {{"group": "Group name", "description": "Description", "columns": ["col1", "col2"]}}
  ],
  "suggested_questions": ["Question 1", "Question 2", "Question 3"]
}}
"""

    try:
        resp = await call_llm(prompt, dataset_id=f"{x_session_id}_overview")
        session["overview"] = resp
        return JSONResponse(content=resp)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history")
async def get_history(
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    import time
    session = _get_session(x_session_id)
    if not session:
        return JSONResponse(content={"expired": True, "items": []})
        
    items = []
    base_time = time.time() - len(session.get("history", [])) * 60
    for idx, h in enumerate(session.get("history", [])):
        res = h.get("result", {})
        charts = res.get("charts", [])
        kpis = res.get("kpis", [])
        items.append({
            "prompt": h.get("prompt", ""),
            "timestamp": base_time + (idx * 60),
            "cannot_answer": res.get("cannot_answer", False),
            "reason": res.get("reason", ""),
            "insight": res.get("insight", ""),
            "chart_specs": [{"type": c.get("type", "bar")} for c in charts],
            "kpi_specs": [{"label": k.get("label", "")} for k in kpis]
        })
        
    return JSONResponse(content={"expired": False, "items": items})


@router.delete("/history")
async def clear_history(
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    session = _get_session(x_session_id)
    if session:
        session["history"] = []
    return JSONResponse(content={"status": "ok"})


# ── Auto-report ───────────────────────────────────────────────────────────────

@router.post("/auto-report")
async def auto_report(
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    """Generate an automatic overview report with pre-defined questions."""
    session = _get_session(x_session_id)
    if not session or not session.get("schema") or not session.get("db_path"):
        return JSONResponse(status_code=404, content={"detail": "No dataset loaded."})

    schema = session["schema"]
    db_path = session["db_path"]
    table_name = schema.get("table_name", "data")
    schema_context = _build_schema_context(schema)

    # Pick auto-report questions based on column roles
    dims = [c["safe_name"] for c in schema.get("columns", []) if c.get("role") == "dimension"]
    scores = [c["safe_name"] for c in schema.get("columns", []) if c.get("role") in ("score", "measure", "continuous")]

    question = "Show the distribution of records"
    if dims:
        question = f"Show the distribution of records by {dims[0]}"
        if len(dims) > 1:
            question += f" and {dims[1]}"

    # Delegate to the query logic
    try:
        stage1 = await run_stage1(
            schema_context=schema_context,
            user_prompt=question,
            table_name=table_name,
            dataset_id=x_session_id,
        )

        if stage1.get("cannot_answer"):
            return JSONResponse(content={"cannot_answer": True, "reason": stage1.get("reason", "")})

        charts_specs = stage1.get("charts", [])
        kpis_specs = stage1.get("kpis", [])

        chart_results = []
        for spec in charts_specs:
            sql = spec.get("sql", "").strip()
            title = spec.get("title", "Untitled")
            if not sql:
                continue
            try:
                validate_sql(sql, table_name)
                rows = await execute_sql(sql, db_path)
                viz = infer_viz(rows)
                raw_spec = {
                    "title": title, "sql": sql,
                    "type": viz["type"], "x_col": viz["x_col"],
                    "y_cols": viz["y_cols"], "color_col": viz["color_col"],
                }
                chart_results.append(post_process_chart(raw_spec, rows))
            except Exception as e:
                chart_results.append({"title": title, "sql": sql, "rows": [], "warning": str(e),
                                      "type": "bar", "x_col": "", "y_cols": [], "color_col": None})

        kpi_results = []
        for kspec in kpis_specs:
            sql = kspec.get("sql", "").strip()
            value = None
            if sql:
                try:
                    validate_sql(sql, table_name)
                    rows = await execute_sql(sql, db_path)
                    if rows:
                        value = str(list(rows[0].values())[0])
                except Exception:
                    pass
            kpi_results.append({"label": kspec.get("label", ""), "value": value,
                                "format": kspec.get("format", "number"), "sql": sql})

        schema_cols = [c["safe_name"] for c in schema.get("columns", []) if "safe_name" in c]
        insight_data = await generate_insight(
            user_prompt=question, chart_results=chart_results,
            schema_columns=schema_cols, dataset_id=x_session_id,
        )

        result = {
            "charts": chart_results, "kpis": kpi_results,
            "insight": insight_data.get("insight", ""),
            "brief_insights": insight_data.get("brief_insights", []),
            "suggestions": insight_data.get("suggestions", []),
            "provider": stage1.get("provider_used", ""),
        }
        return JSONResponse(content=result)

    except Exception as e:
        logger.exception("auto_report_error", error=str(e))
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ── Data preview ──────────────────────────────────────────────────────────────

@router.get("/data-preview")
async def data_preview(
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    session = _get_session(x_session_id)
    if not session or not session.get("db_path"):
        return JSONResponse(status_code=404, content={"detail": "No dataset loaded."})

    db_path = session["db_path"]
    table_name = session["schema"].get("table_name", "data")

    try:
        rows = await execute_sql(f'SELECT * FROM "{table_name}" LIMIT 100', db_path)
        columns = list(rows[0].keys()) if rows else []
        return JSONResponse(content={"columns": columns, "rows": rows})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    request: Request,
    x_session_id: str = Header(default=""),
) -> JSONResponse:
    body = await request.json()
    message = body.get("message", "")
    history = body.get("history", [])
    context = body.get("context")

    from llm.providers import call_llm
    from llm.sanitizer import SYSTEM_INJECTION_GUARD, sanitize_user_input, wrap_for_prompt

    session = _get_session(x_session_id)
    schema_hint = ""
    if session and session.get("schema"):
        cols = [c["safe_name"] for c in session["schema"].get("columns", [])[:15]]
        schema_hint = f"\nDataset columns: {', '.join(cols)}"

    context_hint = ""
    if context and isinstance(context, dict):
        charts = context.get("charts", [])
        kpis = context.get("kpis", [])
        insight = context.get("insight", "")
        
        ctx_lines = []
        if insight:
            ctx_lines.append(f"Primary Insight: {insight}")
        if kpis:
            kpi_strs = [f"{k.get('label')}: {k.get('value')}" for k in kpis if k.get('value') is not None]
            if kpi_strs:
                ctx_lines.append(f"KPIs: {', '.join(kpi_strs)}")
        if charts:
            for c in charts:
                title = c.get("title", "Untitled Chart")
                rows = c.get("rows", [])
                if rows:
                    sample_data = json.dumps(rows[:5])
                    ctx_lines.append(f"Chart '{title}' sample data: {sample_data}")
        
        if ctx_lines:
            context_hint = "\nCurrent Analysis Context:\n" + "\n".join(ctx_lines)

    safe_msg = sanitize_user_input(message)
    prompt = f"""{SYSTEM_INJECTION_GUARD}

You are InsightFlow's brilliant Data Analyst AI. You act as a friendly and capable assistant helping the user navigate their data. You can answer questions about their dataset, explain the current analysis context provided below, and also answer general questions.

If the user asks an irrelevant or trick question, answer it playfully but professionally, reminding them you're an expert data analyst. 
If they ask about data shown in the 'Current Analysis Context', use the provided KPI values and sample chart rows to answer precisely.
{schema_hint}
{context_hint}

Chat history:
{json.dumps(history[-6:]) if history else "(none)"}

User: {wrap_for_prompt(safe_msg)}

Respond with JSON: {{"reply": "your helpful markdown-formatted response"}}"""

    try:
        resp = await call_llm(prompt, dataset_id=f"{x_session_id}_chat")
        return JSONResponse(content={"reply": resp.get("reply", "I couldn't generate a response.")})
    except Exception as e:
        return JSONResponse(content={"reply": f"Sorry, I encountered an error: {e}"})
