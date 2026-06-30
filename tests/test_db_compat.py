"""Unit-Tests der SQLite↔PostgreSQL-Kompatibilitätsschicht (ohne psycopg/Neon)."""

import os
import subprocess
import sys

# Für Endpoint-Boot (web.app) in den PG-Integrationstests benötigt:
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET", "test-secret-key")

import pytest

from db_compat import (
    HybridRow,
    is_postgres,
    translate_ddl,
    translate_dml,
    translate_placeholders,
    _PRAGMA_TABLE_INFO_RE,
)


def test_placeholder_basic():
    assert translate_placeholders("SELECT * FROM t WHERE a = ? AND b = ?") == \
        "SELECT * FROM t WHERE a = %s AND b = %s"


def test_placeholder_question_in_string_literal_kept():
    # ? innerhalb eines String-Literals darf NICHT ersetzt werden
    assert translate_placeholders("SELECT '?' WHERE x = ?") == "SELECT '?' WHERE x = %s"


def test_percent_doubled_for_psycopg():
    # literale % (z. B. LIKE-Muster im SQL) müssen verdoppelt werden
    assert translate_placeholders("WHERE name LIKE '%foo%'") == "WHERE name LIKE '%%foo%%'"
    assert translate_placeholders("strftime('%Y-%m', x)") == "strftime('%%Y-%%m', x)"


def test_percent_and_placeholder_combined():
    assert translate_placeholders("WHERE a LIKE ? AND b = ?") == "WHERE a LIKE %s AND b = %s"


def test_escaped_single_quote_in_string():
    # verdoppeltes Quote ist ein Escape innerhalb des Strings
    assert translate_placeholders("SELECT 'O''Brien' WHERE id = ?") == \
        "SELECT 'O''Brien' WHERE id = %s"


def test_hybrid_row_index_and_name_access():
    row = HybridRow(["id", "email"], [7, "a@b.de"])
    assert row[0] == 7
    assert row["email"] == "a@b.de"
    assert dict(row) == {"id": 7, "email": "a@b.de"}
    assert row.get("missing", "x") == "x"
    assert list(row.keys()) == ["id", "email"]


def test_is_postgres_off_without_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert is_postgres() is False


def test_is_postgres_on_with_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    assert is_postgres() is True


# ---------------------------------------------------------------------------
# DDL-Übersetzung: INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
# ---------------------------------------------------------------------------
def test_ddl_autoincrement_to_serial_basic():
    sql = "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)"
    assert translate_ddl(sql) == "CREATE TABLE t (id SERIAL PRIMARY KEY, name TEXT)"


def test_ddl_autoincrement_case_insensitive():
    sql = "create table t (id integer primary key autoincrement)"
    assert "SERIAL PRIMARY KEY" in translate_ddl(sql)
    assert "autoincrement" not in translate_ddl(sql).lower()


def test_ddl_autoincrement_multiline_whitespace():
    sql = "CREATE TABLE t (\n    id   INTEGER\tPRIMARY  KEY\n    AUTOINCREMENT,\n    x TEXT\n)"
    out = translate_ddl(sql)
    assert "SERIAL PRIMARY KEY" in out
    assert "AUTOINCREMENT" not in out.upper()


def test_ddl_multiple_tables_all_translated():
    sql = (
        "CREATE TABLE a (id INTEGER PRIMARY KEY AUTOINCREMENT);"
        "CREATE TABLE b (id INTEGER PRIMARY KEY AUTOINCREMENT)"
    )
    assert translate_ddl(sql).upper().count("SERIAL PRIMARY KEY") == 2
    assert "AUTOINCREMENT" not in translate_ddl(sql).upper()


def test_ddl_no_autoincrement_unchanged():
    # DML/Statements ohne AUTOINCREMENT bleiben unverändert (kein Risiko für DML)
    sql = "SELECT * FROM users WHERE id = ?"
    assert translate_ddl(sql) == sql
    sql2 = "CREATE TABLE jobs (job_id TEXT PRIMARY KEY, total INTEGER DEFAULT 0)"
    assert translate_ddl(sql2) == sql2


def test_ddl_bare_autoincrement_removed():
    # Defensive: AUTOINCREMENT in anderer Konstellation wird entfernt
    out = translate_ddl("CREATE TABLE t (id BIGINT AUTOINCREMENT)")
    assert "AUTOINCREMENT" not in out.upper()


# ---------------------------------------------------------------------------
# PRAGMA table_info(...) Erkennung
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("sql,table", [
    ("PRAGMA table_info(users)", "users"),
    ("  pragma table_info( jobs )", "jobs"),
    ('PRAGMA table_info("invoices")', "invoices"),
    ("PRAGMA table_info(users);", "users"),
])
def test_pragma_table_info_regex_matches(sql, table):
    m = _PRAGMA_TABLE_INFO_RE.match(sql)
    assert m is not None
    assert m.group("table") == table


def test_pragma_other_not_matched():
    assert _PRAGMA_TABLE_INFO_RE.match("PRAGMA foreign_keys = ON") is None


# ---------------------------------------------------------------------------
# DML-Übersetzung: INSERT OR IGNORE → ON CONFLICT DO NOTHING
# ---------------------------------------------------------------------------
def test_dml_insert_or_ignore_translated():
    out = translate_dml("INSERT OR IGNORE INTO roles (name) VALUES (?)")
    assert out == "INSERT INTO roles (name) VALUES (?) ON CONFLICT DO NOTHING"


def test_dml_insert_or_ignore_case_and_whitespace():
    out = translate_dml("  insert   or   ignore   into t (a) values (?);")
    assert out.strip().lower().startswith("insert into t")
    assert out.rstrip().lower().endswith("on conflict do nothing")
    assert "or ignore" not in out.lower()


def test_dml_plain_insert_unchanged():
    sql = "INSERT INTO roles (name) VALUES (?)"
    assert translate_dml(sql) == sql


def test_dml_insert_or_replace_left_untouched():
    # REPLACE ist NICHT generisch übersetzbar (Konflikt-Ziel unbekannt) → unverändert
    sql = "INSERT OR REPLACE INTO t (a) VALUES (?)"
    assert translate_dml(sql) == sql


# ---------------------------------------------------------------------------
# Integrationstest gegen eine ECHTE PostgreSQL-Instanz.
# Läuft nur, wenn TEST_DATABASE_URL gesetzt ist (sonst übersprungen → CI-sicher).
# Verifiziert: init_database() legt auf Postgres alle Tabellen fehlerfrei an
# (AUTOINCREMENT→SERIAL und PRAGMA table_info-Übersetzung greifen).
# ---------------------------------------------------------------------------
_PG_URL = os.environ.get("TEST_DATABASE_URL")

_EXPECTED_TABLES = {"jobs", "invoices", "users", "export_history", "subscriptions"}


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt (echte Postgres-Instanz nötig)")
def test_init_database_on_real_postgres():
    psycopg = pytest.importorskip("psycopg")

    # Sauberes Schema (frischer Zustand wie Fresh-Install)
    with psycopg.connect(_PG_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.commit()

    # init_database() in frischem Subprozess (kein Modul-State-Leak), DATABASE_URL → PG
    env = dict(os.environ, DATABASE_URL=_PG_URL)
    proc = subprocess.run(
        [sys.executable, "-c", "import database; database.init_database()"],
        env=env, capture_output=True, text=True, cwd=os.getcwd(),
    )
    assert proc.returncode == 0, f"init_database crashte auf Postgres:\nSTDERR:\n{proc.stderr}"
    # Kein AUTOINCREMENT-Syntaxfehler in der Ausgabe
    assert "AUTOINCREMENT" not in (proc.stderr + proc.stdout)

    # Tabellen wurden tatsächlich angelegt
    with psycopg.connect(_PG_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public'"
            )
            tables = {r[0] for r in cur.fetchall()}
            # SERIAL-PK statt AUTOINCREMENT: users.id muss eine Sequence-Default haben
            cur.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='id'"
            )
            id_default = cur.fetchone()[0]

    missing = _EXPECTED_TABLES - tables
    assert not missing, f"Fehlende Tabellen nach init_database(): {missing}"
    assert id_default and "nextval" in id_default, f"users.id ist kein SERIAL: {id_default!r}"


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt (echte Postgres-Instanz nötig)")
def test_user_read_works_on_boolean_is_admin():
    """Login-Bug: _user_dict-Query darf auf Postgres NICHT an boolean is_admin
    scheitern. Roh-Read + Python-bool() funktioniert für boolean UND integer."""
    psycopg = pytest.importorskip("psycopg")
    import db_compat as dbc

    def _pg_conn():
        return dbc.PgConnection(psycopg.connect(_PG_URL, row_factory=dbc._hybrid_row_factory))

    for col_type, true_val in (("boolean", "TRUE"), ("integer", "1")):
        with _pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("DROP TABLE IF EXISTS users_bool_t")
            cur.execute(f"CREATE TABLE users_bool_t (id SERIAL PRIMARY KEY, email TEXT, is_admin {col_type})")
            cur.execute(f"INSERT INTO users_bool_t (email, is_admin) VALUES (?, {true_val})", ("a@b.de",))
            conn.commit()
            # Exakt das Muster aus api_frontend._user_dict (ohne COALESCE):
            cur.execute("SELECT id, email, is_admin FROM users_bool_t WHERE email = ?", ("a@b.de",))
            row = cur.fetchone()
            assert row is not None
            assert bool(row[2]) is True, f"is_admin ({col_type}) nicht als True gelesen"

            # COALESCE(is_admin, 0) läuft jetzt für boolean UND integer durch:
            # der generische Boolean-Translator castet boolean-Spalten zu INTEGER.
            cur2 = conn.cursor()
            cur2.execute("SELECT COALESCE(is_admin, 0) FROM users_bool_t")
            assert int(cur2.fetchone()[0]) == 1, f"COALESCE(is_admin,0) für {col_type} fehlgeschlagen"


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt (echte Postgres-Instanz nötig)")
def test_insert_or_ignore_on_postgres():
    """INSERT OR IGNORE → ON CONFLICT DO NOTHING: Duplikat wird ignoriert, kein Fehler."""
    psycopg = pytest.importorskip("psycopg")
    import db_compat as dbc

    with dbc.PgConnection(psycopg.connect(_PG_URL, row_factory=dbc._hybrid_row_factory)) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS roles_t")
        cur.execute("CREATE TABLE roles_t (id SERIAL PRIMARY KEY, name TEXT UNIQUE)")
        cur.execute("INSERT OR IGNORE INTO roles_t (name) VALUES (?)", ("admin",))
        cur.execute("INSERT OR IGNORE INTO roles_t (name) VALUES (?)", ("admin",))  # Konflikt → no-op
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM roles_t")
        assert cur.fetchone()[0] == 1


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt (echte Postgres-Instanz nötig)")
def test_insert_or_ignore_on_table_without_id_column():
    """Regression (PR-Review): INSERT OR IGNORE darf auf Tabellen OHNE id-Spalte
    (PK z. B. job_id) NICHT an der RETURNING-id-Emulation scheitern."""
    psycopg = pytest.importorskip("psycopg")
    import db_compat as dbc

    with dbc.PgConnection(psycopg.connect(_PG_URL, row_factory=dbc._hybrid_row_factory)) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS jobs_t")
        cur.execute("CREATE TABLE jobs_t (job_id TEXT PRIMARY KEY, status TEXT)")
        cur.execute("INSERT OR IGNORE INTO jobs_t (job_id, status) VALUES (?, ?)", ("J1", "new"))
        cur.execute("INSERT OR IGNORE INTO jobs_t (job_id, status) VALUES (?, ?)", ("J1", "dup"))  # Konflikt
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM jobs_t")
        assert cur.fetchone()[0] == 1
        assert cur.lastrowid is None  # keine id-Emulation für ON CONFLICT DO NOTHING


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt (echte Postgres-Instanz nötig)")
def test_date_timestamp_columns_returned_as_iso_strings():
    """date/timestamp-Spalten werden als ISO-Strings geliefert (SQLite-kompatibel),
    nicht als date/datetime-Objekte → Bestandscode wie last_date[:10] funktioniert."""
    pytest.importorskip("psycopg")

    with _force(_PG_URL) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS dt_t")
        cur.execute("CREATE TABLE dt_t (id SERIAL PRIMARY KEY, d date, ts timestamp)")
        cur.execute("INSERT INTO dt_t (d, ts) VALUES (?, ?)", ("2026-01-15", "2026-01-15 09:00:00"))
        conn.commit()
        cur.execute("SELECT d, ts FROM dt_t")
        d, ts = cur.fetchone()
        assert isinstance(d, str) and d[:10] == "2026-01-15"
        assert isinstance(ts, str) and ts[:10] == "2026-01-15"


def _force(url):
    """PG-Verbindung mit String-Datums-Loadern, unabhängig von DATABASE_URL."""
    import psycopg
    import db_compat as dbc
    raw = psycopg.connect(url, row_factory=dbc._hybrid_row_factory)
    dbc._register_text_datetime_loaders(raw)
    return dbc.PgConnection(raw)


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt (echte Postgres-Instanz nötig)")
def test_dashboard_and_supplier_reads_on_timestamp_schema(monkeypatch):
    """Reproduktion Produktion (Neon): KPI-/Lieferanten-Reads dürfen NICHT an
    SQLite-Datumsfunktionen / date-Objekten scheitern, wenn die Spalten echte
    date/timestamp-Typen sind. Erwartet: Ergebnisse mit Daten, kein Crash."""
    psycopg = pytest.importorskip("psycopg")
    monkeypatch.setenv("DATABASE_URL", _PG_URL)  # get_connection() → Postgres

    # Minimal-Schema im Neon-Stil: date/timestamp-typisierte Spalten
    with psycopg.connect(_PG_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS invoices CASCADE; DROP TABLE IF EXISTS jobs CASCADE;")
            cur.execute("CREATE TABLE jobs (job_id TEXT PRIMARY KEY, created_at timestamp, user_id integer)")
            cur.execute("""CREATE TABLE invoices (
                id SERIAL PRIMARY KEY, job_id TEXT, rechnungsnummer TEXT,
                datum date, rechnungsaussteller TEXT, betrag_brutto real,
                betrag_netto real, mwst_betrag real, waehrung TEXT,
                created_at timestamp, status TEXT, deleted integer DEFAULT 0,
                manual_correction integer DEFAULT 0)""")
            cur.execute("INSERT INTO jobs VALUES ('J1', '2026-06-01 10:00:00', 1)")
            for i in range(17):
                d = f"2026-{(i % 6) + 1:02d}-15"
                cur.execute(
                    "INSERT INTO invoices (job_id,rechnungsnummer,datum,rechnungsaussteller,"
                    "betrag_brutto,betrag_netto,mwst_betrag,waehrung,created_at,status) "
                    "VALUES ('J1',%s,%s,%s,%s,%s,16,'EUR',%s,'approved')",
                    (f"RE-{i:03d}", d, ["Alpha", "Beta", "Gamma"][i % 3], 100.0 + i, 84.0 + i, d + " 09:00:00"),
                )
        conn.commit()

    import importlib
    import enterprise_dashboard, supplier_overview
    importlib.reload(enterprise_dashboard)
    importlib.reload(supplier_overview)

    kpis = enterprise_dashboard.get_kpis(1)
    assert kpis["total_invoices"] == 17
    assert len(kpis["trend"]) == 30          # get_trend: substr(CAST(... AS TEXT),..) ok

    suppliers = supplier_overview.get_suppliers(1)
    assert len(suppliers) == 3
    assert all(isinstance(s["last_date"], str) for s in suppliers)  # date-Objekt[:10] gefixt


# ===========================================================================
# Postgres-Kompatibilitäts-Sweep
# ===========================================================================
@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt")
def test_plain_insert_into_idless_table_no_crash():
    """Write-500-Fix: plain INSERT in Tabelle ohne id-Spalte (job_id-PK) darf
    NICHT an der RETURNING-id-Emulation scheitern."""
    pytest.importorskip("psycopg")
    with _force(_PG_URL) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS jobs_w")
        cur.execute("CREATE TABLE jobs_w (job_id TEXT PRIMARY KEY, status TEXT)")
        cur.execute("INSERT INTO jobs_w (job_id, status) VALUES (?, ?)", ("J1", "new"))
        conn.commit()
        assert cur.lastrowid is None
        cur.execute("SELECT COUNT(*) FROM jobs_w")
        assert cur.fetchone()[0] == 1
        # Tabelle MIT id liefert weiterhin lastrowid
        cur.execute("DROP TABLE IF EXISTS with_id")
        cur.execute("CREATE TABLE with_id (id SERIAL PRIMARY KEY, name TEXT)")
        cur.execute("INSERT INTO with_id (name) VALUES (?)", ("x",))
        assert cur.lastrowid == 1


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt")
def test_insert_or_replace_on_pk_unique_and_no_constraint():
    """INSERT OR REPLACE → ON CONFLICT: PK-Ziel, UNIQUE-Ziel, und Fallback ohne
    Constraint (kein Crash)."""
    pytest.importorskip("psycopg")
    with _force(_PG_URL) as conn:
        cur = conn.cursor()
        # PK-Ziel
        cur.execute("DROP TABLE IF EXISTS rj")
        cur.execute("CREATE TABLE rj (job_id TEXT PRIMARY KEY, status TEXT)")
        cur.execute("INSERT OR REPLACE INTO rj (job_id, status) VALUES (?, ?)", ("J", "a"))
        cur.execute("INSERT OR REPLACE INTO rj (job_id, status) VALUES (?, ?)", ("J", "b"))
        conn.commit()
        cur.execute("SELECT status FROM rj WHERE job_id='J'")
        assert cur.fetchone()[0] == "b"
        cur.execute("SELECT COUNT(*) FROM rj"); assert cur.fetchone()[0] == 1
        # UNIQUE-Ziel (PK id, aber Konflikt auf UNIQUE supplier)
        cur.execute("DROP TABLE IF EXISTS rsp")
        cur.execute("CREATE TABLE rsp (id SERIAL PRIMARY KEY, supplier TEXT UNIQUE, cnt INTEGER)")
        cur.execute("INSERT OR REPLACE INTO rsp (supplier, cnt) VALUES (?, ?)", ("ACME", 1))
        cur.execute("INSERT OR REPLACE INTO rsp (supplier, cnt) VALUES (?, ?)", ("ACME", 9))
        conn.commit()
        cur.execute("SELECT cnt FROM rsp WHERE supplier='ACME'"); assert cur.fetchone()[0] == 9
        cur.execute("SELECT COUNT(*) FROM rsp"); assert cur.fetchone()[0] == 1
        # Fallback: keine Constraint → reiner INSERT, kein Crash
        cur.execute("DROP TABLE IF EXISTS rnoc")
        cur.execute("CREATE TABLE rnoc (a TEXT, b TEXT)")
        cur.execute("INSERT OR REPLACE INTO rnoc (a, b) VALUES (?, ?)", ("x", "y"))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM rnoc"); assert cur.fetchone()[0] == 1


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt")
def test_sqlite_datetime_functions_translated():
    """strftime/datetime('now')/date('now') laufen auf Postgres."""
    pytest.importorskip("psycopg")
    with _force(_PG_URL) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS dtf")
        cur.execute("CREATE TABLE dtf (id SERIAL PRIMARY KEY, created_at timestamp, datum date)")
        cur.execute("INSERT INTO dtf (created_at, datum) VALUES ('2026-03-15 09:00:00', '2026-03-15')")
        conn.commit()
        cur.execute("SELECT strftime('%Y-%m', created_at) FROM dtf"); assert cur.fetchone()[0] == "2026-03"
        cur.execute("SELECT strftime('%Y', datum), strftime('%m', datum) FROM dtf")
        y, mo = cur.fetchone(); assert (y, mo) == ("2026", "03")
        # 'now' + Modifikatoren
        cur.execute("SELECT COUNT(*) FROM dtf WHERE created_at >= datetime('now', ?)", ("-100 years",))
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT COUNT(*) FROM dtf WHERE datum >= date('now', '-100 years')")
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT date('now', 'start of month') <= CURRENT_DATE"); assert cur.fetchone()[0] is True


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt")
def test_boolean_is_admin_write_and_read_universal():
    """Boolean-Writes/Reads funktionieren für boolean UND integer is_admin:
    Write als String '1'/'0' (Assignment-Cast), Read via CAST(... AS INTEGER)."""
    pytest.importorskip("psycopg")
    for ctype in ("boolean", "integer"):
        with _force(_PG_URL) as conn:
            cur = conn.cursor()
            cur.execute("DROP TABLE IF EXISTS uadm")
            cur.execute(f"CREATE TABLE uadm (id SERIAL PRIMARY KEY, is_admin {ctype})")
            # Write wie api_nexus: str(int(...))
            cur.execute("INSERT INTO uadm (is_admin) VALUES (?)", (str(int(True)),))
            cur.execute("UPDATE uadm SET is_admin = ? WHERE id = ?", (str(int(False)), 1))
            conn.commit()
            # Read wie api_nexus/approval: CAST(is_admin AS INTEGER) = 1
            cur.execute("SELECT COUNT(*) FROM uadm WHERE CAST(is_admin AS INTEGER) = 1")
            assert cur.fetchone()[0] == 0, f"{ctype}: nach Update auf 0 darf kein Admin matchen"
            cur.execute("UPDATE uadm SET is_admin = ? WHERE id = ?", (str(int(True)), 1))
            conn.commit()
            cur.execute("SELECT COUNT(*) FROM uadm WHERE CAST(is_admin AS INTEGER) = 1")
            assert cur.fetchone()[0] == 1, f"{ctype}: Admin-Read muss matchen"


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt")
def test_named_endpoint_service_paths_on_postgres(monkeypatch):
    """Produktions-Endpoints (DATEV-Export, Audit, Freigaben, Upload/Job-Anlage,
    GoBD-Protokoll) gegen echtes Postgres: keine SQLite-only-500er mehr."""
    psycopg = pytest.importorskip("psycopg")
    monkeypatch.setenv("DATABASE_URL", _PG_URL)
    from datetime import date

    with psycopg.connect(_PG_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.commit()

    import importlib
    import database
    importlib.reload(database)
    database.init_database()
    uid = database.create_user("ep@test.de", "Secret123!", "EP", "ACME")

    with psycopg.connect(_PG_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO jobs (job_id, created_at, status, user_id) VALUES (%s,%s,%s,%s)",
                        ("J1", "2026-06-01T10:00:00", "completed", uid))
            for i in range(5):
                d = f"2026-0{(i % 5) + 1}-15"
                cur.execute(
                    "INSERT INTO invoices (job_id,rechnungsnummer,datum,rechnungsaussteller,"
                    "betrag_brutto,betrag_netto,mwst_betrag,mwst_satz,waehrung,tenant_id,created_at,status,deleted) "
                    "VALUES ('J1',%s,%s,%s,%s,%s,19,19,'EUR',%s,%s,'approved',0)",
                    (f"RE-{i}", d, ["Alpha", "Beta"][i % 2], 119.0 + i, 100.0 + i, uid, d + "T09:00:00"),
                )
        conn.commit()

    import api_frontend, approval_workflow, audit_events, gobd
    for mod in (api_frontend, approval_workflow, audit_events, gobd):
        importlib.reload(mod)

    # Freigaben + Audit (Reads mit Datums-/Filter-SQL)
    assert isinstance(approval_workflow.get_open_approvals(uid), list)
    assert audit_events.count_events(uid) >= 0
    assert isinstance(audit_events.query_events(uid, limit=10, offset=0), list)
    assert "zeitstempel" in audit_events.export_csv(uid)

    # Upload/Job-Anlage: save_job nutzt INSERT OR REPLACE INTO jobs (job_id-PK)
    database.save_job("J1", {"created_at": "2026-06-02T10:00:00", "status": "processing",
                             "total_files": 1, "upload_path": "/tmp"}, user_id=uid)
    audit_events.log_event(uid, audit_events.AuditEvent.UPLOAD, user_id=uid,
                           entity_type="job", entity_id="J1", details={"files": 1})

    # DATEV-Export: Read + CSV-Erzeugung + GoBD-Protokoll (RETURNING id)
    invoices = [i for i in api_frontend._tenant_invoices(uid, None) if i.get("betrag_brutto") is not None]
    assert len(invoices) == 5
    from datev import DatevExportConfig, Kontenrahmen, export_invoices_to_datev_csv
    cfg = DatevExportConfig(berater_nummer="1000", mandanten_nummer=str(uid),
                            wirtschaftsjahr_beginn=date(2026, 1, 1), kontenrahmen=Kontenrahmen.SKR03)
    import tempfile, os
    p = os.path.join(tempfile.gettempdir(), f"extf_{uid}.csv")
    export_invoices_to_datev_csv(invoices, cfg, p)
    assert os.path.getsize(p) > 0
    rec = gobd.record_export(uid, "datev", b"x;y", file_name="x.csv", row_count=5, user_id=uid)
    assert rec and rec.get("id")


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt")
def test_mixed_type_created_at_coalesce(monkeypatch):
    """Produktions-500: invoices.created_at (timestamp) und jobs.created_at (text)
    haben auf Neon UNTERSCHIEDLICHE Typen → COALESCE(i.created_at, j.created_at)
    wirft DatatypeMismatch. Fix: beide Operanden CAST(... AS TEXT). Erwartet:
    KPI-/Lieferanten-/Invoices-Reads liefern Daten, kein Crash."""
    psycopg = pytest.importorskip("psycopg")
    monkeypatch.setenv("DATABASE_URL", _PG_URL)

    with psycopg.connect(_PG_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.commit()
    import importlib, database
    importlib.reload(database)
    database.init_database()
    uid = database.create_user("mix@test.de", "Secret123!", "M", "ACME")

    with psycopg.connect(_PG_URL) as conn:
        with conn.cursor() as cur:
            # Typ-Mismatch erzeugen: invoices.created_at → timestamp, jobs.created_at bleibt text
            cur.execute("ALTER TABLE invoices ALTER COLUMN created_at TYPE timestamp USING created_at::timestamp")
            cur.execute("INSERT INTO jobs (job_id,created_at,status,user_id) VALUES ('J1','2026-06-01T10:00:00','completed',%s)", (uid,))
            for i in range(6):
                d = f"2026-0{(i % 6) + 1}-15"
                cur.execute(
                    "INSERT INTO invoices (job_id,rechnungsnummer,datum,rechnungsaussteller,"
                    "betrag_brutto,betrag_netto,mwst_betrag,waehrung,tenant_id,created_at,status,deleted) "
                    "VALUES ('J1',%s,%s,%s,%s,%s,16,'EUR',%s,%s,'approved',0)",
                    (f"RE-{i}", d, ["Alpha", "Beta", "Gamma"][i % 3], 119.0 + i, 100.0 + i, uid, d + " 09:00:00"),
                )
        conn.commit()

    import enterprise_dashboard, supplier_overview
    importlib.reload(enterprise_dashboard); importlib.reload(supplier_overview)

    kpis = enterprise_dashboard.get_kpis(uid)          # _count_since + get_trend (COALESCE)
    assert kpis["total_invoices"] == 6
    assert len(kpis["trend"]) == 30                     # get_trend lief (COALESCE-Mismatch gefixt)
    suppliers = supplier_overview.get_suppliers(uid)    # _fetch_invoices COALESCE
    assert len(suppliers) == 3
    assert all(isinstance(s["last_date"], str) for s in suppliers)


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt")
def test_boolean_columns_generic_coalesce_compare_write():
    """Generisch: boolean-Spalten (introspektiert) werden in COALESCE/Vergleich/
    Zuweisung typkonsistent gemacht. Numerische Spalten bleiben unberührt; auf
    integer-Spalten (Fresh-Install) findet KEIN Rewrite statt."""
    psycopg = pytest.importorskip("psycopg")
    import db_compat as dbc

    with _force(_PG_URL) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS bcol")
        cur.execute("CREATE TABLE bcol (id SERIAL PRIMARY KEY, deleted boolean DEFAULT FALSE, "
                    "betrag real, is_active boolean DEFAULT TRUE)")
        conn.commit()
        raw = cur._cur
        # 1) COALESCE(<bool>, <int>) → CAST AS INTEGER
        assert "CAST(deleted AS INTEGER)" in dbc.translate_boolean_ops(raw, "SELECT COALESCE(deleted, 0) FROM bcol")
        # 2) Vergleich
        assert "CAST(b.is_active AS INTEGER) = 1" in dbc.translate_boolean_ops(raw, "SELECT 1 FROM bcol b WHERE b.is_active = 1")
        # 3) Write: SET <bool> = <int> → CAST(<int> AS BOOLEAN)
        assert "CAST(1 AS BOOLEAN)" in dbc.translate_boolean_ops(raw, "UPDATE bcol SET deleted = 1 WHERE id = 5")
        # 4) Numerische Spalte unberührt
        assert dbc.translate_boolean_ops(raw, "SELECT COALESCE(betrag, 0) FROM bcol") == "SELECT COALESCE(betrag, 0) FROM bcol"

        # End-to-End: COALESCE-Filter + Write + Vergleich gegen echte boolean-Spalten
        cur.execute("INSERT INTO bcol (betrag) VALUES (?)", (100.0,))   # deleted default FALSE
        cur.execute("INSERT INTO bcol (betrag) VALUES (?)", (200.0,))
        conn.commit()
        cur.execute("UPDATE bcol SET deleted = 1 WHERE id = ?", (2,))   # Write boolean
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM bcol WHERE COALESCE(deleted, 0) = 0")  # read filter
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT COUNT(*) FROM bcol WHERE is_active = 1")    # bare compare
        assert cur.fetchone()[0] == 2


@pytest.mark.skipif(not _PG_URL, reason="TEST_DATABASE_URL nicht gesetzt")
def test_boolean_deleted_endpoints(monkeypatch):
    """/api/app/invoices (inkl. ?status & ?limit=500), /lieferanten, /dashboard/kpis
    liefern 200 + Daten, wenn invoices.deleted auf Postgres boolean ist."""
    psycopg = pytest.importorskip("psycopg")
    monkeypatch.setenv("DATABASE_URL", _PG_URL)
    with psycopg.connect(_PG_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.commit()
    import importlib, database
    importlib.reload(database); database.init_database()
    uid = database.create_user("bep@test.de", "Secret123!", "B", "ACME")
    with psycopg.connect(_PG_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE invoices ALTER COLUMN deleted DROP DEFAULT")
            cur.execute("ALTER TABLE invoices ALTER COLUMN deleted TYPE boolean USING (COALESCE(deleted,0)<>0)")
            cur.execute("ALTER TABLE invoices ALTER COLUMN deleted SET DEFAULT FALSE")
            cur.execute("INSERT INTO jobs (job_id,created_at,status,user_id) VALUES ('J1','2026-06-15T10:00:00','completed',%s)", (uid,))
            for i in range(6):
                d = f"2026-06-{10 + i:02d}"
                cur.execute(
                    "INSERT INTO invoices (job_id,rechnungsnummer,datum,rechnungsaussteller,betrag_brutto,"
                    "betrag_netto,mwst_betrag,waehrung,tenant_id,created_at,status) "
                    "VALUES ('J1',%s,%s,%s,%s,%s,19,'EUR',%s,%s,'verarbeitet')",
                    (f"RE-{i}", d, ["Alpha", "Beta"][i % 2], 119.0 + i, 100.0 + i, uid, d + " 09:00:00"),
                )
        conn.commit()

    from fastapi.testclient import TestClient
    import web.app as wa, api_frontend
    monkeypatch.setattr(api_frontend, "_require_tenant", lambda r: uid)
    from shared_auth import create_sso_token
    cl = TestClient(wa.app, raise_server_exceptions=False)
    h = {"Authorization": f"Bearer {create_sso_token(uid, 'bep@test.de', 'B')}"}
    for p in ["/api/app/invoices", "/api/app/invoices?status=verarbeitet",
              "/api/app/invoices?limit=500", "/api/app/lieferanten", "/api/app/dashboard/kpis"]:
        r = cl.get(p, headers=h)
        assert r.status_code == 200, f"{p} -> {r.status_code}: {r.text[:200]}"
    assert cl.get("/api/app/invoices", headers=h).json()["total"] == 6
