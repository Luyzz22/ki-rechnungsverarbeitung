"""Tests für Duplikatserkennung (B6) und Schema-Migration (MIG)."""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402
import enterprise_db  # noqa: E402
import duplicate_detection as dd  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Temp-DB mit Basis-invoices/jobs; init_enterprise_schema zieht die MIG-Spalten
    (datei_hash, content_hash, …) und die duplicate_detections-Tabelle nach."""
    p = tmp_path / "dup.db"
    monkeypatch.setattr(database, "_ensure_db_path", lambda: p)
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE jobs (job_id TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT, upload_path TEXT)")
    cur.execute(
        """CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, rechnungsnummer TEXT,
            datum TEXT, rechnungsaussteller TEXT, betrag_brutto REAL, tenant_id INTEGER,
            datei_pfad TEXT)""")
    conn.commit(); conn.close()
    enterprise_db.init_enterprise_schema()
    return p


def _seed(nummer, brutto, tenant=1, aussteller=None, datum=None, datei_hash=None, datei_pfad=None):
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO invoices
           (rechnungsnummer, betrag_brutto, tenant_id, rechnungsaussteller, datum,
            datei_hash, datei_pfad)
           VALUES (?,?,?,?,?,?,?)""",
        (nummer, brutto, tenant, aussteller, datum, datei_hash, datei_pfad),
    )
    iid = cur.lastrowid
    conn.commit(); conn.close()
    return iid


# --- MIG: Spalten + Tabelle idempotent angelegt ---------------------------
def test_mig_columns_and_table_created(db):
    conn = database.get_connection(); cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(invoices)").fetchall()]
    for c in ("datei_hash", "content_hash", "extraktion_raw", "validierung_json",
              "kontierung_json", "datei_pfad"):
        assert c in cols, f"Spalte {c} fehlt (Migration nicht angewandt)"
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='duplicate_detections'"
    ).fetchone()
    conn.close()
    assert row is not None, "duplicate_detections-Tabelle fehlt"


# --- B6: Datei-Hash-Duplikate (layoutunabhängig) --------------------------
def test_file_hash_duplicate_detected(db):
    h = dd.compute_file_hash(b"%PDF identical bytes")
    first = _seed("IT2025032", 1880.2, datei_hash=h)
    second = _seed("IT2025032", 1880.2, datei_hash=h)
    m = dd.check_duplicate_by_file_hash(h, 1, exclude_invoice_id=second)
    assert m and m["id"] == first


def test_file_hash_null_supplier_case(db):
    """Der Doc-36/41-Fall: beide Aussteller NULL, identische Datei → Duplikat."""
    h = dd.compute_file_hash(b"IT2025032 briefkopf-logo only")
    a = _seed("IT2025032", 1880.2, aussteller=None, datei_hash=h)
    b = _seed("IT2025032", 1880.2, aussteller=None, datei_hash=h)
    m = dd.check_duplicate_by_file_hash(h, 1, exclude_invoice_id=b)
    assert m and m["id"] == a


def test_file_hash_tenant_isolated(db):
    h = dd.compute_file_hash(b"x")
    _seed("X", 10.0, tenant=1, datei_hash=h)
    assert dd.check_duplicate_by_file_hash(h, 2) is None  # fremder Tenant


# --- B6: NULL-sicherer Feld-Match -----------------------------------------
def test_field_match_null_supplier(db):
    """NULL-Aussteller darf den Match NICHT kippen (alte Fail-open-Klasse)."""
    a = _seed("IT2025032", 1880.2, aussteller=None)
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "IT2025032", "betrag_brutto": 1880.2}, 1)
    assert m and m["id"] == a


def test_field_match_ignores_datum_format_mismatch(db):
    """B6-Regression (Doc 36/41/45): Bestandsrechnung mit ABWEICHENDEM Datums-
    format (vor der Normalisierung erfasst) darf den Feld-Match NICHT verhindern.
    Identität = (tenant, nummer, betrag); Datum ist nur Sortier-Präferenz."""
    old = _seed("IT2025032", 1880.2, aussteller=None, datum="29.09.2025")  # Altformat
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "IT2025032", "betrag_brutto": 1880.2,
         "datum": "2025-09-29", "rechnungsaussteller": None}, 1)  # neu normalisiert
    assert m and m["id"] == old


def test_field_match_prefers_same_datum(db):
    """Bei mehreren Kandidaten wird der mit gleichem Datum bevorzugt (aber keiner
    ausgeschlossen)."""
    other = _seed("R-1", 100.0, aussteller=None, datum="2020-01-01")
    same = _seed("R-1", 100.0, aussteller=None, datum="2026-05-05")
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "R-1", "betrag_brutto": 100.0, "datum": "2026-05-05"}, 1)
    assert m and m["id"] == same


def test_field_match_different_dates_no_false_positive(db):
    """Codex P2: gleiche Nummer + gleicher Betrag + NULL-Aussteller, aber
    VERSCHIEDENE (beidseitig vorhandene) Daten → KEIN Duplikat (wiederkehrende
    Belege mit simpler Nummer). Datum bleibt format-toleranter Discriminator."""
    _seed("2026-001", 100.0, aussteller=None, datum="2026-01-15")
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "2026-001", "betrag_brutto": 100.0,
         "datum": "2026-07-15", "rechnungsaussteller": None}, 1)
    assert m is None


def test_backfill_skips_ambiguous_multifile_job(db, tmp_path):
    """Codex P1: bei Mehr-Datei-Jobs (geteiltes upload_path, mehrere Rechnungen
    ohne datei_pfad) darf der Backfill KEINEN geteilten Hash setzen."""
    job_dir = tmp_path / "job1"; job_dir.mkdir()
    (job_dir / "a.pdf").write_bytes(b"AAA")
    (job_dir / "b.pdf").write_bytes(b"BBB")
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO jobs (job_id, user_id, upload_path) VALUES (?,?,?)", ("job1", 1, str(job_dir)))
    for nr in ("A", "B"):
        cur.execute("INSERT INTO invoices (job_id, rechnungsnummer, betrag_brutto, tenant_id) VALUES (?,?,?,?)",
                    ("job1", nr, 10.0, 1))
    conn.commit(); conn.close()
    dd.backfill_datei_hashes()
    conn = database.get_connection(); cur = conn.cursor()
    hashes = [r[0] for r in cur.execute("SELECT datei_hash FROM invoices WHERE job_id='job1' ORDER BY id").fetchall()]
    conn.close()
    assert hashes == [None, None]


def test_backfill_single_file_job_gets_hash(db, tmp_path):
    """Ein-Datei-Job (eindeutig) bekommt den korrekten Hash über upload_path."""
    job_dir = tmp_path / "job2"; job_dir.mkdir()
    content = b"%PDF single file"
    (job_dir / "only.pdf").write_bytes(content)
    conn = database.get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO jobs (job_id, user_id, upload_path) VALUES (?,?,?)", ("job2", 1, str(job_dir)))
    cur.execute("INSERT INTO invoices (job_id, rechnungsnummer, betrag_brutto, tenant_id) VALUES (?,?,?,?)",
                ("job2", "S", 5.0, 1))
    conn.commit(); conn.close()
    dd.backfill_datei_hashes()
    conn = database.get_connection(); cur = conn.cursor()
    h = cur.execute("SELECT datei_hash FROM invoices WHERE job_id='job2'").fetchone()[0]
    conn.close()
    assert h == dd.compute_file_hash(content)


def test_field_match_different_amount_no_false_positive(db):
    _seed("IT2025032", 1880.2)
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "IT2025032", "betrag_brutto": 999.0}, 1)
    assert m is None


def test_field_match_edeka_regression(db):
    """Doc 31 (EDEKA): andere Nummer/anderer Betrag → kein Duplikat."""
    _seed("EDEKA-1", 42.0, aussteller="EDEKA")
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "EDEKA-2", "betrag_brutto": 50.0, "rechnungsaussteller": "EDEKA"}, 1)
    assert m is None


def test_field_match_requires_nummer_and_betrag(db):
    _seed("IT2025032", 1880.2)
    assert dd.check_duplicate_by_fields({"betrag_brutto": 1880.2}, 1) is None
    assert dd.check_duplicate_by_fields({"rechnungsnummer": "IT2025032"}, 1) is None


def test_field_match_different_known_suppliers_no_false_positive(db):
    """Codex P2: zwei BEKANNTE, verschiedene Aussteller mit gleicher (simpler)
    Nummer + Betrag → KEIN Duplikat (verschiedene Lieferanten, gleiche Nummer)."""
    _seed("2026-001", 100.0, aussteller="Lieferant A")
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "2026-001", "betrag_brutto": 100.0,
         "rechnungsaussteller": "Lieferant B"}, 1)
    assert m is None


def test_field_match_same_known_supplier_is_duplicate(db):
    a = _seed("2026-001", 100.0, aussteller="Lieferant A")
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "2026-001", "betrag_brutto": 100.0,
         "rechnungsaussteller": "lieferant a"}, 1)  # case-insensitive
    assert m and m["id"] == a


def test_field_match_supplier_guard_null_tolerant(db):
    """NULL-Toleranz bleibt: neuer Beleg mit Aussteller, Altbeleg ohne → Duplikat
    (der Briefkopf-Logo-Fall darf nicht am Aussteller-Guard scheitern)."""
    a = _seed("IT2025032", 1880.2, aussteller=None)
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "IT2025032", "betrag_brutto": 1880.2,
         "rechnungsaussteller": "SBS GmbH"}, 1)
    assert m and m["id"] == a


def test_field_match_tenant_isolated(db):
    _seed("IT2025032", 1880.2, tenant=1)
    m = dd.check_duplicate_by_fields(
        {"rechnungsnummer": "IT2025032", "betrag_brutto": 1880.2}, 2)
    assert m is None


# --- B6: Backfill ---------------------------------------------------------
def test_backfill_datei_hashes(db, tmp_path):
    content = b"%PDF-1.4 backfill test bytes"
    f = tmp_path / "inv.pdf"
    f.write_bytes(content)
    iid = _seed("Z", 5.0, datei_pfad=str(f))  # ohne datei_hash
    n = dd.backfill_datei_hashes()
    assert n >= 1
    conn = database.get_connection(); cur = conn.cursor()
    h = cur.execute("SELECT datei_hash FROM invoices WHERE id=?", (iid,)).fetchone()[0]
    conn.close()
    assert h == dd.compute_file_hash(content)
