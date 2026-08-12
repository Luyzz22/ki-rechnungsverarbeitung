import json

import pytest

from shared.inference_policy import DataClass, InferenceProfile, InferenceProvider
from shared.provider_deployments import DeploymentResidencyMode, ProviderDeploymentPolicy
from shared.provider_governance import (
    ProviderGovernanceError,
    assert_provider_governance_allowed,
    resolve_cloud_processing_region,
    validate_deployment_endpoint_host,
)


HOST = "flowcheck-westeurope.openai.azure.com"


def _policy(**overrides):
    values = {
        "provider": InferenceProvider.AZURE_OPENAI_EU,
        "endpoint_host": HOST,
        "processing_region": "EU",
        "deployment_residency_mode": DeploymentResidencyMode.SINGLE_REGION.value,
        "model_deployment_id": "flowcheck-gpt-4o-prod-2026-06",
        "model_version": "gpt-4o-2024-08-06",
        "purpose_allowlist": frozenset({"invoice_llm_extraction"}),
        "data_class_allowlist": frozenset({DataClass.INVOICE_CONFIDENTIAL}),
        "retention_evidence_ref": "RETENTION-EVIDENCE-001",
        "no_training_evidence_ref": "NO-TRAINING-EVIDENCE-001",
        "provider_governance_approved": True,
    }
    values.update(overrides)
    return ProviderDeploymentPolicy(**values)


def _env(**overrides):
    env = {
        "FLOWCHECK_RUNTIME_ENV": "production",
        "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION": "true",
        "FLOWCHECK_PROVIDER_GOVERNANCE_ENFORCEMENT": "block",
        "FLOWCHECK_CLOUD_PROCESSING_REGION": "EU",
        "FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST": HOST,
    }
    env.update(overrides)
    return env


def test_production_invoice_confidential_standard_with_enforcement_blocks():
    with pytest.raises(ProviderGovernanceError) as exc_info:
        assert_provider_governance_allowed(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.STANDARD,
            provider=InferenceProvider.OPENAI_DIRECT,
            purpose="invoice_llm_extraction",
            env=_env(),
        )

    assert exc_info.value.error_code == "PROVIDER_GOVERNANCE_NOT_APPROVED"
    assert exc_info.value.reason_code == "production_invoice_confidential_requires_eu_regional_cloud"


def test_development_standard_direct_provider_remains_possible():
    decision = assert_provider_governance_allowed(
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.STANDARD,
        provider=InferenceProvider.OPENAI_DIRECT,
        purpose="invoice_llm_extraction",
        env=_env(FLOWCHECK_RUNTIME_ENV="development"),
    )

    assert decision.allowed is True
    assert decision.provider == InferenceProvider.OPENAI_DIRECT.value


def test_eu_regional_cloud_approved_deployment_allowed():
    decision = assert_provider_governance_allowed(
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
        provider=InferenceProvider.AZURE_OPENAI_EU,
        purpose="invoice_llm_extraction",
        endpoint_host=HOST,
        model_deployment_id="flowcheck-gpt-4o-prod-2026-06",
        deployments=[_policy()],
        env=_env(),
    )

    assert decision.allowed is True
    assert decision.cloud_processing_region == "EU"


def test_production_eu_data_zone_residency_mode_blocks_regional_assurance():
    with pytest.raises(ProviderGovernanceError) as exc_info:
        assert_provider_governance_allowed(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            purpose="invoice_llm_extraction",
            endpoint_host=HOST,
            model_deployment_id="flowcheck-gpt-4o-prod-2026-06",
            deployments=[
                _policy(
                    deployment_residency_mode=DeploymentResidencyMode.EU_DATA_ZONE.value
                )
            ],
            env=_env(),
        )

    assert (
        exc_info.value.reason_code
        == "deployment_residency_mode_not_single_region"
    )


def test_unapproved_provider_deployment_blocks():
    with pytest.raises(ProviderGovernanceError) as exc_info:
        assert_provider_governance_allowed(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            purpose="invoice_llm_extraction",
            endpoint_host=HOST,
            model_deployment_id="flowcheck-gpt-4o-prod-2026-06",
            deployments=[_policy(provider_governance_approved=False)],
            env=_env(),
        )

    assert exc_info.value.reason_code == "provider_governance_not_approved"


def test_missing_region_blocks():
    with pytest.raises(ProviderGovernanceError) as exc_info:
        assert_provider_governance_allowed(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            purpose="invoice_llm_extraction",
            endpoint_host=HOST,
            model_deployment_id="flowcheck-gpt-4o-prod-2026-06",
            deployments=[_policy(processing_region="")],
            env=_env(),
        )

    assert exc_info.value.reason_code == "processing_region_invalid"


@pytest.mark.parametrize("region", ["global", "datazone", "auto", "default"])
def test_disallowed_region_values_block(region):
    with pytest.raises(ProviderGovernanceError) as exc_info:
        assert_provider_governance_allowed(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            purpose="invoice_llm_extraction",
            endpoint_host=HOST,
            model_deployment_id="flowcheck-gpt-4o-prod-2026-06",
            deployments=[_policy(processing_region=region)],
            env=_env(),
        )

    assert exc_info.value.reason_code == "processing_region_invalid"


@pytest.mark.parametrize("field", ["model_deployment_id", "model_version"])
def test_missing_model_pinning_blocks(field):
    policy = _policy(**{field: ""})

    with pytest.raises(ProviderGovernanceError) as exc_info:
        assert_provider_governance_allowed(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            purpose="invoice_llm_extraction",
            endpoint_host=HOST,
            model_deployment_id=policy.model_deployment_id,
            deployments=[policy],
            env=_env(),
        )

    assert exc_info.value.reason_code == f"{field}_missing"


@pytest.mark.parametrize("floating", ["latest", "default", "auto", "current"])
def test_floating_model_values_block(floating):
    policy = _policy(model_version=floating)

    with pytest.raises(ProviderGovernanceError) as exc_info:
        assert_provider_governance_allowed(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            purpose="invoice_llm_extraction",
            endpoint_host=HOST,
            model_deployment_id=policy.model_deployment_id,
            deployments=[policy],
            env=_env(),
        )

    assert exc_info.value.reason_code == "model_version_floating"


@pytest.mark.parametrize("field", ["retention_evidence_ref", "no_training_evidence_ref"])
def test_missing_governance_evidence_blocks(field):
    with pytest.raises(ProviderGovernanceError) as exc_info:
        assert_provider_governance_allowed(
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            purpose="invoice_llm_extraction",
            endpoint_host=HOST,
            model_deployment_id="flowcheck-gpt-4o-prod-2026-06",
            deployments=[_policy(**{field: ""})],
            env=_env(),
        )

    assert exc_info.value.reason_code == "governance_evidence_missing"


def test_endpoint_outside_exact_allowlist_blocks():
    with pytest.raises(ProviderGovernanceError) as exc_info:
        validate_deployment_endpoint_host(
            "other-westeurope.openai.azure.com",
            allowed_hosts=HOST,
            provider=InferenceProvider.AZURE_OPENAI_EU,
        )

    assert exc_info.value.reason_code == "endpoint_host_not_allowed"


def test_client_input_cannot_set_governance_fields():
    with pytest.raises(ProviderGovernanceError) as exc_info:
        validate_deployment_endpoint_host(
            HOST,
            allowed_hosts=HOST,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            source="client_input",
        )

    assert exc_info.value.reason_code == "endpoint_source_not_allowed"


def test_provider_deployment_config_is_server_side_json():
    policy = _policy()
    env = _env(
        FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=json.dumps(
            {
                "provider": policy.provider.value,
                "endpoint_host": policy.endpoint_host,
                "processing_region": policy.processing_region,
                "deployment_residency_mode": policy.deployment_residency_mode,
                "model_deployment_id": policy.model_deployment_id,
                "model_version": policy.model_version,
                "purpose_allowlist": sorted(policy.purpose_allowlist),
                "data_class_allowlist": sorted(item.value for item in policy.data_class_allowlist),
                "retention_evidence_ref": policy.retention_evidence_ref,
                "no_training_evidence_ref": policy.no_training_evidence_ref,
                "provider_governance_approved": True,
            }
        )
    )

    decision = assert_provider_governance_allowed(
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
        provider=InferenceProvider.AZURE_OPENAI_EU,
        purpose="invoice_llm_extraction",
        endpoint_host=HOST,
        model_deployment_id=policy.model_deployment_id,
        env=env,
    )

    assert decision.allowed is True


def test_unset_cloud_processing_region_blocks_production_enforcement():
    with pytest.raises(ProviderGovernanceError) as exc_info:
        assert_provider_governance_allowed(
            data_class=DataClass.INTERNAL,
            inference_profile=InferenceProfile.STANDARD,
            provider=InferenceProvider.OPENAI_DIRECT,
            purpose="internal_summary",
            env=_env(FLOWCHECK_CLOUD_PROCESSING_REGION="UNSET"),
        )

    assert exc_info.value.reason_code == "cloud_processing_region_unset"
    assert resolve_cloud_processing_region(env=_env(FLOWCHECK_CLOUD_PROCESSING_REGION="UNSET")).value == "UNSET"
