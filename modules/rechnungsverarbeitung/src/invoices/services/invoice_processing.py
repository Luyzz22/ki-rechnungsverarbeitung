from __future__ import annotations

import uuid
from datetime import datetime
from typing import BinaryIO

from shared.db.session import get_session
from modules.rechnungsverarbeitung.src.invoices.db_models import Invoice
from modules.rechnungsverarbeitung.src.invoices.models import InvoiceDocumentMetadata
from modules.rechnungsverarbeitung.src.invoices.services.invoice_logging import log_invoice_event
from shared.tenant.context import TenantContext


def process_invoice_upload(file_stream: BinaryIO, file_name: str, mime_type: str, uploaded_by: str | None = None) -> InvoiceDocumentMetadata:
    """
    Einstiegspunkt für neue Rechnungsuploads.
    - Erzeugt eine technische Dokument-ID
    - Erzeugt tenant-aware Metadaten
    - Triggert die weitere Verarbeitung (Platzhalter)
    """
    # Stelle sicher, dass ein Tenant gesetzt ist (z.B. durch API-Gateway / Middleware)
    _ = TenantContext.get_current_tenant()

    document_id = str(uuid.uuid4())
    metadata = InvoiceDocumentMetadata.for_new_upload(
        document_id=document_id,
        file_name=file_name,
        mime_type=mime_type,
        uploaded_by=uploaded_by,
    )

    log_invoice_event(metadata, event="upload_received", message="Invoice upload received")
    _persist_metadata(metadata)

    # TODO: Hier folgt deine tatsächliche Extraktion/Verarbeitung des PDF
    # z.B. call_extract_invoice(file_stream, metadata)

    return metadata

def _persist_metadata(metadata: InvoiceDocumentMetadata) -> None:
    from datetime import datetime

    with get_session() as session:
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

