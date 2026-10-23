from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LABACCESS_", env_file=".env", extra="ignore")
    app_name: str = "LabAccess"
    database_url: str = "postgresql+psycopg://labaccess@127.0.0.1:55432/labaccess"
    signing_key: SecretStr = Field(min_length=32)
    biometric_key: SecretStr
    token_minutes: int = Field(default=60, ge=1, le=1440)
    heartbeat_seconds: int = Field(default=10, ge=3)
    stale_seconds: int = Field(default=30, ge=15)
    grace_minutes: int = Field(default=30, ge=1)
    retention_days: int = Field(default=90, ge=1)
    face_enabled: bool = False
    face_threshold: float = Field(default=0.50, ge=0, le=1)
    models_dir: str = "models"
    allow_loopback_http: bool = True
    veyon_url: str = "http://127.0.0.1:11080"
    veyon_key_name: str = "labaccess"
    veyon_private_key_path: str = ""
    veyon_ca: str = ""
