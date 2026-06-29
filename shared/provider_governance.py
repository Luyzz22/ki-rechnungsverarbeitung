"""FlowCheck+ provider governance checks for regional cloud processing."""
from __future__ import annotations

import ipaddress
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from shared.inference_policy import DataClass, InferenceProfile, InferenceProvider, assert_inference_allowed
from shared.provider_deployments import (
    CloudProcessingRegion,
    ProviderDeploymentPolicy,
    provider_deployment_from_mapping,
)
from shared.providers.azure_identity import get_bool_config_value, get_config_value, is_production_runtime


GOVERNANCE_ERROR_CODE = "PROVIDER_GOVERNANCE_NOT_APPROVED"
FLOATING_MODEL_VALUES = frozenset({"latest", "default", "auto", "current"})
DISALLOWED_REGIONS = frozenset({"", "global", "datazone", "auto", "default"})
REGIONAL_CLOUD_PROVIDERS = frozenset(
    {
        InferenceProvider.AZURE_OPENAI_EU,
        InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU,
    }
)


class ProviderGovernanceError(RuntimeError):
    """PII-free provider governance failure."""

    def __init__(
        self,
        reason_code: str,
        *,
        provider: InferenceProvider | str,
        error_code: str = GOVERNANCE_ERROR_CODE,
    ) -> None:
        self.error_code = error_code
        self.reason_code = reason_code
        self.provider = getattr(provider, "value", str(provider))
        super().__init__(f"{error_code}: {reason_code}")

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "reason_code": self.reason_code,
            "provider": self.provider,
        }


@dataclass(frozen=True)
class ProviderGovernanceDecision:
    allowed: bool
    provider: str
    data_class: str
    inference_profile: str
    purpose: str
    cloud_processing_region: str
    deployment_ref: str = ""


def resolve_cloud_processing_region(
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    explicit_region: CloudProcessingRegion | str | None = None,
) -> CloudProcessingRegion | str:
    if explicit_region is not None:
        value = getattr(explicit_region, "value", str(explicit_region))
    else:
        value = get_config_value("FLOWCHECK_CLOUD_PROCESSING_REGION", settings=settings, env=env, default=CloudProcessingRegion.UNSET.value)
    try:
        return CloudProcessingRegion(str(value).strip().upper())
    except ValueError:
        return str(value)


def eu_regional_cloud_required_in_production(
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    return get_bool_config_value(
        "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION",
        settings=settings,
        env=env,
        default=False,
    )


def provider_governance_enforcement(
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    return get_config_value(
        "FLOWCHECK_PROVIDER_GOVERNANCE_ENFORCEMENT",
        settings=settings,
        env=env,
        default="block",
    ).strip().lower() or "block"


def assert_standard_invoice_allowed_for_runtime(
    *,
    data_class: DataClass | str,
    inference_profile: InferenceProfile | str,
    provider: InferenceProvider | str,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> None:
    try:
        data_class_enum = data_class if isinstance(data_class, DataClass) else DataClass(str(data_class))
        profile_enum = inference_profile if isinstance(inference_profile, InferenceProfile) else InferenceProfile(str(inference_profile))
    except ValueError:
        return
    if (
        data_class_enum == DataClass.INVOICE_CONFIDENTIAL
        and profile_enum == InferenceProfile.STANDARD
        and is_production_runtime(settings=settings, env=env)
        and eu_regional_cloud_required_in_production(settings=settings, env=env)
    ):
        raise ProviderGovernanceError(
            "production_invoice_confidential_requires_eu_regional_cloud",
            provider=provider,
        )


def resolve_provider_deployment(
    *,
    provider: InferenceProvider | str,
    endpoint_host: str,
    model_deployment_id: str,
    purpose: str,
    data_class: DataClass | str,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    deployments: Iterable[ProviderDeploymentPolicy] | None = None,
    source: str = "server_config",
) -> ProviderDeploymentPolicy:
    provider_enum = provider if isinstance(provider, InferenceProvider) else InferenceProvider(str(provider))
    data_class_enum = data_class if isinstance(data_class, DataClass) else DataClass(str(data_class))
    normalized_host = validate_deployment_endpoint_host(
        endpoint_host,
        allowed_hosts=get_config_value("FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST", settings=settings, env=env),
        provider=provider_enum,
        source=source,
    )

    for deployment in deployments if deployments is not None else _load_deployments(settings=settings, env=env):
        if deployment.provider != provider_enum:
            continue
        if _normalize_host(deployment.endpoint_host) != normalized_host:
            continue
        if deployment.model_deployment_id != model_deployment_id:
            continue
        validate_provider_deployment_policy(
            deployment,
            purpose=purpose,
            data_class=data_class_enum,
            settings=settings,
            env=env,
        )
        return deployment

    raise ProviderGovernanceError("deployment_policy_not_found", provider=provider_enum)


def assert_provider_governance_allowed(
    *,
    data_class: DataClass | str,
    inference_profile: InferenceProfile | str,
    provider: InferenceProvider | str,
    purpose: str,
    endpoint_host: str | None = None,
    model_deployment_id: str | None = None,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    deployments: Iterable[ProviderDeploymentPolicy] | None = None,
    cloud_processing_region: CloudProcessingRegion | str | None = None,
) -> ProviderGovernanceDecision:
    policy_decision = assert_inference_allowed(
        data_class=data_class,
        inference_profile=inference_profile,
        provider=provider,
        purpose=purpose,
    )
    assert_standard_invoice_allowed_for_runtime(
        data_class=data_class,
        inference_profile=inference_profile,
        provider=provider,
        settings=settings,
        env=env,
    )

    profile_enum = inference_profile if isinstance(inference_profile, InferenceProfile) else InferenceProfile(str(inference_profile))
    provider_enum = provider if isinstance(provider, InferenceProvider) else InferenceProvider(str(provider))
    resolved_cloud_region = resolve_cloud_processing_region(
        settings=settings,
        env=env,
        explicit_region=cloud_processing_region,
    )

    if (
        is_production_runtime(settings=settings, env=env)
        and eu_regional_cloud_required_in_production(settings=settings, env=env)
        and resolved_cloud_region == CloudProcessingRegion.UNSET
        and provider_enum not in {InferenceProvider.LOCAL_OPENAI_COMPAT, InferenceProvider.LOCAL_OCR}
    ):
        raise ProviderGovernanceError("cloud_processing_region_unset", provider=provider_enum)

    if profile_enum != InferenceProfile.EU_REGIONAL_CLOUD:
        return ProviderGovernanceDecision(
            allowed=True,
            provider=provider_enum.value,
            data_class=policy_decision.data_class,
            inference_profile=policy_decision.inference_profile,
            purpose=policy_decision.purpose,
            cloud_processing_region=getattr(resolved_cloud_region, "value", str(resolved_cloud_region)),
        )

    if provider_enum not in REGIONAL_CLOUD_PROVIDERS:
        raise ProviderGovernanceError("regional_cloud_provider_not_allowed", provider=provider_enum)
    if not endpoint_host:
        raise ProviderGovernanceError("endpoint_host_required", provider=provider_enum)
    if not model_deployment_id:
        raise ProviderGovernanceError("model_deployment_id_missing", provider=provider_enum)

    deployment = resolve_provider_deployment(
        provider=provider_enum,
        endpoint_host=endpoint_host,
        model_deployment_id=model_deployment_id,
        purpose=purpose,
        data_class=data_class,
        settings=settings,
        env=env,
        deployments=deployments,
    )
    return ProviderGovernanceDecision(
        allowed=True,
        provider=provider_enum.value,
        data_class=policy_decision.data_class,
        inference_profile=policy_decision.inference_profile,
        purpose=policy_decision.purpose,
        cloud_processing_region=deployment.processing_region,
        deployment_ref=f"{deployment.provider.value}:{deployment.endpoint_host}:{deployment.model_deployment_id}",
    )


def validate_provider_deployment_policy(
    deployment: ProviderDeploymentPolicy,
    *,
    purpose: str,
    data_class: DataClass,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> None:
    provider = deployment.provider
    validate_deployment_endpoint_host(
        deployment.endpoint_host,
        allowed_hosts=get_config_value("FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST", settings=settings, env=env),
        provider=provider,
    )
    _validate_processing_region(deployment.processing_region, provider=provider)
    _validate_model_pin(deployment.model_deployment_id, "model_deployment_id", provider=provider)
    _validate_model_pin(deployment.model_version, "model_version", provider=provider)
    if purpose not in deployment.purpose_allowlist:
        raise ProviderGovernanceError("purpose_not_allowed", provider=provider)
    if data_class not in deployment.data_class_allowlist:
        raise ProviderGovernanceError("data_class_not_allowed", provider=provider)
    if not deployment.retention_evidence_ref or not deployment.no_training_evidence_ref:
        raise ProviderGovernanceError("governance_evidence_missing", provider=provider)
    if not deployment.provider_governance_approved:
        raise ProviderGovernanceError("provider_governance_not_approved", provider=provider)


def validate_deployment_endpoint_host(
    endpoint_host: str,
    *,
    allowed_hosts: str | Iterable[str],
    provider: InferenceProvider | str,
    source: str = "server_config",
) -> str:
    provider_enum = provider if isinstance(provider, InferenceProvider) else InferenceProvider(str(provider))
    if source != "server_config":
        raise ProviderGovernanceError("endpoint_source_not_allowed", provider=provider_enum)
    value = str(endpoint_host or "").strip().lower().rstrip(".")
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or any(token in value for token in ("/", "@", "?", "#")):
        raise ProviderGovernanceError("endpoint_host_must_be_hostname_only", provider=provider_enum)
    if not value or "*" in value:
        raise ProviderGovernanceError("endpoint_host_invalid", provider=provider_enum)
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise ProviderGovernanceError("endpoint_host_ip_not_allowed", provider=provider_enum)

    allowlist = _parse_allowed_hosts(allowed_hosts)
    if not allowlist:
        raise ProviderGovernanceError("endpoint_host_allowlist_required", provider=provider_enum)
    if value not in allowlist:
        raise ProviderGovernanceError("endpoint_host_not_allowed", provider=provider_enum)
    return value


def _validate_processing_region(value: str, *, provider: InferenceProvider) -> None:
    normalized = str(value or "").strip().lower()
    if normalized in DISALLOWED_REGIONS:
        raise ProviderGovernanceError("processing_region_invalid", provider=provider)


def _validate_model_pin(value: str, field_name: str, *, provider: InferenceProvider) -> None:
    normalized = str(value or "").strip().lower()
    if not normalized:
        raise ProviderGovernanceError(f"{field_name}_missing", provider=provider)
    if normalized in FLOATING_MODEL_VALUES:
        raise ProviderGovernanceError(f"{field_name}_floating", provider=provider)


def _load_deployments(
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
) -> list[ProviderDeploymentPolicy]:
    raw = get_config_value("FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG", settings=settings, env=env).strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise ProviderGovernanceError("deployment_config_invalid_json", provider="unknown") from None
    values = parsed if isinstance(parsed, list) else [parsed]
    try:
        return [provider_deployment_from_mapping(item) for item in values if isinstance(item, dict)]
    except (TypeError, ValueError):
        raise ProviderGovernanceError("deployment_config_invalid", provider="unknown") from None


def _parse_allowed_hosts(allowed_hosts: str | Iterable[str]) -> set[str]:
    if isinstance(allowed_hosts, str):
        values = allowed_hosts.split(",")
    else:
        values = list(allowed_hosts)
    return {_normalize_host(value) for value in values if str(value).strip()}


def _normalize_host(value: str) -> str:
    return str(value).strip().lower().rstrip(".")
