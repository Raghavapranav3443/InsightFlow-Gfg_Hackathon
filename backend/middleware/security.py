"""
middleware/security.py
──────────────────────────────────────────────────────────────────────────────
Security headers middleware + request ID injection.
Registered in main.py before any routes.
"""
from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds production security headers to every response.
    Also injects a unique X-Request-ID for log tracing.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Inject request ID for correlation across logs
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        cfg = get_settings()

        # --- Core security headers ---
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"

        # HSTS only in production (HTTPS required)
        if cfg.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy — restrictive by default
        # Allows same-origin scripts + Recharts SVG + font CDN
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # React needs inline scripts
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Don't expose server version
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]

        return response
