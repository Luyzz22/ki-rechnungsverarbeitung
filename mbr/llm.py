from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Optional

from openai import OpenAI

from .data import MBRData
from .types import MBRNarrative


SYSTEM_PROMPT_DE = """\
Du bist ein CFO Operating Partner für ein Enterprise-SaaS.
Aufgabe: Erstelle Inhalte für eine Monthly Business Review (MBR) Präsentation.
Vorgaben:
- Schreibe auf Deutsch, Business-Ton, prägnant, KPI-getrieben.
- Keine erfundenen Zahlen. Nutze ausschließlich die gelieferten Aggregationen.
- Wenn Datenlage dünn/leer ist, erwähne das explizit und gib sinnvolle nächste Schritte.
- Gib Warnungen (Risiken) und konkrete Actions (Owner-Rolle, Priorität, ggf. Due Date).
"""


def _mbr_payload(data: MBRData) -> dict[str, Any]:
    # keep payload stable & minimal for auditability
    return {
        "month_label": data.window.label_de,
        "coverage_note": data.coverage_note,
        "kpis": {
            "invoice_count": data.invoice_count,
            "total_net": data.total_net,
            "total_gross": data.total_gross,
        },
        "top_suppliers": [
            {"supplier": s.supplier, "amount_net": s.amount_net}
            for s in data.top_suppliers
        ],
        "budget_vs_actual_by_category": [
            {
                "category_id": c.category_id,
                "category_name": c.category_name,
                "actual_net": c.actual_net,
                "budget": c.budget,
                "variance": c.variance,
                "variance_pct": c.variance_pct,
            }
            for c in data.categories[:12]
        ],
    }


def generate_narrative_via_llm(
    data: MBRData,
    model: str = "gpt-4o-2024-08-06",
    api_key: Optional[str] = None,
) -> MBRNarrative:
    """
    Uses Structured Outputs (SDK parse) to ensure schema-adherent JSON.
    See OpenAI docs: client.responses.parse(..., text_format=YourPydanticModel). 
    """
    client = OpenAI(api_key=api_key) if api_key else OpenAI()

    payload = _mbr_payload(data)
    user_msg = (
        "Erstelle die MBR-Inhalte als strukturiertes Objekt gemäß Schema. "
        "Nutze ausschließlich diese JSON-Aggregationen:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    resp = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT_DE},
            {"role": "user", "content": user_msg},
        ],
        text_format=MBRNarrative,
    )
    return resp.output_parsed
