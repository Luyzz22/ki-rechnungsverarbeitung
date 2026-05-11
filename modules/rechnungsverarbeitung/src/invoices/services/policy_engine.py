from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from typing import Any, Mapping

from modules.rechnungsverarbeitung.src.invoices.models import InvoiceDocumentMetadata


class PolicySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PolicyStatus(str, Enum):
    PASSED = "passed"
    REVIEW_REQUIRED = "review_required"
    VIOLATED = "violated"


class PolicyNextAction(str, Enum):
    CONTINUE_PIPELINE = "continue_pipeline"
    MANUAL_REVIEW = "manual_review"
    BLOCK_OR_REJECT = "block_or_reject"


@dataclass
class PolicyFinding:
    code: str
    severity: PolicySeverity
    message: str
    field: str | None = None
    details: dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass
class PolicyConfig:
    amount_review_threshold: float = 5000.0
    amount_block_threshold: float | None = None
    allowed_currencies: set[str] = dataclass_field(default_factory=lambda: {"EUR"})
    supplier_allowlist: set[str] | None = None
    supplier_blocklist: set[str] = dataclass_field(default_factory=set)
    required_fields: tuple[str, ...] = ("supplier", "total_amount", "invoice_number")
    budget_warning_ratio: float = 0.9
    budget_block_ratio: float = 1.0


@dataclass
class PolicyEngineResult:
    document_id: str
    tenant_id: str
    status: PolicyStatus
    next_action: PolicyNextAction
    findings: list[PolicyFinding]
    summary: str

    def to_audit_details(self) -> dict[str, Any]:
        return {
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


class PolicyEngine:
    def evaluate(
        self,
        metadata: InvoiceDocumentMetadata,
        extracted: Mapping[str, Any] | None = None,
        policy_context: Mapping[str, Any] | None = None,
        config: PolicyConfig | None = None,
    ) -> PolicyEngineResult:
        extracted_data = dict(extracted or {})
        context = dict(policy_context or {})
        cfg = config or PolicyConfig()
        findings: list[PolicyFinding] = []

        supplier_raw = _first_present(extracted_data, ("supplier", "rechnungsaussteller"))
        supplier_str = str(supplier_raw).strip() if supplier_raw is not None else ""
        supplier_norm = _normalize_supplier(supplier_str) if supplier_str else ""

        amount = _parse_amount(
            _first_present(extracted_data, ("total_amount", "total_amount_gross", "betrag_brutto"))
        )

        currency_raw = _first_present(extracted_data, ("currency", "waehrung"))
        invoice_number_raw = _first_present(extracted_data, ("invoice_number", "rechnungsnummer"))

        for req in cfg.required_fields:
            if req == "supplier":
                if not supplier_str:
                    findings.append(
                        PolicyFinding(
                            code="policy_required_field_missing",
                            severity=PolicySeverity.WARNING,
                            message="Required field supplier is missing",
                            field="supplier",
                            details={"required_field": "supplier"},
                        )
                    )
            elif req == "total_amount":
                if amount is None or amount <= 0:
                    findings.append(
                        PolicyFinding(
                            code="policy_required_field_missing",
                            severity=PolicySeverity.WARNING,
                            message="Required field total_amount is missing or invalid",
                            field="total_amount",
                            details={"required_field": "total_amount"},
                        )
                    )
            elif req == "invoice_number":
                if invoice_number_raw is None or (isinstance(invoice_number_raw, str) and not invoice_number_raw.strip()):
                    findings.append(
                        PolicyFinding(
                            code="policy_required_field_missing",
                            severity=PolicySeverity.WARNING,
                            message="Required field invoice_number is missing",
                            field="invoice_number",
                            details={"required_field": "invoice_number"},
                        )
                    )

        if currency_raw is not None and str(currency_raw).strip():
            cur = str(currency_raw).strip().upper()
            allowed_upper = {c.strip().upper() for c in cfg.allowed_currencies}
            if cur not in allowed_upper:
                findings.append(
                    PolicyFinding(
                        code="policy_currency_not_allowed",
                        severity=PolicySeverity.CRITICAL,
                        message="Currency is not allowed by policy",
                        field="currency",
                        details={
                            "currency": cur,
                            "allowed_currencies": sorted(allowed_upper),
                        },
                    )
                )

        if supplier_norm:
            block_norm = {_normalize_supplier(x) for x in cfg.supplier_blocklist if x}
            if supplier_norm in block_norm:
                findings.append(
                    PolicyFinding(
                        code="policy_supplier_blocked",
                        severity=PolicySeverity.CRITICAL,
                        message="Supplier is blocked by policy",
                        field="supplier",
                        details={"supplier": supplier_str},
                    )
                )

            if cfg.supplier_allowlist is not None:
                allow_norm = {_normalize_supplier(x) for x in cfg.supplier_allowlist if x}
                if supplier_norm not in allow_norm:
                    findings.append(
                        PolicyFinding(
                            code="policy_supplier_not_allowlisted",
                            severity=PolicySeverity.WARNING,
                            message="Supplier is not on the allowlist",
                            field="supplier",
                            details={"supplier": supplier_str},
                        )
                    )

        if amount is not None and amount > 0:
            if cfg.amount_block_threshold is not None and amount >= cfg.amount_block_threshold:
                findings.append(
                    PolicyFinding(
                        code="policy_amount_block_threshold_exceeded",
                        severity=PolicySeverity.CRITICAL,
                        message="Invoice amount exceeds policy block threshold",
                        field="total_amount",
                        details={"amount": amount, "threshold": cfg.amount_block_threshold},
                    )
                )
            elif amount >= cfg.amount_review_threshold:
                findings.append(
                    PolicyFinding(
                        code="policy_amount_review_threshold_exceeded",
                        severity=PolicySeverity.WARNING,
                        message="Invoice amount exceeds policy review threshold",
                        field="total_amount",
                        details={"amount": amount, "threshold": cfg.amount_review_threshold},
                    )
                )

        _apply_budget_guard(findings, amount, context, cfg)

        status, next_action, summary = _resolve_outcome(findings)

        return PolicyEngineResult(
            document_id=metadata.id,
            tenant_id=metadata.tenant_id,
            status=status,
            next_action=next_action,
            findings=findings,
            summary=summary,
        )


def _apply_budget_guard(
    findings: list[PolicyFinding],
    amount: float | None,
    context: dict[str, Any],
    cfg: PolicyConfig,
) -> None:
    limit = _parse_amount(context.get("budget_limit"))
    actual = _parse_amount(context.get("budget_actual"))
    if limit is None or limit <= 0 or actual is None:
        return

    amt = amount if amount is not None and amount > 0 else 0.0
    projected = actual + amt
    ratio = projected / limit
    category = context.get("budget_category")
    cat_str = str(category) if category is not None else None

    details_base: dict[str, Any] = {
        "actual": actual,
        "amount": amt,
        "limit": limit,
        "projected": projected,
        "ratio": ratio,
    }
    if cat_str is not None:
        details_base["budget_category"] = cat_str

    if ratio >= cfg.budget_block_ratio:
        findings.append(
            PolicyFinding(
                code="policy_budget_limit_exceeded",
                severity=PolicySeverity.CRITICAL,
                message="Projected spend would exceed budget limit",
                field="budget",
                details=details_base,
            )
        )
    elif ratio >= cfg.budget_warning_ratio:
        findings.append(
            PolicyFinding(
                code="policy_budget_near_limit",
                severity=PolicySeverity.WARNING,
                message="Projected spend is near budget limit",
                field="budget",
                details=details_base,
            )
        )


def _normalize_supplier(s: str) -> str:
    return s.strip().lower()


def _first_present(data: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


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
        else:
            normalized = normalized.replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return None
    return None


def _resolve_outcome(
    findings: list[PolicyFinding],
) -> tuple[PolicyStatus, PolicyNextAction, str]:
    has_critical = any(finding.severity == PolicySeverity.CRITICAL for finding in findings)
    if has_critical:
        return (
            PolicyStatus.VIOLATED,
            PolicyNextAction.BLOCK_OR_REJECT,
            "FlowCheck+ policy violations require blocking action",
        )

    has_warning = any(finding.severity == PolicySeverity.WARNING for finding in findings)
    if has_warning:
        return (
            PolicyStatus.REVIEW_REQUIRED,
            PolicyNextAction.MANUAL_REVIEW,
            "FlowCheck+ policies require manual review",
        )

    return (
        PolicyStatus.PASSED,
        PolicyNextAction.CONTINUE_PIPELINE,
        "FlowCheck+ policies passed",
    )
