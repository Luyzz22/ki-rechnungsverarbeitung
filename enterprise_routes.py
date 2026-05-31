#!/usr/bin/env python3
"""
SBS Deutschland – Enterprise Routes (Phase 4 + 5)

Bündelt alle UI-Seiten und API-Endpunkte für:
- Phase 4a: Dashboard-KPIs
- Phase 4b: Freigabe-Workflow
- Phase 4c: Lieferanten-Übersicht
- Phase 5a: GoBD (Verfahrensdokumentation, Export-Protokoll, Lock/Soft-Delete)
- Phase 5b: Audit-Trail (durchsuchbar, CSV-Export)
- Phase 5c: DSGVO (Auskunft, Löschung/Anonymisierung, Aufbewahrung)

Alle Seiten sind auth-geschützt (Session) und tenant-isoliert (tenant_id = user_id).
CSRF wird – wie im Bestand – per Session-Token erzwungen.
"""

from __future__ import annotations

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

import approval_workflow
import audit_events
import dsgvo
import gobd
from database import get_connection
from enterprise_dashboard import get_kpis, render_trend_svg
from enterprise_db import get_retention_years, set_retention_years
from supplier_overview import get_supplier_detail, get_suppliers

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


# ---------------------------------------------------------------------------
# Auth / Tenant / CSRF Helfer (konsistent zum Bestand)
# ---------------------------------------------------------------------------
def _tenant_id(request: Request) -> Optional[int]:
    try:
        uid = request.session.get("user_id")
    except Exception:
        return None
    try:
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


def _require_login(request: Request):
    """Gibt None zurück wenn eingeloggt, sonst RedirectResponse auf /login."""
    if _tenant_id(request):
        return None
    next_url = str(request.url.path or "/")
    if request.url.query:
        next_url += "?" + str(request.url.query)
    return RedirectResponse(url=f"/login?next={next_url}", status_code=303)


def _get_user(request: Request) -> dict:
    tid = _tenant_id(request)
    if not tid:
        return {}
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name FROM users WHERE id = ?", (tid,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"id": tid}
    return {"id": row[0], "email": row[1], "name": row[2]}


def _csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def _require_csrf(request: Request, submitted: Optional[str]) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not submitted or not secrets.compare_digest(str(submitted), str(expected)):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def _ctx(request: Request, active_nav: str, **extra) -> dict:
    base = {
        "request": request,
        "user": _get_user(request),
        "active_nav": active_nav,
        "csrf_token": _csrf_token(request),
    }
    base.update(extra)
    return base


# ===========================================================================
# Phase 4a – Dashboard KPIs
# ===========================================================================
@router.get("/dashboard/enterprise", response_class=HTMLResponse)
async def dashboard_enterprise(request: Request):
    redirect = _require_login(request)
    if redirect:
        return redirect
    tid = _tenant_id(request)
    kpis = get_kpis(tid)
    trend_svg = render_trend_svg(kpis["trend"])
    return templates.TemplateResponse(
        "enterprise/dashboard_kpis.html",
        _ctx(request, "dashboard", kpis=kpis, trend_svg=trend_svg),
    )


@router.get("/api/dashboard/kpis")
async def api_dashboard_kpis(request: Request):
    if not _tenant_id(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    return JSONResponse(get_kpis(_tenant_id(request)))


# ===========================================================================
# Phase 4b – Freigabe-Workflow
# ===========================================================================
@router.get("/freigaben", response_class=HTMLResponse)
async def freigaben_page(request: Request):
    redirect = _require_login(request)
    if redirect:
        return redirect
    tid = _tenant_id(request)
    approval_workflow.check_escalations(tid)
    open_approvals = approval_workflow.get_open_approvals(tid)
    rules = approval_workflow.get_rules(tid)
    return templates.TemplateResponse(
        "enterprise/freigaben.html",
        _ctx(request, "approvals", open_approvals=open_approvals, rules=rules),
    )


@router.post("/freigaben/{request_id}/approve")
async def freigabe_approve(request: Request, request_id: int,
                           csrf_token: str = Form(None), comment: str = Form(None)):
    if _require_login(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    _require_csrf(request, csrf_token)
    tid = _tenant_id(request)
    approval_workflow.approve(tid, request_id, tid, comment=comment)
    return RedirectResponse(url="/freigaben", status_code=303)


@router.post("/freigaben/{request_id}/reject")
async def freigabe_reject(request: Request, request_id: int,
                          csrf_token: str = Form(None), comment: str = Form(None)):
    if _require_login(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    _require_csrf(request, csrf_token)
    tid = _tenant_id(request)
    approval_workflow.reject(tid, request_id, tid, comment=comment)
    return RedirectResponse(url="/freigaben", status_code=303)


@router.post("/freigaben/regeln")
async def freigabe_save_rules(request: Request, csrf_token: str = Form(None),
                              t1: float = Form(...), r1: str = Form(...),
                              t2: float = Form(...), r2: str = Form(...),
                              r3: str = Form(...)):
    if _require_login(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    _require_csrf(request, csrf_token)
    tid = _tenant_id(request)
    rules = [
        {"threshold": t1, "role": r1},
        {"threshold": t2, "role": r2},
        {"threshold": approval_workflow._INF_THRESHOLD, "role": r3},
    ]
    approval_workflow.save_rules(tid, rules)
    return RedirectResponse(url="/freigaben", status_code=303)


@router.post("/api/invoices/{invoice_id}/freigabe")
async def api_submit_approval(request: Request, invoice_id: int):
    if not _tenant_id(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    _require_csrf(request, request.headers.get("X-CSRF-Token"))
    tid = _tenant_id(request)
    # Betrag der Rechnung holen (tenant-isoliert)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COALESCE(i.betrag_brutto, 0) FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        WHERE i.id = ? AND j.user_id = ?
        """,
        (invoice_id, tid),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    result = approval_workflow.submit_for_approval(tid, invoice_id, float(row[0]), user_id=tid)
    return JSONResponse(result)


# ===========================================================================
# Phase 4c – Lieferanten-Übersicht
# ===========================================================================
@router.get("/lieferanten", response_class=HTMLResponse)
async def lieferanten_page(request: Request, sort: str = "volumen"):
    redirect = _require_login(request)
    if redirect:
        return redirect
    tid = _tenant_id(request)
    suppliers = get_suppliers(tid, sort_by=sort)
    return templates.TemplateResponse(
        "enterprise/lieferanten.html",
        _ctx(request, "suppliers", suppliers=suppliers, sort=sort),
    )


@router.get("/lieferanten/{supplier}", response_class=HTMLResponse)
async def lieferant_detail(request: Request, supplier: str):
    redirect = _require_login(request)
    if redirect:
        return redirect
    tid = _tenant_id(request)
    detail = get_supplier_detail(tid, supplier)
    return templates.TemplateResponse(
        "enterprise/lieferant_detail.html",
        _ctx(request, "suppliers", detail=detail),
    )


@router.get("/api/lieferanten")
async def api_lieferanten(request: Request, sort: str = "volumen"):
    if not _tenant_id(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    return JSONResponse(get_suppliers(_tenant_id(request), sort_by=sort))


# ===========================================================================
# Phase 5a – GoBD
# ===========================================================================
@router.get("/verfahrensdokumentation", response_class=HTMLResponse)
async def verfahrensdokumentation(request: Request):
    # Statische Seite – auch ohne Login zugänglich (Compliance-Dokument)
    return templates.TemplateResponse(
        "enterprise/verfahrensdokumentation.html",
        {"request": request, "user": _get_user(request), "active_nav": "compliance"},
    )


@router.get("/gobd/export-protokoll", response_class=HTMLResponse)
async def export_protokoll(request: Request):
    redirect = _require_login(request)
    if redirect:
        return redirect
    tid = _tenant_id(request)
    entries = gobd.get_export_protocol(tid)
    return templates.TemplateResponse(
        "enterprise/export_protokoll.html",
        _ctx(request, "compliance", entries=entries),
    )


@router.post("/api/invoices/{invoice_id}/lock")
async def api_lock_invoice(request: Request, invoice_id: int):
    if not _tenant_id(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    _require_csrf(request, request.headers.get("X-CSRF-Token"))
    tid = _tenant_id(request)
    try:
        gobd.lock_invoice(tid, invoice_id, user_id=tid)
    except gobd.GoBDError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return JSONResponse({"ok": True, "invoice_id": invoice_id, "gobd_locked": True})


@router.post("/api/invoices/{invoice_id}/soft-delete")
async def api_soft_delete(request: Request, invoice_id: int, reason: str = Form(...),
                          csrf_token: str = Form(None)):
    if not _tenant_id(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    _require_csrf(request, csrf_token or request.headers.get("X-CSRF-Token"))
    tid = _tenant_id(request)
    try:
        gobd.soft_delete_invoice(tid, invoice_id, reason, user_id=tid)
    except gobd.GoBDError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return JSONResponse({"ok": True, "invoice_id": invoice_id, "deleted": True})


# ===========================================================================
# Phase 5b – Audit-Trail
# ===========================================================================
@router.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request, action: str = "", user: str = "",
                     date_from: str = "", date_to: str = "", page: int = 1):
    redirect = _require_login(request)
    if redirect:
        return redirect
    tid = _tenant_id(request)
    per_page = 50
    page = max(1, page)
    user_id = int(user) if user.isdigit() else None
    filters = {
        "action": action or None,
        "user_id": user_id,
        "date_from": date_from or None,
        "date_to": date_to or None,
    }
    total = audit_events.count_events(tid, **filters)
    events = audit_events.query_events(tid, limit=per_page, offset=(page - 1) * per_page, **filters)
    total_pages = max(1, (total + per_page - 1) // per_page)
    return templates.TemplateResponse(
        "enterprise/audit.html",
        _ctx(request, "compliance", events=events, total=total, page=page,
             total_pages=total_pages, actions=audit_events.KNOWN_ACTIONS,
             f_action=action, f_user=user, f_from=date_from, f_to=date_to),
    )


@router.get("/audit/export.csv")
async def audit_export_csv(request: Request, action: str = "", user: str = "",
                           date_from: str = "", date_to: str = ""):
    if not _tenant_id(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    tid = _tenant_id(request)
    user_id = int(user) if user.isdigit() else None
    csv_data = audit_events.export_csv(
        tid, action=action or None, user_id=user_id,
        date_from=date_from or None, date_to=date_to or None,
    )
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_trail.csv"'},
    )


# ===========================================================================
# Phase 5c – DSGVO
# ===========================================================================
def _enforce_self(request: Request, target_user_id: int) -> None:
    """Ein Tenant darf nur auf eigene Daten zugreifen (Tenant-Isolation)."""
    tid = _tenant_id(request)
    if not tid:
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    if int(target_user_id) != int(tid):
        raise HTTPException(status_code=403, detail="Zugriff nur auf eigene Daten erlaubt")


@router.get("/api/dsgvo/auskunft/{user_id}")
async def api_dsgvo_auskunft(request: Request, user_id: int):
    _enforce_self(request, user_id)
    data = dsgvo.get_auskunft(user_id)
    audit_events.log_event(user_id, "auskunft", user_id=user_id, entity_type="user", entity_id=user_id)
    return JSONResponse(data)


@router.delete("/api/dsgvo/loeschung/{user_id}")
async def api_dsgvo_loeschung(request: Request, user_id: int):
    _enforce_self(request, user_id)
    _require_csrf(request, request.headers.get("X-CSRF-Token"))
    result = dsgvo.anonymize_user(user_id, performed_by=user_id)
    return JSONResponse(result)


@router.get("/dsgvo/einstellungen", response_class=HTMLResponse)
async def dsgvo_settings(request: Request):
    redirect = _require_login(request)
    if redirect:
        return redirect
    tid = _tenant_id(request)
    return templates.TemplateResponse(
        "enterprise/dsgvo_einstellungen.html",
        _ctx(request, "compliance", retention_years=get_retention_years(tid)),
    )


@router.post("/dsgvo/einstellungen")
async def dsgvo_settings_save(request: Request, retention_years: int = Form(...),
                              csrf_token: str = Form(None)):
    if _require_login(request):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    _require_csrf(request, csrf_token)
    tid = _tenant_id(request)
    set_retention_years(tid, retention_years)
    audit_events.log_event(tid, "einstellungen_geaendert", user_id=tid,
                           entity_type="retention_policy", entity_id=tid,
                           details={"retention_years": int(retention_years)})
    return RedirectResponse(url="/dsgvo/einstellungen", status_code=303)
