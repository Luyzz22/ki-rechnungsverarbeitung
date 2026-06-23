#!/usr/bin/env python3
"""
SBS Deutschland – Datenmigration SQLite → PostgreSQL (Neon)

Kopiert Schema (best-effort) und Daten aus der SQLite-DB in eine PostgreSQL-
Datenbank (z. B. Neon, Frankfurt).

Voraussetzungen:
  - psycopg installiert (``pip install 'psycopg[binary]'``)
  - Ziel-DB erreichbar über ``DATABASE_URL`` (oder ``--target``)

Aufruf:
  python scripts/migrate_sqlite_to_postgres.py \
      --source /var/www/invoice-app/invoices.db \
      --target "$DATABASE_URL" [--create-schema] [--dry-run]

Hinweis: Die DDL-Übersetzung ist best-effort (AUTOINCREMENT→SERIAL etc.) und
sollte vor dem Produktiv-Cutover geprüft werden (siehe docs/POSTGRES_MIGRATION.md).
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys

# Reihenfolge: Eltern vor Kindern (FK-frei genug für IF-NOT-EXISTS Inserts)
PREFERRED_ORDER = [
    "users", "roles", "user_roles", "jobs", "invoices",
    "freigabe_rules", "freigabe_log", "freigabe_requests",
    "approval_rules", "approval_history", "approval_delegations",
    "audit_events", "export_history", "export_protocol",
    "invoice_deletions", "retention_policies", "zahlungsbedingungen",
    "spend_alerts",
]

SKIP_TABLES = {"sqlite_sequence"}


def sqlite_tables(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    names = [r[0] for r in rows if r[0] not in SKIP_TABLES]
    ordered = [t for t in PREFERRED_ORDER if t in names]
    ordered += [t for t in names if t not in ordered]
    return ordered


def translate_ddl(sql: str) -> str:
    """Best-effort: SQLite-CREATE-TABLE → PostgreSQL."""
    s = sql
    s = re.sub(r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", "SERIAL PRIMARY KEY", s, flags=re.I)
    s = re.sub(r"\bAUTOINCREMENT\b", "", s, flags=re.I)
    s = re.sub(r"\bDATETIME\b", "TIMESTAMP", s, flags=re.I)
    s = s.replace("CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP")
    # SQLite akzeptiert TEXT/REAL/INTEGER – die kennt PG ebenfalls.
    return s


def create_schema(sqlite_con, pg_cur, tables):
    for t in tables:
        ddl_row = sqlite_con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone()
        if not ddl_row or not ddl_row[0]:
            continue
        ddl = translate_ddl(ddl_row[0])
        ddl = re.sub(r"CREATE TABLE", "CREATE TABLE IF NOT EXISTS", ddl, count=1, flags=re.I)
        print(f"  [schema] {t}")
        pg_cur.execute(ddl)


def copy_table(sqlite_con, pg_cur, table, dry_run=False) -> int:
    cols = [r[1] for r in sqlite_con.execute(f"PRAGMA table_info({table})").fetchall()]
    if not cols:
        return 0
    rows = sqlite_con.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
    if not rows:
        return 0
    collist = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO {table} ({collist}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    if dry_run:
        return len(rows)
    pg_cur.executemany(sql, [tuple(r) for r in rows])
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="SQLite → PostgreSQL Migration")
    ap.add_argument("--source", default=os.getenv("INVOICE_DB_PATH", "/var/www/invoice-app/invoices.db"))
    ap.add_argument("--target", default=os.getenv("DATABASE_URL"))
    ap.add_argument("--create-schema", action="store_true", help="Tabellen im Ziel anlegen (best-effort)")
    ap.add_argument("--dry-run", action="store_true", help="Nur zählen, nicht schreiben")
    args = ap.parse_args()

    if not args.target:
        print("FEHLER: --target bzw. DATABASE_URL erforderlich", file=sys.stderr)
        return 2

    try:
        import psycopg
    except ImportError:
        print("FEHLER: psycopg nicht installiert (pip install 'psycopg[binary]')", file=sys.stderr)
        return 2

    sqlite_con = sqlite3.connect(args.source)
    tables = sqlite_tables(sqlite_con)
    print(f"Quelle: {args.source}\nTabellen: {len(tables)}")

    pg = psycopg.connect(args.target)
    try:
        with pg.cursor() as cur:
            if args.create_schema:
                print("Schema anlegen (best-effort)…")
                create_schema(sqlite_con, cur, tables)
            total = 0
            for t in tables:
                n = copy_table(sqlite_con, cur, t, dry_run=args.dry_run)
                total += n
                print(f"  [data] {t}: {n} Zeilen")
        if not args.dry_run:
            pg.commit()
        print(f"Fertig. {'(dry-run) ' if args.dry_run else ''}Gesamt: {total} Zeilen")
    finally:
        pg.close()
        sqlite_con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
