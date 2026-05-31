#!/usr/bin/env python3
"""
SBS Deutschland – Mehrstufiger Freigabe-Workflow (Phase 4b)

Konfigurierbare, mehrstufige Freigabe nach Betragsgrenzen (pro Tenant):
    <1.000€   → Sachbearbeiter
    <10.000€  → Teamleiter
    >10.000€  → Geschäftsführung

Eine Rechnung durchläuft kumulativ alle Stufen bis zur zuständigen Ebene:
z.B. 15.000€ → Sachbearbeiter → Teamleiter → Geschäftsführung.

Tabellen (siehe enterprise_db):
- freigabe_rules     (tenant_id, threshold, role, stage_order)
- freigabe_log       (invoice_id, user_id, action, timestamp)
- freigabe_requests  (Status/Stufen-Tracking)

Eskalation: Freigaben, die > 48h offen sind, werden mit einem Flag markiert
(und optional per E-Mail eskaliert).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import get_connection

logger = logging.getLogger(__name__)

ESCALATION_HOURS = 48
_INF_THRESHOLD = 1_000_000_000_000.0  # "∞" für die oberste Stufe

DEFAULT_RULES = [
    {"threshold": 1000.0, "role": "Sachbearbeiter", "stage_order": 0},
    {"threshold": 10000.0, "role": "Teamleiter", "stage_order": 1},
    {"threshold": _INF_THRESHOLD, "role": "Geschäftsführung", "stage_order": 2},
]


@dataclass
class Rule:
    threshold: float
    role: str
    stage_order: int


# ---------------------------------------------------------------------------
# Regeln
# ---------------------------------------------------------------------------
def ensure_default_rules(tenant_id: int) -> None:
    """Legt Standard-Freigaberegeln an, falls für den Tenant noch keine existieren."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM freigabe_rules WHERE tenant_id = ?", (int(tenant_id),)
    )
    if cursor.fetchone()[0] == 0:
        for r in DEFAULT_RULES:
            cursor.execute(
                """
                INSERT INTO freigabe_rules (tenant_id, threshold, role, stage_order, active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (int(tenant_id), r["threshold"], r["role"], r["stage_order"]),
            )
        conn.commit()
    conn.close()


def get_rules(tenant_id: int) -> List[Rule]:
    """Liefert die aktiven Freigaberegeln eines Tenants (nach Stufe sortiert)."""
    ensure_default_rules(tenant_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT threshold, role, stage_order
        FROM freigabe_rules
        WHERE tenant_id = ? AND active = 1
        ORDER BY stage_order ASC, threshold ASC
        """,
        (int(tenant_id),),
    )
    rules = [Rule(threshold=float(r[0]), role=r[1], stage_order=int(r[2])) for r in cursor.fetchall()]
    conn.close()
    return rules


def save_rules(tenant_id: int, rules: List[Dict[str, Any]]) -> None:
    """Ersetzt die Freigaberegeln eines Tenants (Konfiguration aus der UI)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM freigabe_rules WHERE tenant_id = ?", (int(tenant_id),))
    for idx, r in enumerate(sorted(rules, key=lambda x: float(x["threshold"]))):
        cursor.execute(
            """
            INSERT INTO freigabe_rules (tenant_id, threshold, role, stage_order, active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (int(tenant_id), float(r["threshold"]), str(r["role"]), idx),
        )
    conn.commit()
    conn.close()


def required_stages(amount: float, rules: List[Rule]) -> List[Rule]:
    """Ermittelt die kumulativ benötigten Freigabestufen für einen Betrag."""
    amount = float(amount or 0)
    stages: List[Rule] = []
    for rule in sorted(rules, key=lambda r: (r.stage_order, r.threshold)):
        stages.append(rule)
        if rule.threshold >= amount:
            break
    return stages


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
def _log(cursor, tenant_id: int, invoice_id: int, user_id: Optional[int],
         action: str, stage: Optional[int], comment: Optional[str]) -> None:
    cursor.execute(
        """
        INSERT INTO freigabe_log (tenant_id, invoice_id, user_id, action, stage, comment, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (int(tenant_id), int(invoice_id), user_id, action, stage, comment,
         datetime.now().isoformat(timespec="seconds")),
    )


def submit_for_approval(tenant_id: int, invoice_id: int, amount: float,
                        user_id: Optional[int] = None, notify: bool = True) -> Dict[str, Any]:
    """Reicht eine Rechnung zur (mehrstufigen) Freigabe ein."""
    rules = get_rules(tenant_id)
    stages = required_stages(amount, rules)
    first_role = stages[0].role if stages else "Sachbearbeiter"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO freigabe_requests
            (tenant_id, invoice_id, amount, current_stage, required_role, status, created_at, updated_at)
        VALUES (?, ?, ?, 0, ?, 'offen', ?, ?)
        """,
        (int(tenant_id), int(invoice_id), float(amount or 0), first_role,
         datetime.now().isoformat(timespec="seconds"),
         datetime.now().isoformat(timespec="seconds")),
    )
    request_id = cursor.lastrowid
    _log(cursor, tenant_id, invoice_id, user_id, "created", 0, None)
    try:
        cursor.execute("UPDATE invoices SET status = 'pending' WHERE id = ?", (int(invoice_id),))
    except Exception:  # pragma: no cover
        pass
    conn.commit()
    conn.close()

    _audit(tenant_id, "freigabe", user_id, "approval_request", request_id,
           {"stage": 0, "stages_required": len(stages)})
    if notify:
        _notify(tenant_id,
                "Neue Freigabeanfrage",
                f"Eine Rechnung (#{invoice_id}) wartet auf Freigabe durch {first_role}.")

    return {"request_id": request_id, "stages": [s.role for s in stages], "required_role": first_role}


def get_open_approvals(tenant_id: int) -> List[Dict[str, Any]]:
    """Liste offener Freigaben inkl. Rechnungs-Eckdaten und Alter/Eskalation."""
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ar.id AS request_id, ar.invoice_id, ar.amount, ar.current_stage,
               ar.required_role, ar.status, ar.escalated, ar.created_at,
               i.rechnungsnummer, i.rechnungsaussteller
        FROM freigabe_requests ar
        LEFT JOIN invoices i ON ar.invoice_id = i.id
        WHERE ar.tenant_id = ? AND ar.status = 'offen'
        ORDER BY ar.created_at ASC
        """,
        (int(tenant_id),),
    )
    rows = cursor.fetchall()
    conn.close()

    now = datetime.now()
    for row in rows:
        age_hours = None
        try:
            age_hours = round((now - datetime.fromisoformat(row["created_at"])).total_seconds() / 3600, 1)
        except (ValueError, TypeError):
            pass
        row["age_hours"] = age_hours
        row["overdue"] = bool(age_hours is not None and age_hours > ESCALATION_HOURS)
    return rows


def _get_request(cursor, tenant_id: int, request_id: int) -> Optional[Dict[str, Any]]:
    cursor.execute(
        "SELECT id, invoice_id, amount, current_stage, status FROM freigabe_requests "
        "WHERE id = ? AND tenant_id = ?",
        (int(request_id), int(tenant_id)),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {"id": row[0], "invoice_id": row[1], "amount": row[2],
            "current_stage": row[3], "status": row[4]}


def approve(tenant_id: int, request_id: int, user_id: int,
            comment: Optional[str] = None, notify: bool = True) -> Dict[str, Any]:
    """Genehmigt die aktuelle Stufe. Sind weitere Stufen nötig, rückt die Freigabe vor."""
    conn = get_connection()
    cursor = conn.cursor()
    req = _get_request(cursor, tenant_id, request_id)
    if not req or req["status"] != "offen":
        conn.close()
        return {"ok": False, "error": "Freigabeanfrage nicht gefunden oder bereits abgeschlossen"}

    rules = get_rules(tenant_id)
    stages = required_stages(req["amount"], rules)
    current = int(req["current_stage"])
    _log(cursor, tenant_id, req["invoice_id"], user_id, "approved", current, comment)

    if current + 1 < len(stages):
        next_role = stages[current + 1].role
        cursor.execute(
            "UPDATE freigabe_requests SET current_stage = ?, required_role = ?, updated_at = ? "
            "WHERE id = ?",
            (current + 1, next_role, datetime.now().isoformat(timespec="seconds"), request_id),
        )
        conn.commit()
        conn.close()
        _audit(tenant_id, "freigabe", user_id, "approval_request", request_id,
               {"stage": current, "advanced_to": current + 1})
        if notify:
            _notify(tenant_id, "Freigabe – nächste Stufe",
                    f"Rechnung #{req['invoice_id']} benötigt nun Freigabe durch {next_role}.")
        return {"ok": True, "status": "offen", "next_role": next_role, "final": False}

    # letzte Stufe genehmigt
    cursor.execute(
        "UPDATE freigabe_requests SET status = 'freigegeben', updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(timespec="seconds"), request_id),
    )
    try:
        cursor.execute(
            "UPDATE invoices SET status = 'approved', gobd_locked = 1 WHERE id = ?",
            (int(req["invoice_id"]),),
        )
    except Exception:  # pragma: no cover
        pass
    conn.commit()
    conn.close()
    _audit(tenant_id, "freigabe", user_id, "approval_request", request_id,
           {"stage": current, "final": True})
    return {"ok": True, "status": "freigegeben", "final": True}


def reject(tenant_id: int, request_id: int, user_id: int,
           comment: Optional[str] = None) -> Dict[str, Any]:
    """Lehnt eine Freigabeanfrage ab."""
    conn = get_connection()
    cursor = conn.cursor()
    req = _get_request(cursor, tenant_id, request_id)
    if not req or req["status"] != "offen":
        conn.close()
        return {"ok": False, "error": "Freigabeanfrage nicht gefunden oder bereits abgeschlossen"}

    _log(cursor, tenant_id, req["invoice_id"], user_id, "rejected", req["current_stage"], comment)
    cursor.execute(
        "UPDATE freigabe_requests SET status = 'abgelehnt', updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(timespec="seconds"), request_id),
    )
    try:
        cursor.execute("UPDATE invoices SET status = 'rejected' WHERE id = ?", (int(req["invoice_id"]),))
    except Exception:  # pragma: no cover
        pass
    conn.commit()
    conn.close()
    _audit(tenant_id, "ablehnung", user_id, "approval_request", request_id, None)
    return {"ok": True, "status": "abgelehnt"}


def check_escalations(tenant_id: Optional[int] = None, notify: bool = False) -> int:
    """Markiert offene Freigaben, die länger als 48h offen sind, als eskaliert.

    Returns:
        Anzahl neu eskalierter Freigaben.
    """
    cutoff = (datetime.now() - timedelta(hours=ESCALATION_HOURS)).isoformat(timespec="seconds")
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cursor = conn.cursor()

    query = (
        "SELECT id, tenant_id, invoice_id, required_role FROM freigabe_requests "
        "WHERE status = 'offen' AND escalated = 0 AND created_at <= ?"
    )
    params: List[Any] = [cutoff]
    if tenant_id is not None:
        query += " AND tenant_id = ?"
        params.append(int(tenant_id))
    cursor.execute(query, params)
    pending = cursor.fetchall()

    for row in pending:
        cursor.execute(
            "UPDATE freigabe_requests SET escalated = 1, escalated_at = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), row["id"]),
        )
        _log(cursor, row["tenant_id"], row["invoice_id"], None, "escalated",
             None, f">{ESCALATION_HOURS}h offen")
    conn.commit()
    conn.close()

    if notify and pending:
        for row in pending:
            _notify(row["tenant_id"], "Eskalation: Freigabe überfällig",
                    f"Freigabe für Rechnung #{row['invoice_id']} ist seit über "
                    f"{ESCALATION_HOURS}h offen ({row['required_role']}).")
    return len(pending)


# ---------------------------------------------------------------------------
# Hilfsfunktionen (Audit + E-Mail), defensiv eingebunden
# ---------------------------------------------------------------------------
def _audit(tenant_id: int, action: str, user_id, entity_type, entity_id, details) -> None:
    try:
        from audit_events import log_event

        log_event(tenant_id, action, user_id=user_id, entity_type=entity_type,
                  entity_id=entity_id, details=details)
    except Exception as exc:  # pragma: no cover
        logger.debug("approval_workflow: audit skip: %s", exc)


def _notify(tenant_id: int, subject: str, body: str) -> None:
    """Sendet eine E-Mail-Benachrichtigung an den Tenant (best effort)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE id = ?", (int(tenant_id),))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            return
        email = row[0]
        try:
            from notifications import send_sendgrid_email

            send_sendgrid_email(email, subject, f"<p>{body}</p>")
        except Exception as exc:  # pragma: no cover - Mailversand optional
            logger.info("approval_workflow: Mailversand übersprungen (%s)", exc)
    except Exception as exc:  # pragma: no cover
        logger.debug("approval_workflow: notify skip: %s", exc)
