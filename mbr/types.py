from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class SlideNarrative(BaseModel):
    title: str = Field(..., max_length=120)
    bullets: list[str] = Field(default_factory=list)


class MBRNarrative(BaseModel):
    """Simplified MBR Narrative for Enterprise Reports."""
    month_label: str = Field(..., max_length=50, description="e.g. 'Januar 2026'")
    executive_summary: SlideNarrative
    kpi_commentary: SlideNarrative
    supplier_insights: SlideNarrative
    budget_insights: SlideNarrative
    risks: list[str] = Field(default_factory=list, description="List of risk statements")
    actions: list[str] = Field(default_factory=list, description="List of action items")
    closing_statement: str = Field(..., max_length=500)
