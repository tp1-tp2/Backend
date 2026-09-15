from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Merged settings for the E3 monolithic baseline — auth + audio + ASR +
    persistence in one process. Intentionally has NO adaptive_mode/force_device
    knobs: `device` is fixed for the lifetime of the process, matching the
    experimental protocol's requirement ("sin conmutación CPU/GPU dinámica").
    Run it twice (DEVICE=cpu, DEVICE=cuda) for symmetric baselines against
    asr-service's adaptive runs — see docker-compose.yml.
    """

    model_config = {"protected_namespaces": ("settings_",), "env_file": ".env"}

    service_name: str = "monolith-baseline"
    version: str = "1.0.0"

    database_url: str = "postgresql+asyncpg://monolith_user:monolith_pass@localhost:5432/monolith_db"

    jwt_secret_key: str = "changeme_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    bcrypt_rounds: int = 12

    model_id: str = "QuechuaBase/whisper-base-qxp-finetuned"
    device: str = "cpu"  # fixed for the whole process — no runtime adaptation

    max_file_size_bytes: int = 52_428_800  # 50 MB
    allowed_formats: list[str] = ["wav", "mp3", "flac", "ogg", "m4a"]
    target_sample_rate: int = 16000
    max_duration_seconds: int = 3600


settings = Settings()
