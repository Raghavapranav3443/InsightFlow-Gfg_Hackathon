<<<<<<< HEAD
"""
main.py
──────────────────────────────────────────────────────────────────────────────
FastAPI application factory for InsightFlow v2.
This file:
  1. Configures logging
  2. Initialises the FastAPI app with lifespan (startup/shutdown)
  3. Registers middleware (CORS, Security headers, Rate limiting)
  4. Registers all routers
  5. Registers exception handlers

RULE: No feature code belongs here. This is a wiring file only.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Core setup — import first so logging is configured before anything logs
from core.config import get_settings
from core.exceptions import register_exception_handlers
from core.logging import configure_logging

# Middleware
from middleware.security import SecurityHeadersMiddleware

configure_logging()
logger = structlog.get_logger()
cfg = get_settings()


# ── Lifespan (startup + shutdown) ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    Startup: create DB tables, validate config, connect Redis.
    Shutdown: close Redis, close DB pool.
    """
    logger.info("insightflow_starting", env=cfg.ENV, version="2.0.0")

    # Validate at least one LLM key exists
    if not cfg.GROQ_API_KEY and not cfg.GEMINI_API_KEY:
        logger.warning(
            "no_llm_api_keys_configured",
            hint="Set GROQ_API_KEY or GEMINI_API_KEY in .env — queries will fail without them",
        )

    # Ensure data directory exists
    Path(cfg.DATA_DIR).mkdir(parents=True, exist_ok=True)

    # ── Create database tables (idempotent — safe to run on every startup) ───
    try:
        from core.database import engine, Base
        # Import all models so their metadata is registered before create_all
        import auth.models  # noqa: F401
        import datasets.models  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("db_tables_ready")
    except Exception as e:
        logger.error("db_table_creation_failed", error=str(e))
        # Don't abort startup — if DB is unavailable let the health check expose it

    # Optional: Sentry
    if cfg.SENTRY_DSN and cfg.is_production:
        import sentry_sdk
        sentry_sdk.init(dsn=cfg.SENTRY_DSN, traces_sample_rate=0.1)
        logger.info("sentry_initialised")

    logger.info("insightflow_ready", allowed_origins=cfg.allowed_origins_list)

    yield  # ← app handles requests here ────────────────────────────────────

    # Shutdown
    from core.redis import close_redis
    from core.database import engine

    await close_redis()
    await engine.dispose()
    logger.info("insightflow_shutdown")


# ── Create FastAPI app ─────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    _app = FastAPI(
        title="InsightFlow API",
        version="2.0.0",
        description="Natural language → BI dashboards",
        docs_url="/docs" if not cfg.is_production else None,  # hide Swagger in prod
        redoc_url=None,
        lifespan=lifespan,
    )

    # ── Rate limiter (Redis-backed, optional) ────────────────────────────────
    try:
        from slowapi import Limiter
        from slowapi.util import get_remote_address

        limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=cfg.REDIS_URL,
        )
        _app.state.limiter = limiter
        _app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        _app.add_middleware(SlowAPIMiddleware)
    except Exception as e:
        logger.warning("rate_limiter_disabled", error=str(e))

    # ── Security headers ─────────────────────────────────────────────────────
    _app.add_middleware(SecurityHeadersMiddleware)

    # ── CORS ─────────────────────────────────────────────────────────────────
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Session-ID"],
    )

    # ── Exception handlers ───────────────────────────────────────────────────
    register_exception_handlers(_app)

    # ── Routers ──────────────────────────────────────────────────────────────
    from auth.router import router as auth_router
    from dashboards.router import router as dashboards_router
    from dashboards.router import share_router
    from datasets.router import router as datasets_router
    from pipeline.history import router as history_router
    from pipeline.router import router as pipeline_router

    # ── Legacy compatibility router ──────────────────────────────────────────
    # Mount first so session-based endpoints override the newer JWT-based ones.
    try:
        from legacy.router import router as legacy_router
        _app.include_router(legacy_router)
        logger.info("legacy_routes_mounted")
    except ImportError:
        logger.debug("no_legacy_router_skip")

    _app.include_router(auth_router)
    _app.include_router(datasets_router)
    _app.include_router(pipeline_router)
    _app.include_router(dashboards_router)
    _app.include_router(history_router)
    _app.include_router(share_router)  # Public endpoint — no auth required

    # ── Health endpoint (no auth, no sensitive info in production) ───────────────
    @_app.get("/health", tags=["meta"])
    async def health() -> dict:
        payload: dict = {"status": "ok", "version": "2.0.0", "env": cfg.ENV}
        # Only expose LLM key hint in non-production environments
        if not cfg.is_production:
            payload["groq_key_looks_valid"] = bool(cfg.GROQ_API_KEY and len(cfg.GROQ_API_KEY) > 15)
        return payload

    return _app


app = create_app()
=======
from __future__ import annotations

# load_dotenv is called HERE, once, before any other local imports.
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import os
from dataclasses import dataclass
from typing import Optional

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ingest import ingest_csv
from query_pipeline import run_query, run_refine
from session_store import get_session, set_session, SessionData

app = FastAPI(title="InsightFlow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

GFG_CSV = Path(__file__).parent.parent / "data" / "Customer_Behaviour__Online_vs_Offline_.csv"


# ── Request models ─────────────────────────────────────────────────────────────

@dataclass
class QueryRequest:
    prompt: str = ""


@dataclass
class RefineRequest:
    message: str = ""
    original_prompt: str = ""


# ── Helper ─────────────────────────────────────────────────────────────────────

def _get_sid(x_session_id: Optional[str]) -> str:
    if not x_session_id or not x_session_id.strip():
        raise HTTPException(status_code=400, detail="X-Session-ID header is required")
    return x_session_id.strip()


def _clean_env(key: str, default: str = "") -> str:
    """Read env var and strip surrounding quotes that dotenv can leave."""
    return os.getenv(key, default).strip().strip('"').strip("'").strip()


# ── Routes ──────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    api_key  = _clean_env("GROQ_API_KEY")
    key_ok   = bool(api_key) and len(api_key) > 20
    return {
        "status": "ok",
        "gemini_key_set": key_ok,           # kept for frontend compatibility
        "gemini_key_looks_valid": key_ok,   # kept for frontend compatibility
        "gemini_key_prefix": (api_key[:8] + "...") if api_key else "NOT SET",
        "gemini_model": _clean_env("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "gfg_dataset_exists": GFG_CSV.exists(),
        "llm_provider": "groq",
    }


@app.get("/health/summary")
def health_summary():
    api_key = _clean_env("GROQ_API_KEY")
    return {
        "api":     True,
        "gemini":  bool(api_key) and len(api_key) > 20,
        "dataset": GFG_CSV.exists(),
    }


@app.get("/debug-llm")
def debug_llm():
    """
    Fires a minimal test call to Groq and returns the raw response.
    Open http://localhost:8000/debug-llm in your browser to diagnose issues.
    """
    import httpx as _httpx

    api_key = _clean_env("GROQ_API_KEY")
    model   = _clean_env("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        return {"ok": False, "problem": "GROQ_API_KEY not set in .env"}

    url     = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say the word hello"}],
        "max_tokens": 10,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        r    = _httpx.post(url, json=payload, headers=headers, timeout=20.0)
        body = r.json() if "application/json" in r.headers.get("content-type", "") else {"raw": r.text[:600]}
        return {
            "ok":          r.status_code == 200,
            "http_status": r.status_code,
            "key_prefix":  api_key[:8] + "...",
            "model":       model,
            "response":    body,
        }
    except Exception as e:
        return {"ok": False, "problem": str(e)}


@app.post("/preload")
def preload(x_session_id: Optional[str] = Header(None)):
    sid = _get_sid(x_session_id)

    # Return cached schema if session already loaded — avoids re-ingesting on every nav
    existing = get_session(sid)
    if existing and existing.schema:
        s = existing.schema
        return {
            "ok": True, "cached": True,
            "table_name": s.table_name, "dataset_name": s.dataset_name,
            "row_count": s.row_count, "column_count": len(s.columns),
            "has_date_column": s.has_date_column,
        }

    if not GFG_CSV.exists():
        raise HTTPException(
            status_code=404,
            detail="GFG dataset not found. Ensure data/Customer_Behaviour__Online_vs_Offline_.csv exists."
        )

    db_path = str(SESSIONS_DIR / f"{sid}.db")

    # Delete stale DB files from previous server runs.
    # Without this, WAL journal replay causes "table already exists" errors.
    for suffix in ("", "-wal", "-shm"):
        f = Path(db_path + suffix) if suffix else Path(db_path)
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass

    try:
        raw    = GFG_CSV.read_bytes()
        schema = ingest_csv(raw, GFG_CSV.name, db_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dataset ingest failed: {e}")

    set_session(sid, SessionData(schema=schema, db_path=db_path))

    return {
        "ok": True, "cached": False,
        "table_name": schema.table_name, "dataset_name": schema.dataset_name,
        "row_count": schema.row_count, "column_count": len(schema.columns),
        "has_date_column": schema.has_date_column,
    }


@app.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    x_session_id: Optional[str] = Header(None),
):
    sid = _get_sid(x_session_id)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    db_path = str(SESSIONS_DIR / f"{sid}.db")

    for suffix in ("", "-wal", "-shm"):
        f = Path(db_path + suffix) if suffix else Path(db_path)
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass

    try:
        schema = ingest_csv(raw, file.filename, db_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"CSV parse error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")

    set_session(sid, SessionData(schema=schema, db_path=db_path))

    return {
        "ok": True,
        "table_name": schema.table_name, "dataset_name": schema.dataset_name,
        "row_count": schema.row_count, "column_count": len(schema.columns),
        "has_date_column": schema.has_date_column,
    }


@app.get("/schema")
def get_schema(x_session_id: Optional[str] = Header(None)):
    sid  = _get_sid(x_session_id)
    sess = get_session(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found or expired. Reload the dataset.")

    return {
        "table_name":      sess.schema.table_name,
        "dataset_name":    sess.schema.dataset_name,
        "row_count":       sess.schema.row_count,
        "has_date_column": sess.schema.has_date_column,
        "columns": [
            {
                "safe_name":     c.safe_name,
                "original_name": c.original_name,
                "role":          c.role,
                "sql_type":      c.sql_type,
                "nunique":       c.nunique,
                "samples":       c.samples,
                "is_ambiguous":  c.is_ambiguous,
            }
            for c in sess.schema.columns
        ],
    }


@app.post("/query")
def query(req: QueryRequest, x_session_id: Optional[str] = Header(None)):
    sid = _get_sid(x_session_id)
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt must not be empty")

    result = run_query(req.prompt.strip(), sid)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/refine")
def refine(req: RefineRequest, x_session_id: Optional[str] = Header(None)):
    sid = _get_sid(x_session_id)
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    result = run_refine(req.message.strip(), sid, req.original_prompt or "")
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.delete("/history")
def clear_history(x_session_id: Optional[str] = Header(None)):
    """Clear query history for this session but keep the dataset loaded."""
    sid  = _get_sid(x_session_id)
    sess = get_session(sid)
    if sess:
        sess.history = []
        set_session(sid, sess)
    return {"ok": True}


@app.post("/overview")
def dataset_overview(x_session_id: Optional[str] = Header(None)):
    """
    Generate an AI overview of the loaded dataset.
    Called once after dataset loads. Returns a plain-English summary
    plus a structured breakdown of column groups.
    """
    from query_pipeline import call_llm
    from schema_context import build_schema_context

    sid  = _get_sid(x_session_id)
    sess = get_session(sid)
    if not sess or not sess.schema:
        raise HTTPException(status_code=404, detail="No dataset loaded.")

    schema = sess.schema
    ctx    = build_schema_context(schema)

    prompt = f"""You are a data analyst. A dataset has just been loaded. Give a concise overview.

SCHEMA:
{ctx}

Respond with ONLY valid JSON — no markdown, no backticks:
{{
  "summary": "2-3 sentence plain-English description of what this dataset contains, who the subjects are, and what questions it can answer. Write for someone unfamiliar with the data.",
  "expert_note": "1-2 sentences pointing out the most analytically interesting structure — e.g. skewed distributions, notable correlations expected, any caveats about ambiguous columns. Write for someone who knows data.",
  "column_groups": [
    {{"group": "Group name", "columns": ["col1", "col2"], "description": "Short description"}}
  ],
  "suggested_questions": [
    "Question 1",
    "Question 2",
    "Question 3"
  ]
}}

Rules:
- column_groups: 3-5 logical groups (demographics, behaviour, spending, psychographic, etc.)
- suggested_questions: exactly 3, specific to this dataset's columns, answerable with the data
- Use safe_names for columns in column_groups
- Keep summary under 60 words
- Keep expert_note under 40 words
"""

    result = call_llm(prompt)

    # Validate — if LLM returned a cannot_answer fallback, return a default
    if result.get("cannot_answer"):
        return {
            "summary": f"Dataset with {schema.row_count:,} rows and {len(schema.columns)} columns.",
            "expert_note": "Load the dataset and explore the columns to understand the structure.",
            "column_groups": [],
            "suggested_questions": [],
        }

    return {
        "summary":            result.get("summary", ""),
        "expert_note":        result.get("expert_note", ""),
        "column_groups":      result.get("column_groups", []),
        "suggested_questions": result.get("suggested_questions", []),
    }



@app.get("/history")
def history(x_session_id: Optional[str] = Header(None)):
    sid  = _get_sid(x_session_id)
    sess = get_session(sid)
    if not sess:
        return {"expired": True, "items": []}

    return {
        "expired": False,
        "items": [
            {
                "prompt":        r.prompt,
                "timestamp":     r.timestamp,
                "chart_specs":   r.chart_specs,
                "kpi_specs":     r.kpi_specs,
                "insight":       r.insight,
                "cannot_answer": r.cannot_answer,
                "reason":        r.reason,
            }
            for r in sess.history
        ],
    }
>>>>>>> 133e016e0e0b1defff61fad3bd011d924aeb6602
