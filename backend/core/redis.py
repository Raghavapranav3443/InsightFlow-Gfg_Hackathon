"""
core/redis.py
──────────────────────────────────────────────────────────────────────────────
Redis client factory — gracefully degrades when Redis is unavailable.
Used for: LLM response cache, rate limiting, refresh token blocklist.
"""
from __future__ import annotations

import structlog

from core.config import get_settings

logger = structlog.get_logger()

_redis_client = None
_redis_available = None  # None = not yet checked, True/False after first attempt


async def get_redis():
    """
    Return the shared async Redis client, or None if Redis is unavailable.
    Initialised lazily on first call.
    """
    global _redis_client, _redis_available

    if _redis_available is False:
        return None

    if _redis_client is None:
        try:
            import redis.asyncio as aioredis
            cfg = get_settings()
            client = aioredis.from_url(
                cfg.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test the connection
            await client.ping()
            _redis_client = client
            _redis_available = True
            logger.info("redis_connected", url=cfg.REDIS_URL)
        except Exception as e:
            _redis_available = False
            logger.warning(
                "redis_unavailable",
                error=str(e),
                hint="Running without Redis — LLM cache and rate limiting disabled",
            )
            return None

    return _redis_client


async def close_redis() -> None:
    """Call this on app shutdown."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None
    _redis_available = None


# ── Typed helpers (all gracefully degrade) ────────────────────────────────────

async def redis_get(key: str) -> str | None:
    r = await get_redis()
    if r is None:
        return None
    try:
        return await r.get(key)
    except Exception:
        return None


async def redis_set(key: str, value: str, ttl_seconds: int | None = None) -> None:
    r = await get_redis()
    if r is None:
        return
    try:
        if ttl_seconds:
            await r.set(key, value, ex=ttl_seconds)
        else:
            await r.set(key, value)
    except Exception:
        pass


async def redis_delete(key: str) -> None:
    r = await get_redis()
    if r is None:
        return
    try:
        await r.delete(key)
    except Exception:
        pass


async def redis_exists(key: str) -> bool:
    r = await get_redis()
    if r is None:
        return False
    try:
        return bool(await r.exists(key))
    except Exception:
        return False
