from __future__ import annotations
import json

import hashlib
import uuid
from datetime import datetime
from typing import BinaryIO

from shared.tenant.context import TenantContext
from modules.rechnungsverarbeitung.src.invoices.models import InvoiceDocumentMetadata
from modules.rechnungsverarbeitung.src.invoices.services.erechnung_hub import ERechnungHubService
from modules.rechnungsverarbeitung.src.invoices.services.ai_extraction import AIExtractionService

from modules.rechnungsverarbeitung.src.invoices.services.invoice_logging import (
    log_invoice_event_from_metadata,
)


STRUCTURED_FORMATS = {"xrechnung", "zugferd", "xml_other"}


def process_invoice_upload(
    file_stream: BinaryIO,
    file_name: str,
    mime_type: str,
    uploaded_by: str | None = None,
) -> InvoiceDocumentMetadata:
    """
    Einstiegspunkt für neue Rechnungsuploads.

    Ablauf (deterministisch):
    - upload_received -> classified
    - Für strukturierte Formate: validation_passed|validation_failed
    - Für PDF/sonstige: classified ohne strukturierte Validierung
    """
    _ = TenantContext.get_current_tenant()

    document_id = str(uuid.uuid4())
    metadata = InvoiceDocumentMetadata.for_new_upload(
        document_id=document_id,
        file_name=file_name,
        mime_type=mime_type,
        uploaded_by=uploaded_by,
    )

    payload = file_stream.read()
    if hasattr(file_stream, "seek"):
        file_stream.seek(0)
    payload_sha256 = hashlib.sha256(payload).hexdigest()

    log_invoice_event_from_metadata(
        metadata=metadata,
        event_type="upload_received",
        status_from=None,
        status_to="uploaded",
        message="Invoice upload received",
        extra_details={"payload_sha256": payload_sha256, "mime_type": mime_type, "file_name": file_name},
    )

    hub = ERechnungHubService()
    detected_format = hub.detect_invoice_format(payload, file_name)
    metadata.document_type = detected_format
    metadata.status = "classified"

    _persist_metadata(metadata)

    log_invoice_event_from_metadata(
        metadata=metadata,
        event_type="format_classified",
        status_from="uploaded",
        status_to="classified",
        message=f"Detected invoice format: {detected_format}",
        extra_details={"detected_format": detected_format, "payload_sha256": payload_sha256},
    )

    if detected_format in STRUCTURED_FORMATS:
        _, _, report = hub.validate_structured_invoice(
            document_id=metadata.id,
            tenant_id=metadata.tenant_id,
            xml_content=payload,
        )
        previous_status = metadata.status
        metadata.status = "validated" if report.status == "passed" else "validation_failed"

        _persist_metadata(metadata)

        log_invoice_event_from_metadata(
            metadata=metadata,
            event_type="validation_completed",
            status_from=previous_status,
            status_to=metadata.status,
            message=f"Validation status={report.status}; engine={report.engine}; config={report.config_version}",
            extra_details={
                "validation_status": report.status,
                "validation_engine": report.engine,
                "validation_config_version": report.config_version,
                "error_count": len(report.errors),
                "warning_count": len(report.warnings),
                "payload_sha256": payload_sha256,
            },
        )
    else:
        log_invoice_event_from_metadata(
            metadata=metadata,
            event_type="validation_skipped",
            status_from="classified",
            status_to="classified",
            message="Structured validation skipped for non-XML invoice format",
            extra_details={"reason": "non_structured_format", "detected_format": detected_format, "payload_sha256": payload_sha256},
        )

    # AI Data Extraction — extract supplier, amount, dates
    try:
        extractor = AIExtractionService()
        extraction = extractor.extract(payload, file_name, mime_type)
        if extraction.supplier or extraction.total_amount_gross:
            _update_extracted_fields(metadata.id, metadata.tenant_id, extraction)
            metadata.status = 'suggested'
            _persist_metadata(metadata)
            log_invoice_event_from_metadata(
                metadata=metadata,
                event_type='ai_extraction_completed',
                status_from='classified',
                status_to='suggested',
                message=f'AI extracted: {extraction.supplier} | {extraction.total_amount_gross} {extraction.currency}',
                extra_details=extraction.to_dict(),
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'AI extraction failed: {e}')

    return metadata


def _update_extracted_fields(document_id: str, tenant_id: str, extraction) -> None:
    """Update invoice record with AI-extracted fields."""
    from shared.db.session import get_session
    from sqlalchemy import text

    with get_session() as session:
        session.execute(
            text("""
                UPDATE invoices SET
                    supplier = :supplier,
                    total_amount = :total_amount,
                    currency = :currency,
                    tax_amount = :tax_amount,
                    invoice_number = :invoice_number,
                    invoice_date = :invoice_date,
                    due_date = :due_date,
                    extracted_data = :extracted_data,
                    status = 'suggested'
                WHERE document_id = :doc_id AND tenant_id = :tenant_id
            """),
            {
                "supplier": extraction.supplier,
                "total_amount": extraction.total_amount_gross,
                "currency": extraction.currency or "EUR",
                "tax_amount": extraction.tax_amount,
                "invoice_number": extraction.invoice_number,
                "invoice_date": extraction.invoice_date,
                "due_date": extraction.due_date,
                "extracted_data": json.dumps(extraction.to_dict(), ensure_ascii=False) if hasattr(extraction, 'to_dict') else '{}',
                "doc_id": document_id,
                "tenant_id": tenant_id,
            },
        )



def _persist_metadata(metadata: InvoiceDocumentMetadata) -> None:
    """
    Persistiert die aktuelle Metadaten-Sicht der Rechnung als Invoice-Row.
    Bei bestehender document_id wird ein Update durchgeführt.
    """
    from shared.db.session import get_session
    from modules.rechnungsverarbeitung.src.invoices.db_models import Invoice

    with get_session() as session:
        existing: Invoice | None = (
            session.query(Invoice)
            .filter(
                Invoice.document_id == metadata.id,
                Invoice.tenant_id == metadata.tenant_id,
            )
            .first()
        )

        if existing:
            existing.document_type = metadata.document_type
            existing.file_name = metadata.file_name
            existing.mime_type = metadata.mime_type
            existing.uploaded_by = metadata.uploaded_by
            existing.processed_at = metadata.processed_at
            existing.source_system = metadata.source_system
            existing.status = metadata.status
            return

        invoice = Invoice(
            document_id=metadata.id,
            tenant_id=metadata.tenant_id,
            document_type=metadata.document_type,
            file_name=metadata.file_name,
            mime_type=metadata.mime_type,
            uploaded_by=metadata.uploaded_by,
            uploaded_at=metadata.uploaded_at or datetime.utcnow(),
            processed_at=metadata.processed_at,
            source_system=metadata.source_system,
            status=metadata.status,
        )
        session.add(invoice)
