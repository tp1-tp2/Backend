from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "audio-processor"
    version: str = "1.0.0"

    database_url: str = "postgresql+asyncpg://audio_user:audio_pass@localhost:5432/audio_db"
    asr_service_url: str = "http://asr-service:8000"
    storage_url: str = "local"

    max_file_size_bytes: int = 52_428_800  # 50 MB
    allowed_formats: list[str] = ["wav", "mp3", "flac", "ogg", "m4a"]
    target_sample_rate: int = 16000
    max_duration_seconds: int = 3600  # 60 minutes

    class Config:
        env_file = ".env"


settings = Settings()
