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

import json
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

    # Tenant-Zuordnung: genau EINE Bedingung pro Zeile über COALESCE –
    # i.tenant_id (neuer Flow / die 17) bevorzugt, sonst jobs.user_id als
    # Legacy-Fallback (klassischer Upload-Flow schrieb invoices ohne tenant_id).
    # Kein OR über zwei ID-Räume: sobald i.tenant_id gesetzt ist, entscheidet
    # ausschließlich diese – ein fremder jobs.user_id kann nichts durchlassen.
    # LEFT JOIN, damit Rechnungen OHNE jobs-Zeile nicht verloren gehen (der
    # frühere INNER JOIN lieferte 0).
    where = ["COALESCE(i.tenant_id, j.user_id) = ?", "COALESCE(i.deleted, 0) = 0"]
    params: list[Any] = [tid]
    if status:
        # Status wie im Dashboard-status_breakdown normalisieren (NULL/leer → 'neu'),
        # damit Kachel-Zahl und gefilterte Liste für Altzeilen ohne Status übereinstimmen.
        where.append("COALESCE(NULLIF(TRIM(i.status), ''), 'neu') = ?")
        params.append(status)
    if q:
        where.append("(i.rechnungsaussteller LIKE ? OR i.rechnungsnummer LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    where_sql = " AND ".join(where)

    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) AS n FROM invoices i LEFT JOIN jobs j ON i.job_id = j.job_id WHERE {where_sql}", params)
    total = cur.fetchone()["n"]
    cur.execute(
        f"""
        SELECT i.id, i.rechnungsnummer, i.datum, i.rechnungsaussteller,
               i.betrag_brutto, i.betrag_netto, i.mwst_betrag, i.waehrung,
               i.validierung_json,
               COALESCE(i.status, 'neu') AS status,
               COALESCE(CAST(i.created_at AS TEXT), CAST(j.created_at AS TEXT)) AS created_at
        FROM invoices i LEFT JOIN jobs j ON i.job_id = j.job_id
        WHERE {where_sql}
        ORDER BY created_at DESC, i.id DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    )
    items = cur.fetchall()
    conn.close()
    # Kompakte Validierung aus derselben Quelle (Badge/Summary je Zeile ohne die
    # volle Check-Liste – die holt das Detail). validierung_json-Rohstring nicht
    # in die Liste durchreichen.
    for it in items:
        v = _normalize_validierung(it.pop("validierung_json", None), include_checks=False)
        it["validierung"] = v
        it["validierung_ok"] = v["ok"] if v else None
    return {"total": total, "limit": limit, "offset": offset, "items": items}


# Menschenlesbare Labels/Kategorien je Check-Name – damit die SPA die
# validierung_json.checks DIREKT rendern kann (Label + ok + severity + message)
# und NICHT clientseitig neu validieren muss (Ursache der IBAN/USt-„ungültig"-
# Falschmeldungen und der „keine Pflichtangaben-Prüfung"-Inkonsistenz).
_CHECK_LABELS: Dict[str, str] = {
    "iban": "IBAN",
    "ust_idnr_format": "USt-IdNr.-Format",
    "betrag_summe": "Betragsprüfung",
    "duplikat": "Duplikat",
    "§14_rechnungsaussteller": "Rechnungsaussteller",
    "§14_rechnungsnummer": "Rechnungsnummer",
    "§14_datum": "Rechnungsdatum",
    "§14_betrag_brutto": "Rechnungsbetrag",
    "§14_steuer_id": "Steuernummer / USt-IdNr.",
    "§14_umsatzsteuer": "Umsatzsteuer",
}


def _normalize_validierung(raw: Any, *, include_checks: bool = True) -> Optional[Dict[str, Any]]:
    """Parst das gespeicherte ``validierung_json`` (String) in ein strukturiertes
    Objekt und reichert jeden Check um Label + Kategorie an.

    Dies ist die EINZIGE Quelle der Wahrheit für die SPA – sowohl der
    Validierung-Tab als auch das Compliance-Panel lesen ``validierung.checks``
    bzw. ``validierung.pflichtangaben``. Ohne diese Normalisierung erhielt das
    Frontend nur einen JSON-String, validierte teils clientseitig neu (mit
    zu strenger IBAN/USt-Regex → Falsch-„ungültig") oder las für Tab und Panel
    unterschiedliche Felder (→ „20/20" vs. „keine Pflichtangaben-Prüfung").

    ``include_checks=False`` liefert die kompakte Variante (ohne ``checks[]``)
    für die Listen-Ansicht – Badge/Summary aus derselben Quelle, ohne die volle
    Check-Liste je Listenzeile zu übertragen (die holt das Detail)."""
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return None
    elif isinstance(raw, dict):
        data = raw
    else:
        return None
    if not isinstance(data, dict):
        return None

    checks = data.get("checks")
    checks = checks if isinstance(checks, list) else []
    norm_checks: List[Dict[str, Any]] = []
    pflicht_total = pflicht_ok = 0
    for c in checks:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", ""))
        is_pflicht = name.startswith("§14_")
        label = _CHECK_LABELS.get(name)
        if not label:
            label = name[4:].replace("_", " ").capitalize() if is_pflicht else name
        item = dict(c)
        item["label"] = label
        item["category"] = "Pflichtangabe (§14 UStG)" if is_pflicht else "Prüfung"
        norm_checks.append(item)
        if is_pflicht:
            pflicht_total += 1
            if c.get("ok"):
                pflicht_ok += 1

    passed = sum(1 for c in norm_checks if c.get("ok"))
    out = {
        "ok": bool(data.get("ok")),
        "error_count": int(data.get("error_count", 0) or 0),
        # Für das Compliance-Panel (identische Zahl wie der Tab → keine Divergenz)
        "pflichtangaben": {
            "ok": pflicht_ok,
            "total": pflicht_total,
            "geprueft": pflicht_total > 0,
            "vollstaendig": pflicht_total > 0 and pflicht_ok == pflicht_total,
        },
        "summary": {"total": len(norm_checks), "passed": passed,
                    "failed": len(norm_checks) - passed},
    }
    if include_checks:
        out["checks"] = norm_checks
    return out


@router.get("/invoices/{invoice_id}")
async def api_invoice_detail(request: Request, invoice_id: int):
    tid = _require_tenant(request)
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cur = conn.cursor()
    cur.execute(
        """
        SELECT i.* FROM invoices i LEFT JOIN jobs j ON i.job_id = j.job_id
        WHERE i.id = ? AND COALESCE(i.tenant_id, j.user_id) = ?
        """,
        (invoice_id, tid),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    # Strukturierte Validierung als einzige Quelle der Wahrheit ergänzen
    # (validierung_json bleibt als Rohstring erhalten – Rückwärtskompatibilität).
    validierung = _normalize_validierung(row.get("validierung_json"))
    row["validierung"] = validierung
    row["validierung_ok"] = validierung["ok"] if validierung else None
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
        FROM invoices i LEFT JOIN jobs j ON i.job_id = j.job_id
        WHERE i.id = ? AND COALESCE(i.tenant_id, j.user_id) = ?
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
def _apply_duplicate_to_outcome(outcome: Dict[str, Any], duplicate: Optional[Dict[str, Any]]) -> None:
    """Spiegelt das Duplikat-Ergebnis in ``outcome['validation']`` (validierung_json),
    damit die Detail-Ansicht/Compliance-Panel den „Duplikat"-Check korrekt anzeigt
    (die Panels lesen validierung_json, nicht die duplicate_detections-Tabelle).
    Bei einem Treffer wird zusätzlich der Status auf 'pruefen' gesetzt (keine
    stille Auto-Freigabe eines Duplikats)."""
    is_dup = duplicate is not None
    val = outcome.get("validation")
    if not isinstance(val, dict):
        # Kein Validierungsergebnis (Extraktion fehlgeschlagen / kein Text): NICHT
        # fälschlich als 'ok' markieren. Nur wenn ein Duplikat vorliegt, legen wir
        # ein (dann fehlgeschlagenes) Validierungsergebnis an; sonst unangetastet.
        if not is_dup:
            return
        val = {"ok": True, "error_count": 0, "checks": []}
        outcome["validation"] = val
    checks = val.setdefault("checks", [])
    # idempotent: evtl. vorhandenen alten Duplikat-Check entfernen (Reprocess)
    checks[:] = [c for c in checks if c.get("name") != "duplikat"]
    checks.append({
        "name": "duplikat",
        "ok": not is_dup,
        "severity": "error" if is_dup else "info",
        "message": (f"Identische Rechnung bereits vorhanden (ID {duplicate['of_id']})"
                    if is_dup else "Keine identische Rechnung gefunden"),
    })
    if is_dup:
        val["ok"] = False
        val["error_count"] = int(val.get("error_count", 0) or 0) + 1
        if outcome.get("status") in ("verarbeitet", None):
            outcome["status"] = "pruefen"


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
    for idx, f in enumerate(files):
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
        # Eindeutiges Ziel je Datei (Index-Präfix): zwei Uploads mit gleichem
        # Basisnamen dürfen sich NICHT gegenseitig überschreiben – sonst würde
        # der gespeicherte datei_hash von der tatsächlich verarbeiteten Datei
        # abweichen.
        base_name = os.path.basename(f.filename or f"upload_{idx}")
        dest = os.path.join(job_dir, f"{idx:03d}_{base_name}")
        with open(dest, "wb") as out:
            out.write(content)
        import duplicate_detection
        saved.append((dest, duplicate_detection.compute_file_hash(content)))

    if not saved:
        raise HTTPException(status_code=400, detail="Keine gültige Datei hochgeladen")

    from database import save_job
    save_job(job_id, {"created_at": datetime.now().isoformat(), "status": "processing",
                      "total_files": len(saved), "upload_path": job_dir}, user_id=tid)
    audit_events.log_event(tid, audit_events.AuditEvent.UPLOAD, user_id=tid,
                           entity_type="job", entity_id=job_id, details={"files": len(saved)})

    import invoice_extraction
    invoice_extraction.ensure_extraction_columns()

    import duplicate_detection
    results = []
    for path, file_hash in saved:
        # Invoice-Record anlegen (Status processing)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO invoices (job_id, status, created_at, tenant_id, datei_pfad, datei_hash) "
            "VALUES (?, 'processing', ?, ?, ?, ?)",
            (job_id, datetime.now().isoformat(), tid, path, file_hash),
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

        # B6: Duplikatserkennung – zuerst layoutunabhängig über den Datei-Hash
        # (fängt Re-Uploads auch bei NULL-Aussteller), sonst NULL-sicherer
        # Feld-Match (Nummer+Betrag). BEIDE Checks laufen VOR update_invoice_record,
        # damit das Ergebnis in validierung_json landet – sonst zeigt die
        # Detail-Ansicht/Compliance-Panel den Treffer nie an.
        duplicate = None
        try:
            match = duplicate_detection.check_duplicate_by_file_hash(
                file_hash, tid, exclude_invoice_id=invoice_id)
            if match:
                duplicate = {"of_id": match["id"], "method": "file_hash"}
        except Exception as exc:  # pragma: no cover - Duplikat-Check darf Upload nie sprengen
            logger.warning("Duplikat-Check (file_hash) invoice=%s: %s", invoice_id, exc)
        if duplicate is None:
            try:
                fmatch = duplicate_detection.check_duplicate_by_fields(
                    outcome.get("fields") or {}, tid, exclude_invoice_id=invoice_id)
                if fmatch:
                    duplicate = {"of_id": fmatch["id"], "method": "fields"}
            except Exception as exc:  # pragma: no cover
                logger.warning("Duplikat-Check (fields) invoice=%s: %s", invoice_id, exc)

        if duplicate is not None:
            try:
                duplicate_detection.save_duplicate_detection(
                    invoice_id, duplicate["of_id"], method=duplicate["method"],
                    confidence=1.0 if duplicate["method"] == "file_hash" else 0.9)
            except Exception as exc:  # pragma: no cover
                logger.warning("save_duplicate_detection invoice=%s: %s", invoice_id, exc)
        # Duplikat-Ergebnis ins validierung_json spiegeln + Status auf 'pruefen'.
        _apply_duplicate_to_outcome(outcome, duplicate)

        # Persistieren (Felder + validierung_json inkl. Duplikat-Check + Status)
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
            "duplicate": duplicate,
            "error": outcome.get("error"),
        })

    statuses = {r["status"] for r in results}
    if statuses == {"verarbeitet"}:
        overall = "verarbeitet"
    elif "verarbeitet" in statuses:
        overall = "teilweise_verarbeitet"
    elif "pruefen" in statuses and "fehler" not in statuses:
        # Extraktion lief, aber (mind.) eine Rechnung ist prüfbedürftig – kein Fehler.
        overall = "pruefen"
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
        "SELECT i.* FROM invoices i LEFT JOIN jobs j ON i.job_id = j.job_id "
        "WHERE COALESCE(i.tenant_id, j.user_id) = ? AND COALESCE(i.deleted, 0) = 0"
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


def _strict_int(v: Any) -> Optional[int]:
    """Nimmt NUR echte Ganzzahlen an (int oder Integer-String). Lehnt bool,
    float/Dezimal (z. B. 1.9) und nicht-numerische Werte ab → der Aufrufer
    liefert dann 422 statt 500 bzw. einer falschen (gerundeten) invoice_id."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip()
        digits = s[1:] if s[:1] in ("+", "-") else s
        if digits.isdigit():
            return int(s)
    return None


# Exportierbare Rechnungsstatus (case-insensitive). "verarbeitet" = fertig
# extrahiert, "approved"/"freigegeben" = nach Freigabe. Rohzustände wie "neu"
# oder "fehler" gehören NICHT in einen DATEV-Stapel.
_DATEV_EXPORTABLE_STATUSES = frozenset({"verarbeitet", "approved", "freigegeben"})


def _datev_exportable(tid: int, invoice_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """Einzige Quelle der DATEV-Auswahlmenge – von Batch-Vorschau UND Export genutzt.

    GoBD/Revision: Vorschau und Export MÜSSEN deckungsgleich sein (was der Nutzer
    in der Vorschau sieht, wird exportiert – und umgekehrt). Exportierbar =
    tenant-isoliert (``_tenant_invoices`` → COALESCE(i.tenant_id, j.user_id)),
    nicht gelöscht, ``betrag_brutto`` gesetzt und Status ∈
    ``_DATEV_EXPORTABLE_STATUSES``. ``invoice_ids`` schränkt zusätzlich ein."""
    return [
        r for r in _tenant_invoices(tid, invoice_ids)
        if r.get("betrag_brutto") is not None
        and str(r.get("status") or "").lower() in _DATEV_EXPORTABLE_STATUSES
    ]


def _datev_buchungen(converter, invoice: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Wandelt EINE Rechnung in serialisierbare DATEV-Buchungssätze um.

    Einzige Stelle der (GoBD-/revisionsrelevanten) Umwandlung – von Einzel- und
    Batch-Vorschau gemeinsam genutzt, damit keine Logik dupliziert wird."""
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
    return buchungen


def _datev_preview(tid: int, invoice_id: int) -> Dict[str, Any]:
    """Tenant-isolierte DATEV-Buchungsvorschau für EINE Rechnung."""
    rows = _tenant_invoices(tid, [invoice_id])
    if not rows:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    invoice = rows[0]

    from datev import InvoiceToBuchungConverter, Kontenrahmen

    converter = InvoiceToBuchungConverter(Kontenrahmen.SKR03)
    return {
        "invoice": {
            "id": invoice.get("id"),
            "rechnungsnummer": invoice.get("rechnungsnummer"),
            "rechnungsaussteller": invoice.get("rechnungsaussteller"),
            "betrag_brutto": invoice.get("betrag_brutto"),
        },
        "buchungen": _datev_buchungen(converter, invoice),
        "detected_account": converter.detect_account(invoice),
    }


def _datev_preview_batch(tid: int) -> Dict[str, Any]:
    """Gesamt-/Batch-Vorschau über ALLE exportierbaren Rechnungen des Mandanten.

    Nutzt dieselbe Auswahl wie der Export (``_datev_exportable``), damit Vorschau
    und CSV deckungsgleich sind. Fremde Mandanten erhalten eine leere Vorschau."""
    from datev import InvoiceToBuchungConverter, Kontenrahmen

    converter = InvoiceToBuchungConverter(Kontenrahmen.SKR03)
    rows = _datev_exportable(tid)
    items: List[Dict[str, Any]] = []
    all_buchungen: List[Dict[str, Any]] = []
    for invoice in rows:
        buchungen = _datev_buchungen(converter, invoice)
        all_buchungen.extend(buchungen)
        items.append({
            "invoice": {
                "id": invoice.get("id"),
                "rechnungsnummer": invoice.get("rechnungsnummer"),
                "rechnungsaussteller": invoice.get("rechnungsaussteller"),
                "betrag_brutto": invoice.get("betrag_brutto"),
            },
            "buchungen": buchungen,
            "detected_account": converter.detect_account(invoice),
        })
    return {
        "batch": True,
        "invoice_count": len(items),
        "buchungen_count": len(all_buchungen),
        "invoices": items,
        "buchungen": all_buchungen,
    }


@router.get("/datev/preview")
async def api_datev_preview(request: Request, invoice_id: Optional[int] = None):
    """DATEV-Buchungsvorschau (tenant-isoliert). Mit ``invoice_id`` → Einzel-
    Vorschau; ohne → Gesamt-/Batch-Vorschau aller exportierbaren Rechnungen."""
    tid = _require_tenant(request)
    if invoice_id is None:
        return _datev_preview_batch(tid)
    return _datev_preview(tid, invoice_id)


@router.post("/datev/preview")
async def api_datev_preview_post(request: Request, invoice_id: Optional[int] = None):
    """POST-Variante – das Frontend ruft /api/app/datev/preview per POST auf.

    ``invoice_id`` aus Query ODER JSON-Body. Ist ein ``invoice_id`` angegeben →
    Einzel-Vorschau (bei ungültigem Wert → 422). Fehlt ``invoice_id`` ganz →
    Gesamt-/Batch-Vorschau (kein 422 mehr für den Seiten-Load)."""
    tid = _require_tenant(request)
    # 1) Query-invoice_id (von FastAPI als int validiert) hat Vorrang.
    if invoice_id is not None:
        return _datev_preview(tid, invoice_id)
    # 2) Body prüfen. Ist der Key vorhanden → strikt validieren (kein stilles
    #    Runden/Fehlgriff); fehlt der Key ganz → Batch-Vorschau.
    try:
        body = await request.json()
    except Exception:
        body = None
    if isinstance(body, dict) and "invoice_id" in body:
        iid = _strict_int(body.get("invoice_id"))
        if iid is None:
            raise HTTPException(status_code=422, detail="invoice_id muss eine ganze Zahl sein")
        return _datev_preview(tid, iid)
    return _datev_preview_batch(tid)


@router.post("/datev/export")
async def api_datev_export(request: Request):
    """Erzeugt einen DATEV EXTF-700-Export (CSV) und protokolliert ihn (GoBD).

    Body optional: { "invoice_ids": [..] } – sonst alle exportierbaren
    Rechnungen des Mandanten (gleiche Auswahl wie die Batch-Vorschau).
    """
    tid = _require_tenant(request)
    invoice_ids = None
    try:
        body = await request.json()
        invoice_ids = body.get("invoice_ids") or None
    except Exception:
        pass

    # Gleiche Auswahlmenge wie die Batch-Vorschau (GoBD: deckungsgleich).
    invoices = _datev_exportable(tid, invoice_ids)
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
