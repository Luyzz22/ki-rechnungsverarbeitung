"""Provider selection and Azure adapter configuration helpers.

This module contains no Azure SDK side effects. It only resolves server-side
configuration and selects provider identities based on the inference policy
profile and purpose.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from shared.inference_policy import DataClass, InferenceProfile, InferenceProvider, assert_inference_allowed
from shared.organization_context import TrustedOrganizationContext, resolve_tenant_policy_for_context
from shared.providers.azure_identity import (
    AzureProviderError,
    get_bool_config_value,
    get_config_value,
    validate_azure_endpoint,
)


AZURE_OPENAI_DEFAULT_SCOPE = "https://cognitiveservices.azure.com/.default"
AZURE_OPENAI_DEFAULT_API_VERSION = "2024-10-21"
AZURE_DOCUMENT_INTELLIGENCE_DEFAULT_MODEL = "prebuilt-invoice"


@dataclass(frozen=True)
class AzureOpenAIConfig:
    endpoint: str
    deployment: str
    api_version: str
    scope: str
    allowed_region: str


@dataclass(frozen=True)
class AzureDocumentIntelligenceConfig:
    endpoint: str
    model: str
    allowed_region: str


def _get_config_value(
    key: str,
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    default: str = "",
) -> str:
    return get_config_value(key, settings=settings, env=env, default=default)


def _get_bool_config_value(
    key: str,
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    default: bool = False,
) -> bool:
    return get_bool_config_value(key, settings=settings, env=env, default=default)


def azure_adapters_enabled(*, settings: Any | None = None, env: Mapping[str, str] | None = None) -> bool:
    return _get_bool_config_value("FLOWCHECK_AZURE_ADAPTERS_ENABLED", settings=settings, env=env, default=False)


def azure_auth_mode(*, settings: Any | None = None, env: Mapping[str, str] | None = None) -> str:
    return _get_config_value("FLOWCHECK_AZURE_AUTH_MODE", settings=settings, env=env, default="entra").strip().lower()


def _validate_entra_auth(*, settings: Any | None, env: Mapping[str, str] | None, provider: InferenceProvider) -> None:
    if azure_auth_mode(settings=settings, env=env) != "entra":
        raise AzureProviderError(
            "AZURE_CONFIGURATION_INVALID",
            "auth_mode_must_be_entra",
            provider=provider,
        )


def _validate_adapters_enabled(*, settings: Any | None, env: Mapping[str, str] | None, provider: InferenceProvider) -> None:
    if not azure_adapters_enabled(settings=settings, env=env):
        raise AzureProviderError(
            "AZURE_ADAPTER_DISABLED",
            "azure_adapters_disabled",
            provider=provider,
        )


def resolve_azure_openai_config(
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> AzureOpenAIConfig:
    provider = InferenceProvider.AZURE_OPENAI_EU
    _validate_adapters_enabled(settings=settings, env=env, provider=provider)
    _validate_entra_auth(settings=settings, env=env, provider=provider)

    endpoint = _get_config_value("AZURE_OPENAI_ENDPOINT", settings=settings, env=env).strip()
    deployment = _get_config_value("AZURE_OPENAI_DEPLOYMENT", settings=settings, env=env).strip()
    api_version = _get_config_value(
        "AZURE_OPENAI_API_VERSION",
        settings=settings,
        env=env,
        default=AZURE_OPENAI_DEFAULT_API_VERSION,
    ).strip() or AZURE_OPENAI_DEFAULT_API_VERSION
    scope = _get_config_value(
        "AZURE_OPENAI_SCOPE",
        settings=settings,
        env=env,
        default=AZURE_OPENAI_DEFAULT_SCOPE,
    ).strip() or AZURE_OPENAI_DEFAULT_SCOPE
    allowed_region = _get_config_value("FLOWCHECK_AZURE_ALLOWED_REGION", settings=settings, env=env).strip()
    allowed_hosts = _get_config_value("FLOWCHECK_AZURE_ENDPOINT_HOST_ALLOWLIST", settings=settings, env=env).strip()

    if not endpoint or not deployment:
        raise AzureProviderError(
            "AZURE_CONFIGURATION_INVALID",
            "azure_openai_endpoint_or_deployment_missing",
            provider=provider,
        )

    endpoint = validate_azure_endpoint(
        endpoint,
        allowed_hosts=allowed_hosts,
        provider=provider,
        source="server_config",
        error_code="AZURE_CONFIGURATION_INVALID",
    )

    if scope != AZURE_OPENAI_DEFAULT_SCOPE:
        raise AzureProviderError(
            "AZURE_CONFIGURATION_INVALID",
            "azure_openai_scope_not_allowed",
            provider=provider,
        )

    return AzureOpenAIConfig(
        endpoint=endpoint,
        deployment=deployment,
        api_version=api_version,
        scope=scope,
        allowed_region=allowed_region,
    )


def resolve_azure_document_intelligence_config(
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> AzureDocumentIntelligenceConfig:
    provider = InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU
    _validate_adapters_enabled(settings=settings, env=env, provider=provider)
    _validate_entra_auth(settings=settings, env=env, provider=provider)

    endpoint = _get_config_value("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", settings=settings, env=env).strip()
    model = _get_config_value(
        "AZURE_DOCUMENT_INTELLIGENCE_MODEL",
        settings=settings,
        env=env,
        default=AZURE_DOCUMENT_INTELLIGENCE_DEFAULT_MODEL,
    ).strip() or AZURE_DOCUMENT_INTELLIGENCE_DEFAULT_MODEL
    allowed_region = _get_config_value("FLOWCHECK_AZURE_ALLOWED_REGION", settings=settings, env=env).strip()
    allowed_hosts = _get_config_value("FLOWCHECK_AZURE_ENDPOINT_HOST_ALLOWLIST", settings=settings, env=env).strip()

    if not endpoint:
        raise AzureProviderError(
            "AZURE_CONFIGURATION_INVALID",
            "azure_document_intelligence_endpoint_missing",
            provider=provider,
        )
    if model != AZURE_DOCUMENT_INTELLIGENCE_DEFAULT_MODEL:
        raise AzureProviderError(
            "AZURE_DOCINTEL_MODEL_UNAVAILABLE",
            "only_prebuilt_invoice_is_allowed",
            provider=provider,
        )

    endpoint = validate_azure_endpoint(
        endpoint,
        allowed_hosts=allowed_hosts,
        provider=provider,
        source="server_config",
        error_code="AZURE_CONFIGURATION_INVALID",
    )

    return AzureDocumentIntelligenceConfig(endpoint=endpoint, model=model, allowed_region=allowed_region)


def select_provider_for_purpose(
    *,
    data_class: DataClass | str,
    inference_profile: InferenceProfile | str,
    purpose: str,
    tenant_processing_policy: Any | None = None,
    organization_context: TrustedOrganizationContext | None = None,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    local_provider_available: bool = False,
) -> InferenceProvider:
    """Select the intended provider identity without instantiating clients.

    Existing standard flows keep their direct-provider behavior. Professional
    secrecy flows are routed to Azure identities by purpose. Sovereign flows are
    routed to local identities only.
    """
    tenant_policy = tenant_processing_policy
    if tenant_policy is not None or organization_context is not None:
        from shared.tenant_processing_policy import assert_tenant_provider_allowed

        if tenant_policy is None:
            tenant_policy = resolve_tenant_policy_for_context(
                organization_context,
                settings=settings,
                env=env,
            )
        inference_profile = tenant_policy.effective_inference_profile

    try:
        profile = inference_profile if isinstance(inference_profile, InferenceProfile) else InferenceProfile(str(inference_profile))
    except ValueError:
        assert_inference_allowed(
            data_class=data_class,
            inference_profile=inference_profile,
            provider="unknown",
            purpose=purpose,
        )
        raise
    purpose_text = str(purpose or "").lower()
    is_document_analysis = any(marker in purpose_text for marker in ("document", "ocr", "vision", "invoice_file"))

    if profile == InferenceProfile.STANDARD:
        provider = InferenceProvider.OPENAI_DIRECT
    elif profile == InferenceProfile.EU_REGIONAL_CLOUD:
        provider = InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU if is_document_analysis else InferenceProvider.AZURE_OPENAI_EU
    elif profile == InferenceProfile.PROFESSIONAL_SECRECY:
        provider = InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU if is_document_analysis else InferenceProvider.AZURE_OPENAI_EU
    elif profile == InferenceProfile.SOVEREIGN:
        provider = InferenceProvider.LOCAL_OCR if is_document_analysis else InferenceProvider.LOCAL_OPENAI_COMPAT
    else:
        provider = "unknown"

    assert_inference_allowed(
        data_class=data_class,
        inference_profile=inference_profile,
        provider=provider,
        purpose=purpose,
    )
    if tenant_policy is not None:
        assert_tenant_provider_allowed(
            tenant_policy,
            provider=provider,
            local_provider_available=local_provider_available,
        )
    return provider


def create_provider(provider: InferenceProvider | str, **kwargs: Any) -> Any:
    """Instantiate a concrete provider adapter by identity."""
    provider_enum = provider if isinstance(provider, InferenceProvider) else InferenceProvider(str(provider))
    if provider_enum == InferenceProvider.AZURE_OPENAI_EU:
        from shared.providers.azure_openai_provider import AzureOpenAIProvider

        return AzureOpenAIProvider(**kwargs)
    if provider_enum == InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU:
        from shared.providers.azure_document_intelligence_provider import AzureDocumentIntelligenceProvider

        return AzureDocumentIntelligenceProvider(**kwargs)
    raise AzureProviderError(
        "AZURE_CONFIGURATION_INVALID",
        "provider_factory_only_supports_azure_adapters",
        provider=provider_enum,
    )
