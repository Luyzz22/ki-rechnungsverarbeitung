"""
Finance Copilot – regelbasierte Antworten auf Basis der Rechnungsdaten.

Wichtig:
- Keine externen LLM-APIs
- Alle Aussagen stammen direkt aus analytics_service / invoices.db
- Deterministisch, auditierbar, schnell
"""

from __future__ import annotations
import re

from typing import Any, Dict, List

from analytics_service import get_finance_snapshot


__all__ = ["generate_finance_answer", "classify_intent"]


# ---------------------------------------------------------------------------
# Intent-Logik
# ---------------------------------------------------------------------------

def classify_intent(question: str) -> str:
    """
    Sehr leichte Intent-Klassifizierung auf Basis von Keywords.

    Rückgabewerte:
        - 'overview'
        - 'top_vendors'
        - 'vat_focus'
        - 'trend'
        - 'generic'
    """
    q = (question or "").lower()

    # Lieferanten / Konzentration
    if any(word in q for word in ("lieferant", "lieferanten", "vendor", "teuersten")):
        return "top_vendors"

    # Mehrwertsteuer / Steuern
    if any(word in q for word in ("mehrwertsteuer", "mwst", "umsatzsteuer", "steuer")):
        return "vat_focus"

    # Entwicklungen / Trends
    if any(word in q for word in ("trend", "entwicklung", "verlauf", "monaten", "monatlich")):
        return "trend"

    # Überblick / Zusammenfassung
    if any(word in q for word in ("überblick", "ueberblick", "zusammenfassung", "kurz", "kurzer")):
        return "overview"

    # Fallback
    return "generic"


# ---------------------------------------------------------------------------
# Hilfsfunktionen für Texte
# ---------------------------------------------------------------------------

def _format_currency(amount: float) -> str:
    """
    Format float als Euro-Betrag mit 2 Nachkommastellen und Tausender-Trenner.

    Die eigentliche Locale-Formatierung übernimmt das Frontend – hier halten
    wir es bewusst simpel und deterministisch.
    """
    try:
        return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"{amount:.2f} €"


def _build_overview_text(kpis: Dict[str, Any], days: int) -> str:
    total_invoices = kpis.get("total_invoices") or 0
    total_gross = float(kpis.get("total_gross") or 0.0)
    total_net = float(kpis.get("total_net") or 0.0)
    total_vat = float(kpis.get("total_vat") or 0.0)
    duplicates = int(kpis.get("duplicates_count") or 0)

    if total_invoices == 0:
        return (
            f"Im gewählten Zeitraum von {days} Tagen wurden keine Eingangsrechnungen gefunden. "
            "Sobald neue Rechnungen verarbeitet wurden, kann ich Ihnen hier eine Finanzübersicht geben."
        )

    parts: List[str] = []

    parts.append(
        f"In den letzten {days} Tagen wurden insgesamt {total_invoices} Rechnungen "
        f"mit einem Bruttogesamtbetrag von rund {_format_currency(total_gross)} verarbeitet."
    )

    parts.append(
        f"Der Nettobetrag liegt bei ca. {_format_currency(total_net)}, "
        f"darin enthalten sind etwa {_format_currency(total_vat)} Mehrwertsteuer."
    )

    if duplicates > 0:
        parts.append(
            f"Davon wurden {duplicates} Rechnungen als potenzielle Dubletten markiert. "
            "Diese sollten vor der Zahlung noch einmal geprüft werden."
        )

    return " ".join(parts)


def _build_top_vendor_text(top_vendors: List[Dict[str, Any]]) -> str:
    if not top_vendors:
        return "Aktuell liegen keine Daten zu Lieferanten vor."

    main_vendor = top_vendors[0]
    name = main_vendor.get("rechnungsaussteller") or "Ihr größter Lieferant"
    inv_count = int(main_vendor.get("invoice_count") or 0)
    total = float(main_vendor.get("total_gross") or 0.0)

    text = (
        f"Ihr größter Lieferant im betrachteten Zeitraum ist {name} "
        f"mit {inv_count} Rechnung(en) und einem Volumen von rund {_format_currency(total)}."
    )

    if len(top_vendors) > 1:
        others = top_vendors[1:3]
        other_names = [v.get("rechnungsaussteller") or "weiterer Lieferant" for v in others]
        if other_names:
            text += " Weitere relevante Lieferanten sind " + ", ".join(other_names) + "."

    return text


def _build_trend_text(monthly_trend: List[Dict[str, Any]]) -> str:
    if not monthly_trend or len(monthly_trend) < 2:
        return ""

    # Sortierung nach Jahr-Monat aufsteigend
    sorted_data = sorted(monthly_trend, key=lambda r: r.get("year_month") or "")
    last = sorted_data[-1]
    prev = sorted_data[-2]

    last_month = last.get("year_month")
    prev_month = prev.get("year_month")
    last_total = float(last.get("total_gross") or 0.0)
    prev_total = float(prev.get("total_gross") or 0.0)

    diff = last_total - prev_total
    if abs(diff) < 1e-2:
        return (
            f"Die Ausgaben im letzten Monat ({last_month}) liegen nahezu auf dem Niveau "
            f"des Vormonats ({prev_month})."
        )

    direction = "höher" if diff > 0 else "niedriger"
    diff_abs = abs(diff)

    return (
        f"Die Ausgaben im letzten Monat ({last_month}) lagen "
        f"{_format_currency(diff_abs)} {direction} als im Vormonat ({prev_month})."
    )


def _build_vat_text(kpis: Dict[str, Any]) -> str:
    total_net = float(kpis.get("total_net") or 0.0)
    total_vat = float(kpis.get("total_vat") or 0.0)

    if total_net <= 0:
        return ""

    vat_ratio = (total_vat / total_net) * 100.0
    return (
        f"Insgesamt steckt in diesem Zeitraum Mehrwertsteuer in Höhe von "
        f"{_format_currency(total_vat)} in Ihren Rechnungen. "
        f"Das entspricht einer MwSt-Quote von grob {vat_ratio:.1f} % bezogen auf den Nettobetrag."
    )


def _default_suggested_questions(days: int) -> List[str]:
    return [
        f"Gib mir einen Überblick über unsere Ausgaben der letzten {days} Tage.",
        "Welche Lieferanten verursachen aktuell die höchsten Kosten?",
        "Wie haben sich unsere Ausgaben in den letzten 6 Monaten entwickelt?",
        "Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?",
    ]


# ---------------------------------------------------------------------------
# Hauptfunktion – wird vom API-Endpoint genutzt
# ---------------------------------------------------------------------------


def _infer_days_from_question(question: str, default_days: int) -> int:
    """
    Versucht aus der Frage (z.B. "letzten 6 Monaten") den Zeitraum
    in Tagen abzuleiten. Fällt sonst auf default_days zurück.
    """
    if not question:
        return default_days

    q = question.lower()

    # Generisches Muster: "letzten 6 Monaten", "letzte 30 Tage", ...
    m = re.search(r"letzte?n?\s+(\d+)\s*(tage|tagen|wochen|monaten|monate|jahren|jahre)", q)
    if m:
        try:
            value = int(m.group(1))
        except ValueError:
            value = None
        unit = m.group(2)
        if value is not None:
            if "tag" in unit:
                return max(1, min(value, 365))
            if "woch" in unit:
                return max(1, min(value * 7, 365))
            if "monat" in unit:
                return max(1, min(value * 30, 365))
            if "jahr" in unit:
                return max(1, min(value * 365, 3 * 365))

    # Häufige feste Phrasen
    if "letzten 6 monaten" in q or "letzte 6 monate" in q:
        return 180
    if "letzten 12 monaten" in q or "letzte 12 monate" in q or "letzten zwölf monaten" in q:
        return 365
    if "letzten jahr" in q or "letzte jahr" in q:
        return 365
    if "letzten 90 tagen" in q or "90 tage" in q:
        return max(1, min(default_days, 365))
    if "letzten 30 tagen" in q or "30 tage" in q:
        return 30

    return default_days


def generate_finance_answer(question: str, days: int = 90) -> Dict[str, Any]:
    """
    Erzeugt eine kompakte, deutschsprachige Finance-Antwort rein auf Basis der
    Rechnungsdaten.

    - nutzt analytics_service.get_finance_snapshot(days)
    - KEINE externen Modellaufrufe
    - perfekt für Live-Copilot im Analytics-Dashboard
    """
    days = _infer_days_from_question(question, days)
    snapshot = get_finance_snapshot(days=days)

    kpis = snapshot.get("kpis", {}) or {}
    total_invoices = int(kpis.get("total_invoices") or 0)

    # Spezieller Fall: im gewählten Zeitraum gibt es keine Rechnungen
    if total_invoices == 0:
        answer = (
            "Für den gewählten Zeitraum liegen noch keine verarbeiteten Rechnungen vor. "
            "Bitte laden Sie Rechnungen hoch oder wählen Sie einen längeren Zeitraum "
            "(z. B. 90 oder 365 Tage)."
        )
        result = FinanceCopilotResult(
            answer=answer,
            question=question,
            days=days,
            snapshot=snapshot,
            suggested_questions=[
                "Gib mir einen Überblick über unsere Ausgaben der letzten 90 Tage.",
                "Wie haben sich unsere Ausgaben in den letzten Monaten entwickelt?",
                "Welche Lieferanten verursachen aktuell die höchsten Kosten?"
            ],
            intent="no_data",
        )
        return result.to_dict()


    kpis = snapshot.get("kpis", {}) or {}
    total_invoices = int(kpis.get("total_invoices") or 0)

    # Spezieller Fall: im gewählten Zeitraum gibt es keine Rechnungen
    if total_invoices == 0:
        answer = (
            "Für den gewählten Zeitraum liegen noch keine verarbeiteten Rechnungen vor. "
            "Bitte laden Sie Rechnungen hoch oder wählen Sie einen längeren Zeitraum "
            "(z. B. 90 oder 365 Tage)."
        )
        result = FinanceCopilotResult(
            answer=answer,
            question=question,
            days=days,
            snapshot=snapshot,
            suggested_questions=[
                "Gib mir einen Überblick über unsere Ausgaben der letzten 90 Tage.",
                "Wie haben sich unsere Ausgaben in den letzten Monaten entwickelt?",
                "Welche Lieferanten verursachen aktuell die höchsten Kosten?"
            ],
            intent="no_data",
        )
        return result.to_dict()

    kpis = snapshot.get("kpis", {})
    top_vendors = snapshot.get("top_vendors", [])
    monthly_trend = snapshot.get("monthly_trend", [])

    intent = classify_intent(question)

    answer_parts: List[str] = []

    # 1) Überblick bildet das Rückgrat fast aller Antworten
    overview_text = _build_overview_text(kpis, days)
    answer_parts.append(overview_text)

    # 2) Intent-spezifische Ergänzungen
    if intent == "top_vendors":
        answer_parts.append(_build_top_vendor_text(top_vendors))
    elif intent == "vat_focus":
        vat_text = _build_vat_text(kpis)
        if vat_text:
            answer_parts.append(vat_text)
        else:
            answer_parts.append(
                "Aktuell liegen nicht genügend Daten vor, um eine sinnvolle Mehrwertsteuer-Auswertung zu berechnen."
            )
    elif intent == "trend":
        trend_text = _build_trend_text(monthly_trend)
        if trend_text:
            answer_parts.append(trend_text)
    elif intent == "overview":
        # Überblick ist schon abgedeckt – optional Trend ergänzen
        trend_text = _build_trend_text(monthly_trend)
        if trend_text:
            answer_parts.append(trend_text)
    else:
        # generic: kurzer Hinweis plus Trend, falls vorhanden
        trend_text = _build_trend_text(monthly_trend)
        if trend_text:
            answer_parts.append(trend_text)

    # 3) Abschluss mit Follow-up-Ideen
    answer_parts.append(
        "Stellen Sie mir gerne eine spezifische Frage, z.B.: "
        "„Welche Lieferanten sind aktuell am teuersten?“, "
        "„Wie haben sich unsere Ausgaben in den letzten Monaten entwickelt?“ "
        "oder „Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?“."
    )

    answer = " ".join(part for part in answer_parts if part)

    result: Dict[str, Any] = {
        "answer": answer,
        "question": question,
        "days": days,
        "snapshot": snapshot,
        "suggested_questions": _default_suggested_questions(days),
        "intent": intent,
    }
    return result


if __name__ == "__main__":
    # Mini-Selbsttest
    demo_questions = [
        "Kurzer Überblick über unsere Ausgaben, bitte.",
        "Wer sind unsere teuersten Lieferanten?",
        "Wie viel Mehrwertsteuer steckt im letzten Jahr?",
        "Wie haben sich unsere Ausgaben in den letzten Monaten entwickelt?",
    ]
    for q in demo_questions:
        res = generate_finance_answer(q, days=365)
        print("==== Frage:", q)
        print(res["answer"])
        print("Intent:", res["intent"])
        print()

# ---------------------------------------------------------------------------
# Robuste Finance-Copilot-Antwort (überschreibt frühere Implementationen)
# ---------------------------------------------------------------------------
from typing import Any, Dict, List


def _fc_format_eur(value: Any) -> str:
    """Einfache EUR-Formatierung im de-DE Stil, z.B. 14141.65 -> '14.141,65 €'."""
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        number = 0.0
    s = f"{number:,.2f}"            # 14141.65 -> '14,141.65'
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " €"


def _fc_describe_period(days: int) -> str:
    """Lesbarer Zeitraum-Text für die Antwort."""
    try:
        d = int(days)
    except (TypeError, ValueError):
        d = 90
    if d >= 365:
        return "die letzten 12 Monate"
    if d == 30:
        return "die letzten 30 Tage"
    if d == 90:
        return "die letzten 90 Tage"
    return f"die letzten {d} Tage"


def _fc_detect_intent(question: str) -> str:
    """Sehr einfache Intent-Erkennung aus der Frage."""
    q = (question or "").lower()
    if "mehrwertsteuer" in q or "mwst" in q or "mwst." in q:
        return "vat"
    if "lieferant" in q or "lieferanten" in q:
        return "suppliers"
    if "trend" in q or "verlauf" in q or "entwicklung" in q or "monaten" in q:
        return "trend"
    if "überblick" in q or "ueberblick" in q or "kurzer" in q:
        return "overview"
    return "overview"


def generate_finance_answer(question: str, days: int = 90) -> Dict[str, Any]:
    """
    Robuste, regelbasierte Antwortgenerierung für den Finance Copilot.

    - Nutzt analytics_service.get_finance_snapshot()
    - Erkennt einfache Intents (Overview, Suppliers, VAT, Trend) aus der Frage
    - Behandelt den No-Data-Fall explizit, ohne Exceptions zu werfen
    """
    # Lazy-Import, damit es keine Zyklen gibt
    from analytics_service import get_finance_snapshot

    # Tage-Fenster absichern
    try:
        d = int(days or 90)
    except (TypeError, ValueError):
        d = 90
    if d < 1:
        d = 1
    if d > 365:
        d = 365

    snapshot = get_finance_snapshot(days=d)
    kpis = snapshot.get("kpis") or {}

    def _num(key: str, default: float = 0.0) -> float:
        try:
            return float(kpis.get(key, default) or 0.0)
        except (TypeError, ValueError):
            return float(default)

    def _int(key: str, default: int = 0) -> int:
        try:
            return int(kpis.get(key, default) or 0)
        except (TypeError, ValueError):
            return int(default)

    total_invoices = _int("total_invoices", 0)
    total_gross = _num("total_gross", 0.0)
    total_net = _num("total_net", 0.0)
    total_vat = _num("total_vat", 0.0)
    duplicates = _int("duplicates_count", 0)

    period_text = _fc_describe_period(d)

    # ---------- No-Data-Case ----------
    if total_invoices == 0:
        answer = (
            f"Für {period_text} liegen in SBS KI-Rechnungsverarbeitung aktuell keine verarbeiteten "
            f"Eingangsrechnungen vor. "
            "Sobald erste Rechnungen verarbeitet wurden, kann der Finance Copilot beispielsweise Fragen beantworten wie:\n"
            "• \"Kurzer Überblick über unsere Ausgaben der letzten 90 Tage\"\n"
            "• \"Wer sind unsere teuersten Lieferanten?\"\n"
            "• \"Wie haben sich unsere Ausgaben in den letzten Monaten entwickelt?\"\n"
            "• \"Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?\"\n"
        )
        suggested = [
            "Kurzer Überblick über unsere Ausgaben der letzten 90 Tage.",
            "Wer sind unsere teuersten Lieferanten?",
            "Wie haben sich unsere Ausgaben in den letzten 6 Monaten entwickelt?",
            "Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?",
        ]
        return {
            "answer": answer,
            "question": question,
            "days": d,
            "snapshot": snapshot,
            "suggested_questions": suggested,
        }

    # ---------- Mit Daten ----------
    intent = _fc_detect_intent(question or "")
    top_vendors: List[Dict[str, Any]] = snapshot.get("top_vendors") or []
    monthly_trend: List[Dict[str, Any]] = snapshot.get("monthly_trend") or []

    base = (
        f"In den letzten {d} Tagen wurden insgesamt {total_invoices} Rechnungen "
        f"mit einem Bruttogesamtbetrag von rund {_fc_format_eur(total_gross)} verarbeitet. "
        f"Der Nettobetrag liegt bei ca. {_fc_format_eur(total_net)}, "
        f"darin enthalten sind etwa {_fc_format_eur(total_vat)} Mehrwertsteuer. "
        f"Davon wurden {duplicates} Rechnungen als potenzielle Dubletten markiert. "
        "Diese sollten vor der Zahlung noch einmal geprüft werden."
    )

    vendor_sentence = ""
    if top_vendors:
        top = top_vendors[0]
        name = top.get("rechnungsaussteller") or "Ihr größter Lieferant"
        try:
            inv_count = int(top.get("invoice_count") or 0)
        except (TypeError, ValueError):
            inv_count = 0
        gross_vendor = _fc_format_eur(top.get("total_gross") or 0.0)
        vendor_sentence = (
            f" Ihr größter Lieferant im Zeitraum ist {name} "
            f"mit {inv_count} Rechnung(en) und einem Volumen von rund {gross_vendor}."
        )

    trend_sentence = ""
    if len(monthly_trend) >= 2:
        last = monthly_trend[-1]
        prev = monthly_trend[-2]
        last_month = last.get("year_month") or "letzten Monat"
        prev_month = prev.get("year_month") or "Vormonat"
        try:
            last_total = float(last.get("total_gross") or 0.0)
            prev_total = float(prev.get("total_gross") or 0.0)
        except (TypeError, ValueError):
            last_total = prev_total = 0.0
        delta = last_total - prev_total
        if abs(delta) > 0.01:
            richtung = "höher" if delta > 0 else "niedriger"
            trend_sentence = (
                f" Die Ausgaben im letzten Monat ({last_month}) lagen "
                f"{_fc_format_eur(abs(delta))} {richtung} als im Vormonat ({prev_month})."
            )

    # Intent-spezifische Ergänzungen
    intent_tail = ""
    if intent == "suppliers":
        if top_vendors:
            names = [
                (v.get("rechnungsaussteller") or "Unbekannter Lieferant")
                for v in top_vendors[:3]
            ]
            intent_tail = (
                " Im Fokus stehen dabei insbesondere folgende Lieferanten: "
                + ", ".join(names)
                + "."
            )
        else:
            intent_tail = (
                " Aktuell liegen im gewählten Zeitraum keine größeren Lieferantenkonzentrationen vor."
            )
    elif intent == "vat":
        quote = 0.0
        if total_net > 0:
            quote = (total_vat / total_net) * 100.0
        intent_tail = (
            f" Insgesamt steckt in diesem Zeitraum Mehrwertsteuer in Höhe von {_fc_format_eur(total_vat)} "
            f"in Ihren Rechnungen, das entspricht einer MwSt-Quote von grob {quote:.1f} % bezogen auf den Nettobetrag."
        )
    elif intent == "trend":
        if trend_sentence:
            intent_tail = trend_sentence
        else:
            intent_tail = (
                " Für eine aussagekräftige Trendanalyse benötigen wir mindestens zwei unterschiedliche Monate mit Daten."
            )

    # Für Overview, Suppliers, VAT nehmen wir Basis + Vendor + Trend, plus Intent-Tail.
    full_answer = base + vendor_sentence + trend_sentence
    if intent in ("suppliers", "vat", "trend"):
        full_answer += intent_tail

    full_answer += (
        " Stellen Sie mir gerne eine spezifische Frage, z.B.: "
        "„Welche Lieferanten sind aktuell am teuersten?“, "
        "„Wie haben sich unsere Ausgaben in den letzten Monaten entwickelt?“ "
        "oder „Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?“. "
    )

    suggested = [
        "Gib mir einen Überblick über unsere Ausgaben der letzten 90 Tage.",
        "Welche Lieferanten verursachen aktuell die höchsten Kosten?",
        "Wie haben sich unsere Ausgaben in den letzten 6 Monaten entwickelt?",
        "Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?",
    ]

    return {
        "answer": full_answer,
        "question": question,
        "days": d,
        "snapshot": snapshot,
        "suggested_questions": suggested,
    }

