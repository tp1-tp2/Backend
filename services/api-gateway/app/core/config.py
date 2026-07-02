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

    allowed_origins: list[str] = [
        "http://localhost:4200",
        "http://localhost:4201",
        "https://asr-quechua-frontend-b722a.web.app",
        "https://asr-quechua-frontend-b722a.firebaseapp.com",
    ]

    class Config:
        env_file = ".env"


settings = Settings()
