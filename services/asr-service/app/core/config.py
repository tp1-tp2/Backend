from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"protected_namespaces": ("settings_",), "env_file": ".env"}

    service_name: str = "asr-service"
    version: str = "1.0.0"

    model_id: str = "QuechuaBase/whisper-base-qxp-finetuned"
    device: str = "cpu"  # startup hint only — device_manager may migrate at runtime

    # --- Runtime adaptation (device/precision) ---
    # See services/asr-service/app/services/device_manager.py and
    # docs/01-adaptive-mechanism.md for the full policy design.
    adaptive_mode: bool = True
    # Pin device/compute_type for clean experiment sample sets (E2). The monitor
    # keeps running and logging what it WOULD have decided, it just never applies it.
    force_device: Optional[str] = None  # "cpu" | "cuda"
    force_compute_type: Optional[str] = None  # "fp32" | "fp16" | "int8"
    adaptation_check_interval_seconds: int = 20
    adaptation_cooldown_seconds: int = 60
    adaptation_hysteresis_checks: int = 3
    gpu_vram_headroom_gb: float = 1.0
    cpu_high_pressure_percent: float = 85.0

    auth_service_url: str = "http://auth-service:8000"
    transcription_manager_url: str = "http://transcription-manager:8000"
    max_concurrent_connections: int = 100
    streaming_partial_interval_seconds: int = 3
    # Caps the rolling PCM buffer kept per streaming session. Raw PCM is cheap in
    # memory (even 10 min at 48kHz/16-bit mono is ~57MB) — the real OOM risk was
    # concurrent Whisper inference threads (see _partial_running in
    # streaming_service.py), not buffer size. A low cap here silently discards the
    # OLDEST audio once exceeded, which truncates real speech from the start of a
    # long recording while only trailing silence survives to finalize().
    audio_buffer_max_seconds: int = 600
    audio_chunk_ms: int = 100
    # Separate, much shorter window used only for partial (live) transcription.
    # get_partial() re-transcribes this whole window from scratch every tick, so
    # keeping it small is what keeps partials catching up with real-time speech
    # instead of falling further behind as the session grows. finalize() is
    # unaffected — it still uses the full audio_buffer_max_seconds buffer.
    partial_window_seconds: int = 10


settings = Settings()
