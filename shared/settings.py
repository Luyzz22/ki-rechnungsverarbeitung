"""Application settings loaded from environment variables."""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-in-production"
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://sbs_user:dev_password_change_me@localhost:5432/sbs_nexus"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    resend_api_key: str = ""
    resend_from_address: str = "luis@sbsdeutschland.de"
    datev_export_dir: str = "./exports/datev"
    datev_default_skr: str = "SKR03"
    gobd_retention_years: int = 10
    gobd_evidence_dir: str = "./evidence"
    kosit_validator_url: str = "http://localhost:8080"
    kosit_validator_timeout: int = 30
    google_client_id: str = ""
    google_client_secret: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
