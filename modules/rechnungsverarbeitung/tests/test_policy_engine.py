from __future__ import annotations

from modules.rechnungsverarbeitung.src.invoices.models import InvoiceDocumentMetadata
from modules.rechnungsverarbeitung.src.invoices.services.policy_engine import (
    PolicyConfig,
    PolicyEngine,
    PolicyNextAction,
    PolicySeverity,
    PolicyStatus,
)


def _metadata() -> InvoiceDocumentMetadata:
    return InvoiceDocumentMetadata(
        id="doc-001",
        tenant_id="tenant-001",
        status="uploaded",
    )


def test_clean_invoice_passes() -> None:
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 1234.56,
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
    )

    assert result.status == PolicyStatus.PASSED
    assert result.next_action == PolicyNextAction.CONTINUE_PIPELINE
    assert result.findings == []


def test_missing_required_invoice_number_review() -> None:
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 100,
            "currency": "EUR",
        },
    )

    assert result.status == PolicyStatus.REVIEW_REQUIRED
    assert result.next_action == PolicyNextAction.MANUAL_REVIEW
    assert [f.code for f in result.findings] == ["policy_required_field_missing"]
    assert result.findings[0].details["required_field"] == "invoice_number"


def test_unsupported_currency_violated() -> None:
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 100,
            "currency": "USD",
            "invoice_number": "INV-001",
        },
    )

    assert result.status == PolicyStatus.VIOLATED
    assert result.next_action == PolicyNextAction.BLOCK_OR_REJECT
    assert any(f.code == "policy_currency_not_allowed" for f in result.findings)


def test_supplier_blocklist_violated() -> None:
    cfg = PolicyConfig(supplier_blocklist={"blocked vendor"})
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Blocked Vendor",
            "total_amount": 100,
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
        config=cfg,
    )

    assert result.status == PolicyStatus.VIOLATED
    assert any(
        f.code == "policy_supplier_blocked" and f.severity == PolicySeverity.CRITICAL for f in result.findings
    )


def test_supplier_allowlist_miss_review() -> None:
    cfg = PolicyConfig(supplier_allowlist={"allowed only"})
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Other Corp",
            "total_amount": 100,
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
        config=cfg,
    )

    assert result.status == PolicyStatus.REVIEW_REQUIRED
    assert any(f.code == "policy_supplier_not_allowlisted" for f in result.findings)


def test_amount_review_threshold_warning() -> None:
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 5000,
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
    )

    assert result.status == PolicyStatus.REVIEW_REQUIRED
    assert [f.code for f in result.findings] == ["policy_amount_review_threshold_exceeded"]
    assert result.findings[0].details["threshold"] == 5000.0


def test_amount_thousands_dot_format_triggers_review() -> None:
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": "6.000",
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
    )

    assert result.status == PolicyStatus.REVIEW_REQUIRED
    assert [f.code for f in result.findings] == ["policy_amount_review_threshold_exceeded"]
    assert result.findings[0].details["amount"] == 6000.0


def test_amount_thousands_comma_format_triggers_review() -> None:
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": "6,000",
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
    )

    assert result.status == PolicyStatus.REVIEW_REQUIRED
    assert result.findings[0].details["amount"] == 6000.0


def test_amount_block_threshold_critical() -> None:
    cfg = PolicyConfig(amount_review_threshold=10_000.0, amount_block_threshold=8000.0)
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 9000,
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
        config=cfg,
    )

    assert result.status == PolicyStatus.VIOLATED
    assert [f.code for f in result.findings] == ["policy_amount_block_threshold_exceeded"]


def test_budget_near_limit_warning() -> None:
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 1000,
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
        policy_context={
            "budget_actual": 8000,
            "budget_limit": 10000,
            "budget_category": "opex",
        },
    )

    assert result.status == PolicyStatus.REVIEW_REQUIRED
    assert any(f.code == "policy_budget_near_limit" for f in result.findings)
    near = next(f for f in result.findings if f.code == "policy_budget_near_limit")
    assert near.details["budget_category"] == "opex"
    assert near.details["ratio"] == 0.9


def test_budget_exceeded_critical() -> None:
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 600,
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
        policy_context={"budget_actual": 9500, "budget_limit": 10000},
    )

    assert result.status == PolicyStatus.VIOLATED
    assert any(f.code == "policy_budget_limit_exceeded" for f in result.findings)


def test_to_audit_details_stable_serializable_structure() -> None:
    result = PolicyEngine().evaluate(
        _metadata(),
        {
            "supplier": "S",
            "total_amount": "6.000,00",
            "currency": "EUR",
            "invoice_number": "N1",
        },
    )

    details = result.to_audit_details()

    assert set(details) == {"status", "next_action", "findings"}
    assert details["status"] == "review_required"
    assert details["next_action"] == "manual_review"
    assert all(
        set(f) == {"code", "severity", "message", "field", "details"} for f in details["findings"]
    )
    codes = [f["code"] for f in details["findings"]]
    assert "policy_amount_review_threshold_exceeded" in codes
    assert isinstance(details["findings"][0]["details"], dict)
