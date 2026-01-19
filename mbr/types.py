from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class RiskItem(BaseModel):
    title: str = Field(..., max_length=80)
    severity: Literal["low", "medium", "high"]
    rationale: str = Field(..., max_length=400)
    recommendation: str = Field(..., max_length=300)


class ActionItem(BaseModel):
    owner_role: str = Field(..., max_length=60)
    action: str = Field(..., max_length=200)
    priority: Literal["P0", "P1", "P2"]
    due_date: Optional[str] = Field(
        default=None,
        description="ISO date YYYY-MM-DD if applicable, else null",
    )


class SlideNarrative(BaseModel):
    title: str = Field(..., max_length=80)
    bullets: list[str] = Field(default_factory=list)


class MBRNarrative(BaseModel):
    month_label: str = Field(..., max_length=30, description="e.g. 'Dezember 2025'")
    executive_summary: SlideNarrative
    kpi_commentary: SlideNarrative
    supplier_insights: SlideNarrative
    budget_insights: SlideNarrative
    risks: list[RiskItem] = Field(default_factory=list)
    actions: list[ActionItem] = Field(default_factory=list)
    closing_statement: str = Field(..., max_length=220)
