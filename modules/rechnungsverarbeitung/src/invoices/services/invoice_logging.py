from __future__ import annotations
import logging
from typing import Optional

from modules.rechnungsverarbeitung.src.invoices.models import InvoiceDocumentMetadata

logger = logging.getLogger(__name__)


def log_invoice_event(
    metadata: InvoiceDocumentMetadata,
    event: str,
    message: Optional[str] = None,
) -> None:
    """
    Privacy by Design: Wir loggen nur Metadaten/IDs, keine Rechnungsinhalte.[web:226][web:288]
    """
    logger.info(
        "invoice_event",
        extra={
            "tenant_id": metadata.tenant_id,
            "document_id": metadata.id,
            "document_type": metadata.document_type,
            "status": metadata.status,
            "event": event,
            "message": message or "",
        },
    )
