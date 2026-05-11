from __future__ import annotations

from modules.rechnungsverarbeitung.src.invoices.models import InvoiceDocumentMetadata
from modules.rechnungsverarbeitung.src.invoices.services.control_engine import (
    ControlEngine,
    ControlSeverity,
    ControlStatus,
    NextAction,
)


def _metadata(status: str = "uploaded") -> InvoiceDocumentMetadata:
    return InvoiceDocumentMetadata(
        id="doc-001",
        tenant_id="tenant-001",
        status=status,
    )


def test_clean_invoice_passes_with_score_100() -> None:
    result = ControlEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 1234.56,
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
    )

    assert result.status == ControlStatus.PASSED
    assert result.score == 100
    assert result.next_action == NextAction.CONTINUE_PIPELINE
    assert result.findings == []


def test_missing_amount_blocks_with_critical_finding() -> None:
    result = ControlEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
    )

    assert result.status == ControlStatus.BLOCKED
    assert result.next_action == NextAction.REJECT_OR_REUPLOAD
    assert any(
        finding.code == "missing_total_amount"
        and finding.severity == ControlSeverity.CRITICAL
        for finding in result.findings
    )


def test_validation_failed_blocks_with_critical_finding() -> None:
    result = ControlEngine().evaluate(
        _metadata(status="validation_failed"),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 100,
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
        {"status": "passed"},
    )

    assert result.status == ControlStatus.BLOCKED
    assert any(
        finding.code == "validation_failed"
        and finding.severity == ControlSeverity.CRITICAL
        for finding in result.findings
    )


def test_high_amount_and_missing_invoice_number_requires_review() -> None:
    result = ControlEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": 5000,
            "currency": "EUR",
        },
    )

    assert result.status == ControlStatus.REVIEW_REQUIRED
    assert result.next_action == NextAction.MANUAL_REVIEW
    assert result.score == 70
    assert {finding.code for finding in result.findings} == {
        "missing_invoice_number",
        "high_amount_review",
    }
    assert all(finding.severity == ControlSeverity.WARNING for finding in result.findings)


def test_string_amount_with_comma_is_parsed_as_positive() -> None:
    result = ControlEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "total_amount": "1234,56",
            "currency": "EUR",
            "invoice_number": "INV-001",
        },
    )

    assert result.status == ControlStatus.PASSED
    assert "missing_total_amount" not in {finding.code for finding in result.findings}


def test_to_audit_details_contains_stable_finding_codes() -> None:
    result = ControlEngine().evaluate(
        _metadata(),
        {
            "supplier": "Supplier GmbH",
            "currency": "USD",
            "invoice_number": "INV-001",
        },
    )

    details = result.to_audit_details()

    assert details["score"] == result.score
    assert details["status"] == "blocked"
    assert details["next_action"] == "reject_or_reupload"
    assert [finding["code"] for finding in details["findings"]] == [
        "missing_total_amount",
        "unsupported_currency",
    ]
    assert details["findings"][0]["severity"] == "critical"
    assert details["findings"][0]["field"] == "total_amount"
    assert isinstance(details["findings"][0]["details"], dict)
