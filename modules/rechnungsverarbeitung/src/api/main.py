"""SBS Nexus Finance API – v1."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, UploadFile, File, Header, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.tenant.context import TenantContext
from shared.db.session import get_session
from modules.rechnungsverarbeitung.src.invoices.services.invoice_processing import (
    process_invoice_upload,
)
from modules.rechnungsverarbeitung.src.invoices.db_models import Invoice, InvoiceEvent

app = FastAPI(
    title="SBS Nexus Finance API",
    version="1.0.0",
    description="KI-gestuetzte E-Rechnungsverarbeitung fuer den deutschen Mittelstand",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

v1 = APIRouter(prefix="/api/v1", tags=["v1"])


@app.get("/api/v1/health")
async def health():
    checks: dict[str, str] = {"api": "ok"}
    try:
        with get_session() as session:
            session.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {
        "status": status,
        "checks": checks,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _require_tenant(x_tenant_id: str | None) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    TenantContext.set_current_tenant(x_tenant_id)
    return x_tenant_id


@v1.post("/invoices/upload")
async def upload_invoice(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    uploaded_by: str | None = Header(default=None, alias="X-User-ID"),
    file: UploadFile = File(...),
):
    _require_tenant(x_tenant_id)
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


@v1.get("/invoices/{document_id}")
async def get_invoice(
    document_id: str,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = _require_tenant(x_tenant_id)
    with get_session() as session:
        invoice: Invoice | None = (
            session.query(Invoice)
            .filter(Invoice.document_id == document_id, Invoice.tenant_id == tenant_id)
            .first()
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return {
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


@v1.get("/invoices")
async def list_invoices(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    limit: int = 50,
    offset: int = 0,
):
    tenant_id = _require_tenant(x_tenant_id)
    with get_session() as session:
        invoices = (
            session.query(Invoice)
            .filter(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        items = [
            {
                "document_id": inv.document_id,
                "status": inv.status,
                "file_name": inv.file_name,
                "uploaded_at": inv.uploaded_at.isoformat() if inv.uploaded_at else None,
            }
            for inv in invoices
        ]
    return {"items": items, "limit": limit, "offset": offset}


@v1.get("/invoices/{document_id}/events")
async def get_invoice_events(
    document_id: str,
    x_tenant_id: str = Header(alias="X-Tenant-ID"),
):
    tenant_id = _require_tenant(x_tenant_id)
    with get_session() as session:
        events = (
            session.query(InvoiceEvent)
            .filter(InvoiceEvent.document_id == document_id, InvoiceEvent.tenant_id == tenant_id)
            .order_by(InvoiceEvent.created_at.asc())
            .all()
        )
        return [
            {
                "id": ev.id,
                "event_type": ev.event_type,
                "status_from": ev.status_from,
                "status_to": ev.status_to,
                "actor": ev.actor,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
                "details": ev.details or {},
            }
            for ev in events
        ]


app.include_router(v1)
