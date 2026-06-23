"""Unit-Tests der SQLite↔PostgreSQL-Kompatibilitätsschicht (ohne psycopg/Neon)."""

import os
import subprocess
import sys

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

            # Gegenprobe: das alte COALESCE(is_admin, 0) bricht je nach Typ
            with pytest.raises(psycopg.errors.DatatypeMismatch):
                cur2 = conn.cursor()
                lit = "0" if col_type == "boolean" else "FALSE"
                cur2.execute(f"SELECT COALESCE(is_admin, {lit}) FROM users_bool_t")
                cur2.fetchone()
            conn.rollback()


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
