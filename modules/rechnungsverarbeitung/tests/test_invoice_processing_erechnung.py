from __future__ import annotations

from io import BytesIO
import sys
import types

try:
    from lxml import etree as _unused_etree  # noqa: F401
except ModuleNotFoundError:
    lxml_module = types.ModuleType("lxml")
    etree_module = types.ModuleType("lxml.etree")
    lxml_module.etree = etree_module
    sys.modules.setdefault("lxml", lxml_module)
    sys.modules.setdefault("lxml.etree", etree_module)

from modules.rechnungsverarbeitung.src.invoices.services import invoice_processing


class DummyValidationReport:
    def __init__(self) -> None:
        self.status = "passed"
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.engine = "kosit"
        self.config_version = "xrechnung-3.0.1"
        self.raw_output = ""


class EmptyExtraction:
    supplier = None
    total_amount_gross = None
    currency = "EUR"

    def to_dict(self) -> dict:
        return {}


class EmptyAIExtractionService:
    def extract(self, file_content: bytes, file_name: str, mime_type: str) -> EmptyExtraction:
        return EmptyExtraction()


def test_process_structured_invoice_validation_pass(monkeypatch) -> None:
    events: list[tuple[str, str | None, str | None, dict]] = []
    persisted_statuses: list[str] = []

    monkeypatch.setattr(
        invoice_processing.TenantContext,
        "get_current_tenant",
        staticmethod(lambda: "tenant-a"),
    )

    def capture_persist(metadata):
        persisted_statuses.append(metadata.status)

    monkeypatch.setattr(invoice_processing, "_persist_metadata", capture_persist)

    def capture_event(metadata, event_type, status_from, status_to, message=None, extra_details=None):
        events.append((event_type, status_from, status_to, extra_details or {}))

    monkeypatch.setattr(invoice_processing, "log_invoice_event_from_metadata", capture_event)

    class DummyHub:
        def detect_invoice_format(self, content: bytes, filename: str = "") -> str:
            assert b"CrossIndustryInvoice" in content
            return "xrechnung"

        def validate_structured_invoice(self, *, document_id: str, tenant_id: str, xml_content: bytes):
            assert document_id
            assert tenant_id == "tenant-a"
            return (
                None,
                None,
                DummyValidationReport(),
            )

    monkeypatch.setattr(invoice_processing, "ERechnungHubService", DummyHub)
    monkeypatch.setattr(invoice_processing, "AIExtractionService", EmptyAIExtractionService)

    metadata = invoice_processing.process_invoice_upload(
        file_stream=BytesIO(b"<rsm:CrossIndustryInvoice/>"),
        file_name="invoice.xml",
        mime_type="application/xml",
        uploaded_by="user-1",
    )

    assert metadata.document_type == "xrechnung"
    assert metadata.status == "validated"
    assert persisted_statuses == ["classified", "validated"]
    assert [event[0] for event in events] == [
        "upload_received",
        "format_classified",
        "validation_completed",
        "flowcheck_controls_evaluated",
        "flowcheck.policy.evaluated",
    ]
    assert all("payload_sha256" in event[3] for event in events[:3])
    assert events[2][3]["validation_status"] == "passed"
    assert events[-2][0] == "flowcheck_controls_evaluated"
    assert {"score", "status", "findings"}.issubset(events[-2][3])
    assert events[-2][3]["status"] == "passed"
    assert events[-2][3]["score"] == 100
    assert events[-2][3]["findings"] == []
    assert events[-1][0] == "flowcheck.policy.evaluated"
    assert events[-1][3]["status"] == "review_required"
    assert "findings" in events[-1][3]


def test_process_pdf_skips_structured_validation(monkeypatch) -> None:
    events: list[tuple[str, str | None, str | None, dict]] = []
    persisted_statuses: list[str] = []

    monkeypatch.setattr(
        invoice_processing.TenantContext,
        "get_current_tenant",
        staticmethod(lambda: "tenant-b"),
    )

    def capture_persist(metadata):
        persisted_statuses.append(metadata.status)

    monkeypatch.setattr(invoice_processing, "_persist_metadata", capture_persist)

    def capture_event(metadata, event_type, status_from, status_to, message=None, extra_details=None):
        events.append((event_type, status_from, status_to, extra_details or {}))

    monkeypatch.setattr(invoice_processing, "log_invoice_event_from_metadata", capture_event)

    class DummyHub:
        def detect_invoice_format(self, content: bytes, filename: str = "") -> str:
            return "pdf_other"

        def validate_structured_invoice(self, *, document_id: str, tenant_id: str, xml_content: bytes):
            raise AssertionError("must not be called for pdf_other")

    monkeypatch.setattr(invoice_processing, "ERechnungHubService", DummyHub)
    monkeypatch.setattr(invoice_processing, "AIExtractionService", EmptyAIExtractionService)

    metadata = invoice_processing.process_invoice_upload(
        file_stream=BytesIO(b"%PDF-1.7"),
        file_name="invoice.pdf",
        mime_type="application/pdf",
        uploaded_by="user-2",
    )

    assert metadata.document_type == "pdf_other"
    assert metadata.status == "classified"
    assert persisted_statuses == ["classified"]
    assert [event[0] for event in events] == [
        "upload_received",
        "format_classified",
        "validation_skipped",
        "flowcheck_controls_evaluated",
        "flowcheck.policy.evaluated",
    ]
    assert events[2][3]["reason"] == "non_structured_format"
    assert events[-2][0] == "flowcheck_controls_evaluated"
    assert {"score", "status", "findings"}.issubset(events[-2][3])
    assert events[-1][0] == "flowcheck.policy.evaluated"
    assert events[-1][3]["status"] == "review_required"


def test_process_pdf_flowcheck_passes_with_extracted_invoice_data(monkeypatch) -> None:
    events: list[tuple[str, str | None, str | None, dict]] = []
    persisted_statuses: list[str] = []
    updated_fields: list[tuple[str, str, object]] = []

    monkeypatch.setattr(
        invoice_processing.TenantContext,
        "get_current_tenant",
        staticmethod(lambda: "tenant-c"),
    )

    def capture_persist(metadata):
        persisted_statuses.append(metadata.status)

    monkeypatch.setattr(invoice_processing, "_persist_metadata", capture_persist)

    def capture_event(metadata, event_type, status_from, status_to, message=None, extra_details=None):
        events.append((event_type, status_from, status_to, extra_details or {}))

    monkeypatch.setattr(invoice_processing, "log_invoice_event_from_metadata", capture_event)

    def capture_update(document_id: str, tenant_id: str, extraction) -> None:
        updated_fields.append((document_id, tenant_id, extraction))

    monkeypatch.setattr(invoice_processing, "_update_extracted_fields", capture_update)

    class DummyHub:
        def detect_invoice_format(self, content: bytes, filename: str = "") -> str:
            return "pdf_other"

        def validate_structured_invoice(self, *, document_id: str, tenant_id: str, xml_content: bytes):
            raise AssertionError("must not be called for pdf_other")

    class DummyExtraction:
        supplier = "Supplier GmbH"
        total_amount_gross = 1234.56
        currency = "EUR"
        invoice_number = "INV-001"
        tax_amount = None
        invoice_date = None
        due_date = None

        def to_dict(self) -> dict:
            return {
                "supplier": self.supplier,
                "total_amount_gross": self.total_amount_gross,
                "currency": self.currency,
                "invoice_number": self.invoice_number,
            }

    class DummyAIExtractionService:
        def extract(self, file_content: bytes, file_name: str, mime_type: str) -> DummyExtraction:
            return DummyExtraction()

    monkeypatch.setattr(invoice_processing, "ERechnungHubService", DummyHub)
    monkeypatch.setattr(invoice_processing, "AIExtractionService", DummyAIExtractionService)

    metadata = invoice_processing.process_invoice_upload(
        file_stream=BytesIO(b"%PDF-1.7"),
        file_name="invoice.pdf",
        mime_type="application/pdf",
        uploaded_by="user-3",
    )

    assert metadata.document_type == "pdf_other"
    assert metadata.status == "suggested"
    assert persisted_statuses == ["classified", "suggested"]
    assert len(updated_fields) == 1
    assert [event[0] for event in events] == [
        "upload_received",
        "format_classified",
        "validation_skipped",
        "ai_extraction_completed",
        "flowcheck_controls_evaluated",
        "flowcheck.policy.evaluated",
    ]
    assert events[-2][0] == "flowcheck_controls_evaluated"
    assert events[-2][3]["status"] == "passed"
    assert events[-2][3]["score"] == 100
    assert events[-2][3]["findings"] == []
    assert events[-1][0] == "flowcheck.policy.evaluated"
    assert events[-1][3]["status"] == "passed"
    assert events[-1][3]["findings"] == []


def test_process_pdf_policy_uses_budget_context(monkeypatch) -> None:
    events: list[tuple[str, str | None, str | None, dict]] = []

    monkeypatch.setattr(
        invoice_processing.TenantContext,
        "get_current_tenant",
        staticmethod(lambda: "tenant-d"),
    )
    monkeypatch.setattr(invoice_processing, "_persist_metadata", lambda metadata: None)

    def capture_event(metadata, event_type, status_from, status_to, message=None, extra_details=None):
        events.append((event_type, status_from, status_to, extra_details or {}))

    monkeypatch.setattr(invoice_processing, "log_invoice_event_from_metadata", capture_event)
    monkeypatch.setattr(invoice_processing, "_update_extracted_fields", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        invoice_processing,
        "_build_policy_context",
        lambda tenant_id, reference_at=None: {
            "budget_actual": 9500,
            "budget_limit": 10000,
            "budget_category": "opex",
        },
    )

    class DummyHub:
        def detect_invoice_format(self, content: bytes, filename: str = "") -> str:
            return "pdf_other"

        def validate_structured_invoice(self, *, document_id: str, tenant_id: str, xml_content: bytes):
            raise AssertionError("must not be called for pdf_other")

    class DummyExtraction:
        supplier = "Supplier GmbH"
        total_amount_gross = 600
        currency = "EUR"
        invoice_number = "INV-001"

        def to_dict(self) -> dict:
            return {
                "supplier": self.supplier,
                "total_amount_gross": self.total_amount_gross,
                "currency": self.currency,
                "invoice_number": self.invoice_number,
            }

    class DummyAIExtractionService:
        def extract(self, file_content: bytes, file_name: str, mime_type: str) -> DummyExtraction:
            return DummyExtraction()

    monkeypatch.setattr(invoice_processing, "ERechnungHubService", DummyHub)
    monkeypatch.setattr(invoice_processing, "AIExtractionService", DummyAIExtractionService)

    invoice_processing.process_invoice_upload(
        file_stream=BytesIO(b"%PDF-1.7"),
        file_name="invoice.pdf",
        mime_type="application/pdf",
        uploaded_by="user-4",
    )

    policy_event = events[-1]
    assert policy_event[0] == "flowcheck.policy.evaluated"
    assert policy_event[3]["status"] == "violated"
    assert any(
        finding["code"] == "policy_budget_limit_exceeded" for finding in policy_event[3]["findings"]
    )
