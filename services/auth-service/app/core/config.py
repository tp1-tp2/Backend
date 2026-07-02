from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "auth-service"
    version: str = "1.0.0"

    database_url: str = "postgresql+asyncpg://auth_user:auth_pass@localhost:5432/auth_db"
    jwt_secret_key: str = "changeme_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    bcrypt_rounds: int = 12
    rate_limit_attempts: int = 5
    rate_limit_window_minutes: int = 15
    recovery_token_length: int = 32
    recovery_token_expiry_hours: int = 1

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""  # empty string → stub mode (logs to console, no email sent)
    smtp_password: str = ""
    smtp_from: str = "noreply@asr-quechua.com"
    frontend_url: str = "http://localhost:4200"

    class Config:
        env_file = ".env"


settings = Settings()
