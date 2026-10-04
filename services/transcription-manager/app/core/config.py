from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "transcription-manager"
    version: str = "1.0.0"

    database_url: str = "postgresql+asyncpg://trans_user:trans_pass@localhost:5432/trans_db"
    # Bounded SQLAlchemy pool per worker (see auth-service config for rationale)
    db_pool_size: int = 5
    db_max_overflow: int = 5
    default_page_size: int = 20
    max_page_size: int = 100
    download_timeout_seconds: int = 30
    max_download_size_bytes: int = 52_428_800  # 50 MB

    class Config:
        env_file = ".env"


settings = Settings()
