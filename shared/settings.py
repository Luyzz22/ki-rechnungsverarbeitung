"""Application settings loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = ""
    app_port: int = 8000
    app_host: str = "127.0.0.1"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://localhost:5432/sbs_nexus"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    flowcheck_default_inference_profile: str = "standard"
    flowcheck_policy_enforcement: str = "block"
    flowcheck_runtime_env: str = ""
    flowcheck_require_eu_regional_cloud_in_production: bool = False
    flowcheck_provider_governance_enforcement: str = "block"
    flowcheck_cloud_processing_region: str = "UNSET"
    flowcheck_provider_deployment_config: str = ""
    flowcheck_provider_endpoint_host_allowlist: str = ""
    flowcheck_azure_adapters_enabled: bool = False
    flowcheck_azure_auth_mode: str = "entra"
    flowcheck_azure_identity_mode: str = "managed_identity"
    flowcheck_azure_managed_identity_client_id: str = ""
    flowcheck_azure_allow_developer_credentials: bool = False
    flowcheck_azure_allowed_region: str = ""
    flowcheck_azure_endpoint_host_allowlist: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_scope: str = "https://cognitiveservices.azure.com/.default"
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_model: str = "prebuilt-invoice"
    local_llm_base_url: str = ""
    local_llm_api_key: str = ""
    local_llm_model: str = ""
    local_ocr_enabled: bool = False
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
