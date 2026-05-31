#!/usr/bin/env python3
"""
SBS Deutschland – GoBD-Konformität (Phase 5a)

- Unveränderbarkeit: verarbeitete Rechnungen werden read-only (``gobd_locked``)
- Kein physisches DELETE auf verarbeiteten Rechnungen – nur Soft-Delete mit Grund
- Export-Protokoll: SHA-256-Hash pro Export-Datei, Zeitstempel, User

Tenant-Isolation über ``jobs.user_id`` (Rechnungen) bzw. ``tenant_id`` (Protokolle).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import get_connection

logger = logging.getLogger(__name__)


class GoBDError(Exception):
    """Verstoß gegen GoBD-Regeln (z.B. Löschversuch einer gesperrten Rechnung)."""


def compute_sha256(data: bytes | str) -> str:
    """Berechnet den SHA-256-Hash (hex) von Bytes oder String."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _invoice_belongs_to_tenant(cursor, tenant_id: int, invoice_id: int) -> bool:
    cursor.execute(
        """
        SELECT 1 FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        WHERE i.id = ? AND j.user_id = ?
        """,
        (int(invoice_id), int(tenant_id)),
    )
    return cursor.fetchone() is not None


def is_locked(invoice_id: int) -> bool:
    """Prüft, ob eine Rechnung GoBD-gesperrt (read-only) ist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(gobd_locked, 0) FROM invoices WHERE id = ?", (int(invoice_id),))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row[0])


def lock_invoice(tenant_id: int, invoice_id: int, user_id: Optional[int] = None) -> bool:
    """Setzt eine (verarbeitete) Rechnung auf read-only (Unveränderbarkeit)."""
    conn = get_connection()
    cursor = conn.cursor()
    if not _invoice_belongs_to_tenant(cursor, tenant_id, invoice_id):
        conn.close()
        raise GoBDError("Rechnung gehört nicht zum Tenant")
    cursor.execute("UPDATE invoices SET gobd_locked = 1 WHERE id = ?", (int(invoice_id),))
    conn.commit()
    conn.close()
    _audit(tenant_id, "gobd_lock", user_id, "invoice", invoice_id, None)
    return True


def soft_delete_invoice(tenant_id: int, invoice_id: int, reason: str,
                        user_id: Optional[int] = None) -> bool:
    """Soft-Delete einer Rechnung MIT Begründung.

    Ein physisches Löschen ist nach GoBD nicht zulässig und wird daher nicht
    angeboten. Ein leerer Grund wird abgelehnt.
    """
    if not reason or not reason.strip():
        raise GoBDError("Soft-Delete erfordert eine Begründung (GoBD)")

    conn = get_connection()
    cursor = conn.cursor()
    if not _invoice_belongs_to_tenant(cursor, tenant_id, invoice_id):
        conn.close()
        raise GoBDError("Rechnung gehört nicht zum Tenant")

    cursor.execute("UPDATE invoices SET deleted = 1, deleted_reason = ? WHERE id = ?",
                   (reason.strip(), int(invoice_id)))
    cursor.execute(
        """
        INSERT INTO invoice_deletions (tenant_id, invoice_id, user_id, reason, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(tenant_id), int(invoice_id), user_id, reason.strip(),
         datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    _audit(tenant_id, "loeschung", user_id, "invoice", invoice_id, {"soft_delete": True})
    return True


def record_export(tenant_id: int, export_type: str, content: bytes | str,
                  file_name: Optional[str] = None, row_count: Optional[int] = None,
                  user_id: Optional[int] = None) -> Dict[str, Any]:
    """Protokolliert einen Export mit SHA-256-Hash, Zeitstempel und User."""
    raw = content.encode("utf-8") if isinstance(content, str) else content
    sha = compute_sha256(raw)
    byte_size = len(raw)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO export_protocol
            (tenant_id, user_id, export_type, file_name, sha256, byte_size, row_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (int(tenant_id), user_id, export_type, file_name, sha, byte_size, row_count,
         datetime.now().isoformat(timespec="seconds")),
    )
    protocol_id = cursor.lastrowid
    conn.commit()
    conn.close()
    _audit(tenant_id, "export", user_id, "export", protocol_id,
           {"export_type": export_type, "sha256": sha, "byte_size": byte_size})
    return {"id": protocol_id, "sha256": sha, "byte_size": byte_size,
            "export_type": export_type, "file_name": file_name}


def get_export_protocol(tenant_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Liefert die Export-Protokolleinträge des Tenants (neueste zuerst)."""
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM export_protocol
        WHERE tenant_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (int(tenant_id), int(limit)),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def _audit(tenant_id, action, user_id, entity_type, entity_id, details) -> None:
    try:
        from audit_events import log_event

        log_event(tenant_id, action, user_id=user_id, entity_type=entity_type,
                  entity_id=entity_id, details=details)
    except Exception as exc:  # pragma: no cover
        logger.debug("gobd: audit skip: %s", exc)
