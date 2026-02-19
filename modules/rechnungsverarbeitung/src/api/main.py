from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, UploadFile, File, Header, HTTPException

from shared.tenant.context import TenantContext
from shared.db.session import get_session
from modules.rechnungsverarbeitung.src.invoices.services.invoice_processing import (
    process_invoice_upload,
)
from modules.rechnungsverarbeitung.src.invoices.db_models import Invoice


app = FastAPI(title="KI-Rechnungsverarbeitung API")


def set_tenant_from_header(x_tenant_id: Optional[str]) -> None:
    """
    Einfache Tenant-Resolution über Header X-Tenant-ID.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    TenantContext.set_current_tenant(x_tenant_id)


@app.post("/invoices/upload")
async def upload_invoice(
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
    uploaded_by: Optional[str] = Header(default=None, alias="X-User-ID"),
    file: UploadFile = File(...),
):
    """
    Mandantenfähiger Upload-Endpunkt für Rechnungen.
    """
    set_tenant_from_header(x_tenant_id)

    # Datei-Stream an den Service durchreichen
    metadata = process_invoice_upload(
        file_stream=file.file,
        file_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=uploaded_by,
    )

    return {
        "document_id": metadata.id,
        "tenant_id": metadata.tenant_id,
        "status": metadata.status,
        "file_name": metadata.file_name,
        "document_type": metadata.document_type,
    }


@app.get("/invoices/{document_id}")
async def get_invoice(
    document_id: str,
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
):
    """
    Liefert eine Rechnung mandantengetrennt über document_id + X-Tenant-ID.
    """
    set_tenant_from_header(x_tenant_id)
    tenant_id = TenantContext.get_current_tenant()

    with get_session() as session:
        invoice: Invoice | None = (
            session.query(Invoice)
            .filter(
                Invoice.document_id == document_id,
                Invoice.tenant_id == tenant_id,
            )
            .first()
        )

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Alle benötigten Felder innerhalb der offenen Session materialisieren
        response_data = {
            "document_id": invoice.document_id,
            "tenant_id": invoice.tenant_id,
            "status": invoice.status,
            "file_name": invoice.file_name,
            "document_type": invoice.document_type,
            "uploaded_by": invoice.uploaded_by,
            "uploaded_at": invoice.uploaded_at.isoformat() if invoice.uploaded_at else None,
            "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None,
            "source_system": invoice.source_system,
        }

    return response_data


@app.get("/invoices")
async def list_invoices(
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
    limit: int = 50,
    offset: int = 0,
):
    """
    Listet Rechnungen mandantengetrennt, mit einfachem Paging.
    """
    set_tenant_from_header(x_tenant_id)
    tenant_id = TenantContext.get_current_tenant()

    with get_session() as session:
        query = (
            session.query(Invoice)
            .filter(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        invoices = list(query)

        items = [
            {
                "document_id": inv.document_id,
                "tenant_id": inv.tenant_id,
                "status": inv.status,
                "file_name": inv.file_name,
                "uploaded_at": inv.uploaded_at.isoformat() if inv.uploaded_at else None,
            }
            for inv in invoices
        ]

    return {
        "items": items,
        "limit": limit,
        "offset": offset,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

