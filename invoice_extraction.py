#!/usr/bin/env python3
"""
SBS Deutschland – KI-Extraktions-Pipeline für Eingangsrechnungen

Schritte:
  1. Text aus PDF extrahieren (pdfplumber, OCR-Fallback via pytesseract)
  2. Felder per KI extrahieren (Claude Sonnet / GPT-4o, JSON, Timeout 30s)
  3. Deterministische Validierung (IBAN, §14 UStG, USt-IdNr-Format)
  4. Regelbasierter Kontierungsvorschlag (SKR03)
  5. Invoice-Record aktualisieren, Status setzen

Robust: schlägt die KI-Extraktion fehl (kein API-Key, Timeout, kein Text),
wird der Status entsprechend gesetzt – ohne den Upload-Request zu sprengen.

Der eigentliche LLM-Aufruf ist in ``_call_llm`` gekapselt (für Tests mockbar).
"""

from __future__ import annotations

import json
import logging
import os
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LLM_TIMEOUT = int(os.getenv("EXTRACTION_LLM_TIMEOUT", "30"))

# Zentrales Anthropic-Modell für ALLE Extraktions-/KI-Aufrufe (Rechnungs-
# extraktion UND Auto-Kategorisierung). Über EXTRACTION_MODEL_ANTHROPIC
# konfigurierbar, damit ein Modell-Rename nicht in mehreren Dateien nachgezogen
# werden muss.
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4o"


def get_anthropic_extraction_model() -> str:
    """Anthropic-Modell für Extraktions-/KI-Aufrufe (Env: EXTRACTION_MODEL_ANTHROPIC)."""
    return os.getenv("EXTRACTION_MODEL_ANTHROPIC", DEFAULT_ANTHROPIC_MODEL)


def get_openai_extraction_model() -> str:
    """OpenAI-Modell für Extraktions-Aufrufe (Env: EXTRACTION_MODEL_OPENAI)."""
    return os.getenv("EXTRACTION_MODEL_OPENAI", DEFAULT_OPENAI_MODEL)

# Zielfelder der Extraktion
FIELDS = [
    "rechnungsaussteller", "rechnungsaussteller_adresse", "rechnungsempfaenger",
    "rechnungsempfaenger_adresse", "rechnungsnummer", "datum", "faelligkeitsdatum",
    "kundennummer", "betrag_brutto", "betrag_netto", "mwst_betrag", "mwst_satz",
    "waehrung", "iban", "bic", "steuernummer", "ust_idnr", "zahlungsbedingungen",
    "artikel",
]

_EXTRACTION_PROMPT = (
    "Extrahiere folgende Felder aus dieser deutschen Rechnung als JSON:\n"
    "- rechnungsaussteller (Firmenname des Absenders)\n"
    "- rechnungsaussteller_adresse\n- rechnungsempfaenger\n- rechnungsempfaenger_adresse\n"
    "- rechnungsnummer\n- datum (Format: YYYY-MM-DD)\n- faelligkeitsdatum (Format: YYYY-MM-DD)\n"
    "- kundennummer\n- betrag_brutto (Dezimalzahl)\n- betrag_netto (Dezimalzahl)\n"
    "- mwst_betrag (Dezimalzahl)\n- mwst_satz (Dezimalzahl, z.B. 19.0)\n- waehrung (z.B. EUR)\n"
    "- iban\n- bic\n- steuernummer\n- ust_idnr\n- zahlungsbedingungen\n"
    "- artikel (Zusammenfassung der Positionen)\n\n"
    "Antworte NUR mit validem JSON, keine Erklärung."
)


class NoLLMConfigured(RuntimeError):
    """Kein ANTHROPIC_API_KEY/OPENAI_API_KEY konfiguriert."""


class LLMProviderError(RuntimeError):
    """Der LLM-Provider hat mit einem 4xx/5xx-Status geantwortet.

    Trägt Statuscode + Antworttext, damit beides in der Fehler-Zeile der
    Rechnung landet (nicht nur im httpx-Log)."""

    def __init__(self, status_code: Optional[int], detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Provider-Fehler {status_code}: {detail}")


def _as_provider_error(exc: Exception) -> Optional["LLMProviderError"]:
    """Erkennt Provider-Statusfehler (Anthropic/OpenAI ``APIStatusError`` u. ä.)
    und extrahiert Statuscode + Antworttext. Gibt ``None`` zurück, wenn ``exc``
    kein HTTP-Statusfehler ist (z. B. Timeout/Netzwerk)."""
    status = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None)
    if status is None:
        return None
    detail = ""
    if response is not None:
        try:
            detail = (response.text or "").strip()
        except Exception:  # pragma: no cover - defensive
            detail = ""
    if not detail:
        detail = str(getattr(exc, "message", "") or exc).strip()
    return LLMProviderError(int(status), detail[:500])


# ---------------------------------------------------------------------------
# Schema: Zusatzspalten für Validierung/Kontierung
# ---------------------------------------------------------------------------
def ensure_extraction_columns() -> None:
    from database import get_connection

    conn = get_connection()
    cur = conn.cursor()
    for col in ("validierung_json", "kontierung_json", "datei_pfad"):
        try:
            cur.execute(f"PRAGMA table_info(invoices)")
            existing = [r[1] for r in cur.fetchall()]
            if col not in existing:
                cur.execute(f"ALTER TABLE invoices ADD COLUMN {col} TEXT")
        except Exception as exc:  # pragma: no cover
            logger.debug("ensure_extraction_columns %s: %s", col, exc)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Schritt 2: Text-Extraktion
# ---------------------------------------------------------------------------
def extract_text_from_pdf(filepath: str) -> str:
    """Extrahiert Text aus einem PDF (pdfplumber)."""
    import pdfplumber

    with pdfplumber.open(filepath) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _ocr_pdf(filepath: str) -> str:
    """OCR-Fallback für Scans ohne Textebene (pytesseract + pdf2image)."""
    try:
        import pdf2image
        import pytesseract

        images = pdf2image.convert_from_path(filepath)
        return "\n".join(pytesseract.image_to_string(img, lang="deu") for img in images)
    except Exception as exc:  # pragma: no cover - poppler/tesseract optional
        logger.info("OCR-Fallback nicht verfügbar: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Schritt 3: KI-Extraktion
# ---------------------------------------------------------------------------
def _parse_json(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def _call_llm(text: str) -> Dict[str, Any]:
    """Ruft das LLM auf und gibt das geparste JSON zurück (mockbar in Tests)."""
    prompt = f"{_EXTRACTION_PROMPT}\n\nRechnungstext:\n{text[:12000]}"

    if os.getenv("ANTHROPIC_API_KEY"):
        from anthropic import Anthropic

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), timeout=LLM_TIMEOUT)
        model = get_anthropic_extraction_model()
        try:
            msg = client.messages.create(
                model=model, max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            provider_err = _as_provider_error(exc)
            if provider_err is not None:
                logger.warning("Anthropic %s (Modell %s): %s",
                               provider_err.status_code, model, provider_err.detail)
                raise provider_err from exc
            raise
        return _parse_json(msg.content[0].text)

    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=LLM_TIMEOUT)
        model = get_openai_extraction_model()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            provider_err = _as_provider_error(exc)
            if provider_err is not None:
                logger.warning("OpenAI %s (Modell %s): %s",
                               provider_err.status_code, model, provider_err.detail)
                raise provider_err from exc
            raise
        return _parse_json(resp.choices[0].message.content)

    raise NoLLMConfigured("Kein ANTHROPIC_API_KEY/OPENAI_API_KEY konfiguriert")


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("€", "").replace(" ", "")
    # deutsches Format 1.234,56 → 1234.56
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(re.sub(r"[^0-9.\-]", "", s))
    except ValueError:
        return None


_CENT = Decimal("0.01")


def _money(value: Decimal) -> float:
    """Kaufmännische Rundung auf 2 Dezimalstellen (ROUND_HALF_UP), als float.

    Beträge werden durchgängig in ``Decimal`` gerechnet – Pythons Float-``round``
    nutzt Banker's Rounding auf Binärbrüchen und würde z. B. 0,475 € auf 0,47 €
    statt (kaufmännisch korrekt) 0,48 € runden."""
    return float(value.quantize(_CENT, rounding=ROUND_HALF_UP))


def _complete_amounts(fields: Dict[str, Any]) -> None:
    """Ergänzt fehlende Beträge (brutto/netto/mwst_betrag) aus den vorhandenen.

    GoBD: berechnete Werte werden NUR gesetzt, wenn das Zielfeld leer ist und der
    Wert eindeutig aus extrahierten Feldern folgt – extrahierte Originalwerte
    haben immer Vorrang und werden nie überschrieben. Berechnung in ``Decimal``
    mit kaufmännischer Cent-Rundung (ROUND_HALF_UP). Kombinationen:

      netto + satz        → mwst_betrag = netto·satz/100, brutto = netto+mwst
      netto + mwst_betrag → brutto = netto+mwst
      brutto + satz       → netto = brutto/(1+satz/100), mwst_betrag = brutto−netto
      brutto + netto      → mwst_betrag = brutto−netto
    """
    def dec(key: str) -> Optional[Decimal]:
        v = fields.get(key)
        return Decimal(str(v)) if isinstance(v, (int, float)) else None

    def empty(key: str) -> bool:
        return fields.get(key) is None

    satz = dec("mwst_satz")
    has_satz = satz is not None and satz >= 0  # 0 % (steuerfrei) ist gültig

    # netto + satz → mwst_betrag, brutto
    if dec("betrag_netto") is not None and has_satz:
        if empty("mwst_betrag"):
            fields["mwst_betrag"] = _money(dec("betrag_netto") * satz / Decimal(100))
        if empty("betrag_brutto") and dec("mwst_betrag") is not None:
            fields["betrag_brutto"] = _money(dec("betrag_netto") + dec("mwst_betrag"))

    # brutto + satz → netto, mwst_betrag
    if dec("betrag_brutto") is not None and has_satz:
        if empty("betrag_netto"):
            fields["betrag_netto"] = _money(dec("betrag_brutto") / (Decimal(1) + satz / Decimal(100)))
        if empty("mwst_betrag") and dec("betrag_netto") is not None:
            fields["mwst_betrag"] = _money(dec("betrag_brutto") - dec("betrag_netto"))

    # netto + mwst_betrag → brutto
    if (dec("betrag_netto") is not None and dec("mwst_betrag") is not None
            and empty("betrag_brutto")):
        fields["betrag_brutto"] = _money(dec("betrag_netto") + dec("mwst_betrag"))

    # brutto + netto → mwst_betrag
    if (dec("betrag_brutto") is not None and dec("betrag_netto") is not None
            and empty("mwst_betrag")):
        fields["mwst_betrag"] = _money(dec("betrag_brutto") - dec("betrag_netto"))


def normalize_fields(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Bringt LLM-Felder in DB-Form (nur bekannte Felder, Beträge als float)."""
    out: Dict[str, Any] = {f: raw.get(f) for f in FIELDS}
    for num in ("betrag_brutto", "betrag_netto", "mwst_betrag", "mwst_satz"):
        out[num] = _to_float(out.get(num))
    # Fehlende Beträge aus den vorhandenen ableiten (ohne Überschreiben).
    _complete_amounts(out)
    if isinstance(out.get("artikel"), (list, dict)):
        out["artikel"] = json.dumps(out["artikel"], ensure_ascii=False)
    if not out.get("waehrung"):
        out["waehrung"] = "EUR"
    return out


# ---------------------------------------------------------------------------
# Schritt 4: Validierung (deterministisch)
# ---------------------------------------------------------------------------
def run_validation(fields: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name, ok, severity, message):
        checks.append({"name": name, "ok": bool(ok), "severity": severity, "message": message})

    # §14 UStG Pflichtangaben
    pflicht = {
        "rechnungsaussteller": "Name des Leistenden",
        "rechnungsnummer": "Rechnungsnummer",
        "datum": "Rechnungsdatum",
        "betrag_brutto": "Rechnungsbetrag",
    }
    for key, label in pflicht.items():
        add(f"§14_{key}", bool(fields.get(key)), "error", f"Pflichtangabe fehlt: {label}")
    has_tax_id = bool(fields.get("steuernummer") or fields.get("ust_idnr"))
    add("§14_steuer_id", has_tax_id, "error", "Steuernummer oder USt-IdNr. erforderlich")
    has_vat = fields.get("mwst_satz") is not None or fields.get("mwst_betrag") is not None
    add("§14_umsatzsteuer", has_vat, "warning", "USt-Satz/-Betrag fehlt")

    # IBAN
    iban = (fields.get("iban") or "").replace(" ", "")
    if iban:
        try:
            from sepa_export import validate_iban
            ok = bool(validate_iban(iban))
        except Exception:
            ok = bool(re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$", iban))
        add("iban", ok, "warning", "IBAN ungültig" if not ok else "IBAN gültig")

    # USt-IdNr-Format
    ust = (fields.get("ust_idnr") or "").replace(" ", "")
    if ust:
        ok = bool(re.match(r"^[A-Z]{2}[A-Z0-9]{2,12}$", ust))
        add("ust_idnr_format", ok, "warning", "USt-IdNr.-Format ungültig" if not ok else "Format ok")

    # Betragsplausibilität: netto + mwst ≈ brutto
    b, n, m = fields.get("betrag_brutto"), fields.get("betrag_netto"), fields.get("mwst_betrag")
    if b is not None and n is not None and m is not None:
        ok = abs((n + m) - b) <= max(0.02, b * 0.01)
        add("betrag_summe", ok, "warning", "Netto + USt ≠ Brutto" if not ok else "Summen stimmig")

    errors = [c for c in checks if not c["ok"] and c["severity"] == "error"]
    return {"ok": not errors, "error_count": len(errors), "checks": checks}


# ---------------------------------------------------------------------------
# Schritt 5: Kontierung (regelbasiert, SKR03)
# ---------------------------------------------------------------------------
def suggest_kontierung(fields: Dict[str, Any]) -> Dict[str, Any]:
    satz = fields.get("mwst_satz")
    try:
        satz = float(satz) if satz is not None else 0.0
    except (TypeError, ValueError):
        satz = 0.0
    if 18.0 <= satz <= 20.0:
        steuerschluessel = 9
    elif 6.0 <= satz <= 8.0:
        steuerschluessel = 8
    else:
        steuerschluessel = 0
    return {"konto": 4400, "gegenkonto": 1200, "steuerschluessel": steuerschluessel,
            "kontenrahmen": "SKR03"}


# ---------------------------------------------------------------------------
# Orchestrierung
# ---------------------------------------------------------------------------
def process_pdf(filepath: str) -> Dict[str, Any]:
    """Führt die komplette Pipeline für eine Datei aus.

    Returns dict mit: status, fields, validation, kontierung, error.
    Status: 'verarbeitet' | 'fehler' | 'manuell_erforderlich'.
    """
    result: Dict[str, Any] = {"status": "fehler", "fields": {}, "validation": None,
                              "kontierung": None, "error": None}

    # Schritt 2: Text
    try:
        text = extract_text_from_pdf(filepath)
    except Exception as exc:
        result["error"] = f"Text-Extraktion fehlgeschlagen: {exc}"
        return result

    if not text or not text.strip():
        text = _ocr_pdf(filepath)
    if not text or not text.strip():
        result["status"] = "manuell_erforderlich"
        result["error"] = "Kein Text extrahierbar (Scan ohne OCR)"
        return result

    # Schritt 3: KI
    try:
        raw = _call_llm(text)
        fields = normalize_fields(raw)
    except NoLLMConfigured as exc:
        result["error"] = str(exc)
        return result
    except LLMProviderError as exc:
        # Provider-4xx/5xx: Statuscode + Antworttext in die Fehler-Zeile.
        result["error"] = f"KI-Provider HTTP {exc.status_code}: {exc.detail}"
        return result
    except Exception as exc:
        result["error"] = f"KI-Extraktion fehlgeschlagen: {exc}"
        return result

    # Schritt 4+5
    validation = run_validation(fields)
    kontierung = suggest_kontierung(fields)

    result.update({"status": "verarbeitet", "fields": fields,
                   "validation": validation, "kontierung": kontierung})
    return result


def update_invoice_record(invoice_id: int, result: Dict[str, Any]) -> None:
    """Schreibt Extraktionsergebnis in den Invoice-Record."""
    from database import get_connection

    conn = get_connection()
    cur = conn.cursor()
    status = result.get("status", "fehler")

    if status == "verarbeitet":
        f = result["fields"]
        cur.execute(
            """
            UPDATE invoices SET
              rechnungsaussteller = ?, rechnungsaussteller_adresse = ?,
              rechnungsempfaenger = ?, rechnungsempfaenger_adresse = ?,
              rechnungsnummer = ?, datum = ?, faelligkeitsdatum = ?, kundennummer = ?,
              betrag_brutto = ?, betrag_netto = ?, mwst_betrag = ?, mwst_satz = ?,
              waehrung = ?, iban = ?, bic = ?, steuernummer = ?, ust_idnr = ?,
              zahlungsbedingungen = ?, artikel = ?,
              validierung_json = ?, kontierung_json = ?, status = 'verarbeitet'
            WHERE id = ?
            """,
            (
                f.get("rechnungsaussteller"), f.get("rechnungsaussteller_adresse"),
                f.get("rechnungsempfaenger"), f.get("rechnungsempfaenger_adresse"),
                f.get("rechnungsnummer"), f.get("datum"), f.get("faelligkeitsdatum"),
                f.get("kundennummer"), f.get("betrag_brutto"), f.get("betrag_netto"),
                f.get("mwst_betrag"), f.get("mwst_satz"), f.get("waehrung"), f.get("iban"),
                f.get("bic"), f.get("steuernummer"), f.get("ust_idnr"),
                f.get("zahlungsbedingungen"), f.get("artikel"),
                json.dumps(result.get("validation"), ensure_ascii=False),
                json.dumps(result.get("kontierung"), ensure_ascii=False),
                int(invoice_id),
            ),
        )
    else:
        # Fehler / manuell_erforderlich – Grund in verwendungszweck (keine PII-Beträge)
        cur.execute(
            "UPDATE invoices SET status = ?, verwendungszweck = ? WHERE id = ?",
            (status, (result.get("error") or "")[:500], int(invoice_id)),
        )
    conn.commit()
    conn.close()
