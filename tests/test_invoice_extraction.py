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


# --- Betrags-Vervollständigung -------------------------------------------
def test_complete_amounts_netto_plus_satz():
    """id=31: netto 288,94 + 19 % → brutto 343,84, mwst_betrag 54,90; §14-Check grün."""
    f = ie.normalize_fields({"betrag_netto": "288,94", "mwst_satz": "19"})
    assert f["mwst_betrag"] == 54.90
    assert f["betrag_brutto"] == 343.84
    # §14-Betragscheck (netto + mwst ≈ brutto) muss grün sein
    v = ie.run_validation(f)
    summe = next(c for c in v["checks"] if c["name"] == "betrag_summe")
    assert summe["ok"] is True


def test_complete_amounts_netto_plus_mwstbetrag():
    f = ie.normalize_fields({"betrag_netto": 100.0, "mwst_betrag": 19.0})
    assert f["betrag_brutto"] == 119.0


def test_complete_amounts_brutto_plus_satz():
    f = ie.normalize_fields({"betrag_brutto": 343.84, "mwst_satz": 19.0})
    assert f["betrag_netto"] == 288.94
    assert f["mwst_betrag"] == 54.90


def test_complete_amounts_brutto_plus_netto():
    f = ie.normalize_fields({"betrag_brutto": 119.0, "betrag_netto": 100.0})
    assert f["mwst_betrag"] == 19.0


def test_complete_amounts_full_never_overwrites():
    """GoBD: extrahierte Originalwerte haben Vorrang – auch wenn (absichtlich)
    inkonsistent, wird nichts überschrieben."""
    f = ie.normalize_fields({"betrag_netto": 100.0, "mwst_satz": 19.0,
                             "mwst_betrag": 99.0, "betrag_brutto": 199.0})
    assert f["mwst_betrag"] == 99.0      # NICHT 19.0
    assert f["betrag_brutto"] == 199.0   # NICHT 119.0


@pytest.mark.parametrize("raw", [
    {"betrag_brutto": 119.0},   # nur brutto, kein satz/netto → nichts ableitbar
    {"betrag_netto": 100.0},    # nur netto, kein satz/mwst → nichts ableitbar
])
def test_complete_amounts_insufficient_data_no_derivation(raw):
    f = ie.normalize_fields(raw)
    present = [k for k in ("betrag_brutto", "betrag_netto", "mwst_betrag") if f[k] is not None]
    assert present == list(raw.keys())  # keine erfundenen Werte


def test_complete_amounts_zero_rate_steuerfrei():
    """0 % (steuerfrei) ist gültig: mwst_betrag = 0, brutto = netto."""
    f = ie.normalize_fields({"betrag_netto": 100.0, "mwst_satz": 0})
    assert f["mwst_betrag"] == 0.0
    assert f["betrag_brutto"] == 100.0


def test_complete_amounts_half_cent_rounds_up_commercially():
    """Halb-Cent-Fall (Codex P2): netto 2,50 · 19 % = 0,475 → kaufmännisch 0,48
    (nicht Banker's-Rounding 0,47). Decimal/ROUND_HALF_UP statt float-round."""
    f = ie.normalize_fields({"betrag_netto": 2.50, "mwst_satz": 19})
    assert f["mwst_betrag"] == 0.48
    assert f["betrag_brutto"] == 2.98
    v = ie.run_validation(f)
    summe = next(c for c in v["checks"] if c["name"] == "betrag_summe")
    assert summe["ok"] is True


# --- B2: Betragscheck fail-closed ----------------------------------------
def test_amount_check_fail_closed_on_null():
    """NULL-Beträge → betrag_summe ist FEHLER (nicht stillschweigend ok)."""
    v = ie.run_validation({"rechnungsaussteller": "A", "rechnungsnummer": "1",
                           "datum": "2026-01-01", "steuernummer": "x"})
    bs = next(c for c in v["checks"] if c["name"] == "betrag_summe")
    assert bs["ok"] is False and bs["severity"] == "error"
    assert "unvollständig" in bs["message"].lower()
    assert v["ok"] is False


def test_amount_check_fail_closed_on_all_zero():
    """0,00 + 0,00 = 0,00 darf NICHT als bestanden gewertet werden (Fail-open-Bug)."""
    v = ie.run_validation({"rechnungsaussteller": "A", "rechnungsnummer": "1",
                           "datum": "2026-01-01", "steuernummer": "x",
                           "betrag_brutto": 0.0, "betrag_netto": 0.0, "mwst_betrag": 0.0})
    bs = next(c for c in v["checks"] if c["name"] == "betrag_summe")
    assert bs["ok"] is False and bs["severity"] == "error"


def test_amount_check_ok_when_consistent():
    v = ie.run_validation({"rechnungsaussteller": "A", "rechnungsnummer": "1",
                           "datum": "2026-01-01", "steuernummer": "x",
                           "betrag_brutto": 119.0, "betrag_netto": 100.0, "mwst_betrag": 19.0})
    bs = next(c for c in v["checks"] if c["name"] == "betrag_summe")
    assert bs["ok"] is True


# --- B3: Status-Semantik --------------------------------------------------
def test_process_pdf_status_pruefen_when_validation_fails(monkeypatch):
    """Extraktion ok, aber §14-Prüfung fehlgeschlagen (fehlende Steuer-ID) → pruefen."""
    path = _write_pdf("Rechnung\nAcme GmbH")
    monkeypatch.setattr(ie, "_call_llm", lambda text: {
        "rechnungsaussteller": "Acme GmbH", "rechnungsnummer": "R1", "datum": "2026-01-01",
        "betrag_brutto": "119,00", "mwst_satz": "19.0",  # KEINE Steuer-ID
    })
    res = ie.process_pdf(path)
    assert res["status"] == "pruefen"
    assert res["validation"]["ok"] is False


def test_process_pdf_status_pruefen_when_amounts_incomplete(monkeypatch):
    """Nur netto, keine weiteren Beträge/Satz → Beträge unvollständig → pruefen."""
    path = _write_pdf("Rechnung\nAcme GmbH")
    monkeypatch.setattr(ie, "_call_llm", lambda text: {
        "rechnungsaussteller": "Acme GmbH", "rechnungsnummer": "R1", "datum": "2026-01-01",
        "steuernummer": "12/345/67890", "betrag_netto": "100,00",
    })
    res = ie.process_pdf(path)
    assert res["status"] == "pruefen"
    bs = next(c for c in res["validation"]["checks"] if c["name"] == "betrag_summe")
    assert bs["ok"] is False and bs["severity"] == "error"


# --- B1a: Truncation-Limit, Roh-Antwort, Prompt-Schärfung -----------------
def test_prompt_sharpened_issuer_and_null_guidance():
    assert "LEISTENDEN" in ie._EXTRACTION_PROMPT  # Aussteller = Leistender/Absender
    assert "null" in ie._EXTRACTION_PROMPT         # fehlende Felder nicht raten


def test_call_llm_captures_raw_and_respects_text_limit(monkeypatch):
    """Roh-Antwort landet unter __raw__; der Prompt erhält nur bis zum Limit."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(ie, "EXTRACTION_TEXT_LIMIT", 50)
    seen = {}

    class _Msg:
        def create(self, **kw):
            seen["prompt"] = kw["messages"][0]["content"]

            class _C:
                text = '{"rechnungsaussteller": "X GmbH"}'

            class _R:
                content = [_C()]

            return _R()

    class _FakeAnthropic:
        def __init__(self, **kw):
            self.messages = _Msg()

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic)
    out = ie._call_llm("A" * 500)
    assert out["__raw__"] == '{"rechnungsaussteller": "X GmbH"}'
    assert out["rechnungsaussteller"] == "X GmbH"
    # Rechnungstext im Prompt auf 50 Zeichen begrenzt
    body = seen["prompt"].split("Rechnungstext:\n", 1)[1]
    assert len(body) == 50


def test_call_llm_unparseable_preserves_raw(monkeypatch):
    """Malformed/truncated JSON → LLMResponseUnparseable mit erhaltener Roh-Antwort."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class _Msg:
        def create(self, **kw):
            class _C:
                text = "Sorry, hier ist die Rechnung: {unvollständig"

            class _R:
                content = [_C()]

            return _R()

    class _FakeAnthropic:
        def __init__(self, **kw):
            self.messages = _Msg()

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic)
    with pytest.raises(ie.LLMResponseUnparseable) as exc_info:
        ie._call_llm("text")
    assert "{unvollständig" in exc_info.value.raw


def test_process_pdf_unparseable_persists_raw_for_diagnosis(monkeypatch):
    """Parse-Fehler → Status fehler, aber Roh-Antwort landet in raw_response
    (Diagnose bleibt möglich, nicht 'blind')."""
    path = _write_pdf("Rechnung\nAcme GmbH")

    def _raise(text):
        raise ie.LLMResponseUnparseable("<<GARBAGE MODEL OUTPUT {>>")

    monkeypatch.setattr(ie, "_call_llm", _raise)
    res = ie.process_pdf(path)
    assert res["status"] == "fehler"
    assert res["raw_response"] == "<<GARBAGE MODEL OUTPUT {>>"
    assert "JSON" in (res["error"] or "")


def test_process_pdf_captures_raw_response(monkeypatch):
    path = _write_pdf("Rechnung\nAcme GmbH")
    monkeypatch.setattr(ie, "_call_llm", lambda text: {
        "rechnungsaussteller": "Acme GmbH", "rechnungsnummer": "R1", "datum": "2026-01-01",
        "steuernummer": "12/345/67890", "betrag_brutto": "119,00", "mwst_satz": "19.0",
        "__raw__": '{"rechnungsaussteller":"Acme GmbH"}  <<RAWMODEL>>',
    })
    res = ie.process_pdf(path)
    assert res["raw_response"] == '{"rechnungsaussteller":"Acme GmbH"}  <<RAWMODEL>>'
    assert "__raw__" not in res["fields"]


def test_update_invoice_record_pruefen_persists_fields_and_raw(tmp_path, monkeypatch):
    """update_invoice_record persistiert bei 'pruefen' die Felder (nicht nur Status)
    und legt die Roh-Antwort in extraktion_raw ab."""
    import sqlite3
    import database
    db = tmp_path / "upd.db"
    monkeypatch.setattr(database, "_ensure_db_path", lambda: db)
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE invoices (
            id INTEGER PRIMARY KEY, rechnungsaussteller TEXT, rechnungsaussteller_adresse TEXT,
            rechnungsempfaenger TEXT, rechnungsempfaenger_adresse TEXT, rechnungsnummer TEXT,
            datum TEXT, faelligkeitsdatum TEXT, kundennummer TEXT, betrag_brutto REAL,
            betrag_netto REAL, mwst_betrag REAL, mwst_satz REAL, waehrung TEXT, iban TEXT,
            bic TEXT, steuernummer TEXT, ust_idnr TEXT, zahlungsbedingungen TEXT, artikel TEXT,
            validierung_json TEXT, kontierung_json TEXT, status TEXT, verwendungszweck TEXT,
            extraktion_raw TEXT)""")
    conn.execute("INSERT INTO invoices (id, status) VALUES (7, 'pending')")
    conn.commit(); conn.close()

    result = {"status": "pruefen",
              "fields": {"rechnungsaussteller": "Acme GmbH", "betrag_netto": 100.0},
              "validation": {"ok": False}, "kontierung": {},
              "raw_response": "<<RAWMODELTEXT>>"}
    ie.update_invoice_record(7, result)

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT status, rechnungsaussteller, betrag_netto, extraktion_raw FROM invoices WHERE id=7"
    ).fetchone()
    conn.close()
    assert row[0] == "pruefen"
    assert row[1] == "Acme GmbH"
    assert row[2] == 100.0
    assert row[3] == "<<RAWMODELTEXT>>"


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


def test_process_pdf_two_stage_ocr_recovers_header_footer_fields(monkeypatch):
    """Aussteller/IBAN/USt-IdNr/Steuernummer stehen nur im Grafik-Fuß (kein
    Textlayer). Fehlen sie nach dem Text-Pass komplett, ergänzt ein zweiter
    Extraktionslauf über OCR die fehlenden Felder – ohne die bereits
    extrahierten Werte zu überschreiben."""
    path = _write_pdf("Rechnung IT2025032\nNetto 1.580,00 EUR")
    calls = {"n": 0}

    def _mock(text):
        calls["n"] += 1
        if "[OCR" in text:  # zweiter Lauf mit OCR-Text
            return {"rechnungsnummer": "WRONG-should-not-win", "betrag_brutto": "0,00",
                    "rechnungsaussteller": "SBS Deutschland GmbH & Co. KG",
                    "iban": "DE19100101238495732107", "bic": "QNTODEB2XXX",
                    "ust_idnr": "DE300066949", "steuernummer": "47013/22377"}
        # erster Lauf (nur Body): Aussteller/IBAN/USt/Steuer NULL
        return {"rechnungsnummer": "IT2025032", "betrag_brutto": "1880,20",
                "betrag_netto": "1580,00", "datum": "2025-09-29"}

    monkeypatch.setattr(ie, "_call_llm", _mock)
    monkeypatch.setattr(ie, "_ocr_pdf", lambda p:
                        "SBS DEUTSCHLAND GMBH & CO. KG\nIBAN: DE19 1001 0123 8495 7321 07\n"
                        "USt-IdNr.: DE300066949\nSteuer-Nr.: 47013/22377")
    res = ie.process_pdf(path)
    assert calls["n"] == 2  # zweistufig ausgelöst
    f = res["fields"]
    assert f["rechnungsaussteller"] == "SBS Deutschland GmbH & Co. KG"
    assert f["iban"] == "DE19100101238495732107"
    assert f["ust_idnr"] == "DE300066949"
    assert f["steuernummer"] == "47013/22377"
    # bereits extrahierte Body-Felder bleiben erhalten (erster Lauf gewinnt)
    assert f["rechnungsnummer"] == "IT2025032"
    assert f["betrag_brutto"] == 1880.2


def test_two_stage_ocr_preserves_zero_valued_first_pass_fields(monkeypatch):
    """Codex P2: ein legitimer Nullwert aus dem ersten Lauf (z. B. mwst_satz=0
    bei steuerfrei) darf vom OCR-Zweitlauf NICHT überschrieben werden."""
    path = _write_pdf("Rechnung steuerfrei")
    def _mock(text):
        if "[OCR" in text:
            return {"rechnungsaussteller": "SBS Deutschland", "iban": "DE19100101238495732107",
                    "ust_idnr": "DE300066949", "steuernummer": "47013/22377",
                    "mwst_satz": "19.0", "mwst_betrag": "300,20"}  # will NICHT gewinnen
        return {"rechnungsnummer": "R-0", "betrag_brutto": "1580,00", "betrag_netto": "1580,00",
                "mwst_satz": 0.0, "mwst_betrag": 0.0}  # steuerfrei, echte Nullwerte
    monkeypatch.setattr(ie, "_call_llm", _mock)
    monkeypatch.setattr(ie, "_ocr_pdf", lambda p: "SBS DEUTSCHLAND\nIBAN: DE19 1001 0123 8495 7321 07")
    res = ie.process_pdf(path)
    f = res["fields"]
    assert f["mwst_satz"] == 0.0   # Nullwert bleibt erhalten
    assert f["mwst_betrag"] == 0.0
    assert f["rechnungsaussteller"] == "SBS Deutschland"  # Lücke wurde ergänzt
    assert f["iban"] == "DE19100101238495732107"


def test_process_pdf_no_second_pass_when_issuer_present(monkeypatch):
    """Sind Aussteller-Felder bereits vorhanden, läuft KEIN zweiter OCR-Pass
    (kein unnötiger OCR-Aufwand pro Upload)."""
    path = _write_pdf("Rechnung\nAcme GmbH")
    calls = {"n": 0}
    monkeypatch.setattr(ie, "_call_llm", lambda text: calls.__setitem__("n", calls["n"] + 1) or {
        "rechnungsaussteller": "Acme GmbH", "rechnungsnummer": "R1", "datum": "2026-01-01",
        "betrag_brutto": "119,00", "mwst_satz": "19.0", "steuernummer": "12/345/67890",
    })
    ocr = {"called": False}
    monkeypatch.setattr(ie, "_ocr_pdf", lambda p: ocr.__setitem__("called", True) or "x")
    res = ie.process_pdf(path)
    assert calls["n"] == 1
    assert ocr["called"] is False
    assert res["fields"]["rechnungsaussteller"] == "Acme GmbH"


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
