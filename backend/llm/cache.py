"""
llm/cache.py
──────────────────────────────────────────────────────────────────────────────
Redis-backed LLM response cache.
Key = SHA-256(prompt + dataset_id) so responses never cross dataset boundaries.
TTL = 10 minutes (configurable).
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import structlog

from core.config import get_settings
from core.redis import redis_get, redis_set

logger = structlog.get_logger()
cfg = get_settings()


def _cache_key(prompt: str, dataset_id: str) -> str:
    """
    Cache key includes dataset_id to prevent cross-dataset cache pollution.
    (Critical: two users asking the same question on different datasets
     must get different SQL results.)
    """
    raw = f"{dataset_id}::{prompt}"
    return "llm_cache:" + hashlib.sha256(raw.encode()).hexdigest()[:32]


async def cache_get(prompt: str, dataset_id: str) -> dict[str, Any] | None:
    """Return cached LLM response or None if not cached."""
    key = _cache_key(prompt, dataset_id)
    raw = await redis_get(key)
    if raw:
        try:
            result = json.loads(raw)
            logger.debug("llm_cache_hit", key=key[:16])
            return result
        except json.JSONDecodeError:
            logger.warning("llm_cache_corrupt", key=key[:16])
    return None


async def cache_set(prompt: str, dataset_id: str, result: dict[str, Any]) -> None:
    """Cache an LLM response in Redis."""
    key = _cache_key(prompt, dataset_id)
    try:
        await redis_set(key, json.dumps(result), ttl_seconds=cfg.LLM_CACHE_TTL_SECONDS)
        logger.debug("llm_cache_set", key=key[:16], ttl=cfg.LLM_CACHE_TTL_SECONDS)
    except Exception as e:
        logger.warning("llm_cache_set_failed", error=str(e))
