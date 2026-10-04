"""Mirrors token revocations into Redis so the api-gateway can validate JWTs
locally (AUTH_MODE=local) without a round-trip to this service on every
request. auth-db stays the source of truth; the Redis key is a TTL'd copy
that expires together with the token itself.

Best-effort by design: a Redis failure is logged and never fails a logout —
the DB write already happened. See services/api-gateway/app/core/token_validator.py
for the consumer side and its fail-open/fail-closed trade-off.
"""
import logging
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)

REVOKED_KEY_PREFIX = "revoked:"  # must match api-gateway token_validator

_redis = None


def _client():
    global _redis
    if _redis is None and settings.redis_url:
        import redis.asyncio as aioredis

        _redis = aioredis.from_url(
            settings.redis_url, socket_timeout=1.0, socket_connect_timeout=1.0
        )
    return _redis


async def publish_revocation(token_hash: str, expires_at: datetime) -> None:
    client = _client()
    if client is None:
        return
    ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    if ttl <= 0:
        return
    try:
        await client.set(REVOKED_KEY_PREFIX + token_hash, "1", ex=ttl)
    except Exception as exc:
        logger.error("Could not mirror revocation to Redis: %s", exc)
