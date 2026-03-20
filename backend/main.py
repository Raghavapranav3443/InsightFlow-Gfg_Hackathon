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