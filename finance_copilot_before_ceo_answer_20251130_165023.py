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

def generate_finance_answer(question, days=90):
    """
    Erzeugt eine natürlichsprachliche Finanz-Antwort für den Finance Copilot.
    Nutzt ausschließlich die aggregierten Daten aus get_finance_snapshot.
    """
    from analytics_service import get_finance_snapshot

    # -----------------------------
    # 1) Eingabe normalisieren
    # -----------------------------
    q_raw = (question or "").strip()
    if not q_raw:
        q_raw = "Kurzer Überblick über unsere Ausgaben."
    q_lower = q_raw.lower()

    # Basis-Tage aus Request (defensiv)
    try:
        base_days = int(days or 90)
    except Exception:
        base_days = 90

    # -----------------------------
    # 2) Intent erkennen
    # -----------------------------
    intent = "overview"
    if any(w in q_lower for w in ("mehrwertsteuer", "mwst", "vat", "steuer")):
        intent = "vat"
    elif "lieferant" in q_lower or "vendor" in q_lower:
        intent = "suppliers"
    elif any(w in q_lower for w in ("trend", "entwicklung", "verlauf", "monate", "monat")):
        intent = "trend"
    if any(w in q_lower for w in ("dubletten", "doppelt", "duplicate")):
        # überschreibt ggf. vorher, Dubletten-Fragen sind spezieller
        intent = "duplicates"

    # -----------------------------
    # 3) Natürliche Zeitangaben aus Frage ableiten
    # -----------------------------
    try:
        # Falls _infer_days_from_question im Modul definiert ist, nutzen wir es.
        base_days = _infer_days_from_question(q_raw, base_days)  # type: ignore[name-defined]
    except Exception:
        pass

    try:
        base_days = int(base_days)
    except Exception:
        base_days = 90

    if base_days < 1:
        base_days = 1
    if base_days > 365:
        base_days = 365

    # -----------------------------
    # 4) Snapshot holen
    # -----------------------------
    snapshot = get_finance_snapshot(days=base_days)
    kpis = snapshot.get("kpis") or {}
    total_invoices = int(kpis.get("total_invoices") or 0)
    total_gross = float(kpis.get("total_gross") or 0.0)
    total_net = float(kpis.get("total_net") or 0.0) if kpis.get("total_net") is not None else 0.0
    total_vat = float(kpis.get("total_vat") or 0.0) if kpis.get("total_vat") is not None else 0.0
    duplicates = int(kpis.get("duplicates_count") or 0)
    top_vendors = snapshot.get("top_vendors") or []
    monthly_trend = snapshot.get("monthly_trend") or []

    # -----------------------------
    # 5) Formatter / Helper
    # -----------------------------
    def fmt_eur(value):
        try:
            x = float(value or 0.0)
        except Exception:
            x = 0.0
        s = f"{x:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} €"

    def fmt_int(value):
        try:
            x = int(value or 0)
        except Exception:
            x = 0
        s = f"{x:,}"
        return s.replace(",", ".")

    def period_label(q, d):
        ql = (q or "").lower()
        # Wenn explizit "Monat" / "Monate" erwähnt sind, sprechen wir auch in Monaten
        if "monat" in ql:
            if d <= 45:
                return "den letzten 1–2 Monaten"
            if d <= 120:
                return "den letzten 3–4 Monaten"
            if d <= 210:
                return "den letzten 6 Monaten"
            return "den letzten 12 Monaten"
        # sonst heuristisch
        if d in (30, 31):
            return "den letzten 30 Tagen"
        if d in (90, 91):
            return "den letzten 90 Tagen"
        if d in (180, 181):
            return "den letzten 6 Monaten"
        if d in (360, 365):
            return "den letzten 12 Monaten"
        return f"den letzten {d} Tagen"

    def month_label(ym):
        # ym z.B. "2025-08"
        try:
            year, month = ym.split("-")
            month = int(month)
        except Exception:
            return ym
        months_de = {
            1: "Januar", 2: "Februar", 3: "März", 4: "April",
            5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
            9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
        }
        return f"{months_de.get(month, month)}/{year}"

    # -----------------------------
    # 6) Kein-Daten-Fall
    # -----------------------------
    if total_invoices == 0:
        answer = (
            f"Für {period_label(q_raw, base_days)} liegen in SBS KI-Rechnungsverarbeitung "
            "aktuell keine verarbeiteten Eingangsrechnungen vor.\n\n"
            "Sobald erste Rechnungen im gewählten Zeitraum verarbeitet wurden, kann der Finance Copilot zum Beispiel:\n"
            "• einen kompakten CFO-Überblick über Volumen, MwSt. und Dubletten geben,\n"
            "• Top-Lieferanten nach Ausgaben identifizieren und\n"
            "• Trends über mehrere Monate hinweg erklären.\n"
        )
        suggested = [
            "Kurzer Überblick über unsere Ausgaben der letzten 90 Tage.",
            "Wer sind unsere teuersten Lieferanten?",
            "Wie haben sich unsere Ausgaben in den letzten 6 Monaten entwickelt?",
            "Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?",
        ]
        return {
            "answer": answer,
            "question": q_raw,
            "days": base_days,
            "snapshot": snapshot,
            "suggested_questions": suggested,
        }

    # -----------------------------
    # 7) Trend-Analyse vorbereiten
    # -----------------------------
    months_sorted = sorted(
        monthly_trend,
        key=lambda m: m.get("year_month") or ""
    ) if monthly_trend else []

    first_month = months_sorted[0] if months_sorted else None
    last_month = months_sorted[-1] if len(months_sorted) >= 1 else None
    trend_delta = None
    if first_month and last_month and first_month is not last_month:
        try:
            first_val = float(first_month.get("total_gross") or 0.0)
            last_val = float(last_month.get("total_gross") or 0.0)
            trend_delta = last_val - first_val
        except Exception:
            trend_delta = None

    # Durchschnittsmonat (für Trend-Kontext)
    avg_month = None
    if months_sorted:
        try:
            avg_month = sum(
                float(m.get("total_gross") or 0.0) for m in months_sorted
            ) / len(months_sorted)
        except Exception:
            avg_month = None

    # teuerster / günstigster Monat
    max_month = None
    min_month = None
    if months_sorted:
        try:
            max_month = max(months_sorted, key=lambda m: float(m.get("total_gross") or 0.0))
            min_month = min(months_sorted, key=lambda m: float(m.get("total_gross") or 0.0))
        except Exception:
            max_month = None
            min_month = None

    # Lieferanten-Konzentration
    main_vendor = top_vendors[0] if top_vendors else None
    main_vendor_share = None
    if main_vendor and total_gross > 0:
        try:
            main_vendor_share = float(main_vendor.get("total_gross") or 0.0) / total_gross * 100.0
        except Exception:
            main_vendor_share = None

    # Dublettenquote
    duplicates_ratio = None
    if total_invoices > 0:
        duplicates_ratio = duplicates / total_invoices * 100.0

    # -----------------------------
    # 8) Antwort nach Intent bauen
    # -----------------------------
    p_label = period_label(q_raw, base_days)

    # Basistext – CFO-Überblick
    base_intro = (
        f"In {p_label} wurden insgesamt {fmt_int(total_invoices)} Rechnungen "
        f"mit einem Bruttogesamtbetrag von rund {fmt_eur(total_gross)} verarbeitet. "
        f"Der Nettobetrag liegt bei etwa {fmt_eur(total_net)}, darin enthalten sind ungefähr {fmt_eur(total_vat)} Mehrwertsteuer. "
    )

    if duplicates > 0:
        base_intro += (
            f"Insgesamt wurden {fmt_int(duplicates)} Rechnungen als potenzielle Dubletten markiert"
        )
        if duplicates_ratio is not None:
            base_intro += f", das entspricht etwa {duplicates_ratio:.1f} % aller Belege. "
        else:
            base_intro += ". "

    answer_parts = [base_intro]

    # 8a) Trend / Entwicklung
    if months_sorted and len(months_sorted) >= 2:
        first_lbl = month_label(first_month.get("year_month")) if first_month else ""
        last_lbl = month_label(last_month.get("year_month")) if last_month else ""
        if trend_delta is not None:
            if trend_delta > 0:
                answer_parts.append(
                    f"Über den Zeitraum sind die Ausgaben von {fmt_eur(first_month.get('total_gross') or 0.0)} "
                    f"im {first_lbl} auf {fmt_eur(last_month.get('total_gross') or 0.0)} im {last_lbl} angestiegen. "
                )
            elif trend_delta < 0:
                answer_parts.append(
                    f"Über den Zeitraum sind die Ausgaben von {fmt_eur(first_month.get('total_gross') or 0.0)} "
                    f"im {first_lbl} auf {fmt_eur(last_month.get('total_gross') or 0.0)} im {last_lbl} zurückgegangen. "
                )
            else:
                answer_parts.append(
                    f"Zwischen {first_lbl} und {last_lbl} bewegen sich die Ausgaben in einer ähnlichen Größenordnung. "
                )

        if avg_month is not None:
            answer_parts.append(
                f"Im Mittel liegen die monatlichen Ausgaben im betrachteten Zeitraum bei rund {fmt_eur(avg_month)}. "
            )

        if max_month and min_month:
            max_lbl = month_label(max_month.get("year_month"))
            min_lbl = month_label(min_month.get("year_month"))
            answer_parts.append(
                f"Der stärkste Monat war {max_lbl} mit {fmt_eur(max_month.get('total_gross') or 0.0)}, "
                f"der schwächste {min_lbl} mit {fmt_eur(min_month.get('total_gross') or 0.0)}. "
            )

    # 8b) Lieferanten-Fokus
    if top_vendors:
        if intent in ("overview", "trend"):
            # kompakter Manager-Satz
            top = top_vendors[0]
            name = top.get("rechnungsaussteller") or "Ihr Hauptlieferant"
            gross = float(top.get("total_gross") or 0.0)
            share_txt = ""
            if main_vendor_share is not None:
                if main_vendor_share >= 60:
                    share_txt = " – eine sehr hohe Lieferantenkonzentration."
                elif main_vendor_share >= 40:
                    share_txt = " – eine spürbare Konzentration auf einen Partner."
                else:
                    share_txt = "."
            answer_parts.append(
                f"Der größte Einzel-Lieferant im Zeitraum ist {name} mit {fmt_eur(gross)} Volumen"
                f"{share_txt} "
            )
        elif intent == "suppliers":
            # detaillierte Auflistung
            top = top_vendors[:5]
            answer_parts.append(
                "Bei den Lieferanten konzentriert sich das Volumen insbesondere auf folgende Partner:\n"
            )
            lines = []
            for v in top:
                name = v.get("rechnungsaussteller") or "Unbekannter Lieferant"
                gross = float(v.get("total_gross") or 0.0)
                count = int(v.get("invoice_count") or 0)
                share = (gross / total_gross * 100.0) if total_gross else 0.0
                lines.append(
                    f"- {name}: {fmt_eur(gross)} über {fmt_int(count)} Rechnung(en), "
                    f"entspricht ca. {share:.1f} % des Gesamtvolumens."
                )
            answer_parts.append("\n".join(lines) + "\n")

    # 8c) Mehrwertsteuer-Fokus
    if intent == "vat":
        vat_ratio = (total_vat / total_net * 100.0) if total_net else None
        if vat_ratio is not None:
            answer_parts.append(
                f"Über alle Rechnungen im Zeitraum entspricht die Mehrwertsteuer damit "
                f"rund {vat_ratio:.1f} % des Nettobetrags. "
            )
        answer_parts.append(
            "Damit sehen Sie auf einen Blick, welche Umsatzsteuer-Last in Ihren Eingangsrechnungen steckt "
            "und ob die Quote zu Ihrer typischen Kostenstruktur passt. "
        )

    # 8d) Dubletten-Fokus
    if intent == "duplicates" and duplicates > 0:
        answer_parts.append(
            "Die erhöhte Dublettenquote kann auf Doppeleinreichungen oder fehlerhafte Prozesse "
            "in der Rechnungsfreigabe hinweisen. Es lohnt sich, diese Fälle systematisch zu prüfen, "
            "bevor Zahlungen ausgelöst werden. "
        )

    # 8e) Abschluss auf CEO-/CFO-Level
    answer_parts.append(
        "Wenn Sie möchten, kann ich im nächsten Schritt z.B. die größten Kostentreiber, "
        "auffällige Monats-Peaks oder Lieferanten mit überdurchschnittlicher Dublettenquote herausarbeiten."
    )

    answer = "".join(answer_parts)

    # -----------------------------
    # 9) Folgefragen vorschlagen
    # -----------------------------
    suggested = [
        "Wer sind unsere drei größten Kostentreiber im aktuellen Zeitraum?",
        "Welche Monate stechen durch besonders hohe Ausgaben hervor?",
        "Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?",
        "Gibt es Lieferanten, bei denen ungewöhnlich viele Dubletten auftreten?",
    ]

    return {
        "answer": answer,
        "question": q_raw,
        "days": base_days,
        "snapshot": snapshot,
        "suggested_questions": suggested,
    }


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




# --- v2 generate_finance_answer with days inference ---
def generate_finance_answer(question: str, days: int = 90) -> Dict[str, Any]:
    base_days = days or 90
    # Versuche, aus der Frage einen sinnvolleren Zeitraum abzuleiten
    try:
        base_days = _infer_days_from_question(question, base_days)
    except Exception:
        pass

    # Sicherheitsbegrenzung
    try:
        days_int = int(base_days)
    except Exception:
        days_int = 90
    if days_int < 1:
        days_int = 1
    if days_int > 365:
        days_int = 365
    days = days_int

    snapshot = get_finance_snapshot(days=days)
    kpis = snapshot.get("kpis", {}) or {}
    top_vendors = snapshot.get("top_vendors") or []
    trend = snapshot.get("monthly_trend") or []

    total_invoices = int(kpis.get("total_invoices") or 0)
    total_gross = float(kpis.get("total_gross") or 0.0)
    total_net = kpis.get("total_net")
    total_vat = kpis.get("total_vat")
    duplicates = int(kpis.get("duplicates_count") or 0)

    def _fmt_eur(value: float) -> str:
        try:
            v = float(value or 0.0)
        except Exception:
            v = 0.0
        s = f"{v:,.2f} €"
        # 12,345.67 -> 12.345,67
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_int(value: Any) -> str:
        try:
            return f"{int(value)}"
        except Exception:
            return "0"

    q = (question or "").lower()

    if "lieferant" in q or "supplier" in q:
        intent = "suppliers"
    elif "mehrwertsteuer" in q or "mwst" in q or "umsatzsteuer" in q:
        intent = "vat"
    elif "trend" in q or "entwickelt" in q or "entwicklung" in q or "verlauf" in q:
        intent = "trend"
    else:
        intent = "overview"

    # Kein Datenbestand im Zeitraum
    if total_invoices <= 0:
        answer = (
            f"Für die letzten {days} Tage liegen in SBS KI-Rechnungsverarbeitung aktuell "
            "keine verarbeiteten Eingangsrechnungen vor. "
            "Sobald erste Rechnungen im gewählten Zeitraum verarbeitet wurden, "
            "kann ich Ihnen z.B. einen Ausgabenüberblick, die teuersten Lieferanten "
            "oder die enthaltene Mehrwertsteuer berechnen."
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
            "days": days,
            "snapshot": snapshot,
            "suggested_questions": suggested,
        }

    # Gemeinsamer Einstieg
    parts = [
        f"In den letzten {days} Tagen wurden insgesamt {_fmt_int(total_invoices)} Rechnungen",
        f"mit einem Bruttogesamtbetrag von rund {_fmt_eur(total_gross)} verarbeitet.",
    ]

    if total_net is not None and total_vat is not None:
        parts.append(
            f"Der Nettobetrag liegt bei etwa {_fmt_eur(total_net)}, "
            f"darin enthalten sind ungefähr {_fmt_eur(total_vat)} Mehrwertsteuer."
        )

    if duplicates > 0:
        parts.append(
            f"Davon wurden {duplicates} Rechnungen als potenzielle Dubletten markiert, "
            "die vor der Zahlung noch einmal geprüft werden sollten."
        )

    answer_body = " ".join(parts)

    # Intent-spezifische Details
    detail = ""
    if intent == "suppliers":
        if top_vendors:
            lines = []
            for v in top_vendors[:5]:
                name = v.get("rechnungsaussteller") or "Unbekannter Lieferant"
                amount = _fmt_eur(v.get("total_gross") or 0.0)
                cnt = _fmt_int(v.get("invoice_count") or 0)
                lines.append(f"- {name}: {amount} über {cnt} Rechnung(en)")
            detail = " Die teuersten Lieferanten im gewählten Zeitraum sind:\n" + "\n".join(lines)
        else:
            detail = " Es konnten keine Lieferantenstatistiken für den Zeitraum ermittelt werden."
    elif intent == "vat":
        if total_vat is not None and total_net:
            try:
                quota = float(total_vat) / float(total_net) * 100.0
            except Exception:
                quota = None
        else:
            quota = None
        if quota is not None:
            detail = (
                f" Insgesamt steckt in diesem Zeitraum Mehrwertsteuer in Höhe von {_fmt_eur(total_vat)} "
                f"in Ihren Rechnungen, das entspricht einer MwSt-Quote von etwa {quota:.1f} % "
                "bezogen auf den Nettobetrag."
            )
        else:
            detail = " Die enthaltene Mehrwertsteuer konnte für diesen Zeitraum nicht vollständig berechnet werden."
    elif intent == "trend":
        if trend:
            ordered = sorted(trend, key=lambda r: r.get("year_month") or "")
            if len(ordered) >= 2:
                last = ordered[-1]
                prev = ordered[-2]
                diff = float(last.get("total_gross") or 0.0) - float(prev.get("total_gross") or 0.0)
                if diff > 0:
                    direction = "höher"
                elif diff < 0:
                    direction = "niedriger"
                else:
                    direction = "auf dem gleichen Niveau"
                detail = (
                    f" Im Zeitverlauf zeigt sich: Im letzten Monat ({last.get('year_month')}) lagen die Ausgaben "
                    f"{'um ' + _fmt_eur(abs(diff)) + ' ' if diff != 0 else ''}{direction} "
                    f"als im Vormonat ({prev.get('year_month')})."
                )
            else:
                detail = " Für einen sinnvollen Verlauf liegen nur Daten aus einem Monat vor."
        else:
            detail = " Es liegen keine Daten für eine Zeitreihen-Analyse im gewählten Zeitraum vor."
    else:
        if trend and len(trend) >= 2:
            ordered = sorted(trend, key=lambda r: r.get("year_month") or "")
            last = ordered[-1]
            prev = ordered[-2]
            diff = float(last.get("total_gross") or 0.0) - float(prev.get("total_gross") or 0.0)
            if diff > 0:
                direction = "höher"
            elif diff < 0:
                direction = "niedriger"
            else:
                direction = "auf dem gleichen Niveau"
            detail = (
                f" Die Ausgaben im letzten Monat ({last.get('year_month')}) lagen "
                f"{'um ' + _fmt_eur(abs(diff)) + ' ' if diff != 0 else ''}{direction} "
                f"als im Vormonat ({prev.get('year_month')})."
            )

    suggested = [
        "Gib mir einen Überblick über unsere Ausgaben der letzten 90 Tage.",
        "Wer sind unsere teuersten Lieferanten?",
        "Wie haben sich unsere Ausgaben in den letzten 6 Monaten entwickelt?",
        "Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?",
    ]

    answer = (
        answer_body
        + detail
        + " Stellen Sie mir gerne eine spezifische Frage, z.B.: "
        "„Welche Lieferanten sind aktuell am teuersten?“, "
        "„Wie haben sich unsere Ausgaben in den letzten Monaten entwickelt?“ "
        "oder „Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?“."
    )

    return {
        "answer": answer,
        "question": question,
        "days": days,
        "snapshot": snapshot,
        "suggested_questions": suggested,
    }
