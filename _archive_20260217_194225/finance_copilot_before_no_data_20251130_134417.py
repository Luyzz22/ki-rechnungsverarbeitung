"""
Finance Copilot – regelbasierte Antworten auf Basis der Rechnungsdaten.

Wichtig:
- Keine externen LLM-APIs
- Alle Aussagen stammen direkt aus analytics_service / invoices.db
- Deterministisch, auditierbar, schnell
"""

from __future__ import annotations

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

def generate_finance_answer(question: str, days: int = 90) -> Dict[str, Any]:
    """
    Erzeugt eine kompakte, deutschsprachige Finance-Antwort rein auf Basis der
    Rechnungsdaten.

    - nutzt analytics_service.get_finance_snapshot(days)
    - KEINE externen Modellaufrufe
    - perfekt für Live-Copilot im Analytics-Dashboard
    """
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
