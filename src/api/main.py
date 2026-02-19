from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from typing import Optional

from src.common.tenant_context import TenantContext
from src.invoices.services.invoice_processing import process_invoice_upload

app = FastAPI(title="KI-Rechnungsverarbeitung API")


def set_tenant_from_header(x_tenant_id: Optional[str]) -> None:
    """
    Einfache Tenant-Resolution über Header X-Tenant-ID.[web:302][web:305]
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
    Mandantenfähiger Upload-Endpunkt für Rechnungen.[web:297][web:304]
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


@app.get("/health")
async def health():
    return {"status": "ok"}
