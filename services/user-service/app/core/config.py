from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "user-service"
    version: str = "1.0.0"

    database_url: str = "postgresql+asyncpg://user_user:user_pass@localhost:5432/user_db"
    auth_service_url: str = "http://auth-service:8000"
    email_confirmation_timeout_seconds: int = 30
    email_change_expiry_hours: int = 24
    min_age_years: int = 13

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""  # empty string → stub mode (logs to console, no email sent)
    smtp_password: str = ""
    smtp_from: str = "noreply@asr-quechua.com"
    frontend_url: str = "http://localhost:4200"

    class Config:
        env_file = ".env"


settings = Settings()
