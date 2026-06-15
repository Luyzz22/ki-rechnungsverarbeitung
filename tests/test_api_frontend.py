"""E2E-Test der Frontend-JSON-API (/api/app, Bearer-Auth) für die Next.js-SPA."""

import os
import tempfile

import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ["INVOICE_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "api_frontend.db")

web_app = pytest.importorskip("web.app", reason="App-Abhängigkeiten nicht installiert")
tc = pytest.importorskip("fastapi.testclient")

from pathlib import Path  # noqa: E402

_DB_FILE = Path(os.environ["INVOICE_DB_PATH"])


@pytest.fixture(autouse=True)
def _pin_db():
    """DB-Pfad-Resolver vor JEDEM Test auf diese Modul-DB fixieren (verhindert
    Leaks durch andere Test-Module, die _ensure_db_path global überschreiben).
    Setzt zudem den Auth-Rate-Limiter zurück (sonst Flakiness über Tests)."""
    import database
    database._ensure_db_path = lambda: _DB_FILE
    try:
        import rate_limiter
        rate_limiter.limiter.requests.clear()
    except Exception:
        pass
    yield


@pytest.fixture(scope="module")
def client():
    import database
    _DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    database._ensure_db_path = lambda: _DB_FILE
    from database import init_database, init_users_table
    init_database()
    init_users_table()
    try:
        import rbac
        rbac.init_rbac_tables()
    except Exception:
        pass
    return tc.TestClient(web_app.app, base_url="https://belegflow-ai.de", raise_server_exceptions=False)


@pytest.fixture(scope="module")
def token(client):
    r = client.post("/api/app/register", json={
        "email": "spa@test.de", "password": "Test1234", "name": "SPA", "company": "ACME"})
    assert r.status_code in (200, 201), r.text
    return r.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_token(client, token):
    r = client.post("/api/app/login", json={"email": "spa@test.de", "password": "Test1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["token"] and body["user"]["email"] == "spa@test.de"


def test_login_wrong_password(client):
    r = client.post("/api/app/login", json={"email": "spa@test.de", "password": "falsch"})
    assert r.status_code == 401


def test_requires_auth(client):
    assert client.get("/api/app/dashboard/kpis").status_code == 401
    assert client.get("/api/app/invoices").status_code == 401


def test_me(client, token):
    r = client.get("/api/app/me", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "spa@test.de"


@pytest.mark.parametrize("path", [
    "/api/app/dashboard/kpis",
    "/api/app/invoices",
    "/api/app/lieferanten",
    "/api/app/freigaben",
    "/api/app/audit",
])
def test_bearer_endpoints_ok(client, token, path):
    r = client.get(path, headers=_auth(token))
    assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:120]}"


def test_kpis_shape(client, token):
    body = client.get("/api/app/dashboard/kpis", headers=_auth(token)).json()
    for k in ("count_month", "automation_rate", "open_approvals", "anomaly_alerts", "trend"):
        assert k in body


def test_invoices_pagination_shape(client, token):
    body = client.get("/api/app/invoices?limit=10", headers=_auth(token)).json()
    assert set(["total", "limit", "offset", "items"]).issubset(body.keys())
    assert body["limit"] == 10


def test_invoice_detail_404(client, token):
    assert client.get("/api/app/invoices/999999", headers=_auth(token)).status_code == 404


def test_audit_csv(client, token):
    r = client.get("/api/app/audit/export.csv", headers=_auth(token))
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Teil 2: neue Endpoints (upload, datev, reject grund)
# ---------------------------------------------------------------------------
def _tenant_id(client, token):
    return client.get("/api/app/me", headers=_auth(token)).json()["user"]["id"]


def _seed_invoice(client, token, **over):
    """Legt Job + Rechnung für den eingeloggten Tenant an, gibt invoice_id zurück."""
    import database
    tid = _tenant_id(client, token)
    conn = database.get_connection()
    cur = conn.cursor()
    job_id = f"job-seed-{over.get('nr','1')}"
    cur.execute("INSERT OR IGNORE INTO jobs (job_id, user_id, created_at) VALUES (?,?,?)",
                (job_id, tid, "2026-01-01T00:00:00"))
    cur.execute(
        """INSERT INTO invoices
           (job_id, rechnungsnummer, datum, rechnungsaussteller, betrag_brutto,
            betrag_netto, mwst_betrag, mwst_satz, waehrung, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (job_id, over.get("nr", "R-1"), "2026-01-15", over.get("supplier", "Acme GmbH"),
         119.0, 100.0, 19.0, 19.0, "EUR", over.get("status", "approved"), "2026-01-15T10:00:00"),
    )
    inv_id = cur.lastrowid
    conn.commit()
    conn.close()
    return inv_id


def _make_pdf(text="Rechnung Nr. 2026-001\nAcme GmbH\nGesamtbetrag: 119,00 EUR"):
    import io
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in text.split("\n"):
        c.drawString(80, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


def test_upload_runs_pipeline(client, token, monkeypatch):
    import invoice_extraction
    # KI-Aufruf mocken (kein API-Key nötig)
    monkeypatch.setattr(invoice_extraction, "_call_llm", lambda text: {
        "rechnungsaussteller": "Acme GmbH", "rechnungsnummer": "2026-001",
        "datum": "2026-01-15", "betrag_brutto": "119,00", "betrag_netto": "100,00",
        "mwst_betrag": "19,00", "mwst_satz": "19.0", "steuernummer": "12/345/67890",
        "iban": "DE89370400440532013000", "waehrung": "EUR",
    })
    files = {"files": ("rechnung.pdf", _make_pdf(), "application/pdf")}
    r = client.post("/api/app/upload", headers=_auth(token), files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == body["job_id"]
    assert body["status"] == "verarbeitet"
    inv = body["invoices"][0]
    assert inv["status"] == "verarbeitet"
    # Invoice-Record wurde aktualisiert
    detail = client.get(f"/api/app/invoices/{inv['id']}", headers=_auth(token)).json()
    assert detail["rechnungsaussteller"] == "Acme GmbH"
    assert detail["betrag_brutto"] == 119.0


def test_upload_without_llm_sets_error(client, token, monkeypatch):
    import invoice_extraction
    def _raise(text):
        raise invoice_extraction.NoLLMConfigured("kein key")
    monkeypatch.setattr(invoice_extraction, "_call_llm", _raise)
    files = {"files": ("r.pdf", _make_pdf(), "application/pdf")}
    r = client.post("/api/app/upload", headers=_auth(token), files=files)
    assert r.status_code == 200
    assert r.json()["invoices"][0]["status"] == "fehler"


def test_upload_rejects_non_document(client, token):
    files = {"files": ("notes.txt", b"hello", "text/plain")}
    r = client.post("/api/app/upload", headers=_auth(token), files=files)
    assert r.status_code == 400


def test_upload_requires_auth(client):
    files = {"files": ("rechnung.pdf", b"%PDF-1.4", "application/pdf")}
    assert client.post("/api/app/upload", files=files).status_code == 401


def test_datev_preview_404(client, token):
    assert client.get("/api/app/datev/preview?invoice_id=999999",
                      headers=_auth(token)).status_code == 404


def test_datev_preview_ok(client, token):
    inv = _seed_invoice(client, token, nr="PREV-1")
    r = client.get(f"/api/app/datev/preview?invoice_id={inv}", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["invoice"]["id"] == inv
    assert isinstance(body["buchungen"], list) and len(body["buchungen"]) >= 1


def test_datev_export_csv(client, token):
    _seed_invoice(client, token, nr="EXP-1")
    r = client.post("/api/app/datev/export", headers=_auth(token), json={})
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    assert r.content  # nicht leer


def test_datev_export_no_invoices_for_ids(client, token):
    r = client.post("/api/app/datev/export", headers=_auth(token),
                    json={"invoice_ids": [999999]})
    assert r.status_code == 404


def test_reject_with_grund(client, token):
    import approval_workflow
    tid = _tenant_id(client, token)
    inv = _seed_invoice(client, token, nr="REJ-1", status="neu")
    res = approval_workflow.submit_for_approval(tid, inv, 500.0, user_id=tid, notify=False)
    r = client.post(f"/api/app/freigaben/{res['request_id']}/reject",
                    headers=_auth(token), json={"grund": "Doppelerfassung"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "abgelehnt"


# ---------------------------------------------------------------------------
# PDF-Serving + Auto-Freigabe nach Upload
# ---------------------------------------------------------------------------
def _mock_llm(monkeypatch, nr="PDF-1", brutto="119,00"):
    import invoice_extraction
    monkeypatch.setattr(invoice_extraction, "_call_llm", lambda text: {
        "rechnungsaussteller": "Acme GmbH", "rechnungsnummer": nr,
        "datum": "2026-01-15", "betrag_brutto": brutto, "mwst_satz": "19.0",
        "steuernummer": "12/345/67890",
    })


def test_invoice_pdf_served(client, token, monkeypatch):
    _mock_llm(monkeypatch, nr="PDF-OK")
    files = {"files": ("meine_rechnung.pdf", _make_pdf(), "application/pdf")}
    inv = client.post("/api/app/upload", headers=_auth(token), files=files).json()["invoices"][0]
    r = client.get(f"/api/app/invoices/{inv['id']}/pdf", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_invoice_pdf_tenant_isolated(client, token, monkeypatch):
    _mock_llm(monkeypatch, nr="PDF-ISO")
    files = {"files": ("r.pdf", _make_pdf(), "application/pdf")}
    inv = client.post("/api/app/upload", headers=_auth(token), files=files).json()["invoices"][0]
    # zweiter Tenant darf die PDF NICHT sehen
    other = client.post("/api/app/register", json={
        "email": "other-tenant@test.de", "password": "Test1234"}).json()["token"]
    r = client.get(f"/api/app/invoices/{inv['id']}/pdf", headers=_auth(other))
    assert r.status_code == 404


def test_invoice_pdf_404_unknown(client, token):
    assert client.get("/api/app/invoices/999999/pdf", headers=_auth(token)).status_code == 404


def test_upload_auto_submits_freigabe(client, token, monkeypatch):
    _mock_llm(monkeypatch, nr="FREI-1")
    files = {"files": ("f.pdf", _make_pdf(), "application/pdf")}
    inv = client.post("/api/app/upload", headers=_auth(token), files=files).json()["invoices"][0]
    items = client.get("/api/app/freigaben", headers=_auth(token)).json()["items"]
    mine = [i for i in items if i["invoice_id"] == inv["id"]]
    assert mine, "verarbeitete Rechnung muss in der Freigabe-Queue stehen"
    assert mine[0]["required_role"] == "Sachbearbeiter"
    assert mine[0]["status"] == "offen"


# ---------------------------------------------------------------------------
# Security-Hardening: Rate-Limit, Passwort-Policy, Upload-Validierung
# ---------------------------------------------------------------------------
def test_login_rate_limited(client):
    # 5 erlaubt (auth: 5/min), der 6. Versuch → 429
    for _ in range(5):
        client.post("/api/app/login", json={"email": "x@y.de", "password": "nope"})
    r = client.post("/api/app/login", json={"email": "x@y.de", "password": "nope"})
    assert r.status_code == 429


def test_register_password_policy(client):
    # zu schwach (kein Großbuchstabe/Zahl)
    r = client.post("/api/app/register", json={"email": "weak@test.de", "password": "weakling"})
    assert r.status_code == 400
    # ok
    r2 = client.post("/api/app/register", json={"email": "strong@test.de", "password": "Strong123"})
    assert r2.status_code == 201, r2.text


def test_upload_rejects_disallowed_type(client, token):
    files = {"files": ("script.exe", b"MZ", "application/octet-stream")}
    r = client.post("/api/app/upload", headers=_auth(token), files=files)
    assert r.status_code == 400


def test_upload_rejects_too_large(client, token, monkeypatch):
    import api_frontend
    monkeypatch.setattr(api_frontend, "UPLOAD_MAX_BYTES", 1024)  # 1 KB Limit
    big = b"%PDF-1.4" + b"0" * 2048
    files = {"files": ("big.pdf", big, "application/pdf")}
    r = client.post("/api/app/upload", headers=_auth(token), files=files)
    assert r.status_code == 413
