from __future__ import annotations

from io import BytesIO

from modules.rechnungsverarbeitung.src.invoices.services import invoice_processing
from modules.rechnungsverarbeitung.src.invoices.services.kosit_validator import KositValidationResult


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
                KositValidationResult(
                    status="passed",
                    errors=[],
                    warnings=[],
                    engine="kosit",
                    config_version="xrechnung-3.0.1",
                    raw_output="",
                ),
            )

    monkeypatch.setattr(invoice_processing, "ERechnungHubService", DummyHub)

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
    ]
    assert all("payload_sha256" in event[3] for event in events)
    assert events[2][3]["validation_status"] == "passed"


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
    ]
    assert events[2][3]["reason"] == "non_structured_format"
