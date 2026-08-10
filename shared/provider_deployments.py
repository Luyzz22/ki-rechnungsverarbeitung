"""Server-side provider deployment policy model for FlowCheck+."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from shared.inference_policy import DataClass, InferenceProvider


class CloudProcessingRegion(str, Enum):
    EU = "EU"
    LOCAL_ONLY = "LOCAL_ONLY"
    UNSET = "UNSET"


class DeploymentResidencyMode(str, Enum):
    SINGLE_REGION = "SINGLE_REGION"
    EU_DATA_ZONE = "EU_DATA_ZONE"
    LOCAL_ONLY = "LOCAL_ONLY"
    UNSET = "UNSET"


@dataclass(frozen=True)
class ProviderDeploymentPolicy:
    provider: InferenceProvider
    endpoint_host: str
    processing_region: str
    model_deployment_id: str
    model_version: str
    purpose_allowlist: frozenset[str]
    data_class_allowlist: frozenset[DataClass]
    retention_evidence_ref: str
    no_training_evidence_ref: str
    provider_governance_approved: bool
    deployment_residency_mode: str = DeploymentResidencyMode.UNSET.value


def provider_deployment_from_mapping(value: dict[str, Any]) -> ProviderDeploymentPolicy:
    """Build a deployment policy from server-side configuration."""
    return ProviderDeploymentPolicy(
        provider=InferenceProvider(str(value.get("provider", ""))),
        endpoint_host=str(value.get("endpoint_host", "")),
        processing_region=str(value.get("processing_region", "")),
        model_deployment_id=str(value.get("model_deployment_id", "")),
        model_version=str(value.get("model_version", "")),
        purpose_allowlist=frozenset(str(item) for item in value.get("purpose_allowlist", [])),
        data_class_allowlist=frozenset(DataClass(str(item)) for item in value.get("data_class_allowlist", [])),
        retention_evidence_ref=str(value.get("retention_evidence_ref", "")),
        no_training_evidence_ref=str(value.get("no_training_evidence_ref", "")),
        provider_governance_approved=bool(value.get("provider_governance_approved", False)),
        deployment_residency_mode=str(
            value.get(
                "deployment_residency_mode",
                DeploymentResidencyMode.UNSET.value,
            )
        ),
    )
