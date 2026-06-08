from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "asr-service"
    version: str = "1.0.0"

    whisper_model: str = "medium"
    whisper_language: str = "qu"
    device: str = "cpu"  # "cuda" for GPU in production

    transcription_manager_url: str = "http://transcription-manager:8000"
    max_concurrent_connections: int = 100
    streaming_partial_interval_seconds: int = 3
    audio_buffer_max_seconds: int = 30
    audio_chunk_ms: int = 100

    class Config:
        env_file = ".env"


settings = Settings()
