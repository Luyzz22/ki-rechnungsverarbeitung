from __future__ import annotations
from typing import BinaryIO

from src.invoices.models import InvoiceDocumentMetadata
from src.invoices.services.invoice_logging import log_invoice_event
from src.common.tenant_context import TenantContext
import uuid


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

    # TODO: Hier folgt deine tatsächliche Extraktion/Verarbeitung des PDF
    # z.B. call_extract_invoice(file_stream, metadata)

    return metadata
