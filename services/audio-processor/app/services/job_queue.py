"""Producer side of the asynchronous transcription queue (Redis Streams).

Key layout (shared with asr-service's job_worker.py and api-gateway's
GET /api/v1/jobs/{id}):
  job:{id}        hash  status, user_id, audio_id, audio_filename,
                        audio_duration, enqueued_at, enqueued_ts, attempts
  job:{id}:audio  bytes 16 kHz mono WAV payload, TTL'd. Shipping the audio
                        through Redis (not a shared volume) is what lets a
                        worker run on another machine (hybrid GPU worker).
  asr:jobs        stream of {"job_id": id}, consumer group "asr-workers"
"""
import time
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.exceptions import JobQueueUnavailableError, QueueFullError

JOB_KEY_PREFIX = "job:"

_redis = None


def _client():
    global _redis
    if _redis is None and settings.redis_url:
        import redis.asyncio as aioredis

        _redis = aioredis.from_url(settings.redis_url, socket_timeout=5.0, socket_connect_timeout=2.0)
    return _redis


async def close() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def _ensure_group(client) -> None:
    from redis.exceptions import ResponseError

    try:
        await client.xgroup_create(settings.job_stream, settings.job_group, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def backlog() -> int:
    """Jobs not yet finished by any worker: undelivered + in progress (pending).

    Undelivered entries are COUNTED (XRANGE after the group's last-delivered
    id, capped at job_max_backlog + 1) instead of trusting XINFO's `lag`: E4 v2
    showed `lag` reporting 1197 waiting jobs on a stream that was fully
    consumed (pending 0, worker idle), which inflated this backlog, the queue
    admission check and the drain wait. `lag` is an estimate Redis may leave
    stale; the id range is exact.
    """
    client = _client()
    await _ensure_group(client)
    for group in await client.xinfo_groups(settings.job_stream):
        name = group.get("name") or group.get(b"name")
        if name in (settings.job_group, settings.job_group.encode()):
            pending = group.get("pending") if "pending" in group else group.get(b"pending")
            last = group.get("last-delivered-id") or group.get(b"last-delivered-id") or b"0-0"
            last = last.decode() if isinstance(last, bytes) else str(last)
            undelivered = await client.xrange(
                settings.job_stream, min=f"({last}", max="+", count=settings.job_max_backlog + 1
            )
            return len(undelivered) + int(pending or 0)
    return 0


async def ensure_capacity() -> int:
    if _client() is None:
        raise JobQueueUnavailableError()
    try:
        current = await backlog()
    except Exception as exc:
        raise JobQueueUnavailableError() from exc
    if current >= settings.job_max_backlog:
        raise QueueFullError()
    return current


async def enqueue(
    user_id: str,
    audio_id: str,
    audio_filename: str,
    audio_duration: float,
    wav_bytes: bytes,
) -> str:
    client = _client()
    job_id = str(uuid.uuid4())
    key = JOB_KEY_PREFIX + job_id
    try:
        pipe = client.pipeline(transaction=True)
        pipe.set(key + ":audio", wav_bytes, ex=settings.job_audio_ttl_seconds)
        pipe.hset(
            key,
            mapping={
                "status": "queued",
                "user_id": user_id,
                "audio_id": audio_id,
                "audio_filename": audio_filename,
                "audio_duration": audio_duration,
                "enqueued_at": datetime.now(timezone.utc).isoformat(),
                "enqueued_ts": time.time(),
                "attempts": 0,
            },
        )
        pipe.expire(key, settings.job_result_ttl_seconds)
        pipe.xadd(settings.job_stream, {"job_id": job_id})
        await pipe.execute()
    except Exception as exc:
        raise JobQueueUnavailableError() from exc
    return job_id
