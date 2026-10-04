from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "api-gateway"
    version: str = "1.0.0"

    auth_service_url: str = "http://auth-service:8000"
    user_service_url: str = "http://user-service:8000"
    audio_processor_url: str = "http://audio-processor:8000"
    asr_service_url: str = "http://asr-service:8000"
    transcription_manager_url: str = "http://transcription-manager:8000"

    request_timeout: int = 30
    # Timeout budget for the synchronous /transcribe chain. Each hop gets a
    # strictly smaller budget than its caller (gateway > audio-processor >
    # asr-service) so the innermost hop times out first and the error surfaces
    # as a clean 504 instead of every layer waiting the same 300s.
    transcribe_timeout: float = 120.0
    auth_validate_timeout_seconds: float = 5.0
    retry_after_seconds: int = 5

    # --- Token validation (see app/core/token_validator.py) ---
    auth_mode: str = "local"  # "local" | "remote"
    jwt_secret_key: str = "changeme_in_production"
    jwt_algorithm: str = "HS256"
    redis_url: str = ""
    redis_timeout_seconds: float = 0.5
    revocation_fail_open: bool = True

    # Shared upstream connection pool (one per worker process)
    http_max_connections: int = 200
    http_max_keepalive: int = 50

    allowed_origins: list[str] = [
        "http://localhost:4200",
        "http://localhost:4201",
        "https://asr-quechua-frontend-b722a.web.app",
        "https://asr-quechua-frontend-b722a.firebaseapp.com",
    ]

    class Config:
        env_file = ".env"


settings = Settings()
