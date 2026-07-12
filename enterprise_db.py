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
        CREATE TABLE IF NOT EXISTS freigabe_rules (
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
        CREATE TABLE IF NOT EXISTS freigabe_log (
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
        CREATE TABLE IF NOT EXISTS freigabe_requests (
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
        "freigabe_rules",
        "freigabe_log",
        "freigabe_requests",
        "audit_events",
        "export_protocol",
        "invoice_deletions",
    ):
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_tenant_id ON {table}(tenant_id)"
        )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_freigabe_requests_status ON freigabe_requests(tenant_id, status)"
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

    # --- Legacy-Kompatibilität (Fresh-Install-Robustheit) ----------------
    # Freigabe-/Zahlungs-Spalten auf invoices (von approval.py genutzt)
    _ensure_column(cursor, "invoices", "assigned_to", "INTEGER")
    _ensure_column(cursor, "invoices", "approved_by", "INTEGER")
    _ensure_column(cursor, "invoices", "approved_at", "TEXT")
    _ensure_column(cursor, "invoices", "rejected_by", "INTEGER")
    _ensure_column(cursor, "invoices", "rejected_at", "TEXT")
    _ensure_column(cursor, "invoices", "approval_comment", "TEXT")
    _ensure_column(cursor, "invoices", "payment_status", "TEXT")
    _ensure_column(cursor, "invoices", "paid_at", "TEXT")

    # --- Extraktions-/Duplikat-Spalten (MIG: bisher nur per Code eingefügt, ohne
    #     Startup-Migration → Schema-Drift zwischen Repo und Prod). Idempotent
    #     hier nachgezogen, damit `import web.app` das vollständige Schema anlegt. ---
    _ensure_column(cursor, "invoices", "content_hash", "TEXT")
    _ensure_column(cursor, "invoices", "datei_hash", "TEXT")
    _ensure_column(cursor, "invoices", "datei_pfad", "TEXT")
    _ensure_column(cursor, "invoices", "validierung_json", "TEXT")
    _ensure_column(cursor, "invoices", "kontierung_json", "TEXT")
    _ensure_column(cursor, "invoices", "extraktion_raw", "TEXT")
    _ensure_column(cursor, "invoices", "confidence", "REAL")
    _ensure_column(cursor, "invoices", "source_format", "TEXT")
    _ensure_column(cursor, "invoices", "einvoice_raw_xml", "TEXT")
    _ensure_column(cursor, "invoices", "einvoice_profile", "TEXT")
    _ensure_column(cursor, "invoices", "einvoice_valid", "INTEGER")
    _ensure_column(cursor, "invoices", "einvoice_validation_message", "TEXT")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_invoices_datei_hash ON invoices(tenant_id, datei_hash)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_invoices_content_hash ON invoices(content_hash)"
    )

    # Duplikat-Erkennung (von duplicate_detection.py genutzt, bislang ohne
    # Migration → auf Prod manuell angelegt; hier idempotent nachgezogen).
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS duplicate_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            duplicate_of_id INTEGER,
            detection_method TEXT,
            confidence REAL,
            status TEXT DEFAULT 'pending',
            reviewed_by INTEGER,
            reviewed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_dup_detections_invoice ON duplicate_detections(invoice_id)"
    )

    # Zahlungsbedingungen (von zahlungs_service.py genutzt, sonst nirgends angelegt)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS zahlungsbedingungen (
            invoice_id INTEGER PRIMARY KEY,
            faelligkeit TEXT,
            skonto_prozent REAL,
            skonto_tage INTEGER,
            skonto_datum TEXT,
            skonto_betrag REAL,
            zahlungsziel_tage INTEGER,
            zahlungsstatus TEXT DEFAULT 'offen',
            geplantes_zahldatum TEXT,
            empfehlung TEXT,
            empfehlung_grund TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Legacy-Freigabe-Tabellen (von approval.py genutzt; sonst nirgends angelegt)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER,
            name TEXT,
            min_amount REAL DEFAULT 0,
            max_amount REAL,
            required_role TEXT,
            auto_approve INTEGER DEFAULT 0,
            priority INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            user_id INTEGER,
            action TEXT,
            old_status TEXT,
            new_status TEXT,
            comment TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_delegations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delegator_id INTEGER,
            delegate_id INTEGER,
            is_active INTEGER DEFAULT 1,
            valid_from TEXT,
            valid_until TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _ensure_column(cursor, "users", "approval_limit", "REAL")

    # Spend-Alerts (vom Dashboard abgefragt; sonst nur von spend_analytics angelegt)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS spend_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT UNIQUE,
            alert_type TEXT,
            severity TEXT,
            title TEXT,
            message TEXT,
            data_json TEXT,
            acknowledged INTEGER DEFAULT 0,
            acknowledged_by INTEGER,
            acknowledged_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()

    # Bestandsdaten-Backfill: Datei-Hashes für Alt-Rechnungen ohne Hash (einmalig,
    # idempotent, best effort – füllt nur NULL-Zeilen mit vorhandener Datei).
    try:
        from duplicate_detection import backfill_datei_hashes
        backfill_datei_hashes()
    except Exception as exc:  # pragma: no cover - darf Start nie sprengen
        logger.debug("datei_hash-Backfill übersprungen: %s", exc)

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
