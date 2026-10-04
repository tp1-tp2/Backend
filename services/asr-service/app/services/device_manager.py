"""Runtime load/hardware monitor that adapts asr-service's inference device,
numeric precision and batch size without restarting the process.

Three axes are adapted:
- device ("cpu"/"cuda"): coarse, rare — migrates the whole model to a different
  accelerator when GPU availability/memory changes, or falls back to CPU after
  repeated CUDA out-of-memory errors.
- compute_type ("fp32"/"fp16"/"int8"): swaps numeric precision. On CUDA, fp16
  under queue pressure or VRAM pressure; on CPU, dynamic int8 quantization
  under queue pressure or CPU pressure. Requires a model rebuild, so it goes
  through hysteresis + cooldown.
- batch_size: how many queued clips the inference scheduler runs per forward
  pass. Cheap to change (no rebuild), so it is applied on every tick.

v2 change (E4 finding, criterion C2.3): the v1 policy only looked at CPU%,
which never crossed its threshold because saturation of a single inference
worker shows up as QUEUEING, not as CPU usage — the mechanism recorded zero
decisions across four load-test rounds. The primary pressure signal is now
the inference scheduler's queue depth (see inference_scheduler.py).

`force_device`/`force_compute_type` let experiments pin a clean sample set while
the monitor keeps running and logging what it WOULD have decided. See
docs/01-adaptive-mechanism.md and docs/09-arquitectura-v2.md.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

import psutil

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import torch
except ImportError:  # pragma: no cover - torch is a hard runtime dependency in prod
    torch = None


@dataclass
class HardwareSnapshot:
    timestamp: str
    cpu_percent: float
    cpu_count: int
    ram_available_gb: float
    ram_total_gb: float
    gpu_available: bool
    gpu_name: Optional[str] = None
    gpu_vram_free_gb: Optional[float] = None
    gpu_vram_total_gb: Optional[float] = None
    # Load signals from the inference scheduler (filled in by DeviceManager)
    queue_depth: int = 0
    estimated_wait_s: float = 0.0
    recent_oom_events: int = 0


@dataclass
class AdaptationDecision:
    timestamp: str
    previous_device: str
    previous_compute_type: str
    new_device: str
    new_compute_type: str
    reason: str
    changed: bool
    forced: bool
    previous_batch_size: int = 1
    new_batch_size: int = 1
    queue_depth: int = 0


def probe_hardware() -> HardwareSnapshot:
    """Blocking — safe to call directly or via run_in_executor."""
    vm = psutil.virtual_memory()
    gpu_available = False
    gpu_name = None
    gpu_vram_free_gb = None
    gpu_vram_total_gb = None
    if torch is not None and torch.cuda.is_available():
        try:
            gpu_available = True
            gpu_name = torch.cuda.get_device_name(0)
            free_bytes, total_bytes = torch.cuda.mem_get_info(0)
            gpu_vram_free_gb = free_bytes / (1024**3)
            gpu_vram_total_gb = total_bytes / (1024**3)
        except Exception as exc:  # pragma: no cover - GPU probing is best-effort
            logger.warning("GPU probe failed, treating as unavailable: %s", exc)
            gpu_available = False
    return HardwareSnapshot(
        timestamp=datetime.now(timezone.utc).isoformat(),
        cpu_percent=psutil.cpu_percent(interval=None),
        cpu_count=psutil.cpu_count() or 1,
        ram_available_gb=vm.available / (1024**3),
        ram_total_gb=vm.total / (1024**3),
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        gpu_vram_free_gb=gpu_vram_free_gb,
        gpu_vram_total_gb=gpu_vram_total_gb,
    )


def evaluate_policy(snapshot: HardwareSnapshot) -> tuple[str, str, int, str]:
    """Pure function: given a snapshot, return the (device, compute_type,
    batch_size, reason) the policy currently prefers — ignoring hysteresis/
    cooldown, which DeviceManager applies separately so this stays trivially
    unit-testable on its own.
    """
    reasons = []
    queue_pressure = snapshot.queue_depth >= settings.queue_pressure_depth
    oom_storm = snapshot.recent_oom_events >= settings.oom_cpu_fallback_events
    vram_free = snapshot.gpu_vram_free_gb or 0.0

    if settings.force_device:
        device = settings.force_device
        reasons.append(f"force_device={settings.force_device}")
    elif snapshot.gpu_available and oom_storm:
        device = "cpu"
        reasons.append(
            f"{snapshot.recent_oom_events} CUDA OOM events in {settings.oom_window_seconds}s -> cpu fallback"
        )
    elif snapshot.gpu_available and vram_free >= settings.gpu_vram_headroom_gb:
        device = "cuda"
        reasons.append(f"gpu available with {vram_free:.2f}GB free VRAM")
    else:
        device = "cpu"
        if snapshot.gpu_available:
            reasons.append(
                f"gpu VRAM pressure ({vram_free:.2f}GB free < {settings.gpu_vram_headroom_gb}GB headroom)"
            )
        else:
            reasons.append("no gpu available")

    if settings.force_compute_type:
        compute_type = settings.force_compute_type
        reasons.append(f"force_compute_type={settings.force_compute_type}")
    elif device == "cuda":
        if queue_pressure:
            compute_type = "fp16"
            reasons.append(f"queue pressure (depth {snapshot.queue_depth}) -> fp16")
        elif vram_free < 2 * settings.gpu_vram_headroom_gb:
            compute_type = "fp16"
            reasons.append("gpu VRAM pressure -> fp16")
        else:
            compute_type = "fp32"
    else:
        if queue_pressure:
            compute_type = "int8"
            reasons.append(f"queue pressure (depth {snapshot.queue_depth}) -> int8 quantization")
        elif snapshot.cpu_percent >= settings.cpu_high_pressure_percent:
            compute_type = "int8"
            reasons.append(
                f"cpu pressure ({snapshot.cpu_percent:.0f}% >= "
                f"{settings.cpu_high_pressure_percent}%) -> int8 quantization"
            )
        else:
            compute_type = "fp32"

    if device == "cuda":
        batch_size = settings.batch_size_gpu
        if queue_pressure:
            batch_size = settings.max_batch_size
        if snapshot.recent_oom_events:
            batch_size = max(1, batch_size // (2 ** snapshot.recent_oom_events))
            reasons.append(f"recent OOM -> batch {batch_size}")
    else:
        batch_size = settings.batch_size_cpu
    if settings.force_batch_size:
        batch_size = settings.force_batch_size
    batch_size = max(1, min(batch_size, settings.max_batch_size))

    return device, compute_type, batch_size, "; ".join(reasons)


class DeviceManager:
    """Owns the background adaptation loop and its decision history."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._history: deque[AdaptationDecision] = deque(maxlen=500)
        self._streak = 0
        self._pending: Optional[tuple[str, str]] = None
        self._last_swap_at: float = 0.0
        self._last_snapshot: Optional[HardwareSnapshot] = None
        self._in_flight = 0
        # Guarded adaptation (see _check_probation): states measured to be
        # slower than the one they replaced are never entered again.
        self._rejected: set[str] = set()
        self._probation: Optional[dict] = None

    @property
    def rejected_states(self) -> list[str]:
        return sorted(self._rejected)

    @property
    def last_snapshot(self) -> Optional[HardwareSnapshot]:
        return self._last_snapshot

    @property
    def history(self) -> list[AdaptationDecision]:
        return list(self._history)

    @property
    def in_flight(self) -> int:
        return self._in_flight

    def inference_started(self) -> None:
        self._in_flight += 1

    def inference_finished(self) -> None:
        self._in_flight = max(0, self._in_flight - 1)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())
            logger.info(
                "Device adaptation monitor started (interval=%ss, adaptive_mode=%s)",
                settings.adaptation_check_interval_seconds,
                settings.adaptive_mode,
            )

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        if not settings.adaptive_mode:
            logger.info("adaptive_mode=False — device adaptation monitor will not run")
            return
        while True:
            try:
                await self._tick()
            except Exception as exc:  # pragma: no cover - the monitor must never die
                logger.error("Adaptation monitor tick failed: %s", exc)
            await asyncio.sleep(settings.adaptation_check_interval_seconds)

    async def _tick(self) -> None:
        from app.services import whisper_service  # local import: avoid a module import cycle
        from app.services.inference_scheduler import scheduler

        loop = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(None, probe_hardware)
        snapshot.queue_depth = scheduler.depth
        snapshot.estimated_wait_s = scheduler.estimated_wait_s()
        snapshot.recent_oom_events = scheduler.recent_oom_events(settings.oom_window_seconds)
        self._last_snapshot = snapshot

        current_device = whisper_service.get_current_device()
        current_compute_type = whisper_service.get_current_compute_type()
        current_batch = scheduler.max_batch_size
        desired_device, desired_compute_type, desired_batch, reason = evaluate_policy(snapshot)

        if await self._check_probation(scheduler, whisper_service, snapshot, current_batch):
            return  # rolled back this tick
        if f"{desired_device}/{desired_compute_type}" in self._rejected:
            # Measured slower on this host before: keep the current model state
            # (batch size still adapts below).
            desired_device, desired_compute_type = current_device, current_compute_type
        # Pins are per axis: evaluate_policy already returns the pinned value
        # for a forced axis, so the others keep adapting (e.g. FORCE_DEVICE=cpu
        # still lets precision go fp32 -> int8 under load). Only when BOTH model
        # axes are pinned is the monitor purely observational ("would have
        # decided" log, nothing applied) — the clean-sample mode for E8.
        forced = bool(settings.force_device and settings.force_compute_type)

        # Batch size: no model rebuild involved, so apply it immediately (the
        # batch is computed for the device that is ACTUALLY loaded right now,
        # so a pending device migration never gets a batch size meant for the
        # other device).
        if desired_device == current_device and desired_batch != current_batch:
            scheduler.max_batch_size = desired_batch
            self._record_decision(
                current_device, current_compute_type, current_device, current_compute_type,
                f"batch {current_batch}->{desired_batch}; {reason}",
                changed=True, forced=forced, prev_batch=current_batch,
                new_batch=desired_batch, queue_depth=snapshot.queue_depth,
            )

        wants_change = (
            desired_device != current_device or desired_compute_type != current_compute_type
        )

        if not wants_change:
            self._streak = 0
            self._pending = None
            return

        if forced:
            # Record what the natural policy would have done, but never apply it —
            # keeps the policy's reasoning evidenced even during pinned experiment runs.
            self._record_decision(
                current_device, current_compute_type, desired_device, desired_compute_type,
                reason + " (forced — not applied)",
                changed=False, forced=True, prev_batch=current_batch,
                new_batch=scheduler.max_batch_size, queue_depth=snapshot.queue_depth,
            )
            return

        # Hysteresis: require the SAME desired state on N consecutive polls before
        # acting, so a single noisy spike doesn't thrash the model between states.
        desired = (desired_device, desired_compute_type)
        if self._pending == desired:
            self._streak += 1
        else:
            self._pending = desired
            self._streak = 1

        stable_enough = self._streak >= settings.adaptation_hysteresis_checks
        cooled_down = (time.monotonic() - self._last_swap_at) >= settings.adaptation_cooldown_seconds
        if not (stable_enough and cooled_down):
            return

        from_state = f"{current_device}/{current_compute_type}"
        to_state = f"{desired_device}/{desired_compute_type}"
        is_speed_move = current_compute_type == "fp32" and desired_compute_type in ("fp16", "int8")
        if is_speed_move and self._measured_not_faster(scheduler, from_state, to_state):
            self._rejected.add(to_state)
            self._record_decision(
                current_device, current_compute_type, desired_device, desired_compute_type,
                f"skipped: {to_state} measured not faster than {from_state} on this host; {reason}",
                changed=False, forced=False, prev_batch=current_batch,
                new_batch=current_batch, queue_depth=snapshot.queue_depth,
            )
            self._streak, self._pending = 0, None
            return

        logger.info(
            "Applying adaptation: device %s->%s, compute_type %s->%s (%s)",
            current_device, desired_device, current_compute_type, desired_compute_type, reason,
        )
        try:
            await loop.run_in_executor(
                None, whisper_service.reload_model, desired_device, desired_compute_type
            )
            self._last_swap_at = time.monotonic()
            self._streak = 0
            self._pending = None
            scheduler.max_batch_size = desired_batch
            if is_speed_move:
                from_total, from_n = scheduler.state_totals(from_state)
                to_total, to_n = scheduler.state_totals(to_state)
                self._probation = {
                    "from_device": current_device, "from_compute": current_compute_type,
                    "from_batch": current_batch, "to_state": to_state,
                    "from_cost": (from_total / from_n) if from_n else None,
                    "to_total0": to_total, "to_n0": to_n,
                }
            self._record_decision(
                current_device, current_compute_type, desired_device, desired_compute_type,
                reason, changed=True, forced=False, prev_batch=current_batch,
                new_batch=desired_batch, queue_depth=snapshot.queue_depth,
            )
        except Exception as exc:
            logger.error(
                "Model reload to device=%s compute_type=%s failed, keeping current state: %s",
                desired_device, desired_compute_type, exc,
            )
            self._record_decision(
                current_device, current_compute_type, desired_device, desired_compute_type,
                f"reload failed: {exc}", changed=False, forced=False,
                prev_batch=current_batch, new_batch=current_batch,
                queue_depth=snapshot.queue_depth,
            )

    @staticmethod
    def _measured_not_faster(scheduler, from_state: str, to_state: str) -> bool:
        f_total, f_n = scheduler.state_totals(from_state)
        t_total, t_n = scheduler.state_totals(to_state)
        if f_n < settings.adaptation_probation_items or t_n < settings.adaptation_probation_items:
            return False  # not enough evidence yet: allow the move (probation will judge)
        return (t_total / t_n) > (f_total / f_n) * (1 - settings.adaptation_min_gain)

    async def _check_probation(self, scheduler, whisper_service, snapshot, current_batch) -> bool:
        """After a speed-motivated precision downgrade, compare the model cost
        per clip measured in the new state against the state it replaced. If
        it is not at least `adaptation_min_gain` cheaper, roll back and never
        enter that state again on this host. Returns True if it rolled back."""
        p = self._probation
        if p is None:
            return False
        current = f"{whisper_service.get_current_device()}/{whisper_service.get_current_compute_type()}"
        if current != p["to_state"]:
            self._probation = None  # the policy already moved on
            return False
        total, n = scheduler.state_totals(p["to_state"])
        new_n = n - p["to_n0"]
        if new_n < settings.adaptation_probation_items:
            return False
        new_cost = (total - p["to_total0"]) / new_n
        self._probation = None
        from_state = f"{p['from_device']}/{p['from_compute']}"
        if p["from_cost"] is None or new_cost <= p["from_cost"] * (1 - settings.adaptation_min_gain):
            self._record_decision(
                p["from_device"], p["from_compute"], *p["to_state"].split("/"),
                f"probation passed: {new_cost:.3f}s/clip vs {p['from_cost'] or 0:.3f}s/clip in {from_state}",
                changed=False, forced=False, prev_batch=current_batch, new_batch=current_batch,
                queue_depth=snapshot.queue_depth,
            )
            return False
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, whisper_service.reload_model, p["from_device"], p["from_compute"]
        )
        scheduler.max_batch_size = p["from_batch"]
        self._rejected.add(p["to_state"])
        self._last_swap_at = time.monotonic()
        self._streak, self._pending = 0, None
        self._record_decision(
            *p["to_state"].split("/"), p["from_device"], p["from_compute"],
            f"rollback: {p['to_state']} measured {new_cost:.3f}s/clip vs "
            f"{p['from_cost']:.3f}s/clip in {from_state} -> state rejected on this host",
            changed=True, forced=False, prev_batch=current_batch, new_batch=p["from_batch"],
            queue_depth=snapshot.queue_depth,
        )
        return True

    def _record_decision(
        self,
        prev_device: str,
        prev_compute: str,
        new_device: str,
        new_compute: str,
        reason: str,
        changed: bool,
        forced: bool,
        prev_batch: int = 1,
        new_batch: int = 1,
        queue_depth: int = 0,
    ) -> None:
        decision = AdaptationDecision(
            timestamp=datetime.now(timezone.utc).isoformat(),
            previous_device=prev_device,
            previous_compute_type=prev_compute,
            new_device=new_device,
            new_compute_type=new_compute,
            reason=reason,
            changed=changed,
            forced=forced,
            previous_batch_size=prev_batch,
            new_batch_size=new_batch,
            queue_depth=queue_depth,
        )
        self._history.append(decision)
        logger.info(json.dumps({"event": "adaptation_decision", **asdict(decision)}))


manager = DeviceManager()
