"""Edge admission control for synchronous transcriptions (docs/16, E4 v2).

E4 on the CPU host showed that admission control at the END of the chain
(asr-service) is not enough under heavy overload: every request that is later
rejected has already been uploaded, converted with ffmpeg and registered in
the database by audio-processor. Thousands of such requests steal CPU from
inference (goodput fell from 0.84 to ~0.3 req/s), make rejections slow
(median 49 s at 1000 users) and overload audio-processor (HTTP 500).

This module caps the number of synchronous /transcribe requests in flight
ACROSS all gateway workers (a Redis sorted set shared by the 4 uvicorn
processes and any replica), and rejects the excess with 503 + Retry-After
BEFORE the request body is read or forwarded. The cap is derived from
capacity with Little's law: in-flight = throughput x target response time
(e.g. 0.86 req/s x ~12 s ~= 10 on the CPU host).

Entries carry a timestamp so a slot leaked by a crashed worker expires after
the transcribe timeout. If Redis is unreachable the gateway fails OPEN (admits),
consistent with the revocation mirror: availability first; asr-service's own
admission control is still the second line of defence.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

_KEY = "gw:sync_transcribe_inflight"

# Atomic: drop stale slots, check the cap, take a slot.
_ACQUIRE = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[2])
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[3]) then
  return 0
end
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""

_acquire_script = None


def enabled() -> bool:
    return settings.edge_max_inflight_transcribe > 0


async def try_acquire() -> tuple[bool, Optional[str]]:
    """Returns (admitted, slot_id). slot_id is None when no slot needs
    releasing (disabled, or Redis unavailable and failing open)."""
    if not enabled():
        return True, None
    client = get_redis()
    if client is None:
        return True, None
    global _acquire_script
    try:
        if _acquire_script is None:
            _acquire_script = client.register_script(_ACQUIRE)
        now = time.time()
        slot = uuid.uuid4().hex
        stale_before = now - (settings.transcribe_timeout + 10)
        ok = await _acquire_script(
            keys=[_KEY],
            args=[now, stale_before, settings.edge_max_inflight_transcribe, slot,
                  int(settings.transcribe_timeout) + 60],
        )
        return (True, slot) if int(ok) == 1 else (False, None)
    except Exception as exc:  # fail open: never block traffic because Redis is down
        logger.warning("Edge admission unavailable, admitting (fail-open): %s", exc)
        return True, None


async def release(slot: Optional[str]) -> None:
    if slot is None:
        return
    client = get_redis()
    if client is None:
        return
    try:
        await client.zrem(_KEY, slot)
    except Exception as exc:  # the slot expires on its own after the timeout
        logger.warning("Edge admission release failed (slot will expire): %s", exc)
