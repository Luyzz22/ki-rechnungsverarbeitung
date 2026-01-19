from __future__ import annotations

import os
import sqlite3
from typing import Any, Optional

from .data import aggregate_mbr_data, previous_month_window
from .llm import generate_narrative_via_llm
from .pptx_renderer import render_presentation_from_template

DEFAULT_TEMPLATE_PATH = os.environ.get("MBR_TEMPLATE_PATH", "pptx_templates/mbr_template.pptx")
DEFAULT_MODEL = os.environ.get("MBR_LLM_MODEL", "gpt-4o-2024-08-06")


def generate_presentation(
    db_connection: Any,
    template_path: str = DEFAULT_TEMPLATE_PATH,
    model: str = DEFAULT_MODEL,
    use_llm: bool = True,
    api_key: Optional[str] = None,
) -> bytes:
    """
    One-click MBR generator.

    Input:
      - db_connection: sqlite3.Connection OR path to sqlite db
    Output:
      - pptx bytes (ready for FastAPI StreamingResponse)

    Behavior:
      - Aggregates previous month (Berlin TZ).
      - If empty month, falls back to latest month with data (coverage_note).
      - LLM produces strict schema narrative (Structured Outputs) unless use_llm=False.
      - Renders into PPTX template with placeholder tokens.

    Template requirement:
      Provide pptx_templates/mbr_template.pptx (enterprise-designed master).
      Place placeholders like:
        {{MBR_MONTH}}, {{TOTAL_NET}}, {{TOP_SUPPLIERS_TABLE}}, {{BUDGET_CHART}}, ...
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"MBR template not found at {template_path}. "
            "Provide a branded PPTX template and set MBR_TEMPLATE_PATH if needed."
        )

    data = aggregate_mbr_data(db_connection)
    if use_llm:
        narrative = generate_narrative_via_llm(data, model=model, api_key=api_key)
    else:
        # deterministic fallback (no API call) for smoke tests
        from .types import MBRNarrative, SlideNarrative
        narrative = MBRNarrative(
            month_label=data.window.label_de,
            executive_summary=SlideNarrative(title="Executive Summary", bullets=["(LLM deaktiviert)"]),
            kpi_commentary=SlideNarrative(title="KPI Kommentar", bullets=["(LLM deaktiviert)"]),
            supplier_insights=SlideNarrative(title="Lieferanten-Insights", bullets=["(LLM deaktiviert)"]),
            budget_insights=SlideNarrative(title="Budget-Insights", bullets=["(LLM deaktiviert)"]),
            risks=[],
            actions=[],
            closing_statement="(LLM deaktiviert)",
        )

    return render_presentation_from_template(template_path, data, narrative)
