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
            betrag_netto, mwst_betrag, mwst_satz, waehrung, status, created_at, tenant_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (job_id, over.get("nr", "R-1"), "2026-01-15", over.get("supplier", "Acme GmbH"),
         119.0, 100.0, 19.0, 19.0, "EUR", over.get("status", "approved"), "2026-01-15T10:00:00", tid),
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


def test_datev_preview_accepts_post(client, token):
    """Regression: Frontend ruft /api/app/datev/preview per POST – darf NICHT 405
    liefern (Method-/Pfad-Mismatch). POST + GET zeigen auf dieselbe Logik."""
    # POST ohne invoice_id → 200 Batch-Vorschau (erreicht den Handler, kein 405/422)
    r = client.post("/api/app/datev/preview", headers=_auth(token), json={})
    assert r.status_code != 405, r.text
    assert r.status_code == 200, r.text
    assert r.json().get("batch") is True
    # POST mit invoice_id (Body) auf fremde/nicht existente Rechnung → 404 (tenant-isoliert)
    r = client.post("/api/app/datev/preview", headers=_auth(token), json={"invoice_id": 999999})
    assert r.status_code == 404
    # POST mit invoice_id als Query funktioniert ebenfalls
    r = client.post("/api/app/datev/preview?invoice_id=999999", headers=_auth(token))
    assert r.status_code == 404
    # GET-Variante bleibt bestehen
    r = client.get("/api/app/datev/preview?invoice_id=999999", headers=_auth(token))
    assert r.status_code == 404


def test_datev_preview_post_requires_auth(client):
    r = client.post("/api/app/datev/preview", json={"invoice_id": 1})
    assert r.status_code == 401


@pytest.mark.parametrize("bad", [1.9, "1.9", True, "abc", "1e3", "", None])
def test_datev_preview_post_rejects_invalid_invoice_id(client, token, bad):
    """Body-invoice_id wird streng validiert: kein 500 und keine stille Rundung
    (1.9/true → 1). Ungültige Werte → 422, nicht falsche/gerundete Rechnung."""
    r = client.post("/api/app/datev/preview", headers=_auth(token), json={"invoice_id": bad})
    assert r.status_code == 422, f"{bad!r} -> {r.status_code}: {r.text[:120]}"


def test_invoices_visible_without_job_and_tenant_isolated(client):
    """Regression: Rechnungen mit gesetztem tenant_id, aber OHNE zugehörige
    jobs-Zeile (Produktionszustand: jobs leer) müssen sichtbar sein – der frühere
    INNER JOIN auf jobs lieferte 0. Isolation läuft jetzt über i.tenant_id."""
    import database
    ta = client.post("/api/app/register", json={
        "email": "orpha@test.de", "password": "Test1234", "name": "A", "company": "X"}).json()["token"]
    tb = client.post("/api/app/register", json={
        "email": "orphb@test.de", "password": "Test1234", "name": "B", "company": "Y"}).json()["token"]
    tid_a = _tenant_id(client, ta)
    conn = database.get_connection(); cur = conn.cursor()
    # KEINE jobs-Zeile für diese job_id → Orphan-Rechnung wie in Produktion
    cur.execute(
        """INSERT INTO invoices
           (job_id, rechnungsnummer, datum, rechnungsaussteller, betrag_brutto,
            betrag_netto, mwst_betrag, waehrung, status, created_at, tenant_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        ("kein-job-vorhanden", "ORPH-A", "2026-03-15", "Waise GmbH", 50.0, 42.0, 8.0,
         "EUR", "verarbeitet", "2026-03-15T10:00:00", tid_a))
    conn.commit(); conn.close()
    # Tenant A sieht die Orphan-Rechnung (trotz leerer jobs-Tabelle)
    a = client.get("/api/app/invoices?limit=500", headers=_auth(ta)).json()
    assert "ORPH-A" in [i["rechnungsnummer"] for i in a["items"]], a["total"]
    assert a["total"] >= 1
    # Tenant B sieht sie NICHT (Isolation über i.tenant_id)
    b = client.get("/api/app/invoices?limit=500", headers=_auth(tb)).json()
    assert "ORPH-A" not in [i["rechnungsnummer"] for i in b["items"]]


def test_invoices_classic_flow_visible_via_job_user_id(client):
    """Regression (Codex P1): der klassische Upload-Flow schreibt invoices OHNE
    tenant_id (Zuordnung nur über jobs.user_id). Diese müssen sichtbar bleiben
    (LEFT JOIN + tenant-sicherer Fallback), aber tenant-isoliert."""
    import database
    ta = client.post("/api/app/register", json={
        "email": "clsa@test.de", "password": "Test1234", "name": "A", "company": "X"}).json()["token"]
    tb = client.post("/api/app/register", json={
        "email": "clsb@test.de", "password": "Test1234", "name": "B", "company": "Y"}).json()["token"]
    tid_a = _tenant_id(client, ta)
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO jobs (job_id, user_id, created_at) VALUES (?,?,?)",
                ("classic-job-1", tid_a, "2026-02-01T00:00:00"))
    # tenant_id NICHT gesetzt → Zuordnung nur über den Job
    cur.execute(
        """INSERT INTO invoices (job_id, rechnungsnummer, datum, rechnungsaussteller,
           betrag_brutto, betrag_netto, mwst_betrag, waehrung, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        ("classic-job-1", "CLASSIC-1", "2026-02-15", "Klassik GmbH", 60.0, 50.4, 9.6, "EUR", "verarbeitet"))
    conn.commit(); conn.close()
    a = client.get("/api/app/invoices?limit=500", headers=_auth(ta)).json()
    assert "CLASSIC-1" in [i["rechnungsnummer"] for i in a["items"]], a["total"]
    # Isolation: Tenant B sieht sie nicht
    b = client.get("/api/app/invoices?limit=500", headers=_auth(tb)).json()
    assert "CLASSIC-1" not in [i["rechnungsnummer"] for i in b["items"]]


def test_invoices_tenant_id_takes_precedence_over_job_user_id(client):
    """Isolation (COALESCE statt OR): Ist i.tenant_id gesetzt, entscheidet AUSSCHLIESSLICH
    dieser Wert – ein fremder jobs.user_id darf nichts durchlassen. Eine Rechnung mit
    i.tenant_id = B, deren Job aber A gehört (jobs.user_id = A), gehört NUR B. Das frühere
    ``(i.tenant_id = ? OR j.user_id = ?)`` hätte sie fälschlich auch A gezeigt (Leak)."""
    import database
    ta = client.post("/api/app/register", json={
        "email": "preca@test.de", "password": "Test1234", "name": "A", "company": "X"}).json()["token"]
    tb = client.post("/api/app/register", json={
        "email": "precb@test.de", "password": "Test1234", "name": "B", "company": "Y"}).json()["token"]
    tid_a = _tenant_id(client, ta)
    tid_b = _tenant_id(client, tb)
    conn = database.get_connection(); cur = conn.cursor()
    # Job gehört A …
    cur.execute("INSERT OR IGNORE INTO jobs (job_id, user_id, created_at) VALUES (?,?,?)",
                ("prec-job-owned-by-a", tid_a, "2026-05-01T00:00:00"))
    # … aber die Rechnung trägt tenant_id = B → gehört NUR B.
    cur.execute(
        """INSERT INTO invoices
           (job_id, rechnungsnummer, datum, rechnungsaussteller, betrag_brutto,
            betrag_netto, mwst_betrag, waehrung, status, created_at, tenant_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        ("prec-job-owned-by-a", "PREC-1", "2026-05-15", "Vorrang GmbH", 70.0, 58.8, 11.2,
         "EUR", "verarbeitet", "2026-05-15T10:00:00", tid_b))
    conn.commit(); conn.close()
    # B (tenant_id) sieht sie
    b = client.get("/api/app/invoices?limit=500", headers=_auth(tb)).json()
    assert "PREC-1" in [i["rechnungsnummer"] for i in b["items"]], b["total"]
    # A (nur Job-Owner) sieht sie NICHT – kein OR-Leak über jobs.user_id
    a = client.get("/api/app/invoices?limit=500", headers=_auth(ta)).json()
    assert "PREC-1" not in [i["rechnungsnummer"] for i in a["items"]]


_FULL_INVOICES_SCHEMA = """
    CREATE TABLE invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT,
        rechnungsnummer TEXT, datum TEXT, faelligkeitsdatum TEXT, zahlungsziel_tage INTEGER,
        rechnungsaussteller TEXT, rechnungsaussteller_adresse TEXT,
        rechnungsempfaenger TEXT, rechnungsempfaenger_adresse TEXT, kundennummer TEXT,
        betrag_brutto REAL, betrag_netto REAL, mwst_betrag REAL, mwst_satz REAL,
        waehrung TEXT, iban TEXT, bic TEXT, steuernummer TEXT, ust_idnr TEXT,
        zahlungsbedingungen TEXT, artikel TEXT, verwendungszweck TEXT, content_hash TEXT,
        source_format TEXT, einvoice_raw_xml TEXT, einvoice_profile TEXT,
        einvoice_valid INTEGER, einvoice_validation_message TEXT, confidence REAL,
        tenant_id INTEGER
    )
"""


def test_save_invoices_sets_tenant_id_from_job(tmp_path, monkeypatch):
    """P1-Folgefix: database.save_invoices (klassischer Flow) muss tenant_id direkt auf
    die Rechnung schreiben – abgeleitet aus jobs.user_id –, damit neue Rechnungen sauber
    zugeordnet sind und der tenant_id-NULL-Altbestand nicht weiterwächst. Eigene Voll-Schema-
    DB, da die schlanke SPA-Test-DB die Migrations-Spalten (content_hash …) nicht führt."""
    import sqlite3
    import database
    db_file = tmp_path / "save_invoices.db"
    monkeypatch.setattr(database, "_ensure_db_path", lambda: db_file)
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE jobs (job_id TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT)")
    conn.execute(_FULL_INVOICES_SCHEMA)
    conn.execute("INSERT INTO jobs (job_id, user_id, created_at) VALUES (?,?,?)",
                 ("save-inv-tenant-1", 4242, "2026-04-01T00:00:00"))
    conn.commit(); conn.close()

    database.save_invoices("save-inv-tenant-1", [{
        "rechnungsnummer": "SAVE-1", "rechnungsaussteller": "Neu GmbH",
        "betrag_brutto": 119.0, "betrag_netto": 100.0, "datum": "2026-04-15",
    }])

    conn = sqlite3.connect(db_file)
    row = conn.execute(
        "SELECT tenant_id FROM invoices WHERE job_id = ? AND rechnungsnummer = ?",
        ("save-inv-tenant-1", "SAVE-1")).fetchone()
    conn.close()
    assert row is not None and row[0] is not None, "tenant_id muss beim Insert gesetzt sein"
    assert int(row[0]) == 4242

    # Explizit übergebener tenant_id hat Vorrang vor jobs.user_id
    database.save_invoices("save-inv-tenant-1", [{
        "rechnungsnummer": "SAVE-2", "rechnungsaussteller": "Neu GmbH", "betrag_brutto": 10.0,
    }], tenant_id=99)
    conn = sqlite3.connect(db_file)
    row = conn.execute(
        "SELECT tenant_id FROM invoices WHERE rechnungsnummer = ?", ("SAVE-2",)).fetchone()
    conn.close()
    assert row is not None and int(row[0]) == 99


# ---------------------------------------------------------------------------
# DATEV-Vorschau: invoice_id optional → Gesamt-/Batch-Vorschau
# ---------------------------------------------------------------------------
def test_datev_preview_batch_post_without_invoice_id(client, token):
    """Regression: DATEV-Export-Seite lädt die Gesamt-Vorschau OHNE invoice_id.
    Früher 422 (erzwungene invoice_id) → jetzt 200 Batch über alle exportierbaren
    Rechnungen des Mandanten."""
    inv = _seed_invoice(client, token, nr="BATCH-1", status="approved")
    r = client.post("/api/app/datev/preview", headers=_auth(token), json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["batch"] is True
    ids = [it["invoice"]["id"] for it in body["invoices"]]
    assert inv in ids, body["invoice_count"]
    assert body["invoice_count"] >= 1
    # jede exportierbare Rechnung erzeugt mind. eine Buchung
    assert body["buchungen_count"] >= 1
    assert isinstance(body["buchungen"], list) and len(body["buchungen"]) >= 1


def test_datev_preview_batch_get_without_invoice_id(client, token):
    """GET-Variante ohne invoice_id liefert dieselbe Batch-Vorschau (kein 422)."""
    _seed_invoice(client, token, nr="BATCH-GET-1", status="verarbeitet")
    r = client.get("/api/app/datev/preview", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["batch"] is True
    assert body["invoice_count"] >= 1
    assert "BATCH-GET-1" in [it["invoice"]["rechnungsnummer"] for it in body["invoices"]]


def test_datev_preview_single_still_works(client, token):
    """Einzel-Vorschau bleibt unverändert: invoice_id gesetzt → genau diese Rechnung."""
    inv = _seed_invoice(client, token, nr="SINGLE-1", status="approved")
    # POST (Body)
    r = client.post("/api/app/datev/preview", headers=_auth(token), json={"invoice_id": inv})
    assert r.status_code == 200, r.text
    assert r.json()["invoice"]["id"] == inv
    assert "batch" not in r.json()
    # GET (Query)
    r = client.get(f"/api/app/datev/preview?invoice_id={inv}", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.json()["invoice"]["id"] == inv


def test_datev_preview_batch_tenant_isolated(client):
    """Fremder Mandant ohne eigene Rechnungen → leere Batch-Vorschau (0), sieht
    keine Rechnungen anderer Tenants."""
    owner = client.post("/api/app/register", json={
        "email": "batchowner@test.de", "password": "Test1234", "name": "O", "company": "X"}).json()["token"]
    stranger = client.post("/api/app/register", json={
        "email": "batchstranger@test.de", "password": "Test1234", "name": "S", "company": "Y"}).json()["token"]
    _seed_invoice(client, owner, nr="ISO-BATCH-1", status="approved")
    # Owner sieht seine Rechnung
    ob = client.post("/api/app/datev/preview", headers=_auth(owner), json={}).json()
    assert "ISO-BATCH-1" in [it["invoice"]["rechnungsnummer"] for it in ob["invoices"]]
    # Fremder Tenant: leere Vorschau
    sb = client.post("/api/app/datev/preview", headers=_auth(stranger), json={}).json()
    assert sb["batch"] is True
    assert sb["invoice_count"] == 0
    assert sb["invoices"] == []
    assert "ISO-BATCH-1" not in [it["invoice"]["rechnungsnummer"] for it in sb["invoices"]]
