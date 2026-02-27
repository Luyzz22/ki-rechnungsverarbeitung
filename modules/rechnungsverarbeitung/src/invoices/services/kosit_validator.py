from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class KositValidationResult:
    """Result container for KoSIT validation runs."""

    status: str
    errors: list[str]
    warnings: list[str]
    engine: str
    config_version: str
    raw_output: str


class KositValidator:
    """Thin adapter for KoSIT validator CLI execution with safe fallback."""

    def __init__(
        self,
        *,
        binary: str | None = None,
        scenario: str | None = None,
        timeout_seconds: int = 30,
        config_version: str = "xrechnung-latest",
    ) -> None:
        self.binary = binary or os.getenv("KOSIT_VALIDATOR_BIN", "kosit-validator")
        self.scenario = scenario or os.getenv("KOSIT_SCENARIO", "scenarios.xml")
        self.timeout_seconds = timeout_seconds
        self.config_version = config_version

    def validate_file(self, invoice_path: str | Path, report_dir: str | Path) -> KositValidationResult:
        """Validate XML invoice with KoSIT CLI and return structured status."""
        invoice_path = Path(invoice_path)
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        if shutil.which(self.binary) is None:
            return KositValidationResult(
                status="warning",
                errors=[],
                warnings=["KoSIT binary not found; fallback mode active"],
                engine="kosit",
                config_version=self.config_version,
                raw_output="",
            )

        cmd = [
            self.binary,
            "-s",
            self.scenario,
            "-o",
            str(report_dir),
            str(invoice_path),
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return KositValidationResult(
                status="failed",
                errors=["KoSIT validation timed out"],
                warnings=[],
                engine="kosit",
                config_version=self.config_version,
                raw_output="",
            )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        raw_output = (stdout + "\n" + stderr).strip()

        if proc.returncode == 0:
            return KositValidationResult(
                status="passed",
                errors=[],
                warnings=[],
                engine="kosit",
                config_version=self.config_version,
                raw_output=raw_output,
            )

        error_lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        if not error_lines:
            error_lines = ["KoSIT validation failed without detailed output"]

        return KositValidationResult(
            status="failed",
            errors=error_lines,
            warnings=[],
            engine="kosit",
            config_version=self.config_version,
            raw_output=raw_output,
        )

    @staticmethod
    def to_json(result: KositValidationResult) -> str:
        """Serialize validator result for logging or persistence."""
        return json.dumps(
            {
                "status": result.status,
                "errors": result.errors,
                "warnings": result.warnings,
                "engine": result.engine,
                "config_version": result.config_version,
            },
            ensure_ascii=False,
        )
