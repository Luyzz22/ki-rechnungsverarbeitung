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


# --- Zentrale Modell-Konfiguration (env-überschreibbar) -------------------
def test_default_anthropic_model_is_sonnet_4_6(monkeypatch):
    monkeypatch.delenv("EXTRACTION_MODEL_ANTHROPIC", raising=False)
    assert ie.get_anthropic_extraction_model() == "claude-sonnet-4-6"
    assert ie.DEFAULT_ANTHROPIC_MODEL == "claude-sonnet-4-6"


def test_anthropic_model_env_override(monkeypatch):
    monkeypatch.setenv("EXTRACTION_MODEL_ANTHROPIC", "claude-test-xyz")
    assert ie.get_anthropic_extraction_model() == "claude-test-xyz"


def test_category_ai_uses_central_model(monkeypatch):
    """category_ai muss dasselbe zentrale Modell wie die Extraktion nutzen –
    nicht mehr hartkodiert (früher claude-sonnet-4-20250514)."""
    import category_ai
    captured = {}

    class _FakeMessages:
        def create(self, **kw):
            captured["model"] = kw["model"]

            class _Content:
                text = '{"category_id": 5, "confidence": 0.9, "reasoning": "ok"}'

            class _Resp:
                content = [_Content()]

            return _Resp()

    class _FakeAnthropic:
        def __init__(self, **kw):
            self.messages = _FakeMessages()

    monkeypatch.setattr(category_ai, "Anthropic", _FakeAnthropic)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("EXTRACTION_MODEL_ANTHROPIC", "claude-sonnet-4-6")
    monkeypatch.setattr(category_ai, "get_learned_category", lambda s, u: None)
    monkeypatch.setattr(category_ai, "get_all_categories", lambda uid: [
        {"id": 5, "name": "Lebensmittel", "description": "x", "account_number": "4400"}])

    cid, conf, reason = category_ai.predict_category({"rechnungsaussteller": "EDEKA"}, user_id=1)
    assert captured["model"] == "claude-sonnet-4-6"
    assert cid == 5 and conf == 0.9


# --- Provider-4xx/5xx landen in der Fehler-Zeile --------------------------
class _FakeResponse:
    def __init__(self, status, text):
        self.status_code = status
        self.text = text


class _FakeStatusError(Exception):
    """Nachbildung von anthropic/openai APIStatusError (status_code + response)."""

    def __init__(self, status, text):
        self.status_code = status
        self.response = _FakeResponse(status, text)
        self.message = text
        super().__init__(text)


def test_as_provider_error_extracts_status_and_text():
    err = ie._as_provider_error(_FakeStatusError(404, "not_found_error: model unknown"))
    assert isinstance(err, ie.LLMProviderError)
    assert err.status_code == 404
    assert "not_found_error" in err.detail


def test_as_provider_error_ignores_non_status():
    # Timeout/Netzwerkfehler ohne HTTP-Status → kein Provider-Statusfehler
    assert ie._as_provider_error(RuntimeError("timeout")) is None


def test_process_pdf_provider_4xx_in_error_line(monkeypatch):
    path = _write_pdf("Rechnung\nAcme GmbH\n119,00 EUR")

    def _raise(text):
        raise ie.LLMProviderError(404, "not_found_error: model claude-x")

    monkeypatch.setattr(ie, "_call_llm", _raise)
    res = ie.process_pdf(path)
    assert res["status"] == "fehler"
    assert "404" in (res["error"] or "")
    assert "not_found_error" in (res["error"] or "")


def test_call_llm_wraps_anthropic_status_error(monkeypatch):
    """Ungültiges Modell → Anthropic wirft 404; _call_llm übersetzt es in einen
    LLMProviderError mit Statuscode + Text (statt es nur ins httpx-Log zu geben)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class _FakeMessages:
        def create(self, **kw):
            raise _FakeStatusError(404, f"model {kw.get('model')} not found")

    class _FakeAnthropic:
        def __init__(self, **kw):
            self.messages = _FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic)
    with pytest.raises(ie.LLMProviderError) as exc_info:
        ie._call_llm("irgendein Rechnungstext")
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail
