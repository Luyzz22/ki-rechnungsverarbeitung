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
    Leaks durch andere Test-Module, die _ensure_db_path global überschreiben)."""
    import database
    database._ensure_db_path = lambda: _DB_FILE
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


def test_upload_creates_job(client, token):
    files = {"files": ("rechnung.pdf", b"%PDF-1.4 minimal", "application/pdf")}
    r = client.post("/api/app/upload", headers=_auth(token), files=files)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "processing"
    assert body["id"] and body["id"] == body["job_id"]


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
