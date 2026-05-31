#!/usr/bin/env python3
"""
SBS Deutschland – Kunden-Routen / deutsche Alias-Pfade

Stellt die im Onboarding erwarteten deutschen Pfade bereit:
- GET /upload        → Upload-Seite (alias von /)
- GET /rechnungen    → Rechnungsliste (alias von /history)
- GET /rechnung/{id} → Rechnungsdetail (→ zugehörige Job-Detailseite)
- GET /export        → Export-Übersicht (alias von /exports)
- GET /preise        → Preisseite (deutsch)
- POST /api/freigaben/{id}/approve → Freigabe genehmigen (JSON, mehrstufig)
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

import approval_workflow
from database import get_connection

router = APIRouter()


def _tenant_id(request: Request):
    try:
        uid = request.session.get("user_id")
    except Exception:
        return None
    try:
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


def _require_csrf(request: Request, submitted):
    expected = request.session.get("csrf_token")
    if not expected or not submitted or not secrets.compare_digest(str(submitted), str(expected)):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


@router.get("/upload")
async def upload_alias():
    """Upload-Seite (die Startseite '/' enthält den Upload-Bereich)."""
    return RedirectResponse(url="/", status_code=307)


@router.get("/rechnungen")
async def rechnungen_alias():
    """Rechnungsliste (Historie)."""
    return RedirectResponse(url="/history", status_code=307)


@router.get("/rechnung/{invoice_id}")
async def rechnung_detail(request: Request, invoice_id: int):
    """Rechnungsdetail → leitet auf die zugehörige Job-Detailseite weiter."""
    if not _tenant_id(request):
        return RedirectResponse(url=f"/login?next=/rechnung/{invoice_id}", status_code=303)
    tid = _tenant_id(request)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT i.job_id FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        WHERE i.id = ? AND j.user_id = ?
        """,
        (invoice_id, tid),
    )
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return RedirectResponse(url=f"/job/{row[0]}", status_code=307)
    return RedirectResponse(url="/history", status_code=303)


@router.get("/export")
async def export_alias():
    """Export-Übersicht."""
    return RedirectResponse(url="/exports", status_code=307)


@router.get("/preise")
async def preise_page():
    """Deutsche Preisseite (statisch)."""
    import os

    path = "web/static/landing/preise.html"
    if os.path.exists(path):
        return FileResponse(path)
    return RedirectResponse(url="/pricing", status_code=307)


@router.post("/api/freigaben/{request_id}/approve")
async def api_freigabe_approve(request: Request, request_id: int, comment: str = Form(None),
                               csrf_token: str = Form(None)):
    """Genehmigt die aktuelle Freigabestufe (JSON-API, mehrstufiger Workflow)."""
    tid = _tenant_id(request)
    if not tid:
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    _require_csrf(request, csrf_token or request.headers.get("X-CSRF-Token"))
    result = approval_workflow.approve(tid, request_id, tid, comment=comment)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Freigabe fehlgeschlagen"))
    return JSONResponse(result)
