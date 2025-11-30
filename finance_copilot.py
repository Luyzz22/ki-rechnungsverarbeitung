"""
Finance Copilot Service – nutzt die bestehenden Analytics-Daten,
um eine verständliche, CFO-taugliche Zusammenfassung zu erzeugen.

V1: komplett deterministisch (ohne externes LLM),
aber so strukturiert, dass später problemlos ein KI-Modell
eingehängt werden kann.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from analytics_service import get_finance_snapshot


def _format_eur(amount: float) -> str:
    """Formatiert Beträge im deutschen EUR-Format, z.B. 14141.65 -> '14.141,65 €'."""
    return (
        f"{amount:,.2f} €"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


@dataclass
class FinanceCopilotResult:
    """
    Strukturierte Antwort des Finance Copilot.

    - answer: natürlichsprachliche, deutsche Antwort
    - question: Originalfrage des Users (für Logging / späteres Fine-Tuning)
    - days: betrachteter Zeitraum
    - snapshot: Rohdaten aus analytics_service (für UI/Charts)
    - suggested_questions: Vorschläge für Folgefragen im Frontend
    """
    answer: str
    question: str
    days: int
    snapshot: Dict[str, Any]
    suggested_questions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "question": self.question,
            "days": self.days,
            "snapshot": self.snapshot,
            "suggested_questions": self.suggested_questions,
        }


def generate_finance_answer(question: str, days: int = 90) -> Dict[str, Any]:
    """
    Kernfunktion des Finance Copilot.

    - zieht sich ein Finance-Snapshot (aggregierte Kennzahlen)
    - baut daraus eine verständliche, kontextreiche Antwort
    - liefert zusätzlich die Rohdaten + Vorschlagsfragen zurück
    """
    # Defensive Defaults
    question = (question or "").strip()
    if not question:
        question = "Gib mir einen kurzen Überblick über unsere Eingangsrechnungen."

    # Zeitraum begrenzen (Safety Guard)
    if days < 1:
        days = 1
    if days > 365:
        days = 365

    # Bestehenden Analytics-Service nutzen
    snapshot = get_finance_snapshot(days=days)
    kpis = snapshot.get("kpis", {}) or {}
    vendors = snapshot.get("top_vendors", []) or []
    monthly = snapshot.get("monthly_trend", []) or []

    total_invoices = int(kpis.get("total_invoices") or 0)
    total_gross = float(kpis.get("total_gross") or 0.0)
    total_net = float(kpis.get("total_net") or 0.0)
    total_vat = float(kpis.get("total_vat") or 0.0)
    duplicates = int(kpis.get("duplicates_count") or 0)

    # Sprachlich schöner Zeitraum
    if days >= 365:
        period_label = "letzten 12 Monaten"
    else:
        period_label = f"letzten {days} Tagen"

    parts: List[str] = []

    # Fall 1: noch keine Daten
    if total_invoices == 0:
        parts.append(
            f"Im gewählten Zeitraum ({period_label}) wurden in Ihrem System "
            "noch keine Eingangsrechnungen erfasst."
        )
        parts.append(
            "Sobald erste Rechnungen vorliegen, kann ich Ihnen z.B. Top-Lieferanten, "
            "Ausgaben-Trends und Auffälligkeiten aufzeigen."
        )

    # Fall 2: es gibt Daten
    else:
        parts.append(
            f"In den {period_label} wurden insgesamt {total_invoices} Rechnungen "
            f"mit einem Bruttogesamtbetrag von rund {_format_eur(total_gross)} verarbeitet."
        )
        parts.append(
            f"Der Nettobetrag liegt bei ca. {_format_eur(total_net)}, darin enthalten sind "
            f"etwa {_format_eur(total_vat)} Mehrwertsteuer."
        )

        if duplicates:
            parts.append(
                f"Davon wurden {duplicates} Rechnungen als potenzielle Dubletten markiert. "
                "Diese sollten vor der Zahlung noch einmal geprüft werden."
            )

        if vendors:
            top = vendors[0]
            vname = (top.get("rechnungsaussteller") or "Ihr Hauptlieferant").strip()
            vcount = int(top.get("invoice_count") or 0)
            vgross = float(top.get("total_gross") or 0.0)
            parts.append(
                f"Ihr größter Lieferant im Zeitraum ist {vname} mit {vcount} Rechnung(en) "
                f"und einem Volumen von rund {_format_eur(vgross)}."
            )

        # Kleine Trend-Aussage (letzter Monat vs. Vormonat), falls Daten vorhanden
        if len(monthly) >= 2:
            last = monthly[-1]
            prev = monthly[-2]
            last_val = float(last.get("total_gross") or 0.0)
            prev_val = float(prev.get("total_gross") or 0.0)
            diff = last_val - prev_val

            if abs(diff) > 1e-2:
                direction = "höher" if diff > 0 else "niedriger"
                parts.append(
                    f"Die Ausgaben im letzten Monat ({last.get('year_month')}) lagen "
                    f"{_format_eur(abs(diff))} {direction} als im Vormonat "
                    f"({prev.get('year_month')})."
                )

        parts.append(
            "Stellen Sie mir gerne eine spezifische Frage, z.B.: "
            "„Welche Lieferanten sind aktuell am teuersten?“, "
            "„Wie haben sich unsere Ausgaben in den letzten Monaten entwickelt?“ oder "
            "„Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?“."
        )

    # Vorschlagsfragen – fürs Frontend, um „Apple-/NVIDIA-Feeling“ zu erzeugen
    suggested_questions = [
        "Gib mir einen Überblick über unsere Ausgaben der letzten 90 Tage.",
        "Welche Lieferanten verursachen aktuell die höchsten Kosten?",
        "Wie haben sich unsere Ausgaben in den letzten 6 Monaten entwickelt?",
        "Wie viel Mehrwertsteuer steckt in den letzten 12 Monaten?",
    ]

    result = FinanceCopilotResult(
        answer=" ".join(parts),
        question=question,
        days=days,
        snapshot=snapshot,
        suggested_questions=suggested_questions,
    )
    return result.to_dict()
