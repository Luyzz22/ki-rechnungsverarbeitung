from __future__ import annotations

import pytest

from postgres_schema_guard import (
    PostgresSchemaCompatibilityError,
    assess_postgres_schema,
    validate_postgres_schema,
)


class FakeCursor:
    def __init__(self, *, tables=None, column_types=None, primary_keys=None):
        self.tables = set(tables or set())
        self.column_types = dict(column_types or {})
        self.primary_keys = dict(primary_keys or {})
        self._one = None
        self._all = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(str(sql).split()).lower()
        if "information_schema.tables" in normalized:
            table = params[0]
            self._one = (table in self.tables,)
            self._all = []
            return
        if "information_schema.columns" in normalized:
            table, column = params
            value = self.column_types.get((table, column))
            self._one = (value,) if value is not None else None
            self._all = []
            return
        if "information_schema.table_constraints" in normalized:
            table = params[0]
            self._all = [(name,) for name in self.primary_keys.get(table, [])]
            self._one = self._all[0] if self._all else None
            return
        raise AssertionError(f"unexpected SQL in schema guard test: {sql}")

    def fetchone(self):
        return self._one

    def fetchall(self):
        return list(self._all)


class FakeConnection:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def cursor(self):
        return FakeCursor(**self.kwargs)


def canonical_connection():
    return FakeConnection(
        tables={"users", "jobs", "subscriptions"},
        column_types={
            ("users", "id"): "integer",
            ("jobs", "user_id"): "integer",
            ("subscriptions", "user_id"): "integer",
        },
        primary_keys={"users": ["id"]},
    )


def test_fresh_database_is_allowed_without_schema_mutation():
    result = assess_postgres_schema(FakeConnection())
    assert result == {"status": "fresh", "compatible": True, "findings": []}


def test_canonical_numeric_user_domain_is_compatible():
    result = validate_postgres_schema(canonical_connection())
    assert result["status"] == "compatible"
    assert result["compatible"] is True
    assert result["findings"] == []


def test_text_users_id_fails_closed_with_metadata_only_error():
    conn = FakeConnection(
        tables={"users", "jobs", "subscriptions"},
        column_types={
            ("users", "id"): "text",
            ("jobs", "user_id"): "integer",
            ("subscriptions", "user_id"): "integer",
        },
        primary_keys={"users": ["id"]},
    )

    with pytest.raises(PostgresSchemaCompatibilityError) as exc_info:
        validate_postgres_schema(conn)

    exc = exc_info.value
    assert exc.code == "USER_ID_DOMAIN_MISMATCH"
    assert any(f.table == "users" and f.actual == "text" for f in exc.findings)
    assert "users.id" in str(exc)
    assert "expected=integer" in str(exc)
    assert "actual=text" in str(exc)


def test_reference_domain_mismatch_fails_closed():
    conn = FakeConnection(
        tables={"users", "jobs", "subscriptions"},
        column_types={
            ("users", "id"): "integer",
            ("jobs", "user_id"): "text",
            ("subscriptions", "user_id"): "integer",
        },
        primary_keys={"users": ["id"]},
    )

    with pytest.raises(PostgresSchemaCompatibilityError) as exc_info:
        validate_postgres_schema(conn)

    assert any(
        f.table == "jobs" and f.column == "user_id" and f.actual == "text"
        for f in exc_info.value.findings
    )


def test_users_id_must_be_the_single_primary_key_column():
    conn = FakeConnection(
        tables={"users"},
        column_types={("users", "id"): "integer"},
        primary_keys={"users": []},
    )

    with pytest.raises(PostgresSchemaCompatibilityError) as exc_info:
        validate_postgres_schema(conn)

    assert any(
        f.table == "users"
        and f.column == "id"
        and f.expected == "single-column primary key"
        and f.actual == "missing"
        for f in exc_info.value.findings
    )


def test_missing_reference_column_is_incompatible_when_table_exists():
    conn = FakeConnection(
        tables={"users", "subscriptions"},
        column_types={("users", "id"): "integer"},
        primary_keys={"users": ["id"]},
    )

    with pytest.raises(PostgresSchemaCompatibilityError) as exc_info:
        validate_postgres_schema(conn)

    assert any(
        f.table == "subscriptions" and f.column == "user_id" and f.actual == "missing"
        for f in exc_info.value.findings
    )
