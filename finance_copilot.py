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

# === FINAL CEO-level generate_finance_answer ===
def generate_finance_answer(question, days=90):
    """
    CEO/CFO-ready answer based on finance snapshot.
    Returns dict with: answer, question, days, snapshot, suggested_questions.
    """
    # local helpers
    def _describe_period(d):
        if d <= 1:
            return "heute"
        if d <= 7:
            return f"den letzten {d} Tagen"
        if 25 <= d <= 35:
            return "den letzten 30 Tagen"
        if 80 <= d <= 100:
            return "den letzten 90 Tagen"
        if 160 <= d <= 200:
            return "den letzten 6 Monaten"
        if 340 <= d <= 380:
            return "den letzten 12 Monaten"
        return f"den letzten {d} Tagen"

    def _fmt_eur(value):
        try:
            x = float(value or 0.0)
        except Exception:
            x = 0.0
        s = f"{x:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} €"

    def _safe_int(x):
        try:
            return int(x or 0)
        except Exception:
            return 0

    def _safe_float(x):
        try:
            return float(x or 0.0)
        except Exception:
            return 0.0

    # optionally infer days from question, if helper exists
    try:
        infer = globals().get("_infer_days_from_question")
        if callable(infer):
            days = infer(question, days)
    except Exception:
        pass

    # import inside function to avoid circulars
    from analytics_service import get_finance_snapshot

    snapshot = get_finance_snapshot(days=days) or {}
    kpis = snapshot.get("kpis", {}) or {}
    top_vendors = snapshot.get("top_vendors") or []
    monthly_trend = snapshot.get("monthly_trend") or []

    total_invoices = _safe_int(kpis.get("total_invoices"))
    total_gross = _safe_float(kpis.get("total_gross"))
    total_net = _safe_float(kpis.get("total_net"))
    total_vat = _safe_float(kpis.get("total_vat"))
    duplicates = _safe_int(kpis.get("duplicates_count"))

    # no-data case
    if total_invoices == 0:
        period_text = _describe_period(days)
        answer = (
            f"Für {period_text} liegen in SBS KI-Rechnungsverarbeitung aktuell keine verarbeiteten "
            "Eingangsrechnungen vor. Sobald erste Rechnungen in diesem Zeitraum vorhanden sind, "
            "kann der Finance Copilot u.a. folgende Fragen beantworten:\n"
            "• \"Kurzer Überblick über unsere Ausgaben der letzten 90 Tage\"\n"
            "• \"Wer sind unsere teuersten Lieferanten?\"\n"
            "• \"Wie haben sich unsere Ausgaben in den letzten Monaten entwickelt?\"\n"
            "• \"Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?\""
        )
        return {
            "answer": answer,
            "question": question,
            "days": days,
            "snapshot": snapshot,
            "suggested_questions": [
                "Kurzer Überblick über unsere Ausgaben der letzten 90 Tage.",
                "Wer sind unsere teuersten Lieferanten?",
                "Wie haben sich unsere Ausgaben in den letzten 6 Monaten entwickelt?",
                "Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?",
            ],
        }

    period_text = _describe_period(days)

    vat_rate = (total_vat / total_net * 100.0) if total_net > 0 else None

    intro_parts = []
    focus_points = []

    intro_parts.append(
        f"In SBS KI-Rechnungsverarbeitung wurden in {period_text} insgesamt {total_invoices} Rechnungen "
        f"mit einem Bruttogesamtbetrag von {_fmt_eur(total_gross)} verarbeitet."
    )

    if total_net:
        if vat_rate is not None:
            intro_parts.append(
                f" Der Nettobetrag liegt bei etwa {_fmt_eur(total_net)}, darin enthalten sind "
                f"ungefähr {_fmt_eur(total_vat)} Mehrwertsteuer "
                f"(effektive MwSt-Quote rund {vat_rate:.1f} %)."
            )
            if vat_rate > 19.5:
                focus_points.append("MwSt-Quote liegt spürbar über dem Standard von 19 %, mögliche Sondersteuersätze prüfen.")
        else:
            intro_parts.append(
                f" Der Nettobetrag liegt bei etwa {_fmt_eur(total_net)}."
            )
    elif total_vat:
        intro_parts.append(
            f" Enthalten sind rund {_fmt_eur(total_vat)} Mehrwertsteuer."
        )

    if duplicates > 0:
        dup_share = duplicates / float(total_invoices) * 100.0
        intro_parts.append(
            f" {duplicates} Rechnung(en) wurden als potenzielle Dubletten markiert "
            f"(ca. {dup_share:.1f} % der Rechnungen) und sollten vor der Zahlung geprüft werden."
        )
        if dup_share >= 5:
            focus_points.append("Dublettenquote liegt im auffälligen Bereich – Prozessqualität im Rechnungseingang prüfen.")

    # vendor analysis
    vendor_parts = []
    main_share = None
    if top_vendors:
        main_vendor = top_vendors[0]
        main_name = main_vendor.get("rechnungsaussteller") or "Ihr Hauptlieferant"
        main_brutto = _safe_float(main_vendor.get("total_gross"))
        main_share = (main_brutto / total_gross * 100.0) if total_gross > 0 else None

        v_sentence = (
            f"Ihr größter Lieferant im betrachteten Zeitraum ist {main_name} "
            f"mit einem Volumen von {_fmt_eur(main_brutto)}"
        )
        if main_share is not None:
            v_sentence += f", das entspricht rund {main_share:.1f} % Ihres gesamten Rechnungsvolumens."
        else:
            v_sentence += "."
        vendor_parts.append(v_sentence)

        if main_share is not None and main_share >= 40:
            focus_points.append("Kosten sind stark auf einen einzelnen Lieferanten konzentriert – Konditionen und Abhängigkeiten prüfen.")

        if len(top_vendors) > 1:
            top3 = top_vendors[:3]
            top3_sum = sum(_safe_float(v.get("total_gross")) for v in top3)
            top3_share = (top3_sum / total_gross * 100.0) if total_gross > 0 else None
            if top3_share is not None:
                vendor_parts.append(
                    f" Die Top-{len(top3)} Lieferanten stehen gemeinsam für etwa "
                    f"{top3_share:.1f} % der Ausgaben in diesem Zeitraum."
                )
                if top3_share >= 70:
                    focus_points.append("Ein Großteil der Ausgaben bündelt sich auf wenige Lieferanten – strategische Lieferantensteuerung sinnvoll.")

    # trend analysis
    trend_parts = []
    if monthly_trend:
        months_sorted = sorted(
            monthly_trend,
            key=lambda m: (m.get("year_month") or "")
        )
        months_with_value = [
            m for m in months_sorted if _safe_float(m.get("total_gross")) > 0
        ]

        spend_trend = None  # "up", "down", "flat"

        if months_with_value:
            first = months_with_value[0]
            last = months_with_value[-1]
            first_val = _safe_float(first.get("total_gross"))
            last_val = _safe_float(last.get("total_gross"))

            avg_month = (
                sum(_safe_float(m.get("total_gross")) for m in months_sorted)
                / float(len(months_sorted))
            )

            max_month = max(
                months_sorted, key=lambda m: _safe_float(m.get("total_gross"))
            )
            min_month = min(
                months_sorted, key=lambda m: _safe_float(m.get("total_gross"))
            )

            def _month_label(m):
                return m.get("year_month") or ""

            delta = last_val - first_val
            if abs(delta) < 1e-6:
                trend_parts.append(
                    f"Über den betrachteten Zeitraum blieb das monatliche Ausgabenvolumen relativ stabil "
                    f"(Startmonat {_month_label(first)} und letzter Monat {_month_label(last)} liegen beide bei "
                    f"{_fmt_eur(last_val)})."
                )
                spend_trend = "flat"
            elif delta > 0:
                trend_parts.append(
                    f"Über den Zeitraum ist ein Anstieg der Ausgaben zu sehen: "
                    f"vom Startmonat {_month_label(first)} mit {_fmt_eur(first_val)} "
                    f"auf {_fmt_eur(last_val)} im letzten Monat {_month_label(last)}."
                )
                spend_trend = "up"
            else:
                trend_parts.append(
                    f"Über den Zeitraum ist ein Rückgang der Ausgaben zu sehen: "
                    f"vom Startmonat {_month_label(first)} mit {_fmt_eur(first_val)} "
                    f"auf {_fmt_eur(last_val)} im letzten Monat {_month_label(last)}."
                )
                spend_trend = "down"

            if avg_month > 0:
                if last_val > avg_month * 1.1:
                    trend_parts.append(
                        f"Der letzte Monat lag mit {_fmt_eur(last_val)} deutlich über Ihrem Durchschnitt von "
                        f"rund {_fmt_eur(avg_month)} pro Monat."
                    )
                elif last_val < avg_month * 0.9:
                    trend_parts.append(
                        f"Der letzte Monat lag mit {_fmt_eur(last_val)} klar unter Ihrem Durchschnitt von "
                        f"rund {_fmt_eur(avg_month)} pro Monat."
                    )
                else:
                    trend_parts.append(
                        f"Der letzte Monat lag mit {_fmt_eur(last_val)} in etwa auf Höhe Ihres Durchschnitts "
                        f"von {_fmt_eur(avg_month)} pro Monat."
                    )

            max_val = _safe_float(max_month.get("total_gross"))
            min_val = _safe_float(min_month.get("total_gross"))
            if max_val > 0:
                trend_parts.append(
                    f"Der umsatzstärkste Monat im Zeitraum war {_month_label(max_month)} "
                    f"mit {_fmt_eur(max_val)}, der schwächste Monat {_month_label(min_month)} "
                    f"mit {_fmt_eur(min_val)}."
                )

            if spend_trend == "up":
                focus_points.append("Ausgaben zeigen einen Aufwärtstrend – Budgetsteuerung und Ursachenanalyse empfehlenswert.")
            elif spend_trend == "down":
                focus_points.append("Ausgaben sind rückläufig – Einsparungen und Effizienzgewinne verifizieren und sichern.")

    # assemble narrative
    answer_parts = []
    answer_parts.append("".join(intro_parts))
    if vendor_parts:
        answer_parts.append(" ".join(vendor_parts))
    if trend_parts:
        answer_parts.append(" ".join(trend_parts))

    if not trend_parts and monthly_trend:
        months_sorted = sorted(
            monthly_trend,
            key=lambda m: (m.get("year_month") or "")
        )
        if len(months_sorted) >= 2:
            prev = months_sorted[-2]
            last = months_sorted[-1]
            prev_val = _safe_float(prev.get("total_gross"))
            last_val = _safe_float(last.get("total_gross"))
            delta = last_val - prev_val
            if abs(delta) > 1e-6:
                direction = "höher" if delta > 0 else "niedriger"
                answer_parts.append(
                    f"Die Ausgaben im letzten Monat ({last.get('year_month')}) lagen "
                    f"{_fmt_eur(abs(delta))} {direction} als im Vormonat ({prev.get('year_month')})."
                )

    if focus_points:
        bullet_intro = (
            "Aus Sicht von Geschäftsführung und CFO ergeben sich daraus insbesondere folgende Schwerpunkte: "
        )
        bullets = "; ".join(focus_points)
        answer_parts.append(bullet_intro + bullets)

    suggested_questions = [
        "Welche Lieferanten verursachen aktuell die höchsten Kosten?",
        "Wie hat sich unser monatliches Ausgabenprofil in den letzten 6 Monaten entwickelt?",
        "Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?",
        "Wo sehen Sie potenzielle Dubletten oder Unstimmigkeiten in den Rechnungen?",
    ]

    full_answer = " ".join(answer_parts).strip()
    if full_answer and not full_answer.endswith("."):
        full_answer += "."

    return {
        "answer": full_answer,
        "question": question,
        "days": days,
        "snapshot": snapshot,
        "suggested_questions": suggested_questions,
    }
