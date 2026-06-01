#!/usr/bin/env python3
"""
SBS Deutschland – Frontend-JSON-API für die Next.js-SPA (belegflow-ai.de)

Eigenständige, JSON-basierte API unter dem Präfix ``/api/app`` für das
cross-domain Single-Page-Frontend. Da die SPA auf einer anderen Domain läuft
(belegflow-ai.de ≠ .sbsdeutschland.com), funktionieren Session-Cookies nicht
zuverlässig → Authentifizierung per **JWT Bearer-Token** (Fallback: Session).

Alle Endpunkte sind tenant-isoliert (tenant_id = user_id) und nutzen die
bestehende Service-Schicht (enterprise_dashboard, supplier_overview,
approval_workflow, audit_events).

Endpunkte:
  POST /api/app/login                  → {token, user}
  POST /api/app/register               → {token, user}
  GET  /api/app/me                     → {user}
  GET  /api/app/dashboard/kpis         → KPIs
  GET  /api/app/invoices               → Liste (Filter: status, q, limit, offset)
  GET  /api/app/invoices/{id}          → Detail
  GET  /api/app/lieferanten            → Lieferantenübersicht (sort)
  GET  /api/app/freigaben              → offene Freigaben
  POST /api/app/freigaben/{id}/approve → genehmigen
  POST /api/app/freigaben/{id}/reject  → ablehnen
  GET  /api/app/audit                  → Audit-Trail (paginiert)
  GET  /api/app/audit/export.csv       → Audit-CSV
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

import approval_workflow
import audit_events
from database import get_connection
from enterprise_dashboard import get_kpis
from supplier_overview import get_supplier_detail, get_suppliers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/app", tags=["Frontend-API"])

_PW_MIN = 8


# ---------------------------------------------------------------------------
# Auth-Helfer (Bearer-Token, Fallback Session)
# ---------------------------------------------------------------------------
def _tenant_from_request(request: Request) -> Optional[int]:
    # 1) Authorization: Bearer <jwt>
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from shared_auth import verify_sso_token

            payload = verify_sso_token(auth[7:].strip())
            if payload and payload.get("user_id") is not None:
                return int(payload["user_id"])
        except Exception:  # pragma: no cover - defensive
            pass
    # 2) Session-Fallback (gleiche Domain)
    try:
        uid = request.session.get("user_id")
        if uid is not None:
            return int(uid)
    except Exception:
        pass
    return None


def _require_tenant(request: Request) -> int:
    tid = _tenant_from_request(request)
    if not tid:
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    return tid


def _user_dict(user_id: int) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email, name, company, COALESCE(is_admin, 0) FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"id": user_id}
    return {"id": row[0], "email": row[1], "name": row[2], "company": row[3], "is_admin": bool(row[4])}


def _issue_token(user_id: int, email: str, name: str = None) -> str:
    from shared_auth import create_sso_token

    return create_sso_token(user_id, email, name)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@router.post("/login")
async def api_login(request: Request):
    from database import verify_user

    body = await request.json()
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    if not email or not password:
        raise HTTPException(status_code=400, detail="E-Mail und Passwort erforderlich")

    user = verify_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="E-Mail oder Passwort falsch")

    token = _issue_token(user["id"], user["email"], user.get("name"))
    audit_events.log_event(user["id"], audit_events.AuditEvent.LOGIN, user_id=user["id"])
    return {"token": token, "user": _user_dict(user["id"])}


@router.post("/register")
async def api_register(request: Request):
    from database import create_user, email_exists

    body = await request.json()
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    name = (body.get("name") or "").strip()
    company = (body.get("company") or "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="E-Mail und Passwort erforderlich")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Ungültige E-Mail-Adresse")
    if len(password) < _PW_MIN:
        raise HTTPException(status_code=400, detail=f"Passwort muss mindestens {_PW_MIN} Zeichen haben")
    if email_exists(email):
        raise HTTPException(status_code=409, detail="E-Mail bereits registriert")

    user_id = create_user(email, password, name, company)
    token = _issue_token(user_id, email, name)
    audit_events.log_event(user_id, audit_events.AuditEvent.LOGIN, user_id=user_id,
                           details={"registered": True})
    return JSONResponse(status_code=201, content={"token": token, "user": _user_dict(user_id)})


@router.get("/me")
async def api_me(request: Request):
    tid = _require_tenant(request)
    return {"user": _user_dict(tid)}


# ---------------------------------------------------------------------------
# Dashboard / Lieferanten
# ---------------------------------------------------------------------------
@router.get("/dashboard/kpis")
async def api_kpis(request: Request):
    return get_kpis(_require_tenant(request))


@router.get("/lieferanten")
async def api_lieferanten(request: Request, sort: str = "volumen"):
    return {"suppliers": get_suppliers(_require_tenant(request), sort_by=sort)}


@router.get("/lieferanten/{supplier}")
async def api_lieferant_detail(request: Request, supplier: str):
    return get_supplier_detail(_require_tenant(request), supplier)


# ---------------------------------------------------------------------------
# Rechnungen
# ---------------------------------------------------------------------------
@router.get("/invoices")
async def api_invoices(request: Request, status: str = "", q: str = "",
                       limit: int = 50, offset: int = 0):
    tid = _require_tenant(request)
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    where = ["j.user_id = ?", "COALESCE(i.deleted, 0) = 0"]
    params: list[Any] = [tid]
    if status:
        where.append("i.status = ?")
        params.append(status)
    if q:
        where.append("(i.rechnungsaussteller LIKE ? OR i.rechnungsnummer LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    where_sql = " AND ".join(where)

    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) AS n FROM invoices i JOIN jobs j ON i.job_id = j.job_id WHERE {where_sql}", params)
    total = cur.fetchone()["n"]
    cur.execute(
        f"""
        SELECT i.id, i.rechnungsnummer, i.datum, i.rechnungsaussteller,
               i.betrag_brutto, i.betrag_netto, i.mwst_betrag, i.waehrung,
               COALESCE(i.status, 'neu') AS status,
               COALESCE(i.created_at, j.created_at) AS created_at
        FROM invoices i JOIN jobs j ON i.job_id = j.job_id
        WHERE {where_sql}
        ORDER BY created_at DESC, i.id DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    )
    items = cur.fetchall()
    conn.close()
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/invoices/{invoice_id}")
async def api_invoice_detail(request: Request, invoice_id: int):
    tid = _require_tenant(request)
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cur = conn.cursor()
    cur.execute(
        """
        SELECT i.* FROM invoices i JOIN jobs j ON i.job_id = j.job_id
        WHERE i.id = ? AND j.user_id = ?
        """,
        (invoice_id, tid),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    return row


# ---------------------------------------------------------------------------
# Freigaben
# ---------------------------------------------------------------------------
@router.get("/freigaben")
async def api_freigaben(request: Request):
    tid = _require_tenant(request)
    approval_workflow.check_escalations(tid)
    return {"items": approval_workflow.get_open_approvals(tid)}


@router.post("/freigaben/{request_id}/approve")
async def api_freigabe_approve(request: Request, request_id: int):
    tid = _require_tenant(request)
    comment = None
    try:
        body = await request.json()
        comment = body.get("comment")
    except Exception:
        pass
    result = approval_workflow.approve(tid, request_id, tid, comment=comment, notify=False)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Freigabe fehlgeschlagen"))
    return result


@router.post("/freigaben/{request_id}/reject")
async def api_freigabe_reject(request: Request, request_id: int):
    tid = _require_tenant(request)
    comment = None
    try:
        body = await request.json()
        comment = body.get("comment")
    except Exception:
        pass
    result = approval_workflow.reject(tid, request_id, tid, comment=comment)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Ablehnung fehlgeschlagen"))
    return result


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
@router.get("/audit")
async def api_audit(request: Request, action: str = "", date_from: str = "",
                    date_to: str = "", limit: int = 50, offset: int = 0):
    tid = _require_tenant(request)
    limit = max(1, min(int(limit), 500))
    filters = {"action": action or None, "date_from": date_from or None, "date_to": date_to or None}
    total = audit_events.count_events(tid, **filters)
    items = audit_events.query_events(tid, limit=limit, offset=max(0, int(offset)), **filters)
    return {"total": total, "limit": limit, "offset": offset,
            "actions": audit_events.KNOWN_ACTIONS, "items": items}


@router.get("/audit/export.csv")
async def api_audit_csv(request: Request, action: str = "", date_from: str = "", date_to: str = ""):
    tid = _require_tenant(request)
    csv_data = audit_events.export_csv(tid, action=action or None,
                                       date_from=date_from or None, date_to=date_to or None)
    return Response(content=csv_data, media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="audit_trail.csv"'})
