from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # env_ignore_empty: compose passes unset knobs as "" (e.g. FORCE_BATCH_SIZE=)
    model_config = {"protected_namespaces": ("settings_",), "env_file": ".env", "env_ignore_empty": True}

    service_name: str = "asr-service"
    version: str = "1.0.0"

    model_id: str = "QuechuaBase/whisper-base-qxp-finetuned"
    device: str = "cpu"  # startup hint only — device_manager may migrate at runtime

    # --- Inference engine (docs/14-optimizacion-cpu.md) ---
    # "transformers": PyTorch pipeline (v1/v2 behaviour).
    # "ctranslate2": same weights converted at build time, run by faster-whisper.
    engine: str = "transformers"
    ct2_model_dir: str = "/models/ct2"
    # Parallel inference lanes: clips decoded concurrently by the model. Only
    # meaningful for ctranslate2 (the transformers pipeline is not safe to call
    # from several threads at once, so it always gets one lane).
    inference_lanes: int = 1
    ct2_cpu_threads: int = 0  # threads per lane; 0 = cpu_count // lanes

    @property
    def effective_lanes(self) -> int:
        return max(1, self.inference_lanes) if self.engine == "ctranslate2" else 1

    # --- Runtime adaptation (device/precision) ---
    # See services/asr-service/app/services/device_manager.py and
    # docs/01-adaptive-mechanism.md for the full policy design.
    adaptive_mode: bool = True
    # Pin device/compute_type for clean experiment sample sets (E2). The monitor
    # keeps running and logging what it WOULD have decided, it just never applies it.
    force_device: Optional[str] = None  # "cpu" | "cuda"
    force_compute_type: Optional[str] = None  # "fp32" | "fp16" | "int8"
    # Shortened from 20s/60s: with 180s load steps the old loop needed ~2 min
    # (3 polls x 20s + 60s cooldown) to react at all (E4 finding, C2.3).
    adaptation_check_interval_seconds: int = 5
    adaptation_cooldown_seconds: int = 30
    adaptation_hysteresis_checks: int = 3
    gpu_vram_headroom_gb: float = 1.0
    cpu_high_pressure_percent: float = 85.0
    # Queue-aware signal: E4 showed saturation surfaces as queueing in front of
    # the single inference worker, not as CPU% — so queue depth is now the
    # primary pressure signal for the policy (see device_manager.evaluate_policy).
    queue_pressure_depth: int = 4
    # Repeated CUDA OOMs within the window push the policy back to CPU.
    oom_cpu_fallback_events: int = 3
    oom_window_seconds: int = 120
    # Guarded adaptation: a precision downgrade made for speed (fp32 -> fp16/
    # int8) is kept only if it MEASURABLY lowers the model cost per clip. After
    # `adaptation_probation_items` clips in the new state, it is rolled back if
    # it is not at least `adaptation_min_gain` cheaper (E9 found dynamic int8
    # 2x SLOWER than fp32 on the evaluation CPU).
    adaptation_probation_items: int = 5
    adaptation_min_gain: float = 0.05

    # --- Inference scheduler: micro-batching + priorities + admission control ---
    # See app/services/inference_scheduler.py and docs/09-arquitectura-v2.md.
    batch_window_ms: int = 25
    max_batch_size: int = 16  # hard ceiling; the adaptive policy picks the effective size
    batch_size_cpu: int = 1
    batch_size_gpu: int = 8
    # Pin the batch size for clean ablation runs (E8); None = adaptive.
    force_batch_size: Optional[int] = None
    # Admission control for synchronous requests: reject fast (503 +
    # Retry-After) instead of queueing a request that would wait past its
    # timeout anyway. A request is rejected if the queue is deeper than
    # max_queue_depth OR its estimated wait exceeds admission_max_wait_seconds.
    max_queue_depth: int = 64
    admission_max_wait_seconds: float = 60.0
    # Live partials are best-effort: shed them when the queue is this deep.
    partial_shed_depth: int = 4
    inference_timeout_seconds: float = 100.0  # < audio-processor's 110s < gateway's 120s
    retry_after_seconds: int = 5
    target_sample_rate: int = 16000

    # --- Asynchronous job worker (Redis Streams consumer group) ---
    redis_url: str = ""
    job_worker_enabled: bool = False
    job_stream: str = "asr:jobs"
    job_group: str = "asr-workers"
    job_worker_concurrency: int = 16
    job_inference_timeout_seconds: float = 600.0
    # A pending job whose worker stopped heartbeating for this long is
    # re-claimed by another worker (at-least-once delivery after a crash).
    job_claim_idle_ms: int = 30_000
    job_max_attempts: int = 3
    job_result_ttl_seconds: int = 86_400

    # --- Token validation for the WebSocket endpoint (same modes as gateway) ---
    auth_mode: str = "local"  # "local" | "remote"
    jwt_secret_key: str = "changeme_in_production"
    jwt_algorithm: str = "HS256"

    persist_retries: int = 3

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
