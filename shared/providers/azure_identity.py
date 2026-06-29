"""Azure identity and endpoint validation for FlowCheck+ adapters."""
from __future__ import annotations

import ipaddress
import os
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse

from shared.inference_policy import InferenceProvider


class AzureProviderError(RuntimeError):
    """PII-free exception for Azure adapter failures."""

    def __init__(
        self,
        error_code: str,
        reason_code: str,
        *,
        provider: InferenceProvider | str,
        retryable: bool = False,
    ) -> None:
        self.error_code = error_code
        self.reason_code = reason_code
        self.provider = getattr(provider, "value", str(provider))
        self.retryable = retryable
        super().__init__(f"{error_code}: {reason_code}")

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "reason_code": self.reason_code,
            "provider": self.provider,
            "retryable": self.retryable,
        }


def get_config_value(
    key: str,
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    default: str = "",
) -> str:
    source = env if env is not None else os.environ
    if key in source:
        return str(source.get(key, ""))
    if settings is not None:
        attr = key.lower()
        if hasattr(settings, attr):
            return str(getattr(settings, attr) or "")
    return default


def get_bool_config_value(
    key: str,
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    default: bool = False,
) -> bool:
    value = get_config_value(key, settings=settings, env=env, default=str(default).lower()).strip().lower()
    return value in {"1", "true", "yes", "on"}


def resolve_runtime_env(*, settings: Any | None = None, env: Mapping[str, str] | None = None) -> str:
    runtime_env = get_config_value("FLOWCHECK_RUNTIME_ENV", settings=settings, env=env).strip()
    if runtime_env:
        return runtime_env.lower()
    app_env = get_config_value("APP_ENV", settings=settings, env=env).strip()
    if app_env:
        return app_env.lower()
    environment = get_config_value("ENVIRONMENT", settings=settings, env=env, default="development").strip()
    return (environment or "development").lower()


def is_production_runtime(*, settings: Any | None = None, env: Mapping[str, str] | None = None) -> bool:
    return resolve_runtime_env(settings=settings, env=env) in {"prod", "production"}


def resolve_azure_credential(
    *,
    provider: InferenceProvider | str,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    managed_identity_credential_cls: type | None = None,
    default_credential_cls: type | None = None,
) -> Any:
    """Resolve the only permitted Azure credential for the active runtime."""
    provider_enum = provider if isinstance(provider, InferenceProvider) else InferenceProvider(str(provider))
    runtime_is_production = is_production_runtime(settings=settings, env=env)
    identity_mode = get_config_value(
        "FLOWCHECK_AZURE_IDENTITY_MODE",
        settings=settings,
        env=env,
        default="managed_identity",
    ).strip().lower()
    developer_credentials_allowed = get_bool_config_value(
        "FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS",
        settings=settings,
        env=env,
        default=False,
    )

    if runtime_is_production and developer_credentials_allowed:
        raise AzureProviderError(
            "AZURE_CONFIGURATION_INVALID",
            "developer_credentials_not_allowed_in_production",
            provider=provider_enum,
        )

    if runtime_is_production and identity_mode != "managed_identity":
        raise AzureProviderError(
            "AZURE_CONFIGURATION_INVALID",
            "production_requires_managed_identity",
            provider=provider_enum,
        )

    if identity_mode == "managed_identity":
        return _build_managed_identity_credential(
            provider=provider_enum,
            settings=settings,
            env=env,
            managed_identity_credential_cls=managed_identity_credential_cls,
        )

    if identity_mode == "developer_credentials":
        if runtime_is_production or not developer_credentials_allowed:
            raise AzureProviderError(
                "AZURE_CONFIGURATION_INVALID",
                "developer_credentials_not_allowed",
                provider=provider_enum,
            )
        return _build_developer_credential(
            provider=provider_enum,
            default_credential_cls=default_credential_cls,
        )

    raise AzureProviderError(
        "AZURE_CONFIGURATION_INVALID",
        "azure_identity_mode_invalid",
        provider=provider_enum,
    )


def _build_managed_identity_credential(
    *,
    provider: InferenceProvider,
    settings: Any | None,
    env: Mapping[str, str] | None,
    managed_identity_credential_cls: type | None,
) -> Any:
    if managed_identity_credential_cls is None:
        try:
            from azure.identity import ManagedIdentityCredential
        except Exception:
            raise AzureProviderError(
                "AZURE_AUTH_UNAVAILABLE",
                "managed_identity_credential_not_available",
                provider=provider,
            ) from None
        managed_identity_credential_cls = ManagedIdentityCredential

    client_id = get_config_value("FLOWCHECK_AZURE_MANAGED_IDENTITY_CLIENT_ID", settings=settings, env=env).strip()
    kwargs = {"client_id": client_id} if client_id else {}
    try:
        return managed_identity_credential_cls(**kwargs)
    except Exception:
        raise AzureProviderError(
            "AZURE_AUTH_UNAVAILABLE",
            "managed_identity_unavailable",
            provider=provider,
        ) from None


def _build_developer_credential(*, provider: InferenceProvider, default_credential_cls: type | None) -> Any:
    if default_credential_cls is None:
        try:
            from azure.identity import DefaultAzureCredential
        except Exception:
            raise AzureProviderError(
                "AZURE_AUTH_UNAVAILABLE",
                "developer_credential_not_available",
                provider=provider,
            ) from None
        default_credential_cls = DefaultAzureCredential

    try:
        return default_credential_cls()
    except Exception:
        raise AzureProviderError(
            "AZURE_AUTH_UNAVAILABLE",
            "developer_credential_unavailable",
            provider=provider,
        ) from None


def validate_azure_endpoint(
    endpoint: str,
    *,
    allowed_hosts: str | Iterable[str],
    provider: InferenceProvider | str,
    source: str = "server_config",
    error_code: str = "AZURE_CONFIGURATION_INVALID",
) -> str:
    """Validate an Azure endpoint against server-side strict rules."""
    provider_enum = provider if isinstance(provider, InferenceProvider) else InferenceProvider(str(provider))
    if source != "server_config":
        raise AzureProviderError(error_code, "endpoint_source_not_allowed", provider=provider_enum)

    parsed = urlparse(str(endpoint or "").strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise AzureProviderError(error_code, "endpoint_must_be_https", provider=provider_enum)
    if parsed.username or parsed.password or "@" in parsed.netloc:
        raise AzureProviderError(error_code, "endpoint_userinfo_not_allowed", provider=provider_enum)
    if parsed.query or parsed.fragment:
        raise AzureProviderError(error_code, "endpoint_query_or_fragment_not_allowed", provider=provider_enum)
    if parsed.path not in ("", "/"):
        raise AzureProviderError(error_code, "endpoint_path_not_allowed", provider=provider_enum)

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        raise AzureProviderError(error_code, "endpoint_host_missing", provider=provider_enum)
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise AzureProviderError(error_code, "endpoint_ip_not_allowed", provider=provider_enum)

    allowlist = _parse_allowed_hosts(allowed_hosts)
    if not allowlist:
        raise AzureProviderError(error_code, "endpoint_host_allowlist_required", provider=provider_enum)
    if hostname not in allowlist:
        raise AzureProviderError(error_code, "endpoint_host_not_allowed", provider=provider_enum)

    return f"https://{parsed.netloc.rstrip('/')}"


def _parse_allowed_hosts(allowed_hosts: str | Iterable[str]) -> set[str]:
    if isinstance(allowed_hosts, str):
        values = allowed_hosts.split(",")
    else:
        values = list(allowed_hosts)
    return {str(value).strip().lower().rstrip(".") for value in values if str(value).strip()}
