"""Read-only PostgreSQL schema compatibility checks for the legacy app runtime.

The production runtime treats numeric user identifiers as a security boundary:
``users.id`` is INTEGER/SERIAL and the user/tenant references in ``jobs`` and
``subscriptions`` are INTEGER.  An already-existing PostgreSQL database with a
text/UUID user-id domain must therefore not be auto-repaired or partially used.

This module performs metadata-only introspection.  It never alters schema or
rows and never includes row values in errors/log output.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


EXPECTED_USER_ID_TYPE = "integer"
_REFERENCE_COLUMNS = (
    ("jobs", "user_id"),
    ("subscriptions", "user_id"),
)
_POSTGRES_PREFIXES = ("postgres://", "postgresql://")


@dataclass(frozen=True)
class SchemaFinding:
    table: str
    column: str
    expected: str
    actual: str
    status: str

    def as_dict(self) -> dict[str, str]:
        return {
            "table": self.table,
            "column": self.column,
            "expected": self.expected,
            "actual": self.actual,
            "status": self.status,
        }


class PostgresSchemaCompatibilityError(RuntimeError):
    """Fail-closed signal for an incompatible existing PostgreSQL schema."""

    def __init__(self, code: str, findings: list[SchemaFinding]):
        self.code = code
        self.findings = tuple(findings)
        safe_summary = ", ".join(
            f"{f.table}.{f.column}: expected={f.expected}, actual={f.actual}"
            for f in findings
        )
        super().__init__(f"{code}: {safe_summary}" if safe_summary else code)


def _table_exists(cur: Any, table: str) -> bool:
    cur.execute(
        "SELECT EXISTS ("
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = %s"
        ")",
        (table,),
    )
    row = cur.fetchone()
    return bool(row and row[0])


def _column_type(cur: Any, table: str, column: str) -> str | None:
    cur.execute(
        "SELECT data_type::text "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s",
        (table, column),
    )
    row = cur.fetchone()
    return str(row[0]).lower() if row and row[0] is not None else None


def _primary_key_columns(cur: Any, table: str) -> list[str]:
    cur.execute(
        "SELECT kcu.column_name::text "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON tc.constraint_name = kcu.constraint_name "
        " AND tc.constraint_schema = kcu.constraint_schema "
        " AND tc.table_name = kcu.table_name "
        "WHERE tc.table_schema = 'public' "
        "  AND tc.table_name = %s "
        "  AND tc.constraint_type = 'PRIMARY KEY' "
        "ORDER BY kcu.ordinal_position",
        (table,),
    )
    return [str(row[0]) for row in cur.fetchall()]


def assess_postgres_schema(connection: Any) -> dict[str, Any]:
    """Return a metadata-only compatibility assessment for an existing schema.

    A completely fresh database (no ``users`` table yet) is allowed so the
    canonical initializer can create it.  Once ``users`` exists, ``users.id``
    must be an INTEGER primary key and any already-existing canonical
    references must use the same INTEGER domain.
    """
    findings: list[SchemaFinding] = []
    with connection.cursor() as cur:
        if not _table_exists(cur, "users"):
            return {"status": "fresh", "compatible": True, "findings": []}

        user_id_type = _column_type(cur, "users", "id")
        if user_id_type != EXPECTED_USER_ID_TYPE:
            findings.append(
                SchemaFinding(
                    "users",
                    "id",
                    EXPECTED_USER_ID_TYPE,
                    user_id_type or "missing",
                    "incompatible",
                )
            )

        pk_columns = _primary_key_columns(cur, "users")
        if pk_columns != ["id"]:
            findings.append(
                SchemaFinding(
                    "users",
                    "id",
                    "single-column primary key",
                    ",".join(pk_columns) if pk_columns else "missing",
                    "incompatible",
                )
            )

        for table, column in _REFERENCE_COLUMNS:
            if not _table_exists(cur, table):
                continue
            actual = _column_type(cur, table, column)
            if actual is None:
                findings.append(
                    SchemaFinding(table, column, EXPECTED_USER_ID_TYPE, "missing", "incompatible")
                )
            elif actual != EXPECTED_USER_ID_TYPE:
                findings.append(
                    SchemaFinding(table, column, EXPECTED_USER_ID_TYPE, actual, "incompatible")
                )

    return {
        "status": "incompatible" if findings else "compatible",
        "compatible": not findings,
        "findings": [finding.as_dict() for finding in findings],
    }


def validate_postgres_schema(connection: Any) -> dict[str, Any]:
    """Raise before application DDL/data access when an existing schema drifts."""
    assessment = assess_postgres_schema(connection)
    if assessment["compatible"]:
        return assessment

    findings = [SchemaFinding(**item) for item in assessment["findings"]]
    has_user_domain_mismatch = any(
        finding.table == "users"
        and finding.column == "id"
        and finding.expected == EXPECTED_USER_ID_TYPE
        for finding in findings
    )
    code = "USER_ID_DOMAIN_MISMATCH" if has_user_domain_mismatch else "POSTGRES_SCHEMA_INCOMPATIBLE"
    raise PostgresSchemaCompatibilityError(code, findings)


def validate_configured_postgres_schema() -> dict[str, Any]:
    """Validate ``DATABASE_URL`` target read-only; no-op for SQLite/unconfigured.

    This function intentionally connects with psycopg directly instead of the
    compatibility wrapper so the guard cannot recurse through normal runtime
    connection creation.
    """
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url or not url.startswith(_POSTGRES_PREFIXES):
        return {"status": "not_configured", "compatible": True, "findings": []}

    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - production dependency contract
        raise RuntimeError("POSTGRES_SCHEMA_GUARD_PSYCOPG_UNAVAILABLE") from exc

    with psycopg.connect(url) as connection:
        with connection.transaction():
            with connection.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
            return validate_postgres_schema(connection)
