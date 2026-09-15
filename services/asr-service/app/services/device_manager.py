"""Runtime hardware/load monitor that adapts asr-service's inference device and
numeric precision without restarting the process.

Two independent axes are adapted:
- device ("cpu"/"cuda"): coarse, rare — migrates the whole model to a different
  accelerator when GPU memory pressure changes.
- compute_type ("fp32"/"fp16"/"int8"): fine-grained — swaps numeric precision
  under CPU/GPU memory pressure. This is what keeps the mechanism meaningful in
  environments with no GPU at all (e.g. prod Azure Container Apps today), where
  device can never change but compute_type still can.

`force_device`/`force_compute_type` let experiments pin a clean sample set while
the monitor keeps running and logging what it WOULD have decided — so the
policy's reasoning is still evidenced even in forced runs. See
docs/01-adaptive-mechanism.md for the full design rationale.
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


def evaluate_policy(snapshot: HardwareSnapshot) -> tuple[str, str, str]:
    """Pure function: given a hardware snapshot, return the (device,
    compute_type, reason) the policy currently prefers — ignoring hysteresis/
    cooldown, which DeviceManager applies separately so this stays trivially
    unit-testable on its own.
    """
    reasons = []

    if settings.force_device:
        device = settings.force_device
        reasons.append(f"force_device={settings.force_device}")
    elif snapshot.gpu_available and (snapshot.gpu_vram_free_gb or 0) >= settings.gpu_vram_headroom_gb:
        device = "cuda"
        reasons.append(f"gpu available with {snapshot.gpu_vram_free_gb:.2f}GB free VRAM")
    else:
        device = "cpu"
        if snapshot.gpu_available:
            reasons.append(
                f"gpu VRAM pressure ({snapshot.gpu_vram_free_gb:.2f}GB free "
                f"< {settings.gpu_vram_headroom_gb}GB headroom)"
            )
        else:
            reasons.append("no gpu available")

    if settings.force_compute_type:
        compute_type = settings.force_compute_type
        reasons.append(f"force_compute_type={settings.force_compute_type}")
    elif device == "cuda":
        if (snapshot.gpu_vram_free_gb or 0) < settings.gpu_vram_headroom_gb:
            compute_type = "fp16"
            reasons.append("gpu VRAM pressure -> fp16")
        else:
            compute_type = "fp32"
    else:
        if snapshot.cpu_percent >= settings.cpu_high_pressure_percent:
            compute_type = "int8"
            reasons.append(
                f"cpu pressure ({snapshot.cpu_percent:.0f}% >= "
                f"{settings.cpu_high_pressure_percent}%) -> int8 quantization"
            )
        else:
            compute_type = "fp32"

    return device, compute_type, "; ".join(reasons)


class DeviceManager:
    """Owns the background adaptation loop and its decision history."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._history: deque[AdaptationDecision] = deque(maxlen=200)
        self._streak = 0
        self._pending: Optional[tuple[str, str]] = None
        self._last_swap_at: float = 0.0
        self._last_snapshot: Optional[HardwareSnapshot] = None
        self._in_flight = 0

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

        loop = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(None, probe_hardware)
        self._last_snapshot = snapshot

        current_device = whisper_service.get_current_device()
        current_compute_type = whisper_service.get_current_compute_type()
        desired_device, desired_compute_type, reason = evaluate_policy(snapshot)

        forced = bool(settings.force_device or settings.force_compute_type)
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
                current_device,
                current_compute_type,
                desired_device,
                desired_compute_type,
                reason + " (forced — not applied)",
                changed=False,
                forced=True,
            )
            return

        # Hysteresis: require the SAME desired state on N consecutive polls before
        # acting, so a single noisy CPU spike doesn't thrash the model between states.
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

        logger.info(
            "Applying adaptation: device %s->%s, compute_type %s->%s (%s)",
            current_device,
            desired_device,
            current_compute_type,
            desired_compute_type,
            reason,
        )
        try:
            await loop.run_in_executor(
                None, whisper_service.reload_model, desired_device, desired_compute_type
            )
            self._last_swap_at = time.monotonic()
            self._streak = 0
            self._pending = None
            self._record_decision(
                current_device,
                current_compute_type,
                desired_device,
                desired_compute_type,
                reason,
                changed=True,
                forced=False,
            )
        except Exception as exc:
            logger.error(
                "Model reload to device=%s compute_type=%s failed, keeping current state: %s",
                desired_device,
                desired_compute_type,
                exc,
            )
            self._record_decision(
                current_device,
                current_compute_type,
                desired_device,
                desired_compute_type,
                f"reload failed: {exc}",
                changed=False,
                forced=False,
            )

    def _record_decision(
        self,
        prev_device: str,
        prev_compute: str,
        new_device: str,
        new_compute: str,
        reason: str,
        changed: bool,
        forced: bool,
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
        )
        self._history.append(decision)
        logger.info(json.dumps({"event": "adaptation_decision", **asdict(decision)}))


manager = DeviceManager()
