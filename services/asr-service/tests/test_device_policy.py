from unittest.mock import patch

from app.core.config import settings
from app.services.device_manager import HardwareSnapshot, evaluate_policy


def _snap(**overrides) -> HardwareSnapshot:
    base = dict(
        timestamp="2026-10-03T00:00:00+00:00",
        cpu_percent=20.0,
        cpu_count=8,
        ram_available_gb=8.0,
        ram_total_gb=16.0,
        gpu_available=False,
        gpu_vram_free_gb=None,
        gpu_vram_total_gb=None,
    )
    base.update(overrides)
    return HardwareSnapshot(**base)


def _gpu(**overrides) -> HardwareSnapshot:
    gpu = dict(gpu_available=True, gpu_name="RTX A1000", gpu_vram_free_gb=7.0, gpu_vram_total_gb=8.0)
    gpu.update(overrides)
    return _snap(**gpu)


def test_cpu_idle_stays_fp32_batch1():
    device, compute, batch, _ = evaluate_policy(_snap())
    assert (device, compute, batch) == ("cpu", "fp32", settings.batch_size_cpu)


def test_cpu_queue_pressure_quantizes_even_with_low_cpu_percent():
    # The v1 blind spot: queueing with moderate CPU% never triggered anything.
    device, compute, _, reason = evaluate_policy(
        _snap(cpu_percent=40.0, queue_depth=settings.queue_pressure_depth)
    )
    assert (device, compute) == ("cpu", "int8")
    assert "queue pressure" in reason


def test_cpu_percent_pressure_still_quantizes():
    _, compute, _, _ = evaluate_policy(_snap(cpu_percent=95.0))
    assert compute == "int8"


def test_gpu_idle_uses_cuda_fp32_default_batch():
    device, compute, batch, _ = evaluate_policy(_gpu())
    assert (device, compute, batch) == ("cuda", "fp32", settings.batch_size_gpu)


def test_gpu_queue_pressure_goes_fp16_and_max_batch():
    device, compute, batch, _ = evaluate_policy(_gpu(queue_depth=settings.queue_pressure_depth + 3))
    assert (device, compute, batch) == ("cuda", "fp16", settings.max_batch_size)


def test_gpu_vram_pressure_falls_back_to_cpu():
    device, _, batch, _ = evaluate_policy(_gpu(gpu_vram_free_gb=0.2))
    assert device == "cpu"
    assert batch == settings.batch_size_cpu


def test_recent_oom_halves_batch():
    _, _, batch, reason = evaluate_policy(_gpu(recent_oom_events=1))
    assert batch == max(1, settings.batch_size_gpu // 2)
    assert "OOM" in reason


def test_oom_storm_falls_back_to_cpu():
    device, _, _, reason = evaluate_policy(_gpu(recent_oom_events=settings.oom_cpu_fallback_events))
    assert device == "cpu"
    assert "fallback" in reason


def test_force_batch_size_wins():
    with patch.object(settings, "force_batch_size", 3):
        _, _, batch, _ = evaluate_policy(_gpu(queue_depth=50))
    assert batch == 3


def test_force_device_and_compute():
    with (
        patch.object(settings, "force_device", "cpu"),
        patch.object(settings, "force_compute_type", "fp32"),
    ):
        device, compute, _, _ = evaluate_policy(_gpu(queue_depth=50))
    assert (device, compute) == ("cpu", "fp32")


# ---------- guarded adaptation: probation + rollback ----------

import asyncio  # noqa: E402

from app.services.device_manager import DeviceManager  # noqa: E402


class _FakeScheduler:
    def __init__(self, costs):
        self.costs = costs  # state -> (total_s, n)
        self.max_batch_size = 1

    def state_totals(self, state):
        return self.costs.get(state, (0.0, 0))


class _FakeWhisper:
    def __init__(self, device, compute):
        self.device, self.compute = device, compute
        self.reloads = []

    def get_current_device(self):
        return self.device

    def get_current_compute_type(self):
        return self.compute

    def reload_model(self, device, compute):
        self.reloads.append((device, compute))
        self.device, self.compute = device, compute


def _probation_after_switch(fp32_cost: float, int8_cost: float, n: int = 10):
    mgr = DeviceManager()
    sched = _FakeScheduler({"cpu/fp32": (fp32_cost * 20, 20), "cpu/int8": (0.0, 0)})
    whisper = _FakeWhisper("cpu", "int8")  # the switch to int8 already happened
    mgr._probation = {
        "from_device": "cpu", "from_compute": "fp32", "from_batch": 1, "to_state": "cpu/int8",
        "from_cost": fp32_cost, "to_total0": 0.0, "to_n0": 0,
    }
    sched.costs["cpu/int8"] = (int8_cost * n, n)
    rolled = asyncio.run(mgr._check_probation(sched, whisper, _snap(), 1))
    return mgr, whisper, rolled


def test_slower_precision_is_rolled_back_and_rejected():
    # E9 finding: dynamic int8 was ~2x slower than fp32 on the evaluation CPU.
    mgr, whisper, rolled = _probation_after_switch(fp32_cost=1.2, int8_cost=2.6)
    assert rolled
    assert whisper.reloads == [("cpu", "fp32")]
    assert "cpu/int8" in mgr.rejected_states
    assert "rollback" in mgr.history[-1].reason


def test_faster_precision_passes_probation():
    mgr, whisper, rolled = _probation_after_switch(fp32_cost=1.2, int8_cost=0.6)
    assert not rolled
    assert whisper.reloads == []
    assert mgr.rejected_states == []
    assert "probation passed" in mgr.history[-1].reason


def test_probation_waits_for_enough_samples():
    mgr, whisper, rolled = _probation_after_switch(fp32_cost=1.2, int8_cost=2.6, n=2)
    assert not rolled and whisper.reloads == []
    assert mgr._probation is not None


def test_measured_not_faster_skips_move():
    sched = _FakeScheduler({"cpu/fp32": (12.0, 10), "cpu/int8": (26.0, 10)})
    assert DeviceManager._measured_not_faster(sched, "cpu/fp32", "cpu/int8")
    sched = _FakeScheduler({"cuda/fp32": (5.0, 10), "cuda/fp16": (3.0, 10)})
    assert not DeviceManager._measured_not_faster(sched, "cuda/fp32", "cuda/fp16")
