"""Unit-Tests der SQLite↔PostgreSQL-Kompatibilitätsschicht (ohne psycopg/Neon)."""

from db_compat import HybridRow, is_postgres, translate_placeholders


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
