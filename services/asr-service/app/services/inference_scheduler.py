"""Inference scheduler: one model, one execution lane, many callers.

Replaces "every caller does run_in_executor(_run_whisper) on the default
thread pool" with an explicit queue in front of the model. That single change
gives the service three properties the E4 results showed it lacked:

1. Micro-batching (performance/scalability). Requests that arrive within
   `batch_window_ms` of each other are run as ONE forward pass of up to
   `max_batch_size` clips. Whisper pads every short-form input to 30 s anyway,
   so on a GPU a batch of N costs far less than N single runs. The effective
   batch size is set at runtime by device_manager (CPU: 1, GPU: grows with
   queue pressure, shrinks after an OOM).

2. Priorities. Streaming finals (a user is waiting on an open socket) go
   before REST requests, which go before queued jobs, which go before live
   partials. Partials are shed entirely when the queue is deep — they are
   best-effort previews, and E5 showed them delaying the PCM final.

3. Admission control (availability). A synchronous request that would wait
   longer than `admission_max_wait_seconds` is rejected immediately with 503 +
   Retry-After instead of queueing for minutes and then timing out (the
   "accept more, fail later" pattern behind E4 round 4's 149 s p99).

The queue depth and estimated wait it exposes are also the pressure signal
that device_manager now adapts on (instead of CPU%).
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Optional

from app.core.config import settings
from app.core.exceptions import CapacityReachedError

logger = logging.getLogger(__name__)

PRIORITY_STREAM_FINAL = 0
PRIORITY_REQUEST = 1
PRIORITY_JOB = 2
PRIORITY_PARTIAL = 3

# Whisper's short-form window. Longer clips go through sequential long-form
# decoding, which we never mix into a batch.
_SHORT_FORM_MAX_S = 30.0


@dataclass(order=True)
class _Item:
    priority: int
    seq: int
    path: str = field(compare=False)
    duration: float = field(compare=False)
    future: asyncio.Future = field(compare=False)
    enqueued_at: float = field(compare=False)


def _is_oom(exc: BaseException) -> bool:
    return "out of memory" in str(exc).lower() or type(exc).__name__ == "OutOfMemoryError"


class InferenceScheduler:
    def __init__(self, run_batch: Callable[[list[str]], list[dict]]) -> None:
        self._run_batch = run_batch  # blocking; executed on the single inference thread
        self._queue: Optional[asyncio.PriorityQueue] = None
        self._seq = itertools.count()
        self._task: Optional[asyncio.Task] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self.max_batch_size = settings.batch_size_cpu
        self._ewma_item_s: Optional[float] = None  # seconds of model time per clip
        self._in_flight = 0
        self._oom_times: deque[float] = deque(maxlen=50)
        # Counters exposed at /status/scheduler for the experiments
        self.batches = 0
        self.items = 0
        self.rejected = 0
        self.shed_partials = 0
        self.batch_size_hist: Counter[int] = Counter()
        self.queue_wait_ewma_s: Optional[float] = None
        # Measured model time per clip, per "device/compute_type" state: the
        # ground truth device_manager uses to keep or roll back an adaptation.
        self.cost_by_state: dict[str, list] = {}

    # ---- lifecycle ----
    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._queue = asyncio.PriorityQueue()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="inference")
        self._task = asyncio.create_task(self._loop())
        logger.info("Inference scheduler started (window=%sms)", settings.batch_window_ms)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

    # ---- signals ----
    @property
    def depth(self) -> int:
        return self._queue.qsize() if self._queue is not None else 0

    @property
    def in_flight(self) -> int:
        return self._in_flight

    def estimated_wait_s(self) -> float:
        """Expected time before a newly queued clip starts running."""
        per_item = self._ewma_item_s or 0.0
        return (self.depth + self._in_flight) * per_item

    def state_totals(self, state: str) -> tuple[float, int]:
        """(total model seconds, clips) measured in `state` so far."""
        total, n = self.cost_by_state.get(state, (0.0, 0))
        return total, n

    def recent_oom_events(self, window_s: float) -> int:
        cutoff = time.monotonic() - window_s
        return sum(1 for t in self._oom_times if t >= cutoff)

    def snapshot(self) -> dict:
        return {
            "running": self.running,
            "queue_depth": self.depth,
            "in_flight": self._in_flight,
            "max_batch_size": self.max_batch_size,
            "estimated_wait_s": round(self.estimated_wait_s(), 3),
            "ewma_model_s_per_clip": round(self._ewma_item_s, 4) if self._ewma_item_s else None,
            "ewma_queue_wait_s": round(self.queue_wait_ewma_s, 3) if self.queue_wait_ewma_s else None,
            "batches": self.batches,
            "items": self.items,
            "rejected": self.rejected,
            "shed_partials": self.shed_partials,
            "oom_events": len(self._oom_times),
            "batch_size_histogram": dict(sorted(self.batch_size_hist.items())),
            "model_s_per_clip_by_state": {
                k: round(t / n, 4) for k, (t, n) in self.cost_by_state.items() if n
            },
        }

    # ---- submission ----
    async def submit(
        self, path: str, duration: float, priority: int, admission: bool = True
    ) -> Optional[dict]:
        """Queue one clip and wait for its result. Returns None only for a shed
        partial. Raises CapacityReachedError when admission control rejects."""
        if not self.running:
            raise RuntimeError("scheduler not running")

        if priority == PRIORITY_PARTIAL and self.depth >= settings.partial_shed_depth:
            self.shed_partials += 1
            return None

        if admission:
            if self.depth >= settings.max_queue_depth:
                self.rejected += 1
                raise CapacityReachedError("Inference queue full")
            if self.estimated_wait_s() > settings.admission_max_wait_seconds:
                self.rejected += 1
                raise CapacityReachedError("Estimated wait exceeds admission limit")

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        await self._queue.put(
            _Item(priority, next(self._seq), path, duration, fut, time.monotonic())
        )
        return await fut

    # ---- execution ----
    async def _loop(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            item = await self._queue.get()
            if item.future.done():  # caller timed out / was cancelled while queued
                continue
            batch = [item]
            if item.duration <= _SHORT_FORM_MAX_S and self.max_batch_size > 1:
                deadline = loop.time() + settings.batch_window_ms / 1000.0
                while len(batch) < self.max_batch_size:
                    try:
                        nxt = self._queue.get_nowait()
                    except asyncio.QueueEmpty:
                        remaining = deadline - loop.time()
                        if remaining <= 0:
                            break
                        try:
                            nxt = await asyncio.wait_for(self._queue.get(), remaining)
                        except asyncio.TimeoutError:
                            break
                    if nxt.future.done():
                        continue
                    if nxt.duration > _SHORT_FORM_MAX_S:
                        await self._queue.put(nxt)  # keeps its priority/seq; runs alone next
                        break
                    batch.append(nxt)
            await self._execute(batch)

    async def _execute(self, batch: list[_Item]) -> None:
        loop = asyncio.get_running_loop()
        now = time.monotonic()
        for it in batch:
            wait = now - it.enqueued_at
            self.queue_wait_ewma_s = (
                wait if self.queue_wait_ewma_s is None else 0.8 * self.queue_wait_ewma_s + 0.2 * wait
            )
        self._in_flight = len(batch)
        t0 = time.monotonic()
        try:
            results = await loop.run_in_executor(
                self._executor, self._run_batch, [it.path for it in batch]
            )
        except Exception as exc:
            if _is_oom(exc):
                self._oom_times.append(time.monotonic())
                logger.warning("CUDA OOM on batch of %d — splitting and retrying", len(batch))
                self._clear_cuda_cache()
                if len(batch) > 1:
                    half = len(batch) // 2
                    self._in_flight = 0
                    await self._execute(batch[:half])
                    await self._execute(batch[half:])
                    return
            for it in batch:
                if not it.future.done():
                    it.future.set_exception(exc)
            return
        finally:
            self._in_flight = 0

        elapsed = time.monotonic() - t0
        per_item = elapsed / len(batch)
        self._ewma_item_s = per_item if self._ewma_item_s is None else 0.8 * self._ewma_item_s + 0.2 * per_item
        self.batches += 1
        self.items += len(batch)
        self.batch_size_hist[len(batch)] += 1
        state = _current_state()
        acc = self.cost_by_state.setdefault(state, [0.0, 0])
        acc[0] += elapsed
        acc[1] += len(batch)
        for it, res in zip(batch, results):
            if not it.future.done():
                it.future.set_result(res)

    @staticmethod
    def _clear_cuda_cache() -> None:
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


def _current_state() -> str:
    from app.services import whisper_service

    return f"{whisper_service.get_current_device()}/{whisper_service.get_current_compute_type()}"


def _build() -> InferenceScheduler:
    from app.services import whisper_service

    return InferenceScheduler(lambda paths: whisper_service._run_whisper_batch(paths))


scheduler = _build()
