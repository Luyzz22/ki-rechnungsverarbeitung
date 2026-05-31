#!/usr/bin/env python3
"""
SBS Deutschland – Audit-Trail Enterprise (Phase 5b)

Append-only Audit-Log (``audit_events``). Es gibt bewusst KEINE Update-/
Delete-Funktionen – Einträge sind unveränderbar (GoBD/Revisionssicherheit).

Geloggte Aktionen (Auswahl): upload, ki_extraktion, validierung, freigabe,
ablehnung, export, login, logout, einstellungen_geaendert.

Aufbewahrung: 10 Jahre Standard (GoBD).
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import get_connection

logger = logging.getLogger(__name__)


class AuditEvent:
    """Standardisierte Aktionsnamen für den Enterprise-Audit-Trail."""

    UPLOAD = "upload"
    KI_EXTRAKTION = "ki_extraktion"
    VALIDIERUNG = "validierung"
    FREIGABE = "freigabe"
    ABLEHNUNG = "ablehnung"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    EINSTELLUNGEN_GEAENDERT = "einstellungen_geaendert"
    LOESCHUNG = "loeschung"
    ANONYMISIERUNG = "anonymisierung"
    GOBD_LOCK = "gobd_lock"
    AUSKUNFT = "auskunft"


# Aktionen für Dropdown-Filter in der UI
KNOWN_ACTIONS = [
    AuditEvent.UPLOAD,
    AuditEvent.KI_EXTRAKTION,
    AuditEvent.VALIDIERUNG,
    AuditEvent.FREIGABE,
    AuditEvent.ABLEHNUNG,
    AuditEvent.EXPORT,
    AuditEvent.LOGIN,
    AuditEvent.LOGOUT,
    AuditEvent.EINSTELLUNGEN_GEAENDERT,
    AuditEvent.LOESCHUNG,
    AuditEvent.ANONYMISIERUNG,
    AuditEvent.GOBD_LOCK,
    AuditEvent.AUSKUNFT,
]


def log_event(
    tenant_id: int,
    action: str,
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[Any] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Schreibt ein Audit-Event (append-only).

    Wichtig (DSGVO): ``details`` darf KEINE personenbezogenen Daten oder
    Rechnungsinhalte (Beträge, Rechnungsnummern) enthalten – nur IDs und
    technische Metadaten.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit_events
                (tenant_id, user_id, action, entity_type, entity_id, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(tenant_id),
                user_id,
                action,
                entity_type,
                str(entity_id) if entity_id is not None else None,
                json.dumps(details, ensure_ascii=False) if details else None,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as exc:  # pragma: no cover - logging darf nie crashen
        logger.error("audit_events.log_event Fehler: %s", exc)


def query_events(
    tenant_id: int,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Durchsucht den Audit-Trail (immer tenant-isoliert)."""
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cursor = conn.cursor()

    query = "SELECT * FROM audit_events WHERE tenant_id = ?"
    params: List[Any] = [int(tenant_id)]

    if action:
        query += " AND action = ?"
        params.append(action)
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        # bis einschließlich Tagesende
        query += " AND created_at <= ?"
        params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)

    query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([int(limit), int(offset)])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def count_events(
    tenant_id: int,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> int:
    """Zählt Treffer (für Pagination)."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT COUNT(*) FROM audit_events WHERE tenant_id = ?"
    params: List[Any] = [int(tenant_id)]
    if action:
        query += " AND action = ?"
        params.append(action)
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        params.append(date_to + "T23:59:59" if len(date_to) == 10 else date_to)

    cursor.execute(query, params)
    total = cursor.fetchone()[0]
    conn.close()
    return int(total or 0)


def export_csv(
    tenant_id: int,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """Exportiert den (gefilterten) Audit-Trail als CSV-String (Betriebsprüfung)."""
    rows = query_events(
        tenant_id,
        action=action,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        limit=1_000_000,
        offset=0,
    )
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        ["id", "zeitstempel", "user_id", "aktion", "entitaet", "entitaet_id", "details"]
    )
    for r in rows:
        writer.writerow(
            [
                r.get("id"),
                r.get("created_at"),
                r.get("user_id"),
                r.get("action"),
                r.get("entity_type"),
                r.get("entity_id"),
                r.get("details_json") or "",
            ]
        )
    return output.getvalue()
