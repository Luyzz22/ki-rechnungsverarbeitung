#!/usr/bin/env python3
"""
SBS Deutschland – Enterprise Schema & Tenant Context (Phase 4 + 5)

Zentrale Stelle für:
- Alle neuen DB-Tabellen (Phase 4 UI + Phase 5 GoBD/Audit/DSGVO)
- Tenant-Isolation Helfer

Hinweis zur Tenant-Isolation:
Die SQLite-Hauptanwendung isoliert Daten historisch über ``jobs.user_id``
(Rechnungen via JOIN). In diesem Datenmodell entspricht ein Benutzer genau
einem Mandanten. Neue Tabellen erhalten daher – wie in den Vorgaben gefordert –
eine eigene ``tenant_id``-Spalte (+ Index), die mit der ``user_id`` des
aktuell angemeldeten Benutzers befüllt wird.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from database import get_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tenant-Kontext
# ---------------------------------------------------------------------------
def get_tenant_id(request) -> Optional[int]:
    """Ermittelt die Tenant-ID (= user_id) aus der Session.

    Returns:
        Tenant-ID als int oder None, wenn nicht angemeldet.
    """
    try:
        user_id = request.session.get("user_id")
    except Exception:  # pragma: no cover - defensive
        user_id = None
    if user_id is None:
        return None
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Schema-Helfer
# ---------------------------------------------------------------------------
def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _ensure_column(cursor, table: str, column: str, ddl: str) -> None:
    """Fügt eine Spalte hinzu, falls sie noch nicht existiert (idempotent)."""
    try:
        if not _column_exists(cursor, table, column):
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            logger.info("enterprise_db: Spalte %s.%s ergänzt", table, column)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("enterprise_db: Spalte %s.%s konnte nicht ergänzt werden: %s", table, column, exc)


def init_enterprise_schema() -> None:
    """Legt alle Enterprise-Tabellen an und ergänzt benötigte Spalten.

    Idempotent – kann bei jedem Start aufgerufen werden.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # --- Phase 4b: Freigabe-Workflow -------------------------------------
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            threshold REAL NOT NULL,
            role TEXT NOT NULL,
            stage_order INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            invoice_id INTEGER NOT NULL,
            user_id INTEGER,
            action TEXT NOT NULL,
            stage INTEGER,
            comment TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            invoice_id INTEGER NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            current_stage INTEGER NOT NULL DEFAULT 0,
            required_role TEXT,
            status TEXT NOT NULL DEFAULT 'offen',
            escalated INTEGER NOT NULL DEFAULT 0,
            escalated_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --- Phase 5b: Audit-Trail Enterprise (append-only) ------------------
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            details_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --- Phase 5a: GoBD Export-Protokoll ---------------------------------
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS export_protocol (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            user_id INTEGER,
            export_type TEXT NOT NULL,
            file_name TEXT,
            sha256 TEXT NOT NULL,
            byte_size INTEGER,
            row_count INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --- Phase 5a: GoBD Soft-Delete Protokoll ----------------------------
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS invoice_deletions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            invoice_id INTEGER NOT NULL,
            user_id INTEGER,
            reason TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --- Phase 5c: DSGVO Aufbewahrungsfristen pro Tenant -----------------
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS retention_policies (
            tenant_id INTEGER PRIMARY KEY,
            retention_years INTEGER NOT NULL DEFAULT 10,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --- Indizes (tenant_id) ---------------------------------------------
    for table in (
        "approval_rules",
        "approval_log",
        "approval_requests",
        "audit_events",
        "export_protocol",
        "invoice_deletions",
    ):
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_tenant_id ON {table}(tenant_id)"
        )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_approval_requests_status ON approval_requests(tenant_id, status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_events_created ON audit_events(tenant_id, created_at)"
    )

    # --- Zusatzspalten auf invoices (GoBD / Tenant) ----------------------
    # Die Basistabelle ``invoices`` kennt diese Spalten teils nicht; wir
    # ergänzen sie idempotent, damit Enterprise-Features auch auf einer
    # frischen DB (CI/Tests) funktionieren.
    # Tenant-Isolation der Hauptanwendung hängt an jobs.user_id
    _ensure_column(cursor, "jobs", "user_id", "INTEGER")
    _ensure_column(cursor, "invoices", "tenant_id", "INTEGER")
    _ensure_column(cursor, "invoices", "status", "TEXT")
    _ensure_column(cursor, "invoices", "created_at", "TEXT")
    _ensure_column(cursor, "invoices", "gobd_locked", "INTEGER DEFAULT 0")
    _ensure_column(cursor, "invoices", "deleted", "INTEGER DEFAULT 0")
    _ensure_column(cursor, "invoices", "deleted_reason", "TEXT")
    _ensure_column(cursor, "invoices", "anonymized", "INTEGER DEFAULT 0")
    _ensure_column(cursor, "invoices", "manual_correction", "INTEGER DEFAULT 0")

    conn.commit()
    conn.close()
    logger.info("enterprise_db: Schema initialisiert")


def get_retention_years(tenant_id: int) -> int:
    """Liefert die konfigurierte Aufbewahrungsfrist (Default 10 Jahre, GoBD)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT retention_years FROM retention_policies WHERE tenant_id = ?",
        (tenant_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return int(row[0])
    return 10


def set_retention_years(tenant_id: int, years: int) -> None:
    """Setzt die Aufbewahrungsfrist für einen Tenant."""
    years = max(1, int(years))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO retention_policies (tenant_id, retention_years, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(tenant_id) DO UPDATE SET
            retention_years = excluded.retention_years,
            updated_at = excluded.updated_at
        """,
        (tenant_id, years, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    init_enterprise_schema()
    print("Enterprise-Schema initialisiert.")
