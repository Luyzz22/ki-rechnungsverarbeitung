"""Tests der KI-Extraktions-Pipeline (invoice_extraction)."""

import io
import os
import tempfile

import pytest

import invoice_extraction as ie


def _pdf_bytes(text):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in text.split("\n"):
        c.drawString(72, y, line)
        y -= 18
    c.save()
    return buf.getvalue()


def _write_pdf(text):
    path = os.path.join(tempfile.mkdtemp(), "r.pdf")
    with open(path, "wb") as f:
        f.write(_pdf_bytes(text))
    return path


# --- Schritt 2: Text-Extraktion ------------------------------------------
def test_extract_text_from_pdf():
    path = _write_pdf("Rechnung Nr. 2026-007\nMuster GmbH")
    text = ie.extract_text_from_pdf(path)
    assert "Rechnung Nr. 2026-007" in text
    assert "Muster GmbH" in text


# --- normalize_fields -----------------------------------------------------
def test_normalize_german_numbers():
    f = ie.normalize_fields({"betrag_brutto": "1.234,56", "mwst_satz": "19,0",
                             "artikel": [{"pos": 1}]})
    assert f["betrag_brutto"] == 1234.56
    assert f["mwst_satz"] == 19.0
    assert isinstance(f["artikel"], str)  # Liste → JSON-String
    assert f["waehrung"] == "EUR"


# --- Schritt 4: Validierung ----------------------------------------------
def test_validation_full_ok():
    v = ie.run_validation({
        "rechnungsaussteller": "Acme GmbH", "rechnungsnummer": "1", "datum": "2026-01-01",
        "betrag_brutto": 119.0, "betrag_netto": 100.0, "mwst_betrag": 19.0,
        "mwst_satz": 19.0, "steuernummer": "12/345/67890",
        "iban": "DE89370400440532013000",
    })
    assert v["ok"] is True and v["error_count"] == 0


def test_validation_missing_pflicht():
    v = ie.run_validation({"rechnungsaussteller": "Acme"})  # nummer/datum/betrag fehlen
    assert v["ok"] is False
    assert v["error_count"] >= 3


def test_validation_bad_iban_flagged():
    v = ie.run_validation({
        "rechnungsaussteller": "A", "rechnungsnummer": "1", "datum": "2026-01-01",
        "betrag_brutto": 1.0, "steuernummer": "x", "iban": "DE00INVALID",
    })
    iban_check = next(c for c in v["checks"] if c["name"] == "iban")
    assert iban_check["ok"] is False


# --- Schritt 5: Kontierung ------------------------------------------------
@pytest.mark.parametrize("satz,expected", [(19.0, 9), (7.0, 8), (0.0, 0), (None, 0)])
def test_kontierung_steuerschluessel(satz, expected):
    k = ie.suggest_kontierung({"mwst_satz": satz})
    assert k["konto"] == 4400 and k["gegenkonto"] == 1200
    assert k["steuerschluessel"] == expected


# --- Orchestrierung -------------------------------------------------------
def test_process_pdf_success(monkeypatch):
    path = _write_pdf("Rechnung\nAcme GmbH\n119,00 EUR")
    monkeypatch.setattr(ie, "_call_llm", lambda text: {
        "rechnungsaussteller": "Acme GmbH", "rechnungsnummer": "R1", "datum": "2026-01-01",
        "betrag_brutto": "119,00", "mwst_satz": "19.0", "steuernummer": "12/345/67890",
    })
    res = ie.process_pdf(path)
    assert res["status"] == "verarbeitet"
    assert res["fields"]["rechnungsaussteller"] == "Acme GmbH"
    assert res["kontierung"]["steuerschluessel"] == 9
    assert res["validation"]["ok"] is True


def test_process_pdf_no_llm(monkeypatch):
    path = _write_pdf("Rechnung\nAcme GmbH")
    def _raise(text):
        raise ie.NoLLMConfigured("kein key")
    monkeypatch.setattr(ie, "_call_llm", _raise)
    res = ie.process_pdf(path)
    assert res["status"] == "fehler"
    assert "key" in (res["error"] or "").lower()


def test_process_pdf_empty_text(monkeypatch):
    path = _write_pdf("x")
    monkeypatch.setattr(ie, "extract_text_from_pdf", lambda p: "")
    monkeypatch.setattr(ie, "_ocr_pdf", lambda p: "")
    res = ie.process_pdf(path)
    assert res["status"] == "manuell_erforderlich"
