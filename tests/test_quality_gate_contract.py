from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_quality_gate.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "quality-gate.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_quality_gate_runner_exists():
    assert RUNNER.exists()


def test_runner_has_no_azure_login_or_deployment_commands():
    text = _text(RUNNER).lower()

    blocked = ("az login", "az account", "az deployment", "bicep deploy", "terraform apply")
    assert not any(command in text for command in blocked)
    assert "shell=true" not in text.replace(" ", "")


def test_runner_does_not_print_secret_or_environment_values():
    text = _text(RUNNER).lower()

    blocked_output_terms = ("api_key", "apikey", "clientsecret", "password", "token", "authorization", "environ")
    assert not any(term in text for term in blocked_output_terms)
    assert "completed.stdout" not in text
    assert "completed.stderr" not in text


def test_runner_includes_required_validators_and_checks():
    text = _text(RUNNER)

    assert "py_compile" in text
    assert "pytest" in text
    assert "scripts/validate_provider_governance.py" in text
    assert "scripts/validate_azure_nonprod_plan.py" in text
    assert "git\", \"diff\", \"--check" in text


def test_runner_defines_clean_bicep_fallback():
    text = _text(RUNNER)

    assert "shutil.which(\"bicep\")" in text
    assert "BICEP_TOOL_NOT_FOUND" in text
    assert "status=SKIP" in text
    assert "brew install" not in text
    assert "curl " not in text


def test_github_workflow_has_no_azure_login_or_secrets():
    text = _text(WORKFLOW).lower()
    workflow = yaml.safe_load(_text(WORKFLOW))

    assert "azure/login" not in text
    assert "az login" not in text
    assert "secrets." not in text
    assert "push" not in workflow.get(True, {})


def test_workflow_contains_no_deployment_step():
    text = _text(WORKFLOW).lower()

    blocked = ("az deployment", "bicep deploy", "terraform apply", "kubectl apply")
    assert not any(command in text for command in blocked)


def test_workflow_runs_bicep_build_and_lint():
    text = _text(WORKFLOW)

    assert "bicep build infra/azure/nonprod/main.bicep" in text
    assert "bicep build-params infra/azure/nonprod/nonprod.example.bicepparam" in text
    assert "bicep lint infra/azure/nonprod/main.bicep" in text
    assert "bicep lint infra/azure/nonprod/modules/ai-services.bicep" in text
    assert "bicep lint infra/azure/nonprod/modules/network-transition.bicep" in text
    assert "bicep lint infra/azure/nonprod/modules/rbac.bicep" in text
