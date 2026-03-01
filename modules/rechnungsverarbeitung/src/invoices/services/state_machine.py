"""Deterministic invoice lifecycle state machine.

Defines all valid states, transitions, and guard conditions.
Ensures GoBD-compliant, auditable document processing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class InvoiceStatus(StrEnum):
    UPLOADED = "uploaded"
    CLASSIFIED = "classified"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    SUGGESTED = "suggested"
    APPROVED = "approved"
    EXPORTED = "exported"
    ARCHIVED = "archived"
    REJECTED = "rejected"


TERMINAL_STATES: frozenset[InvoiceStatus] = frozenset({
    InvoiceStatus.ARCHIVED,
    InvoiceStatus.REJECTED,
})


@dataclass(frozen=True)
class TransitionRule:
    from_status: InvoiceStatus
    to_status: InvoiceStatus
    event_type: str
    requires_actor: bool = False
    description: str = ""


TRANSITION_TABLE: tuple[TransitionRule, ...] = (
    TransitionRule(InvoiceStatus.UPLOADED, InvoiceStatus.CLASSIFIED, "format_classified", description="Format detection completed"),
    TransitionRule(InvoiceStatus.CLASSIFIED, InvoiceStatus.VALIDATED, "validation_passed", description="Structural validation passed"),
    TransitionRule(InvoiceStatus.CLASSIFIED, InvoiceStatus.VALIDATION_FAILED, "validation_failed", description="Structural validation failed"),
    TransitionRule(InvoiceStatus.VALIDATED, InvoiceStatus.SUGGESTED, "kontierung_suggested", description="AI account assignment generated"),
    TransitionRule(InvoiceStatus.CLASSIFIED, InvoiceStatus.SUGGESTED, "kontierung_suggested", description="AI assignment for non-structured format"),
    TransitionRule(InvoiceStatus.VALIDATION_FAILED, InvoiceStatus.SUGGESTED, "kontierung_suggested", requires_actor=True, description="Manual override despite validation failure"),
    TransitionRule(InvoiceStatus.SUGGESTED, InvoiceStatus.APPROVED, "invoice_approved", requires_actor=True, description="Human approval granted"),
    TransitionRule(InvoiceStatus.SUGGESTED, InvoiceStatus.REJECTED, "invoice_rejected", requires_actor=True, description="Approver rejected invoice"),
    TransitionRule(InvoiceStatus.APPROVED, InvoiceStatus.EXPORTED, "datev_exported", description="Exported to accounting system"),
    TransitionRule(InvoiceStatus.EXPORTED, InvoiceStatus.ARCHIVED, "gobd_archived", description="GoBD evidence package sealed"),
)

_TRANSITION_INDEX: dict[tuple[InvoiceStatus, InvoiceStatus], TransitionRule] = {
    (rule.from_status, rule.to_status): rule for rule in TRANSITION_TABLE
}


class TransitionError(Exception):
    def __init__(self, from_status: str, to_status: str, reason: str, document_id: str | None = None) -> None:
        self.from_status = from_status
        self.to_status = to_status
        self.reason = reason
        self.document_id = document_id
        super().__init__(f"Transition {from_status} -> {to_status} denied{f' for {document_id}' if document_id else ''}: {reason}")


@dataclass
class TransitionResult:
    from_status: InvoiceStatus
    to_status: InvoiceStatus
    event_type: str
    actor: str | None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


class InvoiceStateMachine:
    def get_allowed_transitions(self, current_status: str) -> list[InvoiceStatus]:
        status = InvoiceStatus(current_status)
        return [rule.to_status for rule in TRANSITION_TABLE if rule.from_status == status]

    def can_transition(self, current_status: str, target_status: str) -> bool:
        try:
            return (InvoiceStatus(current_status), InvoiceStatus(target_status)) in _TRANSITION_INDEX
        except ValueError:
            return False

    def transition(self, document_id: str, current_status: str, target_status: str, actor: str | None = None, details: dict[str, Any] | None = None) -> TransitionResult:
        try:
            from_s = InvoiceStatus(current_status)
        except ValueError:
            raise TransitionError(current_status, target_status, f"Unknown source status: {current_status}", document_id)
        try:
            to_s = InvoiceStatus(target_status)
        except ValueError:
            raise TransitionError(current_status, target_status, f"Unknown target status: {target_status}", document_id)

        if from_s in TERMINAL_STATES:
            raise TransitionError(current_status, target_status, f"Document is in terminal state '{from_s}'", document_id)

        rule = _TRANSITION_INDEX.get((from_s, to_s))
        if rule is None:
            allowed = self.get_allowed_transitions(current_status)
            raise TransitionError(current_status, target_status, f"Transition not defined. Allowed targets: {[s.value for s in allowed]}", document_id)

        if rule.requires_actor and not actor:
            raise TransitionError(current_status, target_status, "Transition requires an actor (human approval/rejection)", document_id)

        result = TransitionResult(from_status=from_s, to_status=to_s, event_type=rule.event_type, actor=actor, details=details or {})
        logger.info("state_transition", extra={"document_id": document_id, "from": from_s.value, "to": to_s.value, "event_type": rule.event_type, "actor": actor})
        return result
