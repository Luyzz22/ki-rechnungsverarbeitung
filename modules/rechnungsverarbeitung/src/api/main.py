"""SBS Nexus Finance API – v1.1.0

Phase 1: State Machine + Audit Chain + GoBD Evidence integration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, File, Header, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.settings import get_settings
from shared.tenant.context import TenantContext
from shared.db.session import get_session
from modules.rechnungsverarbeitung.src.invoices.services.invoice_processing import (
    process_invoice_upload,
)
from modules.rechnungsverarbeitung.src.invoices.services.notifications import (
    NotificationService,
)

notification_service = NotificationService()

from modules.rechnungsverarbeitung.src.invoices.services.state_machine import (
    InvoiceStateMachine,
    TransitionError,
)
from modules.rechnungsverarbeitung.src.invoices.services.audit_chain import (
    AuditChain,
)
from modules.rechnungsverarbeitung.src.invoices.services.gobd_evidence import (
    GoBDEvidenceService,
    EvidenceArtifact,
)
from modules.rechnungsverarbeitung.src.invoices.db_models import Invoice, InvoiceEvent

# ── Singletons ────────────────────────────────────────────────────────

state_machine = InvoiceStateMachine()
settings = get_settings()
evidence_service = GoBDEvidenceService(evidence_dir=settings.gobd_evidence_dir)

# ── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="SBS Nexus Finance API",
    version="1.1.0",
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


# ── Request/Response Models ───────────────────────────────────────────


class TransitionRequest(BaseModel):
    target_status: str
    actor: str | None = None
    details: dict[str, Any] | None = None


class TransitionResponse(BaseModel):
    document_id: str
    from_status: str
    to_status: str
    event_type: str
    actor: str | None
    timestamp: str


# ── Helpers ───────────────────────────────────────────────────────────


def _require_tenant(x_tenant_id: str | None) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    TenantContext.set_current_tenant(x_tenant_id)
    return x_tenant_id


def _get_invoice_or_404(session, document_id: str, tenant_id: str) -> Invoice:
    invoice: Invoice | None = (
        session.query(Invoice)
        .filter(Invoice.document_id == document_id, Invoice.tenant_id == tenant_id)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


def _build_audit_chain(session, document_id: str, tenant_id: str) -> AuditChain:
    """Reconstruct audit chain from persisted events."""
    events = (
        session.query(InvoiceEvent)
        .filter(InvoiceEvent.document_id == document_id, InvoiceEvent.tenant_id == tenant_id)
        .order_by(InvoiceEvent.created_at.asc())
        .all()
    )
    chain = AuditChain(document_id=document_id, tenant_id=tenant_id)
    for ev in events:
        chain.append(
            event_type=ev.event_type,
            status_from=ev.status_from,
            status_to=ev.status_to,
            actor=ev.actor,
            details=ev.details or {},
            timestamp=ev.created_at,
        )
    return chain


# ── Health ────────────────────────────────────────────────────────────


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
        "version": "1.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Upload ────────────────────────────────────────────────────────────


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


# ── CRUD ──────────────────────────────────────────────────────────────


@v1.get("/invoices")
async def list_invoices(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    tenant_id = _require_tenant(x_tenant_id)
    with get_session() as session:
        query = session.query(Invoice).filter(Invoice.tenant_id == tenant_id)
        if status:
            query = query.filter(Invoice.status == status)
        invoices = (
            query.order_by(Invoice.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        items = [
            {
                "document_id": inv.document_id,
                "status": inv.status,
                "file_name": inv.file_name,
                "document_type": inv.document_type,
                "uploaded_at": inv.uploaded_at.isoformat() if inv.uploaded_at else None,
            }
            for inv in invoices
        ]
    return {"items": items, "total": len(items), "limit": limit, "offset": offset}


@v1.get("/invoices/{document_id}")
async def get_invoice(
    document_id: str,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = _require_tenant(x_tenant_id)
    with get_session() as session:
        invoice = _get_invoice_or_404(session, document_id, tenant_id)
        allowed = state_machine.get_allowed_transitions(invoice.status)
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
            "allowed_transitions": [s.value for s in allowed],
        }


# ── State Transitions ─────────────────────────────────────────────────


@v1.post("/invoices/{document_id}/transition", response_model=TransitionResponse)
async def transition_invoice(
    document_id: str,
    body: TransitionRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Execute a validated state transition on an invoice."""
    tenant_id = _require_tenant(x_tenant_id)

    with get_session() as session:
        invoice = _get_invoice_or_404(session, document_id, tenant_id)

        try:
            result = state_machine.transition(
                document_id=document_id,
                current_status=invoice.status,
                target_status=body.target_status,
                actor=body.actor,
                details=body.details,
            )
        except TransitionError as e:
            raise HTTPException(status_code=409, detail=str(e))

        # Update invoice status
        invoice.status = result.to_status.value
        if result.to_status.value in ("exported", "archived"):
            invoice.processed_at = datetime.utcnow()

        # Persist audit event
        event = InvoiceEvent(
            tenant_id=tenant_id,
            document_id=document_id,
            event_type=result.event_type,
            status_from=result.from_status.value,
            status_to=result.to_status.value,
            actor=result.actor,
            created_at=result.timestamp,
            details=result.details,
        )
        session.add(event)

    # Notify
    notification_service.notify_transition(
        document_id=document_id,
        file_name=invoice.file_name if hasattr(invoice, "file_name") else document_id,
        from_status=result.from_status.value,
        to_status=result.to_status.value,
        actor=result.actor,
        details=result.details,
        tenant_id=tenant_id,
    )

    return TransitionResponse(
        document_id=document_id,
        from_status=result.from_status.value,
        to_status=result.to_status.value,
        event_type=result.event_type,
        actor=result.actor,
        timestamp=result.timestamp.isoformat(),
    )


@v1.get("/invoices/{document_id}/transitions")
async def get_allowed_transitions(
    document_id: str,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Query which transitions are currently valid for this invoice."""
    tenant_id = _require_tenant(x_tenant_id)
    with get_session() as session:
        invoice = _get_invoice_or_404(session, document_id, tenant_id)
        allowed = state_machine.get_allowed_transitions(invoice.status)
        return {
            "document_id": document_id,
            "current_status": invoice.status,
            "allowed_transitions": [s.value for s in allowed],
        }


# ── Audit Events ──────────────────────────────────────────────────────


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


# ── Chain Verification ────────────────────────────────────────────────


@v1.get("/invoices/{document_id}/chain/verify")
async def verify_chain(
    document_id: str,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Verify the hash-chain integrity for a document's audit trail."""
    tenant_id = _require_tenant(x_tenant_id)
    with get_session() as session:
        _get_invoice_or_404(session, document_id, tenant_id)
        chain = _build_audit_chain(session, document_id, tenant_id)
        verified = chain.verify()
        return {
            "document_id": document_id,
            "chain_length": chain.length,
            "verified": verified,
            "last_hash": chain.last_hash[:16] + "..." if chain.length > 0 else None,
        }


# ── GoBD Evidence ─────────────────────────────────────────────────────


@v1.post("/invoices/{document_id}/evidence")
async def create_evidence_package(
    document_id: str,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Create a sealed GoBD evidence package for this invoice."""
    tenant_id = _require_tenant(x_tenant_id)

    with get_session() as session:
        invoice = _get_invoice_or_404(session, document_id, tenant_id)

        if invoice.status not in ("exported", "archived"):
            raise HTTPException(
                status_code=409,
                detail=f"Evidence package requires status 'exported' or 'archived', current: '{invoice.status}'",
            )

        chain = _build_audit_chain(session, document_id, tenant_id)

        path = evidence_service.create_package(
            document_id=document_id,
            tenant_id=tenant_id,
            audit_chain=chain,
            metadata={
                "file_name": invoice.file_name,
                "document_type": invoice.document_type,
                "source_system": invoice.source_system,
                "uploaded_by": invoice.uploaded_by,
                "uploaded_at": invoice.uploaded_at.isoformat() if invoice.uploaded_at else None,
                "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None,
            },
        )

        return {
            "document_id": document_id,
            "evidence_path": str(path),
            "chain_length": chain.length,
            "chain_verified": chain.verify(),
            "size_bytes": path.stat().st_size,
        }




# ── DATEV Export ──────────────────────────────────────────────────────

from modules.rechnungsverarbeitung.src.invoices.services.datev_export import (
    DatevExportService,
)

datev_service = DatevExportService(
    export_dir=settings.datev_export_dir,
    skr=settings.datev_default_skr,
)


class DatevExportRequest(BaseModel):
    konto: str = "4400"
    gegenkonto: str = "1200"
    betrag: float
    buchungstext: str = ""
    steuerschluessel: str = ""
    kostenstelle: str = ""
    belegdatum: str = ""


@v1.post("/invoices/{document_id}/datev-export")
async def export_to_datev(
    document_id: str,
    body: DatevExportRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Export approved invoice to DATEV Buchungsstapel."""
    tenant_id = _require_tenant(x_tenant_id)

    with get_session() as session:
        invoice = _get_invoice_or_404(session, document_id, tenant_id)

        if invoice.status != "approved":
            raise HTTPException(
                status_code=409,
                detail=f"DATEV export requires status 'approved', current: '{invoice.status}'",
            )

        result = datev_service.export_invoice(
            document_id=document_id,
            tenant_id=tenant_id,
            kontierung=body.model_dump(),
            invoice_data={"file_name": invoice.file_name},
        )

        # Transition to exported
        try:
            tr = state_machine.transition(
                document_id=document_id,
                current_status=invoice.status,
                target_status="exported",
                details={"datev_batch": result.batch_id, "export_hash": result.export_hash},
            )
            invoice.status = tr.to_status.value
            invoice.processed_at = datetime.utcnow()

            event = InvoiceEvent(
                tenant_id=tenant_id,
                document_id=document_id,
                event_type=tr.event_type,
                status_from=tr.from_status.value,
                status_to=tr.to_status.value,
                actor=tr.actor,
                created_at=tr.timestamp,
                details=tr.details,
            )
            session.add(event)
        except TransitionError as e:
            raise HTTPException(status_code=409, detail=str(e))

    return {
        "batch_id": result.batch_id,
        "document_id": document_id,
        "file_path": result.file_path,
        "records_count": result.records_count,
        "total_amount": result.total_amount,
        "export_hash": result.export_hash,
        "skr": result.skr,
        "status": "exported",
    }


# ── KoSIT Validation ─────────────────────────────────────────────────

from modules.rechnungsverarbeitung.src.invoices.services.erechnung_hub import (
    ERechnungHubService,
)

erechnung_hub = ERechnungHubService()


@v1.post("/invoices/{document_id}/validate")
async def validate_invoice(
    document_id: str,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    file: UploadFile = File(...),
):
    """Run KoSIT validation on an uploaded XML invoice."""
    tenant_id = _require_tenant(x_tenant_id)

    with get_session() as session:
        invoice = _get_invoice_or_404(session, document_id, tenant_id)
        content = await file.read()

        # Detect format
        detected = erechnung_hub.detect_invoice_format(content, file.filename or "")

        if detected not in ("xrechnung", "zugferd", "xml_other"):
            return {
                "document_id": document_id,
                "format": detected,
                "validation": "skipped",
                "reason": "Non-XML format, structural validation not applicable",
            }

        # Run validation
        json_path, txt_path, report = erechnung_hub.validate_structured_invoice(
            document_id=document_id,
            tenant_id=tenant_id,
            xml_content=content,
        )

        # Transition based on result
        target = "validated" if report.status == "passed" else "validation_failed"
        if state_machine.can_transition(invoice.status, target):
            try:
                tr = state_machine.transition(
                    document_id=document_id,
                    current_status=invoice.status,
                    target_status=target,
                    details={
                        "engine": report.engine,
                        "config_version": report.config_version,
                        "error_count": len(report.errors),
                        "warning_count": len(report.warnings),
                    },
                )
                invoice.status = tr.to_status.value

                event = InvoiceEvent(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    event_type=tr.event_type,
                    status_from=tr.from_status.value,
                    status_to=tr.to_status.value,
                    actor=tr.actor,
                    created_at=tr.timestamp,
                    details=tr.details,
                )
                session.add(event)
            except TransitionError:
                pass  # Validation result logged but transition skipped

        return {
            "document_id": document_id,
            "format": detected,
            "validation_status": report.status,
            "engine": report.engine,
            "config_version": report.config_version,
            "errors": report.errors,
            "warnings": report.warnings,
            "report_hash": report.report_hash,
            "current_status": invoice.status,
        }



# ── AI Kontierung ─────────────────────────────────────────────────────

from modules.rechnungsverarbeitung.src.invoices.services.ai_kontierung import (
    AIKontierungService,
)

ai_kontierung = AIKontierungService()


class KontierungRequest(BaseModel):
    invoice_data: dict[str, Any]
    skr: str = "SKR03"


@v1.post("/invoices/{document_id}/kontierung")
async def suggest_kontierung(
    document_id: str,
    body: KontierungRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """AI-powered account assignment suggestion."""
    tenant_id = _require_tenant(x_tenant_id)

    with get_session() as session:
        invoice = _get_invoice_or_404(session, document_id, tenant_id)

        result = ai_kontierung.suggest(
            invoice_data=body.invoice_data,
            skr=body.skr,
        )

        current_status = invoice.status

        # Transition to suggested if possible
        if state_machine.can_transition(current_status, "suggested"):
            try:
                tr = state_machine.transition(
                    document_id=document_id,
                    current_status=current_status,
                    target_status="suggested",
                    actor=f"ai:{result.model}",
                    details=result.to_dict(),
                )
                invoice.status = tr.to_status.value
                current_status = tr.to_status.value

                event = InvoiceEvent(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    event_type=tr.event_type,
                    status_from=tr.from_status.value,
                    status_to=tr.to_status.value,
                    actor=tr.actor,
                    created_at=tr.timestamp,
                    details=tr.details,
                )
                session.add(event)
            except TransitionError:
                pass

    return {
        "document_id": document_id,
        "suggestion": result.to_dict(),
        "current_status": current_status,
    }




class DatevBatchRequest(BaseModel):
    document_ids: list[str]
    kontierungen: dict[str, dict[str, Any]]  # document_id -> kontierung


@v1.post("/invoices/datev-batch")
async def batch_export_datev(
    body: DatevBatchRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Batch export multiple approved invoices to single DATEV file."""
    tenant_id = _require_tenant(x_tenant_id)

    invoices_data = []
    with get_session() as session:
        for doc_id in body.document_ids:
            invoice = _get_invoice_or_404(session, doc_id, tenant_id)
            if invoice.status != "approved":
                raise HTTPException(
                    status_code=409,
                    detail=f"Invoice {doc_id} not approved (status: {invoice.status})",
                )
            k = body.kontierungen.get(doc_id, {})
            invoices_data.append({
                "document_id": doc_id,
                "kontierung": k,
                "invoice_data": {"file_name": invoice.file_name},
            })

    result = datev_service.export_batch(tenant_id=tenant_id, invoices=invoices_data)

    # Transition all to exported
    with get_session() as session:
        for doc_id in body.document_ids:
            invoice = _get_invoice_or_404(session, doc_id, tenant_id)
            try:
                tr = state_machine.transition(
                    document_id=doc_id,
                    current_status=invoice.status,
                    target_status="exported",
                    details={"datev_batch": result.batch_id},
                )
                invoice.status = tr.to_status.value
                invoice.processed_at = datetime.utcnow()
                session.add(InvoiceEvent(
                    tenant_id=tenant_id,
                    document_id=doc_id,
                    event_type=tr.event_type,
                    status_from=tr.from_status.value,
                    status_to=tr.to_status.value,
                    actor=tr.actor,
                    created_at=tr.timestamp,
                    details=tr.details,
                ))
            except TransitionError:
                pass

    return {
        "batch_id": result.batch_id,
        "records_count": result.records_count,
        "total_amount": result.total_amount,
        "export_hash": result.export_hash,
        "skr": result.skr,
        "document_ids": body.document_ids,
    }


app.include_router(v1)
