"""Asynchronous transcription worker: a Redis Streams consumer-group member.

Scalability: POST /api/v1/jobs no longer holds an HTTP connection open through
four services while the model works. audio-processor enqueues the converted
WAV and answers 202 immediately; every asr-service replica running this worker
pulls jobs at the rate its hardware sustains. Because workers PULL, a replica
can live anywhere that can reach Redis — e.g. a local GPU machine joining a
cloud deployment with no inbound port exposed (docs/09-arquitectura-v2.md).

Availability (at-least-once delivery):
- A job is XACK'ed only after its result is stored and persisted.
- While processing, the worker heartbeats its pending entry (XCLAIM to itself,
  which resets the idle time). If the worker dies, the entry goes idle and any
  other worker re-claims it after `job_claim_idle_ms` (XAUTOCLAIM).
- Duplicates are harmless: a job already marked done/failed is just ACK'ed,
  and the transcription id is the job id, so a re-persist is idempotent.
- Transient failures are retried by re-enqueueing, up to `job_max_attempts`.

Key layout (shared with audio-processor and api-gateway):
  job:{id}        hash  status/user_id/audio_id/.../result fields (TTL)
  job:{id}:audio  bytes 16 kHz mono WAV (TTL, deleted on completion)
  asr:jobs        stream of {"job_id": id}, consumer group "asr-workers"
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

JOB_KEY_PREFIX = "job:"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _s(value) -> str:
    return value.decode() if isinstance(value, (bytes, bytearray)) else str(value)


class JobWorker:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._redis = None
        self._active: set[asyncio.Task] = set()
        self.consumer = f"{socket.gethostname()}-{os.getpid()}"
        self.processed = 0
        self.failed = 0
        self.retried = 0
        self.reclaimed = 0
        self.duplicates = 0
        self.last_error: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return settings.job_worker_enabled and bool(settings.redis_url)

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def snapshot(self) -> dict:
        return {
            "enabled": self.enabled,
            "running": self.running,
            "consumer": self.consumer,
            "active": len(self._active),
            "processed": self.processed,
            "failed": self.failed,
            "retried": self.retried,
            "reclaimed": self.reclaimed,
            "duplicates": self.duplicates,
            "last_error": self.last_error,
        }

    async def start(self) -> None:
        if not self.enabled or self.running:
            return
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(settings.redis_url, socket_timeout=10.0)
        self._task = asyncio.create_task(self._loop())
        logger.info("Job worker started as consumer %s", self.consumer)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        for t in list(self._active):
            t.cancel()
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def _ensure_group(self) -> None:
        from redis.exceptions import ResponseError

        try:
            await self._redis.xgroup_create(
                settings.job_stream, settings.job_group, id="0", mkstream=True
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def _free_slots(self) -> int:
        return settings.job_worker_concurrency - len(self._active)

    def _spawn(self, msg_id, fields) -> None:
        task = asyncio.create_task(self._handle(_s(msg_id), fields))
        self._active.add(task)
        task.add_done_callback(self._active.discard)

    async def _loop(self) -> None:
        last_reclaim = 0.0
        group_ready = False
        while True:
            try:
                if not group_ready:
                    await self._ensure_group()
                    group_ready = True
                free = self._free_slots()
                if free <= 0:
                    await asyncio.sleep(0.05)
                    continue
                if time.monotonic() - last_reclaim > settings.job_claim_idle_ms / 3000.0:
                    last_reclaim = time.monotonic()
                    await self._reclaim(free)
                    free = self._free_slots()
                    if free <= 0:
                        continue
                resp = await self._redis.xreadgroup(
                    settings.job_group,
                    self.consumer,
                    {settings.job_stream: ">"},
                    count=free,
                    block=1000,
                )
                for _stream, messages in resp or []:
                    for msg_id, fields in messages:
                        self._spawn(msg_id, fields)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Redis down/restarting: keep retrying; re-create the group in
                # case the stream was lost (NOGROUP).
                self.last_error = str(exc)
                group_ready = False
                logger.warning("Job worker loop error (retrying): %s", exc)
                await asyncio.sleep(1.0)

    async def _reclaim(self, count: int) -> None:
        """Take over jobs whose worker stopped heartbeating (crashed/killed)."""
        result = await self._redis.xautoclaim(
            settings.job_stream,
            settings.job_group,
            self.consumer,
            min_idle_time=settings.job_claim_idle_ms,
            start_id="0-0",
            count=count,
        )
        messages = result[1] if len(result) > 1 else []
        for msg_id, fields in messages:
            if fields is None:  # entry was trimmed from the stream
                await self._redis.xack(settings.job_stream, settings.job_group, msg_id)
                continue
            self.reclaimed += 1
            logger.info("Re-claimed orphaned job message %s", _s(msg_id))
            self._spawn(msg_id, fields)

    async def _heartbeat(self, msg_id: str) -> None:
        while True:
            await asyncio.sleep(settings.job_claim_idle_ms / 3000.0)
            try:
                await self._redis.xclaim(
                    settings.job_stream, settings.job_group, self.consumer,
                    min_idle_time=0, message_ids=[msg_id], justid=True,
                )
            except Exception as exc:  # pragma: no cover - best effort
                logger.debug("Heartbeat for %s failed: %s", msg_id, exc)

    async def _ack(self, msg_id: str, job_id: Optional[str] = None) -> None:
        await self._redis.xack(settings.job_stream, settings.job_group, msg_id)
        if job_id:
            await self._redis.delete(f"{JOB_KEY_PREFIX}{job_id}:audio")

    async def _handle(self, msg_id: str, fields: dict) -> None:
        from app.services import whisper_service
        from app.services.inference_scheduler import PRIORITY_JOB

        raw_job_id = fields.get(b"job_id") or fields.get("job_id")
        if raw_job_id is None:
            await self._ack(msg_id)
            return
        job_id = _s(raw_job_id)
        key = f"{JOB_KEY_PREFIX}{job_id}"
        job = {_s(k): _s(v) for k, v in (await self._redis.hgetall(key)).items()}

        if not job:  # expired before anyone got to it
            await self._ack(msg_id, job_id)
            return
        if job.get("status") in ("done", "failed"):
            self.duplicates += 1  # at-least-once redelivery; already finished
            await self._ack(msg_id, job_id)
            return

        attempts = await self._redis.hincrby(key, "attempts", 1)
        if attempts > settings.job_max_attempts:
            await self._fail(msg_id, job_id, key, f"exceeded {settings.job_max_attempts} attempts")
            return

        audio = await self._redis.get(f"{key}:audio")
        if audio is None:
            await self._fail(msg_id, job_id, key, "audio payload expired")
            return

        started_at = time.time()
        await self._redis.hset(
            key,
            mapping={"status": "processing", "started_at": _now_iso(),
                     "started_ts": started_at, "worker": self.consumer},
        )
        heartbeat = asyncio.create_task(self._heartbeat(msg_id))
        tmp_dir = Path(tempfile.gettempdir()) / "asr_jobs"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"{job_id}.wav"
        try:
            tmp_path.write_bytes(audio)
            result = await whisper_service.transcribe(
                audio_path=str(tmp_path),
                user_id=job.get("user_id", ""),
                audio_id=job.get("audio_id", ""),
                audio_filename=job.get("audio_filename", f"{job_id}.wav"),
                audio_duration=float(job.get("audio_duration") or 0.0),
                transcription_id=job_id,
                priority=PRIORITY_JOB,
                admission=False,  # the queue IS the admission control for jobs
                timeout=settings.job_inference_timeout_seconds,
                persist="await",  # persist before ACK: at-least-once durability
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.last_error = str(exc)
            if attempts < settings.job_max_attempts:
                # Re-enqueue as a fresh entry for an immediate retry.
                self.retried += 1
                await self._redis.hset(key, mapping={"status": "queued", "last_error": str(exc)})
                await self._redis.xadd(settings.job_stream, {"job_id": job_id})
                await self._redis.xack(settings.job_stream, settings.job_group, msg_id)
            else:
                await self._fail(msg_id, job_id, key, str(exc))
            return
        finally:
            heartbeat.cancel()
            tmp_path.unlink(missing_ok=True)

        finished_at = time.time()
        enqueued_ts = float(job.get("enqueued_ts") or started_at)
        await self._redis.hset(
            key,
            mapping={
                "status": "done",
                "finished_at": _now_iso(),
                "transcription_id": result.transcription_id,
                "text": result.text,
                "device_used": result.device_used,
                "compute_type": result.compute_type,
                "queue_wait_s": round(started_at - enqueued_ts, 3),
                "processing_s": round(finished_at - started_at, 3),
                "total_s": round(finished_at - enqueued_ts, 3),
            },
        )
        await self._redis.expire(key, settings.job_result_ttl_seconds)
        await self._ack(msg_id, job_id)
        self.processed += 1

    async def _fail(self, msg_id: str, job_id: str, key: str, error: str) -> None:
        self.failed += 1
        await self._redis.hset(
            key, mapping={"status": "failed", "error": error, "finished_at": _now_iso()}
        )
        await self._redis.expire(key, settings.job_result_ttl_seconds)
        await self._ack(msg_id, job_id)


worker = JobWorker()
