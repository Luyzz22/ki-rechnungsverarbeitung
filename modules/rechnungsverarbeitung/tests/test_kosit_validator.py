from __future__ import annotations

import subprocess
from pathlib import Path

from modules.rechnungsverarbeitung.src.invoices.services.kosit_validator import KositValidator


def test_validate_file_missing_binary_returns_warning(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _bin: None)
    validator = KositValidator(binary="missing-kosit")

    result = validator.validate_file(tmp_path / "invoice.xml", tmp_path / "reports")

    assert result.status == "warning"
    assert "fallback" in result.warnings[0].lower()


def test_validate_file_success(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _bin: "/usr/bin/kosit-validator")

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    invoice = tmp_path / "invoice.xml"
    invoice.write_text("<xml/>", encoding="utf-8")

    validator = KositValidator(binary="kosit-validator")
    result = validator.validate_file(invoice, tmp_path / "reports")

    assert result.status == "passed"
    assert result.errors == []


def test_validate_file_failure_parses_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _bin: "/usr/bin/kosit-validator")

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="BR-DE-15 failed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    invoice = tmp_path / "invoice.xml"
    invoice.write_text("<xml/>", encoding="utf-8")

    validator = KositValidator(binary="kosit-validator")
    result = validator.validate_file(invoice, tmp_path / "reports")

    assert result.status == "failed"
    assert any("BR-DE-15" in err for err in result.errors)


def test_validate_file_timeout(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _bin: "/usr/bin/kosit-validator")

    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="kosit-validator", timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)

    invoice = tmp_path / "invoice.xml"
    invoice.write_text("<xml/>", encoding="utf-8")

    validator = KositValidator(binary="kosit-validator")
    result = validator.validate_file(invoice, tmp_path / "reports")

    assert result.status == "failed"
    assert "timed out" in result.errors[0].lower()
