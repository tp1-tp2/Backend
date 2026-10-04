from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "audio-processor"
    version: str = "1.0.0"

    database_url: str = "postgresql+asyncpg://audio_user:audio_pass@localhost:5432/audio_db"
    # Bounded SQLAlchemy pool per worker (see auth-service config for rationale)
    db_pool_size: int = 5
    db_max_overflow: int = 5
    asr_service_url: str = "http://asr-service:8000"
    # Timeout budget: strictly below the gateway's 120s, strictly above
    # asr-service's own 100s inference timeout (innermost hop fails first).
    asr_timeout_seconds: float = 110.0
    asr_connect_retries: int = 2

    # --- Asynchronous jobs (Redis Streams); empty redis_url disables /jobs ---
    redis_url: str = ""
    job_stream: str = "asr:jobs"
    job_group: str = "asr-workers"
    job_max_backlog: int = 5000
    job_audio_ttl_seconds: int = 3600
    job_result_ttl_seconds: int = 86400
    storage_url: str = "local"

    max_file_size_bytes: int = 52_428_800  # 50 MB
    allowed_formats: list[str] = ["wav", "mp3", "flac", "ogg", "m4a"]
    target_sample_rate: int = 16000
    max_duration_seconds: int = 3600  # 60 minutes

    class Config:
        env_file = ".env"


settings = Settings()
