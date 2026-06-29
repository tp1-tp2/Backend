from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"protected_namespaces": ("settings_",), "env_file": ".env"}

    service_name: str = "asr-service"
    version: str = "1.0.0"

    model_id: str = "QuechuaBase/whisper-base-qxp-finetuned"
    device: str = "cpu"  # "cuda" for GPU in production

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
