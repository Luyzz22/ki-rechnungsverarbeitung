import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_azure_nonprod_plan import format_plan_result, validate_azure_nonprod_plan


REPO_ROOT = Path(__file__).resolve().parents[1]
IAC_ROOT = REPO_ROOT / "infra" / "azure" / "nonprod"
EXAMPLE_PARAMS = IAC_ROOT / "nonprod.example.bicepparam"


REQUIRED_FILES = [
    IAC_ROOT / "main.bicep",
    EXAMPLE_PARAMS,
    IAC_ROOT / "modules" / "ai-services.bicep",
    IAC_ROOT / "modules" / "network-transition.bicep",
    IAC_ROOT / "modules" / "rbac.bicep",
    IAC_ROOT / "README.md",
    IAC_ROOT / "architecture.md",
    REPO_ROOT / "scripts" / "validate_azure_nonprod_plan.py",
    REPO_ROOT / "docs" / "FLOWCHECK_AZURE_NONPROD_RUNBOOK.md",
    REPO_ROOT / "docs" / "FLOWCHECK_AZURE_EGRESS_TRANSITION.md",
]


def _codes(result):
    return {issue.error_code for issue in result.issues}


def _fields(result):
    return {issue.field for issue in result.issues}


def _write_params(tmp_path, replacements):
    text = EXAMPLE_PARAMS.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    path = tmp_path / "plan.bicepparam"
    path.write_text(text, encoding="utf-8")
    return path


def test_required_iac_and_runbook_files_exist():
    for path in REQUIRED_FILES:
        assert path.exists(), path


def test_bicep_has_no_secret_or_api_key_parameters():
    parameter_pattern = re.compile(r"^\s*param\s+([A-Za-z0-9_]+)\b", re.MULTILINE)
    blocked_tokens = ("apikey", "api_key", "secret", "token", "credential", "password")
    for path in IAC_ROOT.rglob("*.bicep"):
        text = path.read_text(encoding="utf-8")
        for parameter_name in parameter_pattern.findall(text):
            normalized = parameter_name.lower()
            assert not any(token in normalized for token in blocked_tokens), parameter_name


def test_iac_files_do_not_contain_public_allow_all_cidrs():
    for path in list(IAC_ROOT.rglob("*.bicep")) + list(IAC_ROOT.rglob("*.bicepparam")):
        text = path.read_text(encoding="utf-8")
        assert "0.0.0.0/0" not in text
        assert "::/0" not in text


def test_default_deny_network_rule_is_declared_for_ai_services():
    ai_services = (IAC_ROOT / "modules" / "ai-services.bicep").read_text(encoding="utf-8")
    network = (IAC_ROOT / "modules" / "network-transition.bicep").read_text(encoding="utf-8")

    assert "networkAcls: networkAcls" in ai_services
    assert ai_services.count("publicNetworkAccess: publicNetworkAccess") == 2
    assert network.count("defaultAction: 'Deny'") >= 2
    assert "ipRules: [" in network


def test_public_network_access_is_explicitly_set_in_both_modes():
    ai_services = (IAC_ROOT / "modules" / "ai-services.bicep").read_text(encoding="utf-8")
    network = (IAC_ROOT / "modules" / "network-transition.bicep").read_text(encoding="utf-8")

    assert ai_services.count("publicNetworkAccess: publicNetworkAccess") == 2
    assert "isTransitionalStaticEgress ? 'Enabled' : 'Disabled'" in network


def test_transition_mode_has_default_deny_and_parameterized_cidrs_only():
    network = (IAC_ROOT / "modules" / "network-transition.bicep").read_text(encoding="utf-8")

    assert "defaultAction: 'Deny'" in network
    assert "for cidr in allowedHetznerEgressCidrs" in network
    assert "0.0.0.0/0" not in network
    assert "::/0" not in network


def test_private_endpoint_target_disables_public_access():
    network = (IAC_ROOT / "modules" / "network-transition.bicep").read_text(encoding="utf-8")
    main = (IAC_ROOT / "main.bicep").read_text(encoding="utf-8")

    assert "PRIVATE_VNET_TARGET" in network
    assert "output publicNetworkAccess string = isTransitionalStaticEgress ? 'Enabled' : 'Disabled'" in network
    assert "privateEndpointSubnetResourceId" in network
    assert "privateDnsZoneResourceIds" in network
    assert "param privateEndpointSubnetResourceId string = ''" not in main
    assert "param privateDnsZoneResourceIds array = []" not in main
    assert "param privateEndpointConnectionResourceIds array = []" not in main


def test_local_auth_and_api_key_fallbacks_are_not_modeled():
    ai_services = (IAC_ROOT / "modules" / "ai-services.bicep").read_text(encoding="utf-8")
    all_iac = "\n".join(path.read_text(encoding="utf-8") for path in IAC_ROOT.rglob("*.bicep"))

    assert ai_services.count("disableLocalAuth: true") == 2
    assert "apiKey" not in all_iac
    assert "api_key" not in all_iac
    assert "keyCredentials" not in all_iac
    assert "listKeys" not in all_iac


def test_transition_mode_requires_static_cidrs(tmp_path):
    param_file = _write_params(
        tmp_path,
        {
            "param networkMode = 'PRIVATE_VNET_TARGET'": "param networkMode = 'TRANSITIONAL_STATIC_EGRESS'",
        },
    )

    result = validate_azure_nonprod_plan(parameter_file=param_file)

    assert result.ok is False
    assert "AZURE_NONPROD_TRANSITIONAL_CIDR_REQUIRED" in _codes(result)
    assert "allowedHetznerEgressCidrs" in _fields(result)


def test_private_mode_requires_private_endpoint_contract(tmp_path):
    param_file = _write_params(
        tmp_path,
        {
            "param privateEndpointSubnetResourceId = '<private-endpoint-subnet-resource-id-placeholder>'": "param privateEndpointSubnetResourceId = ''",
            "'<private-dns-zone-resource-id-placeholder>'": "",
        },
    )

    result = validate_azure_nonprod_plan(parameter_file=param_file)

    assert result.ok is False
    assert "AZURE_NONPROD_PRIVATE_TARGET_CONTRACT_MISSING" in _codes(result)


def test_rbac_uses_principal_id_parameter_and_no_client_credentials():
    rbac = (IAC_ROOT / "modules" / "rbac.bicep").read_text(encoding="utf-8")

    assert "workloadManagedIdentityPrincipalId" in rbac
    assert "principalId: workloadManagedIdentityPrincipalId" in rbac
    assert "scope: azureOpenAiAccount" in rbac
    assert "scope: documentIntelligenceAccount" in rbac
    assert "scope: resourceGroup()" not in rbac
    assert "scope: subscription()" not in rbac
    assert "clientSecret" not in rbac
    assert "clientId" not in rbac
    assert "password" not in rbac.lower()


def test_model_version_is_required(tmp_path):
    param_file = _write_params(
        tmp_path,
        {
            "param azureOpenAiModelVersion = '<pinned-azure-openai-model-version-placeholder>'": "param azureOpenAiModelVersion = ''",
        },
    )

    result = validate_azure_nonprod_plan(parameter_file=param_file)

    assert result.ok is False
    assert "AZURE_NONPROD_MODEL_PINNING_MISSING" in _codes(result)
    assert "azureOpenAiModelVersion" in _fields(result)


def test_floating_model_aliases_are_blocked(tmp_path):
    for alias in ("latest", "default", "auto", "current"):
        param_file = _write_params(
            tmp_path,
            {
                "param azureOpenAiModelVersion = '<pinned-azure-openai-model-version-placeholder>'": f"param azureOpenAiModelVersion = '{alias}'",
            },
        )
        result = validate_azure_nonprod_plan(parameter_file=param_file)

        assert result.ok is False
        assert "AZURE_NONPROD_MODEL_ALIAS_FLOATING" in _codes(result)


def test_documentation_marks_transition_as_non_production_only():
    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            IAC_ROOT / "README.md",
            IAC_ROOT / "architecture.md",
            REPO_ROOT / "docs" / "FLOWCHECK_AZURE_NONPROD_RUNBOOK.md",
            REPO_ROOT / "docs" / "FLOWCHECK_AZURE_EGRESS_TRANSITION.md",
        )
    ).lower()

    assert "non-production-only" in docs or "non-production only" in docs
    assert "produktionszielzustand" in docs or "production target" in docs


def test_egress_docs_do_not_claim_host_firewall_guarantees_fqdn_blocking():
    doc = (REPO_ROOT / "docs" / "FLOWCHECK_AZURE_EGRESS_TRANSITION.md").read_text(encoding="utf-8").lower()

    assert "kann fqdn-allowlisting nicht" in doc
    assert "fqdn-faehigen egress-proxy" in doc
    assert "keinen technischen" in doc and "egress-nachweis" in doc
    assert "host-firewall garantiert" not in doc
    assert "statische ip-regeln" in doc


def test_default_validator_succeeds_for_placeholder_example():
    result = validate_azure_nonprod_plan()

    assert result.ok is True
    assert format_plan_result(result) == "AZURE_NONPROD_PLAN_OK"


def test_validator_output_does_not_expose_parameter_values(tmp_path):
    sensitive_subdomain = "sensitive-subdomain"
    sensitive_model = "sensitive-model"
    param_file = _write_params(
        tmp_path,
        {
            "param azureOpenAiCustomSubdomain = '<azure-openai-custom-subdomain-placeholder>'": f"param azureOpenAiCustomSubdomain = '{sensitive_subdomain}'",
            "param azureOpenAiModelName = '<pinned-azure-openai-model-name-placeholder>'": f"param azureOpenAiModelName = '{sensitive_model}'",
            "param networkMode = 'PRIVATE_VNET_TARGET'": "param networkMode = 'TRANSITIONAL_STATIC_EGRESS'",
            "param allowedHetznerEgressCidrs = []": "param allowedHetznerEgressCidrs = [\n  '0.0.0.0/0'\n]",
        },
    )

    completed = subprocess.run(
        [sys.executable, "scripts/validate_azure_nonprod_plan.py", "--parameters", str(param_file)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    rendered = completed.stdout + completed.stderr
    assert completed.returncode == 1
    assert "AZURE_NONPROD_PLAN_FAILED" in rendered
    assert "AZURE_NONPROD_ALLOW_ALL_CIDR_BLOCKED" in rendered
    assert sensitive_subdomain not in rendered
    assert sensitive_model not in rendered
    assert "0.0.0.0/0" not in rendered


def test_local_bicep_compile_when_tool_is_available(tmp_path):
    output_file = tmp_path / "main.json"
    bicep = shutil.which("bicep")
    az = shutil.which("az")
    if bicep:
        command = [bicep, "build", str(IAC_ROOT / "main.bicep"), "--outfile", str(output_file)]
    elif az:
        command = [
            az,
            "bicep",
            "build",
            "--file",
            str(IAC_ROOT / "main.bicep"),
            "--outfile",
            str(output_file),
        ]
    else:
        pytest.skip("local Bicep compiler unavailable; report as local tooling gap")

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert output_file.exists()
