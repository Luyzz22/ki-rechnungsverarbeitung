"""Tests für den öffentlichen E-Rechnungs-Validierungs-Endpoint /api/public/validate."""

import io
import os
import tempfile

import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("INVOICE_DB_PATH", os.path.join(tempfile.mkdtemp(), "public_validate.db"))

web_app = pytest.importorskip("web.app", reason="App-Abhängigkeiten nicht installiert")
tc = pytest.importorskip("fastapi.testclient")


@pytest.fixture(autouse=True)
def _reset_limiter():
    try:
        import rate_limiter
        rate_limiter.limiter.requests.clear()
    except Exception:
        pass
    yield


@pytest.fixture(scope="module")
def client():
    return tc.TestClient(web_app.app, base_url="https://belegflow-ai.de",
                         raise_server_exceptions=False)


VALID_UBL = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"'
    ' xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"'
    ' xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
    '<cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0</cbc:CustomizationID>'
    '<cbc:ID>RE-2026-001</cbc:ID>'
    '<cbc:IssueDate>2026-01-15</cbc:IssueDate>'
    '<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>'
    '<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>'
    '<cbc:BuyerReference>04011000-12345-34</cbc:BuyerReference>'
    '<cac:AccountingSupplierParty><cac:Party><cac:PartyName><cbc:Name>Muster GmbH</cbc:Name>'
    '</cac:PartyName></cac:Party></cac:AccountingSupplierParty>'
    '<cac:AccountingCustomerParty><cac:Party><cac:PartyName><cbc:Name>Kunde AG</cbc:Name>'
    '</cac:PartyName></cac:Party></cac:AccountingCustomerParty>'
    '<cac:LegalMonetaryTotal><cbc:PayableAmount currencyID="EUR">119.00</cbc:PayableAmount>'
    '</cac:LegalMonetaryTotal>'
    '<cac:InvoiceLine><cbc:ID>1</cbc:ID></cac:InvoiceLine>'
    '</Invoice>'
)


def _post(client, name, data, ctype):
    return client.post("/api/public/validate", files={"file": (name, data, ctype)})


def test_no_auth_required_and_contract_shape(client):
    r = _post(client, "rechnung.xml", VALID_UBL.encode(), "application/xml")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"level", "summary", "messages", "readable"}
    assert set(body["level"].keys()) == {"syntax", "schema", "schematron"}
    assert body["level"]["syntax"] == "ok"
    assert body["summary"]["format"] == "UBL"
    assert body["readable"]["invoiceNumber"] == "RE-2026-001"
    assert body["readable"]["totals"]["currency"] == "EUR"


def test_valid_invoice_passes(client):
    body = _post(client, "ok.xml", VALID_UBL.encode(), "application/xml").json()
    assert body["summary"]["valid"] is True
    assert body["summary"]["errors"] == 0


def test_invalid_invoice_reports_messages(client):
    # BuyerReference (BR-DE-15) + InvoiceLine fehlen → Fehler mit rule/field
    bad = VALID_UBL.replace('<cbc:BuyerReference>04011000-12345-34</cbc:BuyerReference>', '') \
                   .replace('<cac:InvoiceLine><cbc:ID>1</cbc:ID></cac:InvoiceLine>', '')
    body = _post(client, "bad.xml", bad.encode(), "application/xml").json()
    assert body["summary"]["valid"] is False
    rules = [m["rule"] for m in body["messages"]]
    assert any(r and "BR-DE-15" in r for r in rules)


def test_malformed_xml_422(client):
    r = _post(client, "broken.xml", b"<Invoice><unclosed>", "application/xml")
    assert r.status_code == 422
    assert "error" in r.json()


def test_wrong_type_400(client):
    r = _post(client, "notes.txt", b"hello world", "text/plain")
    assert r.status_code == 400


def test_empty_file_400(client):
    r = _post(client, "empty.xml", b"", "application/xml")
    assert r.status_code == 400


def test_too_large_400(client):
    big = b"<?xml version='1.0'?><Invoice>" + b"a" * (10 * 1024 * 1024 + 10) + b"</Invoice>"
    r = _post(client, "big.xml", big, "application/xml")
    assert r.status_code == 400


def test_xxe_external_entity_not_resolved_unit():
    """Beweis: gehärteter Parser löst externe Entities NICHT auf (kein Datei-Leak)."""
    import public_validate
    secret_path = os.path.join(tempfile.mkdtemp(), "secret.txt")
    with open(secret_path, "w") as f:
        f.write("TOPSECRET_XXE_CONTENT")
    xxe = (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE r [<!ENTITY xxe SYSTEM "file://{secret_path}">]>'
        '<r>&xxe;</r>'
    )
    leaked = False
    try:
        tree = public_validate._safe_parse(xxe.encode())
        from lxml import etree
        leaked = b"TOPSECRET_XXE_CONTENT" in etree.tostring(tree)
    except Exception:
        leaked = False  # Parser hat die Entity verweigert → ebenfalls sicher
    assert leaked is False


def test_xxe_external_entity_no_leak_http(client):
    secret_path = os.path.join(tempfile.mkdtemp(), "secret2.txt")
    with open(secret_path, "w") as f:
        f.write("TOPSECRET_HTTP_LEAK")
    xxe = (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file://{secret_path}">]>'
        '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">&xxe;</Invoice>'
    )
    r = _post(client, "xxe.xml", xxe.encode(), "application/xml")
    assert r.status_code in (200, 422)          # kontrolliert, kein 500
    assert "TOPSECRET_HTTP_LEAK" not in r.text  # kein Datei-Leak


def test_pdf_without_embedded_xml_422(client):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 800, "Kein ZUGFeRD")
    c.save()
    r = _post(client, "scan.pdf", buf.getvalue(), "application/pdf")
    assert r.status_code == 422


def test_rate_limit_429_with_retry_after(client):
    for _ in range(15):
        _post(client, "ok.xml", VALID_UBL.encode(), "application/xml")
    r = _post(client, "ok.xml", VALID_UBL.encode(), "application/xml")
    assert r.status_code == 429
    assert r.headers.get("Retry-After")


def test_summary_exposes_engine(client):
    body = _post(client, "ok.xml", VALID_UBL.encode(), "application/xml").json()
    assert body["summary"]["engine"] in ("kosit", "kosit-python")


def test_engine_kosit_when_service_wired(client, monkeypatch):
    """End-to-End: bei erreichbarem KoSIT-Daemon weist summary.engine 'kosit' aus."""
    import requests
    monkeypatch.setenv("KOSIT_VALIDATOR_URL", "http://kosit-validator:8080")
    accept = (
        b'<rep:report xmlns:rep="http://www.xoev.de/de/validator/varl/1">'
        b'<rep:assessment><rep:accept/></rep:assessment></rep:report>'
    )

    class _R:
        status_code = 200
        content = accept

    monkeypatch.setattr(requests, "post", lambda *a, **k: _R())
    body = _post(client, "ok.xml", VALID_UBL.encode(), "application/xml").json()
    assert body["summary"]["engine"] == "kosit"
