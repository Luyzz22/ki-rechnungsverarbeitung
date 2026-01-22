from __future__ import annotations

import json
import logging
from typing import Any, Optional

from openai import OpenAI

from .data import MBRData
from .types import MBRNarrative, SlideNarrative

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_DE = """\
Du bist ein CFO Operating Partner für ein Enterprise-SaaS.
Aufgabe: Erstelle Inhalte für eine Monthly Business Review (MBR) Präsentation.

Vorgaben:
- Schreibe auf Deutsch, Business-Ton, prägnant, KPI-getrieben.
- Keine erfundenen Zahlen. Nutze ausschließlich die gelieferten Aggregationen.
- Wenn Datenlage dünn/leer ist, erwähne das explizit und gib sinnvolle nächste Schritte.
- Gib Warnungen (Risiken) und konkrete Actions (Owner-Rolle, Priorität).

Antworte NUR mit validem JSON im folgenden Format:
{
  "month_label": "Monat Jahr",
  "executive_summary": {
    "title": "Executive Summary",
    "bullets": ["Punkt 1", "Punkt 2", "Punkt 3"]
  },
  "kpi_commentary": {
    "title": "KPI Kommentar", 
    "bullets": ["Insight 1", "Insight 2"]
  },
  "supplier_insights": {
    "title": "Lieferanten-Analyse",
    "bullets": ["Insight 1", "Insight 2"]
  },
  "budget_insights": {
    "title": "Budget-Analyse",
    "bullets": ["Insight 1", "Insight 2"]
  },
  "risks": ["Risiko 1", "Risiko 2"],
  "actions": ["Maßnahme 1", "Maßnahme 2"],
  "closing_statement": "Zusammenfassender Satz"
}
"""


def _mbr_payload(data: MBRData) -> dict[str, Any]:
    return {
        "month_label": data.window.label_de,
        "coverage_note": data.coverage_note,
        "user_name": data.user_name,
        "kpis": {
            "invoice_count": data.invoice_count,
            "total_net": round(data.total_net, 2),
            "total_gross": round(data.total_gross, 2),
        },
        "top_suppliers": [
            {"supplier": s.supplier, "amount_net": round(s.amount_net, 2)}
            for s in data.top_suppliers
        ],
        "budget_vs_actual": [
            {
                "category": c.category_name,
                "actual": round(c.actual_net, 2),
                "budget": round(c.budget, 2),
                "variance": round(c.variance, 2),
                "variance_pct": round(c.variance_pct * 100, 1) if c.variance_pct else None,
            }
            for c in data.categories[:10]
        ],
    }


def generate_narrative_via_llm(
    data: MBRData,
    model: str = "gpt-4o-2024-08-06",
    api_key: Optional[str] = None,
) -> MBRNarrative:
    """
    Generate MBR narrative using OpenAI Chat Completions API.
    Falls back to basic narrative on error.
    """
    try:
        client = OpenAI(api_key=api_key) if api_key else OpenAI()
        
        payload = _mbr_payload(data)
        user_msg = (
            "Erstelle die MBR-Inhalte basierend auf diesen Daten:\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_DE},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        
        return MBRNarrative(
            month_label=result.get("month_label", data.window.label_de),
            executive_summary=SlideNarrative(
                title=result.get("executive_summary", {}).get("title", "Executive Summary"),
                bullets=result.get("executive_summary", {}).get("bullets", [])
            ),
            kpi_commentary=SlideNarrative(
                title=result.get("kpi_commentary", {}).get("title", "KPI Kommentar"),
                bullets=result.get("kpi_commentary", {}).get("bullets", [])
            ),
            supplier_insights=SlideNarrative(
                title=result.get("supplier_insights", {}).get("title", "Lieferanten-Analyse"),
                bullets=result.get("supplier_insights", {}).get("bullets", [])
            ),
            budget_insights=SlideNarrative(
                title=result.get("budget_insights", {}).get("title", "Budget-Analyse"),
                bullets=result.get("budget_insights", {}).get("bullets", [])
            ),
            risks=result.get("risks", []),
            actions=result.get("actions", []),
            closing_statement=result.get("closing_statement", ""),
        )
        
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        # Fallback to data-driven narrative without LLM
        return _generate_fallback_narrative(data)


def _generate_fallback_narrative(data: MBRData) -> MBRNarrative:
    """Generate basic narrative from data without LLM."""
    
    # Format currency
    def fmt(x): return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    
    # Executive summary bullets
    exec_bullets = [
        f"Im {data.window.label_de} wurden {data.invoice_count} Rechnungen verarbeitet.",
        f"Gesamtausgaben: {fmt(data.total_net)} netto / {fmt(data.total_gross)} brutto.",
    ]
    if data.top_suppliers:
        top = data.top_suppliers[0]
        exec_bullets.append(f"Größter Lieferant: {top.supplier} ({fmt(top.amount_net)})")
    
    # Supplier insights
    supplier_bullets = []
    for s in data.top_suppliers[:3]:
        pct = (s.amount_net / data.total_net * 100) if data.total_net else 0
        supplier_bullets.append(f"{s.supplier}: {fmt(s.amount_net)} ({pct:.1f}% der Ausgaben)")
    
    # Budget insights  
    budget_bullets = []
    over_budget = [c for c in data.categories if c.variance > 0 and c.budget > 0]
    under_budget = [c for c in data.categories if c.variance < 0 and c.budget > 0]
    
    if over_budget:
        c = over_budget[0]
        budget_bullets.append(f"⚠️ {c.category_name}: {fmt(c.variance)} über Budget")
    if under_budget:
        c = under_budget[0]
        budget_bullets.append(f"✅ {c.category_name}: {fmt(abs(c.variance))} unter Budget")
    if not budget_bullets:
        budget_bullets.append("Keine Budget-Daten für diesen Monat verfügbar.")
    
    return MBRNarrative(
        month_label=data.window.label_de,
        executive_summary=SlideNarrative(title="Executive Summary", bullets=exec_bullets),
        kpi_commentary=SlideNarrative(title="KPI Kommentar", bullets=[
            f"Durchschnittlicher Rechnungswert: {fmt(data.total_net / data.invoice_count) if data.invoice_count else 'N/A'}",
            f"Datenquelle: {data.data_source}"
        ]),
        supplier_insights=SlideNarrative(title="Lieferanten-Analyse", bullets=supplier_bullets or ["Keine Lieferantendaten"]),
        budget_insights=SlideNarrative(title="Budget-Analyse", bullets=budget_bullets),
        risks=["Budget-Überschreitungen prüfen", "Lieferantenkonzentration beobachten"] if over_budget else [],
        actions=["Monatlichen Review-Prozess etablieren", "Budget-Alerts einrichten"],
        closing_statement=f"Der MBR für {data.window.label_de} zeigt {data.invoice_count} verarbeitete Rechnungen mit Gesamtausgaben von {fmt(data.total_net)}.",
    )
