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
import os
import re
import tempfile
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response

import approval_workflow
import audit_events
from database import get_connection
from enterprise_dashboard import get_kpis
from supplier_overview import get_supplier_detail, get_suppliers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/app", tags=["Frontend-API"])

_PW_MIN = 8

# Upload-Hardening
UPLOAD_MAX_BYTES = int(os.getenv("UPLOAD_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB
UPLOAD_ALLOWED_EXT = {".pdf", ".xml", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}


def _rate_limit_auth(request: Request) -> None:
    """Per-IP Rate-Limit für Auth-Endpunkte (5/min, via rate_limiter).

    HTTPException(429) wird durchgereicht; andere Fehler werden ignoriert,
    damit der Login bei Limiter-Problemen nicht hart bricht.
    """
    try:
        from rate_limiter import check_rate_limit
        check_rate_limit(request, "auth")
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - Limiter optional
        logger.debug("rate_limit skip: %s", exc)


def _check_password_policy(password: str) -> None:
    """Passwort-Richtlinie konsistent zum restlichen Bestand."""
    if len(password) < _PW_MIN:
        raise HTTPException(status_code=400, detail=f"Passwort muss mindestens {_PW_MIN} Zeichen haben")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Passwort muss einen Großbuchstaben enthalten")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Passwort muss einen Kleinbuchstaben enthalten")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Passwort muss eine Zahl enthalten")


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
    # is_admin NICHT per COALESCE(.., 0) lesen: auf PostgreSQL ist die Spalte je
    # nach Herkunft boolean (Bestand) ODER integer (Fresh-Install via
    # init_database). COALESCE mit Integer-Literal wirft dort DatatypeMismatch
    # (boolean vs integer); ein FALSE-Literal bräche umgekehrt den Integer-Fall.
    # Spalte roh lesen, Default/Typ in Python normalisieren (bool(None) == False).
    cur.execute("SELECT id, email, name, company, is_admin FROM users WHERE id = ?", (user_id,))
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

    _rate_limit_auth(request)
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

    _rate_limit_auth(request)
    body = await request.json()
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    name = (body.get("name") or "").strip()
    company = (body.get("company") or "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="E-Mail und Passwort erforderlich")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Ungültige E-Mail-Adresse")
    _check_password_policy(password)
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
               COALESCE(CAST(i.created_at AS TEXT), CAST(j.created_at AS TEXT)) AS created_at
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


@router.get("/invoices/{invoice_id}/pdf")
async def api_invoice_pdf(request: Request, invoice_id: int):
    """Liefert die Original-PDF einer Rechnung (tenant-isoliert).

    Auflösung: gespeicherter datei_pfad → sonst PDF im Upload-Verzeichnis des
    zugehörigen Jobs. Niemals Dateien fremder Mandanten.
    """
    from fastapi.responses import FileResponse

    tid = _require_tenant(request)
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cur = conn.cursor()
    cur.execute(
        """
        SELECT i.job_id, i.datei_pfad, j.upload_path
        FROM invoices i JOIN jobs j ON i.job_id = j.job_id
        WHERE i.id = ? AND j.user_id = ?
        """,
        (invoice_id, tid),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    # 1) direkt gespeicherter Pfad
    candidates = []
    if row.get("datei_pfad"):
        candidates.append(row["datei_pfad"])
    # 2) Upload-Verzeichnis des Jobs (erste PDF)
    job_dirs = [d for d in (row.get("upload_path"),
                            os.path.join(os.getenv("UPLOAD_DIR") or os.path.join(os.getcwd(), "web", "uploads"),
                                         str(row.get("job_id") or ""))) if d]
    for d in job_dirs:
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if name.lower().endswith(".pdf"):
                    candidates.append(os.path.join(d, name))

    for path in candidates:
        if path and os.path.isfile(path):
            return FileResponse(path, media_type="application/pdf",
                                filename=os.path.basename(path))
    raise HTTPException(status_code=404, detail="PDF nicht gefunden")


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
        # Frontend sendet { grund }, Abwärtskompatibilität: comment
        comment = body.get("grund") or body.get("comment")
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


# ---------------------------------------------------------------------------
# Upload (multipart) – KI-Extraktions-Pipeline (synchron, MVP)
# ---------------------------------------------------------------------------
@router.post("/upload")
async def api_upload(request: Request, files: List[UploadFile] = File(...)):
    """Nimmt PDF-Rechnungen entgegen, speichert sie, legt je Datei einen
    Invoice-Record an und durchläuft synchron die KI-Pipeline
    (Text → KI-Extraktion → Validierung → Kontierung → DB-Update).

    Antwort: { id, job_id, status, invoices: [...] }.
    """
    tid = _require_tenant(request)

    base = os.getenv("UPLOAD_DIR") or os.path.join(os.getcwd(), "web", "uploads")
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(base, job_id)
    os.makedirs(job_dir, exist_ok=True)

    saved = []
    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in UPLOAD_ALLOWED_EXT:
            raise HTTPException(
                status_code=400,
                detail=f"Dateityp {ext or '?'} nicht erlaubt. Erlaubt: PDF, XML, JPG, PNG, TIFF",
            )
        content = await f.read()
        if len(content) > UPLOAD_MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Datei zu groß (max. {UPLOAD_MAX_BYTES // (1024 * 1024)} MB)",
            )
        dest = os.path.join(job_dir, os.path.basename(f.filename))
        with open(dest, "wb") as out:
            out.write(content)
        saved.append(dest)

    if not saved:
        raise HTTPException(status_code=400, detail="Keine gültige Datei hochgeladen")

    from database import save_job
    save_job(job_id, {"created_at": datetime.now().isoformat(), "status": "processing",
                      "total_files": len(saved), "upload_path": job_dir}, user_id=tid)
    audit_events.log_event(tid, audit_events.AuditEvent.UPLOAD, user_id=tid,
                           entity_type="job", entity_id=job_id, details={"files": len(saved)})

    import invoice_extraction
    invoice_extraction.ensure_extraction_columns()

    results = []
    for path in saved:
        # Invoice-Record anlegen (Status processing)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO invoices (job_id, status, created_at, tenant_id, datei_pfad) "
            "VALUES (?, 'processing', ?, ?, ?)",
            (job_id, datetime.now().isoformat(), tid, path),
        )
        invoice_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Pipeline synchron ausführen (crasht nie – Status spiegelt Fehler)
        try:
            outcome = invoice_extraction.process_pdf(path)
        except Exception as exc:  # pragma: no cover - defensive
            outcome = {"status": "fehler", "error": str(exc), "fields": {},
                       "validation": None, "kontierung": None}
        try:
            invoice_extraction.update_invoice_record(invoice_id, outcome)
        except Exception as exc:  # pragma: no cover
            logger.error("update_invoice_record id=%s: %s", invoice_id, exc)

        audit_events.log_event(tid, audit_events.AuditEvent.KI_EXTRAKTION, user_id=tid,
                               entity_type="invoice", entity_id=invoice_id,
                               details={"status": outcome.get("status")})

        # Erfolgreich verarbeitete Rechnungen automatisch zur Freigabe einreichen
        # (damit die Freigabe-Queue /api/app/freigaben echte Einträge zeigt)
        if outcome.get("status") == "verarbeitet":
            betrag = (outcome.get("fields") or {}).get("betrag_brutto")
            if betrag is not None:
                try:
                    approval_workflow.submit_for_approval(tid, invoice_id, float(betrag),
                                                          user_id=tid, notify=False)
                except Exception as exc:  # pragma: no cover
                    logger.warning("Auto-Freigabe invoice=%s: %s", invoice_id, exc)

        results.append({
            "id": invoice_id,
            "datei": os.path.basename(path),
            "status": outcome.get("status"),
            "validierung_ok": (outcome.get("validation") or {}).get("ok"),
            "error": outcome.get("error"),
        })

    statuses = {r["status"] for r in results}
    if statuses == {"verarbeitet"}:
        overall = "verarbeitet"
    elif "verarbeitet" in statuses:
        overall = "teilweise_verarbeitet"
    else:
        overall = "fehler"

    return JSONResponse(status_code=200, content={
        "id": job_id, "job_id": job_id, "status": overall,
        "files": len(saved), "invoices": results})


# ---------------------------------------------------------------------------
# DATEV
# ---------------------------------------------------------------------------
def _tenant_invoices(tid: int, invoice_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cur = conn.cursor()
    sql = (
        "SELECT i.* FROM invoices i JOIN jobs j ON i.job_id = j.job_id "
        "WHERE j.user_id = ? AND COALESCE(i.deleted, 0) = 0"
    )
    params: List[Any] = [int(tid)]
    if invoice_ids:
        placeholders = ",".join("?" for _ in invoice_ids)
        sql += f" AND i.id IN ({placeholders})"
        params.extend(int(x) for x in invoice_ids)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


@router.get("/datev/preview")
async def api_datev_preview(request: Request, invoice_id: int):
    """DATEV-Buchungsvorschau für eine Rechnung (tenant-isoliert)."""
    tid = _require_tenant(request)
    rows = _tenant_invoices(tid, [invoice_id])
    if not rows:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    invoice = rows[0]

    from datev import InvoiceToBuchungConverter, Kontenrahmen

    converter = InvoiceToBuchungConverter(Kontenrahmen.SKR03)
    buchungen = []
    for b in converter.convert(invoice):
        buchungen.append({
            "umsatz": str(b.umsatz),
            "soll_haben": b.soll_haben,
            "konto": b.konto,
            "gegenkonto": b.gegenkonto,
            "belegdatum": b.belegdatum.isoformat() if getattr(b, "belegdatum", None) else None,
            "belegnummer": b.belegnummer,
            "buchungstext": b.buchungstext,
            "steuerschluessel": b.steuerschluessel,
        })
    return {
        "invoice": {
            "id": invoice.get("id"),
            "rechnungsnummer": invoice.get("rechnungsnummer"),
            "rechnungsaussteller": invoice.get("rechnungsaussteller"),
            "betrag_brutto": invoice.get("betrag_brutto"),
        },
        "buchungen": buchungen,
        "detected_account": converter.detect_account(invoice),
    }


@router.post("/datev/export")
async def api_datev_export(request: Request):
    """Erzeugt einen DATEV EXTF-700-Export (CSV) und protokolliert ihn (GoBD).

    Body optional: { "invoice_ids": [..] } – sonst alle (nicht gelöschten)
    Rechnungen des Mandanten.
    """
    tid = _require_tenant(request)
    invoice_ids = None
    try:
        body = await request.json()
        invoice_ids = body.get("invoice_ids") or None
    except Exception:
        pass

    invoices = [i for i in _tenant_invoices(tid, invoice_ids)
                if i.get("betrag_brutto") is not None]
    if not invoices:
        raise HTTPException(status_code=404, detail="Keine exportierbaren Rechnungen gefunden")

    from datev import DatevExportConfig, Kontenrahmen, export_invoices_to_datev_csv

    config = DatevExportConfig(
        berater_nummer=os.getenv("DATEV_BERATER_NR", "1000"),
        mandanten_nummer=os.getenv("DATEV_MANDANT_NR", str(tid)),
        wirtschaftsjahr_beginn=date(date.today().year, 1, 1),
        kontenrahmen=Kontenrahmen.SKR03,
    )

    tmp_path = os.path.join(tempfile.gettempdir(), f"EXTF_{tid}_{uuid.uuid4().hex}.csv")
    export_invoices_to_datev_csv(invoices, config, tmp_path)
    with open(tmp_path, "rb") as fh:
        content = fh.read()
    try:
        os.remove(tmp_path)
    except OSError:  # pragma: no cover
        pass

    # GoBD: Export mit SHA-256 protokollieren
    try:
        import gobd

        gobd.record_export(tid, "datev", content, file_name="EXTF_Buchungen.csv",
                           row_count=len(invoices), user_id=tid)
    except Exception as exc:  # pragma: no cover
        logger.warning("Export-Protokoll fehlgeschlagen: %s", exc)

    filename = f"EXTF_Buchungen_{datetime.now():%Y%m%d_%H%M%S}.csv"
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
