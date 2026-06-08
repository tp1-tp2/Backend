from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "user-service"
    version: str = "1.0.0"

    database_url: str = "postgresql+asyncpg://user_user:user_pass@localhost:5432/user_db"
    email_confirmation_timeout_seconds: int = 30
    email_change_expiry_hours: int = 24
    min_age_years: int = 13

    class Config:
        env_file = ".env"


settings = Settings()
