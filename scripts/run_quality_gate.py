#!/usr/bin/env python3
"""Run FlowCheck local quality gates without Azure access or provider calls."""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_FILES = (
    "shared/inference_policy.py",
    "shared/provider_governance.py",
    "shared/production_preflight.py",
    "shared/providers/azure_identity.py",
    "shared/providers/azure_openai_provider.py",
    "shared/providers/azure_document_intelligence_provider.py",
)
BICEP_FILES = (
    "infra/azure/nonprod/main.bicep",
    "infra/azure/nonprod/modules/ai-services.bicep",
    "infra/azure/nonprod/modules/network-transition.bicep",
    "infra/azure/nonprod/modules/rbac.bicep",
)
BICEP_BUILD_DIR = Path("/tmp/flowcheck-quality-gate-bicep")


@dataclass(frozen=True)
class GateStep:
    code: str
    command: tuple[str, ...]


def main() -> int:
    print("QUALITY_GATE_START")
    failed = False

    steps = [
        GateStep("PY_COMPILE", (sys.executable, "-m", "py_compile", *PYTHON_FILES)),
        GateStep("PYTEST", (sys.executable, "-m", "pytest", "-q")),
        GateStep("PRODUCTION_PREFLIGHT", (sys.executable, "scripts/validate_provider_governance.py")),
        GateStep("AZURE_NONPROD_PLAN", (sys.executable, "scripts/validate_azure_nonprod_plan.py")),
    ]

    for step in steps:
        if not _run_step(step):
            failed = True

    if not _run_bicep_steps():
        failed = True

    if not _run_step(GateStep("GIT_DIFF_CHECK", ("git", "diff", "--check"))):
        failed = True

    print("QUALITY_GATE_FAIL" if failed else "QUALITY_GATE_PASS")
    return 1 if failed else 0


def _run_bicep_steps() -> bool:
    bicep_path = shutil.which("bicep")
    if not bicep_path:
        print("CHECK BICEP_TOOL_NOT_FOUND status=SKIP")
        return True

    if BICEP_BUILD_DIR.exists():
        shutil.rmtree(BICEP_BUILD_DIR)
    BICEP_BUILD_DIR.mkdir(parents=True, exist_ok=True)

    steps = [
        GateStep(
            "BICEP_BUILD_MAIN",
            (
                bicep_path,
                "build",
                "infra/azure/nonprod/main.bicep",
                "--outfile",
                str(BICEP_BUILD_DIR / "main.json"),
            ),
        ),
        GateStep(
            "BICEP_BUILD_PARAMS",
            (
                bicep_path,
                "build-params",
                "infra/azure/nonprod/nonprod.example.bicepparam",
                "--outfile",
                str(BICEP_BUILD_DIR / "nonprod.example.json"),
            ),
        ),
    ]
    steps.extend(GateStep("BICEP_LINT", (bicep_path, "lint", path)) for path in BICEP_FILES)

    ok = True
    for step in steps:
        if not _run_step(step):
            ok = False
    return ok


def _run_step(step: GateStep) -> bool:
    completed = subprocess.run(
        list(step.command),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        print(f"CHECK {step.code} status=PASS")
        return True
    print(f"CHECK {step.code} status=FAIL exit_code={completed.returncode}")
    return False


if __name__ == "__main__":
    raise SystemExit(main())
