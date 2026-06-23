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


# --- KoSIT HTTP-Daemon (validationtool -D) -----------------------------------

_VARL_ACCEPT = (
    b'<rep:report xmlns:rep="http://www.xoev.de/de/validator/varl/1">'
    b'<rep:assessment><rep:accept/></rep:assessment></rep:report>'
)
_VARL_REJECT = (
    b'<rep:report xmlns:rep="http://www.xoev.de/de/validator/varl/1"'
    b' xmlns:s="http://www.xoev.de/de/validator/framework/1/scenarios">'
    b'<rep:assessment><rep:reject/></rep:assessment>'
    b'<rep:scenarioMatched><s:validationStepResult>'
    b'<s:message level="error" code="BR-DE-15">BuyerReference fehlt</s:message>'
    b'<s:message level="warning" code="BR-DE-1">CustomizationID Hinweis</s:message>'
    b'</s:validationStepResult></rep:scenarioMatched></rep:report>'
)


class _Resp:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content


def _make_validator(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _bin: None)  # no binary -> service is the only "kosit"
    invoice = tmp_path / "invoice.xml"
    invoice.write_text("<Invoice/>", encoding="utf-8")
    return KositValidator(service_url="http://kosit-validator:8080"), invoice


def test_service_accept_passes(tmp_path, monkeypatch) -> None:
    import requests
    validator, invoice = _make_validator(tmp_path, monkeypatch)
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(200, _VARL_ACCEPT))

    result = validator.validate_file(invoice, tmp_path / "reports")

    assert result.status == "passed"
    assert result.engine == "kosit"
    assert result.errors == []


def test_service_reject_parses_messages(tmp_path, monkeypatch) -> None:
    import requests
    validator, invoice = _make_validator(tmp_path, monkeypatch)
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(200, _VARL_REJECT))

    result = validator.validate_file(invoice, tmp_path / "reports")

    assert result.status == "failed"
    assert result.engine == "kosit"
    assert any("BR-DE-15" in e for e in result.errors)
    assert any("BR-DE-1" in w for w in result.warnings)


def test_service_unreachable_falls_back_to_python(tmp_path, monkeypatch) -> None:
    import requests
    validator, invoice = _make_validator(tmp_path, monkeypatch)

    def boom(*_a, **_k):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "post", boom)

    result = validator.validate_file(invoice, tmp_path / "reports")

    # Service down + no binary -> clean fallback (engine != real 'kosit')
    assert result.status == "warning"
    assert result.engine == "kosit-fallback"


def test_service_http_error_falls_back(tmp_path, monkeypatch) -> None:
    import requests
    validator, invoice = _make_validator(tmp_path, monkeypatch)
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(503, b""))

    result = validator.validate_file(invoice, tmp_path / "reports")

    assert result.engine == "kosit-fallback"


def test_no_service_url_uses_binary_path(tmp_path, monkeypatch) -> None:
    # service_url=None (env unset) -> unchanged binary behaviour
    monkeypatch.delenv("KOSIT_VALIDATOR_URL", raising=False)
    monkeypatch.setattr("shutil.which", lambda _bin: None)
    validator = KositValidator(binary="missing-kosit")
    assert validator.service_url is None
    result = validator.validate_file(tmp_path / "i.xml", tmp_path / "r")
    assert result.status == "warning"
    assert result.engine == "kosit-fallback"
