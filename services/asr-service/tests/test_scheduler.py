import asyncio
import threading
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.exceptions import CapacityReachedError
from app.services.inference_scheduler import (
    PRIORITY_JOB,
    PRIORITY_PARTIAL,
    PRIORITY_REQUEST,
    PRIORITY_STREAM_FINAL,
    InferenceScheduler,
)


def _echo_batches(calls: list):
    def run(paths):
        calls.append(list(paths))
        return [{"text": p, "segments": []} for p in paths]

    return run


async def test_concurrent_requests_are_batched():
    calls = []
    sched = InferenceScheduler(_echo_batches(calls))
    sched.max_batch_size = 4
    await sched.start()
    try:
        results = await asyncio.gather(
            *[sched.submit(f"a{i}.wav", 5.0, PRIORITY_REQUEST) for i in range(4)]
        )
    finally:
        await sched.stop()
    assert [r["text"] for r in results] == ["a0.wav", "a1.wav", "a2.wav", "a3.wav"]
    assert max(len(c) for c in calls) > 1  # at least one real batch
    assert sum(len(c) for c in calls) == 4
    assert all(len(c) <= 4 for c in calls)


async def test_batch_size_one_never_batches():
    calls = []
    sched = InferenceScheduler(_echo_batches(calls))
    sched.max_batch_size = 1
    await sched.start()
    try:
        await asyncio.gather(*[sched.submit(f"a{i}.wav", 5.0, PRIORITY_REQUEST) for i in range(3)])
    finally:
        await sched.stop()
    assert all(len(c) == 1 for c in calls)


async def test_long_audio_runs_alone():
    calls = []
    sched = InferenceScheduler(_echo_batches(calls))
    sched.max_batch_size = 8
    await sched.start()
    try:
        await asyncio.gather(
            sched.submit("long.wav", 45.0, PRIORITY_REQUEST),
            sched.submit("s1.wav", 5.0, PRIORITY_REQUEST),
            sched.submit("s2.wav", 5.0, PRIORITY_REQUEST),
        )
    finally:
        await sched.stop()
    assert ["long.wav"] in calls
    assert all("long.wav" not in c or len(c) == 1 for c in calls)


async def test_priority_order_final_request_job_partial():
    order = []
    gate = threading.Event()

    def run(paths):
        if paths == ["blocker"]:
            gate.wait(5)
        order.extend(paths)
        return [{"text": p, "segments": []} for p in paths]

    sched = InferenceScheduler(run)
    sched.max_batch_size = 1
    with patch.object(settings, "partial_shed_depth", 100):
        await sched.start()
        try:
            blocker = asyncio.create_task(sched.submit("blocker", 1.0, PRIORITY_REQUEST))
            await asyncio.sleep(0.05)  # blocker is now executing
            tasks = [
                asyncio.create_task(sched.submit("partial", 1.0, PRIORITY_PARTIAL)),
                asyncio.create_task(sched.submit("job", 1.0, PRIORITY_JOB)),
                asyncio.create_task(sched.submit("request", 1.0, PRIORITY_REQUEST)),
                asyncio.create_task(sched.submit("final", 1.0, PRIORITY_STREAM_FINAL)),
            ]
            await asyncio.sleep(0.05)
            gate.set()
            await asyncio.gather(blocker, *tasks)
        finally:
            await sched.stop()
    assert order == ["blocker", "final", "request", "job", "partial"]


async def test_admission_rejects_when_queue_full():
    gate = threading.Event()

    def run(paths):
        gate.wait(5)
        return [{"text": "", "segments": []} for _ in paths]

    sched = InferenceScheduler(run)
    sched.max_batch_size = 1
    with patch.object(settings, "max_queue_depth", 2):
        await sched.start()
        try:
            running = [asyncio.create_task(sched.submit("q0", 1.0, PRIORITY_REQUEST))]
            await asyncio.sleep(0.05)  # q0 is executing (queue empty again)
            running += [asyncio.create_task(sched.submit(f"q{i}", 1.0, PRIORITY_REQUEST)) for i in (1, 2)]
            await asyncio.sleep(0.05)  # 1 executing, 2 queued
            with pytest.raises(CapacityReachedError) as exc_info:
                await sched.submit("rejected", 1.0, PRIORITY_REQUEST)
            assert exc_info.value.status_code == 503
            assert "Retry-After" in exc_info.value.headers
            # Jobs / stream finals bypass admission (admission=False)
            bypass = asyncio.create_task(sched.submit("job", 1.0, PRIORITY_JOB, admission=False))
            gate.set()
            await asyncio.gather(*running, bypass)
        finally:
            await sched.stop()
    assert sched.rejected == 1


async def test_partials_are_shed_under_pressure():
    gate = threading.Event()

    def run(paths):
        gate.wait(5)
        return [{"text": "", "segments": []} for _ in paths]

    sched = InferenceScheduler(run)
    sched.max_batch_size = 1
    with patch.object(settings, "partial_shed_depth", 1):
        await sched.start()
        try:
            running = [asyncio.create_task(sched.submit("q0", 1.0, PRIORITY_REQUEST))]
            await asyncio.sleep(0.05)  # q0 executing
            running.append(asyncio.create_task(sched.submit("q1", 1.0, PRIORITY_REQUEST)))
            await asyncio.sleep(0.05)  # 1 executing, 1 queued -> depth 1
            assert await sched.submit("partial", 1.0, PRIORITY_PARTIAL) is None
            gate.set()
            await asyncio.gather(*running)
        finally:
            await sched.stop()
    assert sched.shed_partials == 1


async def test_cuda_oom_splits_batch_and_recovers():
    calls = []

    def run(paths):
        calls.append(len(paths))
        if len(paths) > 1:
            raise RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB")
        return [{"text": paths[0], "segments": []}]

    sched = InferenceScheduler(run)
    sched.max_batch_size = 4
    await sched.start()
    try:
        results = await asyncio.gather(*[sched.submit(f"a{i}", 5.0, PRIORITY_REQUEST) for i in range(4)])
    finally:
        await sched.stop()
    assert sorted(r["text"] for r in results) == ["a0", "a1", "a2", "a3"]
    assert sched.recent_oom_events(60) >= 1


async def test_cancelled_waiter_is_skipped():
    calls = []
    gate = threading.Event()

    def run(paths):
        if paths == ["blocker"]:
            gate.wait(5)
        calls.append(list(paths))
        return [{"text": p, "segments": []} for p in paths]

    sched = InferenceScheduler(run)
    sched.max_batch_size = 1
    await sched.start()
    try:
        blocker = asyncio.create_task(sched.submit("blocker", 1.0, PRIORITY_REQUEST))
        await asyncio.sleep(0.05)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(sched.submit("abandoned", 1.0, PRIORITY_REQUEST), 0.05)
        gate.set()
        await blocker
        await asyncio.sleep(0.05)
    finally:
        await sched.stop()
    assert ["abandoned"] not in calls  # timed-out caller never costs model time


async def test_parallel_lanes_run_concurrently_and_keep_priority():
    """With N lanes (ctranslate2 engine) N clips run at the same time; the
    queue still releases waiting items in priority order (docs/14)."""
    running, peak = [0], [0]
    order = []
    lock = threading.Lock()
    gate = threading.Event()

    def run(paths):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        if paths[0].startswith("blocker"):
            gate.wait(5)
        with lock:
            running[0] -= 1
            order.extend(paths)
        return [{"text": p, "segments": []} for p in paths]

    sched = InferenceScheduler(run)
    sched.max_batch_size = 1
    with patch.object(settings, "engine", "ctranslate2"), patch.object(settings, "inference_lanes", 2), \
            patch.object(settings, "partial_shed_depth", 100):
        await sched.start()
        try:
            assert sched.lanes == 2
            blockers = [asyncio.create_task(sched.submit(f"blocker{i}", 1.0, PRIORITY_REQUEST)) for i in (1, 2)]
            await asyncio.sleep(0.05)  # both lanes busy
            assert sched.in_flight == 2
            tasks = [
                asyncio.create_task(sched.submit("job", 1.0, PRIORITY_JOB)),
                asyncio.create_task(sched.submit("final", 1.0, PRIORITY_STREAM_FINAL)),
            ]
            await asyncio.sleep(0.05)
            gate.set()
            await asyncio.gather(*blockers, *tasks)
        finally:
            await sched.stop()
    assert peak[0] == 2
    assert order.index("final") < order.index("job")
    assert sched.in_flight == 0


def test_transformers_engine_always_gets_one_lane():
    with patch.object(settings, "engine", "transformers"), patch.object(settings, "inference_lanes", 4):
        assert settings.effective_lanes == 1
