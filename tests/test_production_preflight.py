import json
import subprocess
import sys
from pathlib import Path

from shared.inference_policy import DataClass, InferenceProfile, InferenceProvider
from shared.provider_deployments import DeploymentResidencyMode
from shared.production_preflight import format_preflight_result, run_production_preflight


HOST = "flowcheck-westeurope.openai.azure.com"
DEPLOYMENT_ID = "flowcheck-gpt-4o-prod-2026-06"
MODEL_VERSION = "gpt-4o-2024-08-06"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _deployment_config(**overrides):
    values = {
        "provider": InferenceProvider.AZURE_OPENAI_EU.value,
        "endpoint_host": HOST,
        "processing_region": "EU",
        "deployment_residency_mode": DeploymentResidencyMode.SINGLE_REGION.value,
        "model_deployment_id": DEPLOYMENT_ID,
        "model_version": MODEL_VERSION,
        "purpose_allowlist": ["invoice_llm_extraction"],
        "data_class_allowlist": [DataClass.INVOICE_CONFIDENTIAL.value],
        "retention_evidence_ref": "RETENTION-EVIDENCE-001",
        "no_training_evidence_ref": "NO-TRAINING-EVIDENCE-001",
        "provider_governance_approved": True,
    }
    values.update(overrides)
    return json.dumps(values)


def _env(**overrides):
    env = {
        "FLOWCHECK_RUNTIME_ENV": "production",
        "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION": "true",
        "FLOWCHECK_DEFAULT_INFERENCE_PROFILE": InferenceProfile.EU_REGIONAL_CLOUD.value,
        "FLOWCHECK_PROVIDER_GOVERNANCE_ENFORCEMENT": "block",
        "FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST": HOST,
        "FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG": _deployment_config(),
        "FLOWCHECK_AZURE_ADAPTERS_ENABLED": "true",
        "FLOWCHECK_AZURE_IDENTITY_MODE": "managed_identity",
        "FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS": "false",
    }
    env.update(overrides)
    return env


def _codes(result):
    return {issue.error_code for issue in result.issues}


def _fields(result):
    return {issue.field for issue in result.issues}


def test_development_empty_governance_config_has_no_production_error():
    result = run_production_preflight(env={"FLOWCHECK_RUNTIME_ENV": "development"})

    assert result.ok is True
    assert result.issues == ()


def test_production_with_regional_cloud_enforcement_disabled_blocks():
    result = run_production_preflight(
        env=_env(FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION="false")
    )

    assert result.ok is False
    assert "PREFLIGHT_PRODUCTION_REGIONAL_CLOUD_ENFORCEMENT_DISABLED" in _codes(result)
    assert "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION" in _fields(result)


def test_production_standard_default_profile_blocks():
    result = run_production_preflight(
        env=_env(FLOWCHECK_DEFAULT_INFERENCE_PROFILE=InferenceProfile.STANDARD.value)
    )

    assert result.ok is False
    assert "PREFLIGHT_DEFAULT_PROFILE_STANDARD" in _codes(result)
    assert "FLOWCHECK_DEFAULT_INFERENCE_PROFILE" in _fields(result)


def test_production_empty_host_allowlist_blocks():
    result = run_production_preflight(env=_env(FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST=""))

    assert result.ok is False
    assert "PREFLIGHT_PROVIDER_ENDPOINT_HOST_ALLOWLIST_EMPTY" in _codes(result)
    assert "PREFLIGHT_DEPLOYMENT_ENDPOINT_HOST_INVALID" in _codes(result)


def test_production_non_block_governance_enforcement_blocks():
    result = run_production_preflight(env=_env(FLOWCHECK_PROVIDER_GOVERNANCE_ENFORCEMENT="warn"))

    assert result.ok is False
    assert "PREFLIGHT_PROVIDER_GOVERNANCE_ENFORCEMENT_NOT_BLOCK" in _codes(result)


def test_production_empty_deployment_config_blocks():
    result = run_production_preflight(env=_env(FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=""))

    assert result.ok is False
    assert "PREFLIGHT_PROVIDER_DEPLOYMENT_CONFIG_EMPTY" in _codes(result)


def test_production_invalid_deployment_config_blocks_without_values():
    result = run_production_preflight(env=_env(FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG="{not-json"))

    assert result.ok is False
    assert "PREFLIGHT_PROVIDER_DEPLOYMENT_CONFIG_INVALID" in _codes(result)


def test_production_disallowed_regions_block():
    for region in ("global", "datazone", "auto", "default"):
        result = run_production_preflight(
            env=_env(FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=_deployment_config(processing_region=region))
        )

        assert result.ok is False
        assert "PREFLIGHT_DEPLOYMENT_PROCESSING_REGION_INVALID" in _codes(result)


def test_production_eu_data_zone_residency_mode_blocks():
    result = run_production_preflight(
        env=_env(
            FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=_deployment_config(
                deployment_residency_mode=DeploymentResidencyMode.EU_DATA_ZONE.value
            )
        )
    )

    assert result.ok is False
    assert "PREFLIGHT_DEPLOYMENT_RESIDENCY_MODE_NOT_SINGLE_REGION" in _codes(result)
    assert "deployment_residency_mode" in _fields(result)


def test_production_missing_model_version_blocks():
    result = run_production_preflight(
        env=_env(FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=_deployment_config(model_version=""))
    )

    assert result.ok is False
    assert "PREFLIGHT_MODEL_PINNING_MISSING" in _codes(result)
    assert "model_version" in _fields(result)


def test_production_floating_model_values_block():
    for value in ("latest", "default", "auto", "current"):
        result = run_production_preflight(
            env=_env(FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=_deployment_config(model_version=value))
        )

        assert result.ok is False
        assert "PREFLIGHT_MODEL_PINNING_FLOATING" in _codes(result)


def test_production_missing_evidence_blocks():
    result = run_production_preflight(
        env=_env(
            FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=_deployment_config(
                retention_evidence_ref="",
                no_training_evidence_ref="",
            )
        )
    )

    assert result.ok is False
    assert "PREFLIGHT_RETENTION_EVIDENCE_MISSING" in _codes(result)
    assert "PREFLIGHT_NO_TRAINING_EVIDENCE_MISSING" in _codes(result)


def test_production_unapproved_provider_blocks():
    result = run_production_preflight(
        env=_env(FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=_deployment_config(provider_governance_approved=False))
    )

    assert result.ok is False
    assert "PREFLIGHT_PROVIDER_GOVERNANCE_NOT_APPROVED" in _codes(result)


def test_production_developer_credentials_block():
    result = run_production_preflight(env=_env(FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS="true"))

    assert result.ok is False
    assert "PREFLIGHT_AZURE_DEVELOPER_CREDENTIALS_ENABLED" in _codes(result)


def test_production_non_managed_identity_blocks():
    result = run_production_preflight(env=_env(FLOWCHECK_AZURE_IDENTITY_MODE="developer_credentials"))

    assert result.ok is False
    assert "PREFLIGHT_AZURE_IDENTITY_MODE_INVALID" in _codes(result)


def test_production_azure_regional_provider_requires_enabled_adapters():
    result = run_production_preflight(env=_env(FLOWCHECK_AZURE_ADAPTERS_ENABLED="false"))

    assert result.ok is False
    assert "PREFLIGHT_AZURE_ADAPTERS_DISABLED" in _codes(result)


def test_production_complete_mock_configuration_succeeds():
    result = run_production_preflight(env=_env())

    assert result.ok is True
    assert format_preflight_result(result) == "PRODUCTION_PREFLIGHT_OK"


def test_preflight_output_contains_only_codes_and_field_names():
    sensitive_host = "sensitive-westeurope.openai.azure.com"
    sensitive_deployment = "flowcheck-secret-deployment"
    sensitive_model = "secret-model-version"
    sensitive_evidence = "AVV-DPA-ZDR-NO-TRAINING-SECRET-REF"
    sensitive_token = "secret-token-value"
    sensitive_tenant = "00000000-0000-0000-0000-000000000000"
    result = run_production_preflight(
        env=_env(
            FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST="",
            FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=_deployment_config(
                endpoint_host=sensitive_host,
                model_deployment_id=sensitive_deployment,
                model_version=sensitive_model,
                retention_evidence_ref=sensitive_evidence,
                no_training_evidence_ref=sensitive_evidence,
            ),
            FLOWCHECK_AZURE_MANAGED_IDENTITY_CLIENT_ID=sensitive_tenant,
            AZURE_OPENAI_TOKEN=sensitive_token,
        )
    )

    rendered = format_preflight_result(result)
    assert result.ok is False
    for sensitive_value in (
        sensitive_host,
        sensitive_deployment,
        sensitive_model,
        sensitive_evidence,
        sensitive_token,
        sensitive_tenant,
        HOST,
        DEPLOYMENT_ID,
        MODEL_VERSION,
    ):
        assert sensitive_value not in rendered
    assert "field=endpoint_host" in rendered
    assert "PREFLIGHT_DEPLOYMENT_ENDPOINT_HOST_INVALID" in rendered


def test_cli_returns_zero_for_activatable_configuration():
    completed = subprocess.run(
        [sys.executable, "scripts/validate_provider_governance.py"],
        cwd=REPO_ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.strip() == "PRODUCTION_PREFLIGHT_OK"
    assert completed.stderr == ""


def test_cli_returns_one_for_blocked_configuration_without_values():
    completed = subprocess.run(
        [sys.executable, "scripts/validate_provider_governance.py"],
        cwd=REPO_ROOT,
        env=_env(
            FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST="",
            FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=_deployment_config(endpoint_host="secret.openai.azure.com"),
        ),
        capture_output=True,
        text=True,
        check=False,
    )

    rendered = completed.stdout + completed.stderr
    assert completed.returncode == 1
    assert "PRODUCTION_PREFLIGHT_FAILED" in rendered
    assert "PREFLIGHT_PROVIDER_ENDPOINT_HOST_ALLOWLIST_EMPTY" in rendered
    assert "secret.openai.azure.com" not in rendered
