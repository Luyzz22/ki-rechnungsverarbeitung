from __future__ import annotations

import re
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from typing import Any, Mapping

from modules.rechnungsverarbeitung.src.invoices.models import InvoiceDocumentMetadata

_THOUSANDS_COMMA_PATTERN = re.compile(r"^\d{1,3}(?:,\d{3})+$")
_THOUSANDS_DOT_PATTERN = re.compile(r"^\d{1,3}(?:\.\d{3})+$")


class ControlSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ControlStatus(str, Enum):
    PASSED = "passed"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class NextAction(str, Enum):
    CONTINUE_PIPELINE = "continue_pipeline"
    MANUAL_REVIEW = "manual_review"
    REJECT_OR_REUPLOAD = "reject_or_reupload"


@dataclass
class ControlFinding:
    code: str
    severity: ControlSeverity
    message: str
    field: str | None = None
    details: dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass
class ControlEngineResult:
    document_id: str
    tenant_id: str
    status: ControlStatus
    score: int
    next_action: NextAction
    findings: list[ControlFinding]
    summary: str

    def to_audit_details(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "status": self.status.value,
            "next_action": self.next_action.value,
            "findings": [
                {
                    "code": finding.code,
                    "severity": finding.severity.value,
                    "message": finding.message,
                    "field": finding.field,
                    "details": finding.details,
                }
                for finding in self.findings
            ],
        }


class ControlEngine:
    HIGH_AMOUNT_THRESHOLD = 5000.0

    def evaluate(
        self,
        metadata: InvoiceDocumentMetadata,
        extracted: Mapping[str, Any] | None = None,
        validation: Mapping[str, Any] | None = None,
    ) -> ControlEngineResult:
        extracted_data = extracted or {}
        validation_data = validation or {}
        findings: list[ControlFinding] = []
        extraction_available = _has_substantive_extraction_fields(extracted_data)

        amount: float | None = None
        if extraction_available:
            supplier = _first_present(extracted_data, ("supplier", "rechnungsaussteller"))
            if not supplier:
                findings.append(
                    ControlFinding(
                        code="missing_supplier",
                        severity=ControlSeverity.WARNING,
                        message="Supplier is missing",
                        field="supplier",
                    )
                )

            amount = _parse_amount(
                _first_present(extracted_data, ("total_amount", "total_amount_gross", "betrag_brutto"))
            )
            if amount is None or amount <= 0:
                findings.append(
                    ControlFinding(
                        code="missing_total_amount",
                        severity=ControlSeverity.CRITICAL,
                        message="Total amount is missing or invalid",
                        field="total_amount",
                    )
                )

            currency = _first_present(extracted_data, ("currency", "waehrung"))
            if currency and str(currency).strip().upper() != "EUR":
                findings.append(
                    ControlFinding(
                        code="unsupported_currency",
                        severity=ControlSeverity.WARNING,
                        message="Currency is not supported",
                        field="currency",
                        details={"currency": str(currency).strip()},
                    )
                )

            invoice_number = _first_present(extracted_data, ("invoice_number", "rechnungsnummer"))
            if not invoice_number:
                findings.append(
                    ControlFinding(
                        code="missing_invoice_number",
                        severity=ControlSeverity.WARNING,
                        message="Invoice number is missing",
                        field="invoice_number",
                    )
                )

        if metadata.status == "validation_failed" or validation_data.get("status") == "failed":
            findings.append(
                ControlFinding(
                    code="validation_failed",
                    severity=ControlSeverity.CRITICAL,
                    message="Validation failed",
                    field="validation.status",
                )
            )

        warnings = validation_data.get("warnings")
        if isinstance(warnings, list) and warnings:
            findings.append(
                ControlFinding(
                    code="validation_warnings",
                    severity=ControlSeverity.WARNING,
                    message="Validation produced warnings",
                    field="validation.warnings",
                    details={"warning_count": len(warnings)},
                )
            )

        if extraction_available and amount is not None and amount >= self.HIGH_AMOUNT_THRESHOLD:
            findings.append(
                ControlFinding(
                    code="high_amount_review",
                    severity=ControlSeverity.WARNING,
                    message="Invoice amount requires manual review",
                    field="total_amount",
                    details={"amount": amount, "threshold": self.HIGH_AMOUNT_THRESHOLD},
                )
            )

        score = _calculate_score(findings)
        status, next_action, summary = _resolve_outcome(findings)

        return ControlEngineResult(
            document_id=metadata.id,
            tenant_id=metadata.tenant_id,
            status=status,
            score=score,
            next_action=next_action,
            findings=findings,
            summary=summary,
        )


def _first_present(data: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _has_substantive_extraction_fields(data: Mapping[str, Any]) -> bool:
    return _first_present(
        data,
        (
            "supplier",
            "rechnungsaussteller",
            "total_amount",
            "total_amount_gross",
            "betrag_brutto",
            "invoice_number",
            "rechnungsnummer",
        ),
    ) is not None


def _parse_amount(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().replace(" ", "")
        if not normalized:
            return None
        if "," in normalized and "." in normalized:
            if normalized.rfind(",") > normalized.rfind("."):
                normalized = normalized.replace(".", "").replace(",", ".")
            else:
                normalized = normalized.replace(",", "")
        elif "," in normalized:
            if _THOUSANDS_COMMA_PATTERN.fullmatch(normalized):
                normalized = normalized.replace(",", "")
            else:
                normalized = normalized.replace(",", ".")
        elif "." in normalized:
            if _THOUSANDS_DOT_PATTERN.fullmatch(normalized):
                normalized = normalized.replace(".", "")
        try:
            return float(normalized)
        except ValueError:
            return None
    return None


def _calculate_score(findings: list[ControlFinding]) -> int:
    score = 100
    penalties = {
        ControlSeverity.CRITICAL: 40,
        ControlSeverity.WARNING: 15,
        ControlSeverity.INFO: 5,
    }
    for finding in findings:
        score -= penalties[finding.severity]
    return max(0, min(100, score))


def _resolve_outcome(
    findings: list[ControlFinding],
) -> tuple[ControlStatus, NextAction, str]:
    has_critical = any(finding.severity == ControlSeverity.CRITICAL for finding in findings)
    if has_critical:
        return (
            ControlStatus.BLOCKED,
            NextAction.REJECT_OR_REUPLOAD,
            "FlowCheck+ controls blocked pipeline progression",
        )

    has_warning = any(finding.severity == ControlSeverity.WARNING for finding in findings)
    if has_warning:
        return (
            ControlStatus.REVIEW_REQUIRED,
            NextAction.MANUAL_REVIEW,
            "FlowCheck+ controls require manual review",
        )

    return (
        ControlStatus.PASSED,
        NextAction.CONTINUE_PIPELINE,
        "FlowCheck+ controls passed",
    )
