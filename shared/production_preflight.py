"""Local production preflight for FlowCheck+ provider governance.

The preflight validates server-side configuration only. It must not instantiate
provider clients, resolve Azure credentials, or perform network access.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from shared.inference_policy import InferenceProfile, InferenceProvider
from shared.provider_deployments import ProviderDeploymentPolicy, provider_deployment_from_mapping
from shared.provider_governance import (
    DISALLOWED_REGIONS,
    FLOATING_MODEL_VALUES,
    REGIONAL_CLOUD_PROVIDERS,
    ProviderGovernanceError,
    validate_deployment_endpoint_host,
)
from shared.providers.azure_identity import get_bool_config_value, get_config_value, is_production_runtime


PREFLIGHT_OK_CODE = "PRODUCTION_PREFLIGHT_OK"
PREFLIGHT_FAILED_CODE = "PRODUCTION_PREFLIGHT_FAILED"
AZURE_REGIONAL_PROVIDERS = frozenset(
    {
        InferenceProvider.AZURE_OPENAI_EU,
        InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU,
    }
)


@dataclass(frozen=True)
class ProductionPreflightIssue:
    """PII-free production preflight issue."""

    error_code: str
    field: str


@dataclass(frozen=True)
class ProductionPreflightResult:
    """Result returned by the local production preflight."""

    ok: bool
    issues: tuple[ProductionPreflightIssue, ...]


def run_production_preflight(
    *,
    settings: Any | None = None,
    env: Mapping[str, str] | None = None,
    deployments: Iterable[ProviderDeploymentPolicy] | None = None,
) -> ProductionPreflightResult:
    """Validate production-governance readiness without touching providers."""
    if not is_production_runtime(settings=settings, env=env):
        return ProductionPreflightResult(ok=True, issues=())

    issues: list[ProductionPreflightIssue] = []
    require_regional_cloud = get_bool_config_value(
        "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION",
        settings=settings,
        env=env,
        default=False,
    )
    if not require_regional_cloud:
        issues.append(
            ProductionPreflightIssue(
                "PREFLIGHT_PRODUCTION_REGIONAL_CLOUD_ENFORCEMENT_DISABLED",
                "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION",
            )
        )

    default_profile = get_config_value(
        "FLOWCHECK_DEFAULT_INFERENCE_PROFILE",
        settings=settings,
        env=env,
        default=InferenceProfile.STANDARD.value,
    ).strip().lower()
    if default_profile == InferenceProfile.STANDARD.value:
        issues.append(
            ProductionPreflightIssue(
                "PREFLIGHT_DEFAULT_PROFILE_STANDARD",
                "FLOWCHECK_DEFAULT_INFERENCE_PROFILE",
            )
        )

    governance_enforcement = get_config_value(
        "FLOWCHECK_PROVIDER_GOVERNANCE_ENFORCEMENT",
        settings=settings,
        env=env,
        default="block",
    ).strip().lower()
    if governance_enforcement != "block":
        issues.append(
            ProductionPreflightIssue(
                "PREFLIGHT_PROVIDER_GOVERNANCE_ENFORCEMENT_NOT_BLOCK",
                "FLOWCHECK_PROVIDER_GOVERNANCE_ENFORCEMENT",
            )
        )

    allowed_hosts = get_config_value(
        "FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST",
        settings=settings,
        env=env,
    )
    if not _parse_csv_values(allowed_hosts):
        issues.append(
            ProductionPreflightIssue(
                "PREFLIGHT_PROVIDER_ENDPOINT_HOST_ALLOWLIST_EMPTY",
                "FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST",
            )
        )

    deployment_values = list(deployments) if deployments is not None else _load_preflight_deployments(settings=settings, env=env, issues=issues)
    if not deployment_values:
        issues.append(
            ProductionPreflightIssue(
                "PREFLIGHT_PROVIDER_DEPLOYMENT_CONFIG_EMPTY",
                "FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG",
            )
        )
    else:
        for deployment in deployment_values:
            issues.extend(_validate_deployment(deployment, allowed_hosts=allowed_hosts))

    if any(deployment.provider in AZURE_REGIONAL_PROVIDERS for deployment in deployment_values):
        issues.extend(_validate_azure_runtime_settings(settings=settings, env=env))

    return ProductionPreflightResult(ok=not issues, issues=tuple(issues))


def format_preflight_result(result: ProductionPreflightResult) -> str:
    """Render a sanitized preflight result for CLI output."""
    if result.ok:
        return PREFLIGHT_OK_CODE
    lines = [PREFLIGHT_FAILED_CODE]
    lines.extend(f"{issue.error_code} field={issue.field}" for issue in result.issues)
    return "\n".join(lines)


def _load_preflight_deployments(
    *,
    settings: Any | None,
    env: Mapping[str, str] | None,
    issues: list[ProductionPreflightIssue],
) -> list[ProviderDeploymentPolicy]:
    raw = get_config_value("FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG", settings=settings, env=env).strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        issues.append(
            ProductionPreflightIssue(
                "PREFLIGHT_PROVIDER_DEPLOYMENT_CONFIG_INVALID",
                "FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG",
            )
        )
        return []

    values = parsed if isinstance(parsed, list) else [parsed]
    deployments: list[ProviderDeploymentPolicy] = []
    for item in values:
        if not isinstance(item, dict):
            issues.append(
                ProductionPreflightIssue(
                    "PREFLIGHT_PROVIDER_DEPLOYMENT_CONFIG_INVALID",
                    "FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG",
                )
            )
            continue
        try:
            deployments.append(provider_deployment_from_mapping(item))
        except (TypeError, ValueError):
            issues.append(
                ProductionPreflightIssue(
                    "PREFLIGHT_PROVIDER_DEPLOYMENT_CONFIG_INVALID",
                    "FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG",
                )
            )
    return deployments


def _validate_deployment(
    deployment: ProviderDeploymentPolicy,
    *,
    allowed_hosts: str,
) -> list[ProductionPreflightIssue]:
    issues: list[ProductionPreflightIssue] = []
    if deployment.provider not in REGIONAL_CLOUD_PROVIDERS:
        issues.append(ProductionPreflightIssue("PREFLIGHT_PROVIDER_NOT_REGIONAL_CLOUD", "provider"))
        return issues

    try:
        validate_deployment_endpoint_host(
            deployment.endpoint_host,
            allowed_hosts=allowed_hosts,
            provider=deployment.provider,
        )
    except ProviderGovernanceError:
        issues.append(ProductionPreflightIssue("PREFLIGHT_DEPLOYMENT_ENDPOINT_HOST_INVALID", "endpoint_host"))

    region = str(deployment.processing_region or "").strip().lower()
    if region in DISALLOWED_REGIONS:
        issues.append(ProductionPreflightIssue("PREFLIGHT_DEPLOYMENT_PROCESSING_REGION_INVALID", "processing_region"))

    issues.extend(_validate_model_pin(deployment.model_deployment_id, field="model_deployment_id"))
    issues.extend(_validate_model_pin(deployment.model_version, field="model_version"))

    if not deployment.provider_governance_approved:
        issues.append(ProductionPreflightIssue("PREFLIGHT_PROVIDER_GOVERNANCE_NOT_APPROVED", "provider_governance_approved"))
    if not str(deployment.retention_evidence_ref or "").strip():
        issues.append(ProductionPreflightIssue("PREFLIGHT_RETENTION_EVIDENCE_MISSING", "retention_evidence_ref"))
    if not str(deployment.no_training_evidence_ref or "").strip():
        issues.append(ProductionPreflightIssue("PREFLIGHT_NO_TRAINING_EVIDENCE_MISSING", "no_training_evidence_ref"))
    return issues


def _validate_model_pin(value: str, *, field: str) -> list[ProductionPreflightIssue]:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return [ProductionPreflightIssue("PREFLIGHT_MODEL_PINNING_MISSING", field)]
    if normalized in FLOATING_MODEL_VALUES:
        return [ProductionPreflightIssue("PREFLIGHT_MODEL_PINNING_FLOATING", field)]
    return []


def _validate_azure_runtime_settings(
    *,
    settings: Any | None,
    env: Mapping[str, str] | None,
) -> list[ProductionPreflightIssue]:
    issues: list[ProductionPreflightIssue] = []
    if not get_bool_config_value("FLOWCHECK_AZURE_ADAPTERS_ENABLED", settings=settings, env=env, default=False):
        issues.append(ProductionPreflightIssue("PREFLIGHT_AZURE_ADAPTERS_DISABLED", "FLOWCHECK_AZURE_ADAPTERS_ENABLED"))

    identity_mode = get_config_value(
        "FLOWCHECK_AZURE_IDENTITY_MODE",
        settings=settings,
        env=env,
        default="managed_identity",
    ).strip().lower()
    if identity_mode != "managed_identity":
        issues.append(ProductionPreflightIssue("PREFLIGHT_AZURE_IDENTITY_MODE_INVALID", "FLOWCHECK_AZURE_IDENTITY_MODE"))

    if get_bool_config_value("FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS", settings=settings, env=env, default=False):
        issues.append(
            ProductionPreflightIssue(
                "PREFLIGHT_AZURE_DEVELOPER_CREDENTIALS_ENABLED",
                "FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS",
            )
        )
    return issues


def _parse_csv_values(value: str) -> set[str]:
    return {item.strip().lower().rstrip(".") for item in str(value or "").split(",") if item.strip()}
