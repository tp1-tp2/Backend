"""Shared lazily-built Redis client for the gateway (revocation set + job
status reads). None when REDIS_URL is unset, so the gateway still runs in the
original Redis-less configuration.
"""
from app.core.config import settings

_redis = None


def get_redis():
    global _redis
    if _redis is None and settings.redis_url:
        import redis.asyncio as aioredis

        _redis = aioredis.from_url(
            settings.redis_url,
            socket_timeout=settings.redis_timeout_seconds,
            socket_connect_timeout=settings.redis_timeout_seconds,
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
