#!/usr/bin/env python3
"""
BelegFlow – Öffentlicher E-Rechnungs-Validierungs-Endpoint (login-frei)

POST /api/public/validate  ·  multipart/form-data  ·  Feld ``file``
(XML oder ZUGFeRD/Factur-X-PDF) · max 10 MB · KEINE Auth.

Reuse (nichts neu implementiert):
- KoSIT/EN-16931: ``KoSITValidator.validate()`` (immer) + ``validate_file()``
  (echtes KoSIT-Binary, falls vorhanden) – modules/.../kosit_validator.py
- ZUGFeRD-PDF → eingebettetes XML: ``einvoice_import.extract_xml_from_pdf``
- Lesbare Felder: ``einvoice_import.EInvoiceImporter().parse_xml``
- Rate-Limiter: ``rate_limiter`` (per-IP)

Sicherheit:
- XXE-Schutz: gehärteter lxml-Parser (keine Entity-/DTD-Auflösung, kein Netz).
- Eigener strenger per-IP Rate-Limit (15 / 10 min) → 429 + Retry-After.
- Keine Persistenz, keine PII im Log, Temp-Dateien werden verworfen.
- Niemals Stacktrace nach außen.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger("public_validate")

router = APIRouter(prefix="/api/public", tags=["Public Validate"])

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
RATE_LIMIT = 15
RATE_WINDOW = 600  # 10 Minuten
VALIDATION_TIMEOUT = 25  # Sekunden (CPU-intensiv) → 504


# ---------------------------------------------------------------------------
# XXE-sicherer XML-Parser (lxml, keine Entities/DTD/Netz)
# ---------------------------------------------------------------------------
def _safe_parser():
    from lxml import etree
    return etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False,
        dtd_validation=False, huge_tree=False,
    )


def _safe_parse(xml_bytes: bytes):
    """Parst XML XXE-sicher. Wirft lxml.etree.XMLSyntaxError bei Müll."""
    from lxml import etree
    return etree.fromstring(xml_bytes, _safe_parser())


# ---------------------------------------------------------------------------
# Rate-Limit (eigener, strenger per-IP Limiter mit Retry-After)
# ---------------------------------------------------------------------------
def _rate_limited(request: Request) -> Optional[int]:
    """Gibt Retry-After (Sekunden) zurück, wenn limitiert, sonst None."""
    try:
        from rate_limiter import limiter, get_client_ip
        ip = get_client_ip(request)
        if not limiter.is_allowed(ip, "/api/public/validate", RATE_LIMIT, RATE_WINDOW):
            return RATE_WINDOW
    except Exception as exc:  # pragma: no cover - Limiter darf nie hart brechen
        logger.debug("rate_limit skip: %s", exc)
    return None


def _err(status: int, message: str, headers: Optional[Dict[str, str]] = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message}, headers=headers or {})


# ---------------------------------------------------------------------------
# Helfer
# ---------------------------------------------------------------------------
def _none_if_empty(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _num(value: Any) -> Any:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


_RULE_RE = re.compile(r"(BR-[A-Z]*-?\d+|BR-[A-Z]+-\d+|BR-\d+)")
_FIELD_RE = re.compile(r"(BT-\d+|BG-\d+)")


def _message(level: str, text: str) -> Dict[str, Any]:
    rule = _RULE_RE.search(text)
    field = _FIELD_RE.search(text)
    return {
        "level": level,
        "rule": rule.group(1) if rule else None,
        "field": field.group(1) if field else None,
        "text": text,
    }


def _detect_format(root_tag: str, from_pdf: bool) -> str:
    if from_pdf:
        return "ZUGFERD_PDF"
    t = (root_tag or "").lower()
    if "crossindustryinvoice" in t:
        return "CII"
    if "invoice" in t:
        return "UBL"
    return "UNKNOWN"


def _build_readable(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Mappt parse_xml-Ausgabe → Vertrags-``readable`` (fehlend = null)."""
    line_items: List[Dict[str, Any]] = []
    for pos in (parsed.get("positionen") or parsed.get("line_items") or []):
        if isinstance(pos, dict):
            line_items.append({
                "name": _none_if_empty(pos.get("bezeichnung") or pos.get("name") or pos.get("description")),
                "quantity": _num(pos.get("menge") or pos.get("quantity")),
                "unitPrice": _num(pos.get("einzelpreis") or pos.get("unitPrice")),
                "net": _num(pos.get("netto") or pos.get("net") or pos.get("total")),
                "vatRate": _num(pos.get("mwst_satz") or pos.get("vatRate")),
            })
    return {
        "invoiceNumber": _none_if_empty(parsed.get("rechnungsnummer")),
        "issueDate": _none_if_empty(parsed.get("datum")),
        "dueDate": _none_if_empty(parsed.get("faelligkeitsdatum")),
        "seller": {
            "name": _none_if_empty(parsed.get("rechnungsaussteller")),
            "vatId": _none_if_empty(parsed.get("ust_idnr") or parsed.get("ust_id") or parsed.get("steuernummer")),
            "address": _none_if_empty(parsed.get("rechnungsaussteller_adresse")),
        },
        "buyer": {
            "name": _none_if_empty(parsed.get("rechnungsempfaenger")),
            "vatId": _none_if_empty(parsed.get("buyer_ust_idnr")),
            "address": _none_if_empty(parsed.get("rechnungsempfaenger_adresse")),
        },
        "lineItems": line_items,
        "totals": {
            "net": _num(parsed.get("betrag_netto")),
            "vat": _num(parsed.get("mwst_betrag")),
            "gross": _num(parsed.get("betrag_brutto")),
            "currency": _none_if_empty(parsed.get("waehrung")) or "EUR",
        },
    }


def _run_validation(xml_bytes: bytes) -> Dict[str, Any]:
    """Führt die (wiederverwendete) KoSIT-Validierung aus und normalisiert."""
    from modules.rechnungsverarbeitung.src.invoices.services.kosit_validator import KoSITValidator

    validator = KoSITValidator()
    result = validator.validate(xml_bytes)  # immer verfügbar (lxml, EN16931 + BR-DE)

    errors = list(result.errors)
    warnings = list(result.warnings)

    # Ebenen-Mapping
    syntax = "error" if any("XML Syntax Error" in e or "Root element must be" in e for e in errors) else "ok"
    schema_errs = [e for e in errors if _FIELD_RE.search(e)]
    schema = "error" if schema_errs else "ok"
    br_errs = [e for e in errors if "BR-" in e]
    br_warns = [w for w in warnings if "BR-" in w]
    if br_errs:
        schematron = "error"
    elif br_warns:
        schematron = "warning"
    else:
        schematron = "ok"
    if syntax == "error":
        schema = "error"
        schematron = "skipped"

    # Echtes KoSIT-Binary (falls vorhanden) als zusätzliche Schematron-Quelle
    engine = "kosit-python"
    try:
        with tempfile.TemporaryDirectory() as td:
            xmlp = os.path.join(td, "invoice.xml")
            with open(xmlp, "wb") as fh:
                fh.write(xml_bytes)
            file_res = validator.validate_file(xmlp, td)
        if file_res.engine == "kosit":  # echtes Prüftool lief
            engine = "kosit"
            if file_res.status == "failed":
                schematron = "error"
                errors.extend(file_res.errors)
            elif file_res.status == "passed" and schematron == "ok":
                schematron = "ok"
    except Exception as exc:  # pragma: no cover
        logger.debug("kosit binary skip: %s", exc)

    messages = [_message("error", e) for e in errors] + [_message("warning", w) for w in warnings]
    return {
        "engine": engine,
        "levels": {"syntax": syntax, "schema": schema, "schematron": schematron},
        "errors": errors,
        "warnings": warnings,
        "messages": messages,
        "valid": len(errors) == 0,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post("/validate")
async def public_validate(request: Request, file: UploadFile = File(...)):
    retry = _rate_limited(request)
    if retry is not None:
        return _err(429, "Zu viele Anfragen. Bitte später erneut versuchen.",
                    headers={"Retry-After": str(retry)})

    content = await file.read()
    if not content:
        return _err(400, "Leere Datei.")
    if len(content) > MAX_BYTES:
        return _err(400, "Datei zu groß (max. 10 MB).")

    head = content[:1024].lstrip()
    is_pdf = content[:5] == b"%PDF-"
    is_xml = head[:5].lower() == b"<?xml" or head[:1] == b"<"
    ctype = (file.content_type or "").lower()

    from_pdf = False
    xml_bytes: Optional[bytes] = None

    if is_pdf or ctype == "application/pdf" or (file.filename or "").lower().endswith(".pdf"):
        if not is_pdf:
            return _err(400, "Ungültige PDF (Magic-Bytes).")
        from_pdf = True
        # ZUGFeRD/Factur-X eingebettetes XML extrahieren (Reuse, Temp, kein Archiv)
        tmp_pdf = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
                tf.write(content)
                tmp_pdf = tf.name
            from einvoice_import import extract_xml_from_pdf
            xml_str = extract_xml_from_pdf(tmp_pdf)
        except Exception as exc:
            logger.info("pdf extract failed: %s", type(exc).__name__)
            xml_str = None
        finally:
            if tmp_pdf and os.path.exists(tmp_pdf):
                os.remove(tmp_pdf)
        if not xml_str:
            return _err(422, "Kein eingebettetes E-Rechnungs-XML im PDF gefunden (ZUGFeRD/Factur-X erforderlich).")
        xml_bytes = xml_str.encode("utf-8") if isinstance(xml_str, str) else xml_str
    elif is_xml or ctype in ("application/xml", "text/xml") or (file.filename or "").lower().endswith(".xml"):
        if not is_xml:
            return _err(400, "Ungültiges XML (Magic-Bytes).")
        xml_bytes = content
    else:
        return _err(400, "Dateityp nicht erlaubt. Erlaubt: XML oder ZUGFeRD/Factur-X-PDF.")

    # XXE-sicher parsen (für readable + Format) – blockiert externe Entities/DTD
    try:
        root = _safe_parse(xml_bytes)
        root_tag = root.tag
    except Exception:
        return _err(422, "XML konnte nicht geparst werden (ungültig oder nicht erlaubt).")

    # Validierung mit Timeout-Wächter (CPU-intensiv → 504)
    box: Dict[str, Any] = {}

    def _work():
        try:
            box["val"] = _run_validation(xml_bytes)
        except Exception as exc:  # pragma: no cover
            box["exc"] = exc

    t = threading.Thread(target=_work, daemon=True)
    t.start()
    t.join(VALIDATION_TIMEOUT)
    if t.is_alive():
        return _err(504, "Validierung hat das Zeitlimit überschritten.")
    if "exc" in box or "val" not in box:
        return _err(422, "Validierung fehlgeschlagen.")
    val = box["val"]

    # Lesbare Felder (best effort, fehlend = null)
    readable = {"invoiceNumber": None, "issueDate": None, "dueDate": None,
                "seller": {"name": None, "vatId": None, "address": None},
                "buyer": {"name": None, "vatId": None, "address": None},
                "lineItems": [], "totals": {"net": None, "vat": None, "gross": None, "currency": "EUR"}}
    try:
        from einvoice_import import EInvoiceImporter
        parsed = EInvoiceImporter().parse_xml(
            xml_bytes.decode("utf-8", errors="ignore") if isinstance(xml_bytes, bytes) else xml_bytes
        )
        if isinstance(parsed, dict) and "error" not in parsed:
            readable = _build_readable(parsed)
            profile = parsed.get("profile") or "EN16931"
        else:
            profile = "EN16931"
    except Exception:  # pragma: no cover
        profile = "EN16931"

    fmt = _detect_format(root_tag, from_pdf)
    return JSONResponse(status_code=200, content={
        "level": val["levels"],
        "summary": {
            "valid": val["valid"],
            "errors": len(val["errors"]),
            "warnings": len(val["warnings"]),
            "format": fmt,
            "profile": profile,
            "engine": val["engine"],  # transparent: 'kosit' (echtes Prüftool) | 'kosit-python' (Fallback)
        },
        "messages": val["messages"],
        "readable": readable,
    })
