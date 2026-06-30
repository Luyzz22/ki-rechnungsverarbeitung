#!/usr/bin/env python3
"""Validate the local FlowCheck Azure non-production IaC contract."""
from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
IAC_ROOT = REPO_ROOT / "infra" / "azure" / "nonprod"
DEFAULT_PARAMETERS = IAC_ROOT / "nonprod.example.bicepparam"

OK_CODE = "AZURE_NONPROD_PLAN_OK"
FAILED_CODE = "AZURE_NONPROD_PLAN_FAILED"
FLOATING_MODEL_ALIASES = frozenset({"latest", "default", "auto", "current"})
ALLOW_ALL_CIDRS = frozenset({"0.0.0.0/0", "::/0"})
REQUIRED_FILES = {
    "main_bicep": IAC_ROOT / "main.bicep",
    "example_parameters": DEFAULT_PARAMETERS,
    "ai_services_module": IAC_ROOT / "modules" / "ai-services.bicep",
    "network_transition_module": IAC_ROOT / "modules" / "network-transition.bicep",
    "rbac_module": IAC_ROOT / "modules" / "rbac.bicep",
    "readme": IAC_ROOT / "README.md",
    "architecture": IAC_ROOT / "architecture.md",
}
REQUIRED_PARAMETERS = frozenset(
    {
        "environment",
        "location",
        "resourcePrefix",
        "azureOpenAiAccountName",
        "documentIntelligenceAccountName",
        "azureOpenAiCustomSubdomain",
        "documentIntelligenceCustomSubdomain",
        "workloadManagedIdentityPrincipalId",
        "networkMode",
        "allowedHetznerEgressCidrs",
        "privateEndpointSubnetResourceId",
        "privateDnsZoneResourceIds",
        "privateEndpointConnectionResourceIds",
        "azureOpenAiInferenceRoleDefinitionId",
        "documentIntelligenceInferenceRoleDefinitionId",
        "azureOpenAiDeploymentName",
        "azureOpenAiModelName",
        "azureOpenAiModelVersion",
        "azureOpenAiModelFormat",
        "azureOpenAiModelCapacity",
    }
)
PRIVATE_TARGET_FIELDS = frozenset(
    {
        "privateEndpointSubnetResourceId",
        "privateDnsZoneResourceIds",
        "privateEndpointConnectionResourceIds",
    }
)
PLACEHOLDER_REQUIRED_IN_EXAMPLE = frozenset(
    {
        "workloadManagedIdentityPrincipalId",
        "azureOpenAiInferenceRoleDefinitionId",
        "documentIntelligenceInferenceRoleDefinitionId",
    }
)
REAL_VALUE_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"/subscriptions/", re.IGNORECASE),
    re.compile(r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b", re.IGNORECASE),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b"),
)
PARAM_DECLARATION_RE = re.compile(r"^\s*param\s+([A-Za-z0-9_]+)\b", re.MULTILINE)


@dataclass(frozen=True)
class AzureNonprodPlanIssue:
    error_code: str
    field: str


@dataclass(frozen=True)
class AzureNonprodPlanResult:
    ok: bool
    issues: tuple[AzureNonprodPlanIssue, ...]


def validate_azure_nonprod_plan(
    *,
    repo_root: Path = REPO_ROOT,
    parameter_file: Path | None = None,
) -> AzureNonprodPlanResult:
    """Validate the non-production IaC files without Azure or network access."""
    root = Path(repo_root)
    iac_root = root / "infra" / "azure" / "nonprod"
    parameter_path = parameter_file or iac_root / "nonprod.example.bicepparam"
    issues: list[AzureNonprodPlanIssue] = []

    required_files = {
        key: (root / path.relative_to(REPO_ROOT)) if path.is_absolute() else path
        for key, path in REQUIRED_FILES.items()
    }
    for field, path in required_files.items():
        if not path.exists():
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_REQUIRED_FILE_MISSING", field))

    if parameter_path.exists():
        params = parse_bicepparam_file(parameter_path)
        issues.extend(_validate_parameter_contract(params, is_example=parameter_path.name.endswith(".example.bicepparam")))
    else:
        issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_REQUIRED_FILE_MISSING", "example_parameters"))

    if iac_root.exists():
        issues.extend(_validate_infra_text_contract(iac_root))

    return AzureNonprodPlanResult(ok=not issues, issues=tuple(issues))


def format_plan_result(result: AzureNonprodPlanResult) -> str:
    if result.ok:
        return OK_CODE
    lines = [FAILED_CODE]
    lines.extend(f"{issue.error_code} field={issue.field}" for issue in result.issues)
    return "\n".join(lines)


def parse_bicepparam_file(path: Path) -> dict[str, Any]:
    params: dict[str, Any] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped.startswith("param ") or "=" not in stripped:
            index += 1
            continue

        name_part, raw_part = stripped[len("param ") :].split("=", 1)
        name = name_part.strip()
        raw_value = raw_part.strip()
        if raw_value.startswith("[") and raw_value.count("[") > raw_value.count("]"):
            while raw_value.count("[") > raw_value.count("]") and index + 1 < len(lines):
                index += 1
                raw_value += "\n" + lines[index].strip()
        params[name] = _parse_bicep_value(raw_value)
        index += 1
    return params


def _parse_bicep_value(raw_value: str) -> Any:
    value = raw_value.strip()
    if value.startswith("["):
        return re.findall(r"'([^']*)'", value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def _validate_parameter_contract(params: dict[str, Any], *, is_example: bool) -> list[AzureNonprodPlanIssue]:
    issues: list[AzureNonprodPlanIssue] = []
    for field in sorted(REQUIRED_PARAMETERS):
        if field not in params:
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_PARAMETER_MISSING", field))

    network_mode = str(params.get("networkMode", "")).strip()
    if network_mode not in {"TRANSITIONAL_STATIC_EGRESS", "PRIVATE_VNET_TARGET"}:
        issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_NETWORK_MODE_INVALID", "networkMode"))
    if network_mode == "TRANSITIONAL_STATIC_EGRESS":
        issues.extend(_validate_transitional_cidrs(params.get("allowedHetznerEgressCidrs", [])))
    if network_mode == "PRIVATE_VNET_TARGET":
        issues.extend(_validate_private_target_contract(params))

    for field in ("azureOpenAiCustomSubdomain", "documentIntelligenceCustomSubdomain"):
        if not _is_non_empty(params.get(field)):
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_CUSTOM_SUBDOMAIN_EMPTY", field))

    for field in ("azureOpenAiModelName", "azureOpenAiModelVersion", "azureOpenAiModelFormat", "azureOpenAiDeploymentName"):
        normalized = str(params.get(field, "")).strip().lower()
        if not normalized:
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_MODEL_PINNING_MISSING", field))
        elif normalized in FLOATING_MODEL_ALIASES:
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_MODEL_ALIAS_FLOATING", field))

    if is_example:
        issues.extend(_validate_example_placeholders(params))
        issues.extend(_validate_example_has_no_real_values(params))
    return issues


def _validate_transitional_cidrs(value: Any) -> list[AzureNonprodPlanIssue]:
    issues: list[AzureNonprodPlanIssue] = []
    cidrs = value if isinstance(value, list) else []
    if not cidrs:
        return [AzureNonprodPlanIssue("AZURE_NONPROD_TRANSITIONAL_CIDR_REQUIRED", "allowedHetznerEgressCidrs")]
    for cidr in cidrs:
        normalized = str(cidr).strip()
        if normalized in ALLOW_ALL_CIDRS:
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_ALLOW_ALL_CIDR_BLOCKED", "allowedHetznerEgressCidrs"))
            continue
        try:
            ipaddress.ip_network(normalized, strict=False)
        except ValueError:
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_TRANSITIONAL_CIDR_INVALID", "allowedHetznerEgressCidrs"))
    return issues


def _validate_private_target_contract(params: dict[str, Any]) -> list[AzureNonprodPlanIssue]:
    issues: list[AzureNonprodPlanIssue] = []
    for field in sorted(PRIVATE_TARGET_FIELDS):
        if not _is_non_empty(params.get(field)):
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_PRIVATE_TARGET_CONTRACT_MISSING", field))
    return issues


def _validate_example_placeholders(params: dict[str, Any]) -> list[AzureNonprodPlanIssue]:
    issues: list[AzureNonprodPlanIssue] = []
    for field in sorted(PLACEHOLDER_REQUIRED_IN_EXAMPLE):
        if not _is_placeholder(params.get(field)):
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_EXAMPLE_PLACEHOLDER_REQUIRED", field))
    return issues


def _validate_example_has_no_real_values(params: dict[str, Any]) -> list[AzureNonprodPlanIssue]:
    issues: list[AzureNonprodPlanIssue] = []
    for field, value in params.items():
        for item in _flatten_values(value):
            if any(pattern.search(item) for pattern in REAL_VALUE_PATTERNS):
                issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_EXAMPLE_REAL_VALUE_BLOCKED", field))
                break
    return issues


def _validate_infra_text_contract(iac_root: Path) -> list[AzureNonprodPlanIssue]:
    issues: list[AzureNonprodPlanIssue] = []
    for path in sorted(iac_root.rglob("*.bicep")) + sorted(iac_root.rglob("*.bicepparam")):
        text = path.read_text(encoding="utf-8")
        for field in PARAM_DECLARATION_RE.findall(text):
            if _field_name_is_credential_like(field):
                issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_CREDENTIAL_PARAMETER_BLOCKED", field))
        if "0.0.0.0/0" in text or "::/0" in text:
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_PUBLIC_ALLOW_ALL_BLOCKED", path.name))
        if "Allow" in text and "defaultAction" in text:
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_NETWORK_DEFAULT_ALLOW_BLOCKED", path.name))
        if path.name == "ai-services.bicep" and text.count("disableLocalAuth: true") < 2:
            issues.append(AzureNonprodPlanIssue("AZURE_NONPROD_LOCAL_AUTH_NOT_DISABLED", path.name))
    return issues


def _field_name_is_credential_like(field: str) -> bool:
    normalized = field.lower()
    return any(token in normalized for token in ("apikey", "api_key", "secret", "token", "credential", "password"))


def _is_non_empty(value: Any) -> bool:
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value or "").strip())


def _is_placeholder(value: Any) -> bool:
    if isinstance(value, list):
        return all(_is_placeholder(item) for item in value if str(item).strip())
    rendered = str(value or "").strip()
    return rendered.startswith("<") and rendered.endswith(">")


def _flatten_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate local Azure non-production IaC contract.")
    parser.add_argument("--parameters", type=Path, default=DEFAULT_PARAMETERS)
    args = parser.parse_args(argv)
    result = validate_azure_nonprod_plan(parameter_file=args.parameters)
    print(format_plan_result(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
