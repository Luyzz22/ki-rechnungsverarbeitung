#!/usr/bin/env python3
"""Read-only assessment for a PostgreSQL user-id domain migration.

The report intentionally emits schema metadata and aggregate counts only.  It
never prints user IDs, tenant IDs, emails, URLs, credentials, or row samples.
It does not alter schema/data and must not be used as an automatic migration.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from postgres_schema_guard import assess_postgres_schema

_INT32_MIN = -2147483648
_INT32_MAX = 2147483647


def _scalar(cur: Any, sql: str, params=()) -> int:
    cur.execute(sql, params)
    row = cur.fetchone()
    return int(row[0] or 0) if row else 0


def _table_exists(cur: Any, table: str) -> bool:
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=%s)",
        (table,),
    )
    row = cur.fetchone()
    return bool(row and row[0])


def _column_type(cur: Any, table: str, column: str) -> str | None:
    cur.execute(
        "SELECT data_type::text FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=%s AND column_name=%s",
        (table, column),
    )
    row = cur.fetchone()
    return str(row[0]).lower() if row else None


def build_report(connection: Any) -> dict[str, Any]:
    schema = assess_postgres_schema(connection)
    report: dict[str, Any] = {
        "schema": schema,
        "aggregates": {},
        "automatic_migration_permitted": False,
    }

    with connection.cursor() as cur:
        if not _table_exists(cur, "users"):
            report["aggregates"]["users"] = {"row_count": 0}
            return report

        users_type = _column_type(cur, "users", "id")
        users = {"row_count": _scalar(cur, "SELECT COUNT(*) FROM users")}

        if users_type in {"text", "character varying", "character"}:
            numeric_predicate = "id ~ '^[+-]?[0-9]+$'"
            users["non_decimal_id_count"] = _scalar(
                cur,
                f"SELECT COUNT(*) FROM users WHERE id IS NULL OR NOT ({numeric_predicate})",
            )
            users["out_of_int32_range_count"] = _scalar(
                cur,
                "SELECT COUNT(*) FROM users "
                f"WHERE {numeric_predicate} "
                "AND (id::numeric < %s OR id::numeric > %s)",
                (_INT32_MIN, _INT32_MAX),
            )
            users["numeric_collision_group_count"] = _scalar(
                cur,
                "SELECT COUNT(*) FROM ("
                "  SELECT id::numeric AS numeric_id "
                "  FROM users "
                f"  WHERE {numeric_predicate} "
                "  GROUP BY id::numeric "
                "  HAVING COUNT(*) > 1"
                ") collisions",
            )
        report["aggregates"]["users"] = users

        for table in ("jobs", "subscriptions"):
            if not _table_exists(cur, table):
                continue
            if _column_type(cur, table, "user_id") is None:
                continue
            report["aggregates"][table] = {
                "row_count": _scalar(cur, f"SELECT COUNT(*) FROM {table}"),
                "orphan_user_reference_count": _scalar(
                    cur,
                    f"SELECT COUNT(*) FROM {table} child "
                    "LEFT JOIN users u ON child.user_id::text = u.id::text "
                    "WHERE child.user_id IS NOT NULL AND u.id IS NULL",
                ),
            }

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only PostgreSQL user-id migration assessment"
    )
    parser.add_argument("--target", default=os.getenv("DATABASE_URL"))
    args = parser.parse_args()

    if not args.target:
        print("FEHLER: --target bzw. DATABASE_URL erforderlich", file=sys.stderr)
        return 2

    try:
        import psycopg
    except ImportError:
        print("FEHLER: psycopg nicht installiert", file=sys.stderr)
        return 2

    with psycopg.connect(args.target) as connection:
        with connection.transaction():
            with connection.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
            report = build_report(connection)

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["schema"]["compatible"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
