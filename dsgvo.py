#!/usr/bin/env python3
"""
SBS Deutschland – DSGVO (Phase 5c)

- Löschkonzept: konfigurierbare Aufbewahrungsfristen pro Tenant (Default 10 Jahre)
- Geplante Bereinigung: abgelaufene Daten werden (GoBD-konform) soft-gelöscht
- Recht auf Auskunft: alle Daten eines Users als JSON
- Recht auf Löschung: Anonymisierung (kein physisches Löschen wegen GoBD)

Hinweis: Es werden keine personenbezogenen Daten in Logs geschrieben – nur IDs.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from database import get_connection
from enterprise_db import get_retention_years

logger = logging.getLogger(__name__)

# Spalten in users, die KEINE PII zurückgeben sollen
_USER_SENSITIVE = {"password_hash", "totp_secret", "reset_token"}


def _table_columns(cursor, table: str) -> List[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def get_auskunft(user_id: int) -> Dict[str, Any]:
    """Recht auf Auskunft (Art. 15 DSGVO): alle Daten eines Users als JSON.

    Tenant-Isolation: ``user_id`` ist gleichzeitig die Tenant-ID.
    """
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cursor = conn.cursor()

    # Userdaten (ohne Geheimnisse)
    cursor.execute("SELECT * FROM users WHERE id = ?", (int(user_id),))
    user_row = cursor.fetchone() or {}
    user = {k: v for k, v in user_row.items() if k not in _USER_SENSITIVE}

    # Jobs
    cursor.execute("SELECT * FROM jobs WHERE user_id = ?", (int(user_id),))
    jobs = cursor.fetchall()

    # Rechnungen (über jobs)
    cursor.execute(
        """
        SELECT i.* FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        WHERE j.user_id = ?
        """,
        (int(user_id),),
    )
    invoices = cursor.fetchall()

    # Audit-Events
    audit_events: List[Dict[str, Any]] = []
    try:
        cursor.execute(
            "SELECT * FROM audit_events WHERE tenant_id = ? OR user_id = ? ORDER BY created_at",
            (int(user_id), int(user_id)),
        )
        audit_events = cursor.fetchall()
    except Exception:  # pragma: no cover
        pass

    conn.close()
    logger.info("DSGVO Auskunft erstellt für user_id=%s", user_id)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "user_id": int(user_id),
        "user": user,
        "jobs": jobs,
        "invoices": invoices,
        "audit_events": audit_events,
        "hinweis": "Rechnungen unterliegen der gesetzlichen Aufbewahrungspflicht (GoBD).",
    }


def anonymize_user(user_id: int, performed_by: Optional[int] = None) -> Dict[str, Any]:
    """Recht auf Löschung (Art. 17 DSGVO) als Anonymisierung.

    Personenbezogene Daten des Users werden unkenntlich gemacht. Rechnungen
    bleiben aus GoBD-Gründen erhalten, werden aber als anonymisiert markiert.
    """
    conn = get_connection()
    cursor = conn.cursor()

    user_cols = _table_columns(cursor, "users")
    updates: List[str] = []
    params: List[Any] = []
    placeholder_email = f"anonym-{int(user_id)}@geloescht.invalid"
    if "name" in user_cols:
        updates.append("name = ?")
        params.append("Anonymisiert")
    if "email" in user_cols:
        updates.append("email = ?")
        params.append(placeholder_email)
    if "company" in user_cols:
        updates.append("company = ?")
        params.append(None)
    if "oauth_email" in user_cols:
        updates.append("oauth_email = ?")
        params.append(None)
    if "is_active" in user_cols:
        updates.append("is_active = 0")

    if updates:
        params.append(int(user_id))
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)

    # Rechnungen als anonymisiert markieren (Aufbewahrung bleibt bestehen)
    cursor.execute(
        """
        UPDATE invoices SET anonymized = 1
        WHERE job_id IN (SELECT job_id FROM jobs WHERE user_id = ?)
        """,
        (int(user_id),),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    _audit(user_id, "anonymisierung", performed_by, "user", user_id,
           {"invoices_marked": affected})
    logger.info("DSGVO Anonymisierung durchgeführt für user_id=%s", user_id)
    return {"ok": True, "user_id": int(user_id), "invoices_marked": affected,
            "hinweis": "Anonymisiert – physisches Löschen aufgrund GoBD-Aufbewahrung unterbleibt."}


def run_retention_cleanup(tenant_id: Optional[int] = None) -> Dict[str, Any]:
    """Geplanter Task: markiert abgelaufene Rechnungen als soft-gelöscht.

    Aufbewahrungsfrist pro Tenant (Default 10 Jahre). Aufgrund GoBD erfolgt
    keine physische Löschung, sondern eine markierte Soft-Löschung.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if tenant_id is not None:
        tenant_ids = [int(tenant_id)]
    else:
        cursor.execute("SELECT DISTINCT user_id FROM jobs WHERE user_id IS NOT NULL")
        tenant_ids = [int(r[0]) for r in cursor.fetchall()]

    total_marked = 0
    today = date.today()
    for tid in tenant_ids:
        years = get_retention_years(tid)
        try:
            cutoff = today.replace(year=today.year - years).isoformat()
        except ValueError:  # 29.02. → 28.02.
            cutoff = today.replace(year=today.year - years, day=28).isoformat()

        cursor.execute(
            """
            UPDATE invoices
            SET deleted = 1,
                deleted_reason = COALESCE(deleted_reason, 'Aufbewahrungsfrist abgelaufen (DSGVO)')
            WHERE COALESCE(deleted, 0) = 0
              AND job_id IN (SELECT job_id FROM jobs WHERE user_id = ?)
              AND COALESCE(CAST(datum AS TEXT), substr(CAST(created_at AS TEXT), 1, 10)) < ?
            """,
            (tid, cutoff),
        )
        total_marked += cursor.rowcount

    conn.commit()
    conn.close()
    logger.info("DSGVO Retention-Cleanup: %s Rechnungen markiert", total_marked)
    return {"tenants_processed": len(tenant_ids), "invoices_marked": total_marked}


def _audit(tenant_id, action, user_id, entity_type, entity_id, details) -> None:
    try:
        from audit_events import log_event

        log_event(tenant_id, action, user_id=user_id, entity_type=entity_type,
                  entity_id=entity_id, details=details)
    except Exception as exc:  # pragma: no cover
        logger.debug("dsgvo: audit skip: %s", exc)
