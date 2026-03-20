"""
core/exceptions.py
──────────────────────────────────────────────────────────────────────────────
Custom exception classes and FastAPI exception handlers.
Import and register all handlers in main.py.
"""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


# ── Domain exceptions ─────────────────────────────────────────────────────────

class InsightFlowError(Exception):
    """Base class for all application-level errors."""
    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(InsightFlowError):
    """Resource not found OR not owned by the requesting user (intentionally ambiguous)."""
    status_code = 404
    error_code = "not_found"


class ForbiddenError(InsightFlowError):
    """Action not permitted for the current user."""
    status_code = 403
    error_code = "forbidden"


class ValidationError(InsightFlowError):
    """Input validation failed."""
    status_code = 422
    error_code = "validation_error"


class AuthError(InsightFlowError):
    """Authentication failed — invalid or expired token."""
    status_code = 401
    error_code = "auth_error"


class RateLimitError(InsightFlowError):
    """Rate limit exceeded."""
    status_code = 429
    error_code = "rate_limit_exceeded"


class LLMError(InsightFlowError):
    """All LLM providers failed or returned unusable response."""
    status_code = 503
    error_code = "llm_unavailable"


class DatasetError(InsightFlowError):
    """Dataset-related error (ingest failure, not found, quota exceeded)."""
    status_code = 400
    error_code = "dataset_error"


# ── Error response format ─────────────────────────────────────────────────────

def _error_response(status: int, error_code: str, message: str, details: dict) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": error_code,
            "message": message,
            "details": details,
        },
    )


# ── Exception handlers ────────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""

    @app.exception_handler(InsightFlowError)
    async def handle_app_error(request: Request, exc: InsightFlowError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error(
                "application_error",
                error_code=exc.error_code,
                message=exc.message,
                path=str(request.url),
            )
        return _error_response(exc.status_code, exc.error_code, exc.message, exc.details)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unexpected_error",
            path=str(request.url),
            error=str(exc),
        )
        return _error_response(500, "internal_error", "An unexpected error occurred.", {})
