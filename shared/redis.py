"""One Redis connection per process, for every package that keeps state there."""

from __future__ import annotations

import redis
import redis.asyncio as aioredis

from shared.config import base_settings

_async: aioredis.Redis | None = None
_sync: redis.Redis | None = None


def async_client() -> aioredis.Redis:
    global _async  # noqa: PLW0603
    if _async is None:
        _async = aioredis.from_url(base_settings().redis_url, decode_responses=True)
    return _async


def sync_client() -> redis.Redis:
    global _sync  # noqa: PLW0603
    if _sync is None:
        _sync = redis.from_url(base_settings().redis_url, decode_responses=True)
    return _sync
