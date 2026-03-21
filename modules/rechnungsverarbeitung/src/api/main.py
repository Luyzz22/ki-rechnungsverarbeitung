from __future__ import annotations

import sentry_sdk
import os
from dotenv import load_dotenv
load_dotenv("/var/www/invoice-app/.env")

if os.getenv('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        environment=os.getenv('SENTRY_ENV', 'production'),
        release='belegflow-ai@1.0.0',
        send_default_pii=False,
    )

"""SBS Nexus Finance API – v1.0.0

Phase 1: State Machine + Audit Chain + GoBD Evidence integration.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, File, Header, HTTPException, APIRouter, Depends, Request
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

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from modules.rechnungsverarbeitung.src.auth.rate_limiter import limiter, rate_limit_handler
from modules.rechnungsverarbeitung.src.auth.jwt_auth import (
    create_tokens, decode_token, verify_password, hash_password,
    get_current_user, get_tenant_from_auth, UserAuth, TokenResponse,
)
from pydantic import BaseModel as PydanticBaseModel

app = FastAPI(
    title="SBS Nexus Finance API",
    description="Enterprise KI-Rechnungsverarbeitung — GoBD-konform, DATEV-ready",
    version="1.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    contact={"name": "SBS Deutschland GmbH & Co. KG", "email": "ki@sbsdeutschland.de"},
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

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
        "version": "1.0.0",
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
                "current_state": inv.status,
                "status": inv.status,
                "file_name": inv.file_name,
                "document_type": inv.document_type,
                "supplier": getattr(inv, 'supplier', None),
                "total_amount": float(inv.total_amount) if getattr(inv, 'total_amount', None) else None,
                "currency": getattr(inv, 'currency', None) or 'EUR',
                "invoice_number": getattr(inv, 'invoice_number', None),
                "created_at": inv.uploaded_at.isoformat() if inv.uploaded_at else None,
                "uploaded_at": inv.uploaded_at.isoformat() if inv.uploaded_at else None,
            }
            for inv in invoices
        ]
    return items


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
            "current_state": invoice.status,
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

        # Notify (inside session so invoice attrs accessible)
        _file_name = invoice.file_name or document_id
        notification_service.notify_transition(
            document_id=document_id,
            file_name=_file_name,
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




# ---------------------------------------------------------------------------
# Finance Copilot
# ---------------------------------------------------------------------------
from modules.rechnungsverarbeitung.src.invoices.services.finance_copilot import (
    FinanceCopilotService,
)

copilot_service = FinanceCopilotService()


class CopilotRequest(BaseModel):
    question: str
    conversation_history: list[dict[str, str]] | None = None


@v1.post("/copilot/chat")
async def copilot_chat(
    body: CopilotRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """AI Finance Copilot – ask questions about your invoices."""
    tenant_id = _require_tenant(x_tenant_id)
    result = copilot_service.chat(
        question=body.question,
        tenant_id=tenant_id,
        conversation_history=body.conversation_history,
    )
    return result




# ---------------------------------------------------------------------------
# Dashboard Analytics
# ---------------------------------------------------------------------------
from modules.rechnungsverarbeitung.src.invoices.services.analytics_service import AnalyticsService
analytics_service = AnalyticsService()

@v1.get("/analytics/dashboard")
async def analytics_dashboard(days: int = 90, x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")):
    tenant_id = _require_tenant(x_tenant_id)
    return analytics_service.get_dashboard(tenant_id=tenant_id, days=days)




# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------
class LoginRequest(PydanticBaseModel):
    email: str
    password: str

class RefreshRequest(PydanticBaseModel):
    refresh_token: str

@v1.post("/auth/token", response_model=TokenResponse, tags=["Auth"])
async def login(body: LoginRequest):
    """Authenticate and receive JWT tokens."""
    # For now, simple demo auth — replace with DB lookup
    if body.email == "demo@sbsdeutschland.de" and body.password == "demo2026":
        return create_tokens(user_id="demo-user", tenant_id="test-ai-live", role="user")
    raise HTTPException(status_code=401, detail="Invalid credentials")

@v1.post("/auth/refresh", response_model=TokenResponse, tags=["Auth"])
async def refresh(body: RefreshRequest):
    """Refresh an expired access token."""
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return create_tokens(user_id=payload["sub"], tenant_id=payload["tenant_id"])

@v1.get("/auth/me", tags=["Auth"])
async def get_me(user: UserAuth = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {"user_id": user.user_id, "tenant_id": user.tenant_id, "role": user.role}




# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------
from modules.rechnungsverarbeitung.src.invoices.services.user_service import UserService
user_service = UserService()

class RegisterRequest(PydanticBaseModel):
    email: str
    password: str
    name: str
    company: str = ""

class LoginRequest2(PydanticBaseModel):
    email: str
    password: str

@v1.post("/users/register", tags=["Users"])
async def register_user(body: RegisterRequest):
    """Register a new user and create tenant."""
    try:
        result = user_service.register(email=body.email, password=body.password, name=body.name, company=body.company)
        tokens = create_tokens(user_id=result["user_id"], tenant_id=result["tenant_id"], role=result["role"])
        # Send welcome email
        email_notification_service.send_welcome(to_email=body.email, name=body.name)
        return {"user": result, "tokens": tokens}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@v1.post("/users/login", tags=["Users"])
async def login_user(body: LoginRequest2):
    """Login with email/password, returns JWT + user profile."""
    try:
        result = user_service.login(email=body.email, password=body.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@v1.get("/users/profile", tags=["Users"])
async def get_profile(user: UserAuth = Depends(get_current_user)):
    """Get current user profile."""
    profile = user_service.get_user(user.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile

@v1.get("/users/team", tags=["Users"])
async def list_team(user: UserAuth = Depends(get_current_user)):
    """List all users in current tenant."""
    return user_service.list_users(user.tenant_id)




# ---------------------------------------------------------------------------
# Email Ingestion
# ---------------------------------------------------------------------------
from modules.rechnungsverarbeitung.src.invoices.services.email_ingestion import EmailIngestionService
email_service = EmailIngestionService()

@v1.post("/email/poll", tags=["Email Ingestion"])
async def trigger_email_poll(user: UserAuth = Depends(get_current_user)):
    """Manually trigger email inbox polling."""
    results = email_service.poll()
    return {"processed": len(results), "invoices": results}

@v1.get("/email/status", tags=["Email Ingestion"])
async def email_status():
    """Check email ingestion configuration status."""
    configured = all([email_service.host, email_service.user, email_service.password])
    return {
        "configured": configured,
        "imap_host": email_service.host if configured else None,
        "imap_user": email_service.user if configured else None,
        "folder": email_service.folder,
        "slack_webhook": bool(email_service.slack_webhook),
    }




# ---------------------------------------------------------------------------
# Subscriptions & Billing (Stripe)
# ---------------------------------------------------------------------------
from modules.rechnungsverarbeitung.src.invoices.services.subscription_service import SubscriptionService
from modules.rechnungsverarbeitung.src.invoices.services.email_notifications import EmailService
email_notification_service = EmailService()

subscription_service = SubscriptionService()

@v1.get("/billing/plans", tags=["Billing"])
async def list_plans():
    """List available subscription plans."""
    return subscription_service.get_plans()

@v1.get("/billing/subscription", tags=["Billing"])
async def get_subscription(user: UserAuth = Depends(get_current_user)):
    """Get current tenant subscription status."""
    return subscription_service.get_tenant_subscription(user.tenant_id)

@v1.post("/billing/checkout", tags=["Billing"])
async def create_checkout(
    plan_id: str,
    user: UserAuth = Depends(get_current_user),
):
    """Create Stripe Checkout session for plan upgrade."""
    try:
        from modules.rechnungsverarbeitung.src.invoices.services.user_service import UserService
        us = UserService()
        profile = us.get_user(user.user_id)
        email = profile.get("email", "") if profile else ""
        result = subscription_service.create_checkout_session(
            tenant_id=user.tenant_id,
            plan_id=plan_id,
            user_email=email,
            success_url="https://belegflow-ai.de/billing/success",
            cancel_url="https://belegflow-ai.de/billing/cancel",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@v1.post("/billing/portal", tags=["Billing"])
async def create_portal(user: UserAuth = Depends(get_current_user)):
    """Create Stripe Customer Portal session."""
    try:
        result = subscription_service.create_portal_session(
            tenant_id=user.tenant_id,
            return_url="https://belegflow-ai.de/dashboard",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@v1.get("/billing/usage", tags=["Billing"])
async def check_usage(user: UserAuth = Depends(get_current_user)):
    """Check invoice processing usage vs plan limit."""
    return subscription_service.check_invoice_limit(user.tenant_id)

@v1.post("/billing/webhook", tags=["Billing"], include_in_schema=False)
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint."""
    from fastapi import Request
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        result = subscription_service.handle_webhook(payload, sig)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))




# ---------------------------------------------------------------------------
# RBAC — Role-Based Access Control
# ---------------------------------------------------------------------------
class UpdateRoleRequest(PydanticBaseModel):
    user_id: str
    role: str  # admin, editor, viewer

class InviteRequest(PydanticBaseModel):
    email: str
    name: str
    role: str = "editor"
    password: str = ""

@v1.put("/users/role", tags=["RBAC"])
async def update_user_role(body: UpdateRoleRequest, user: UserAuth = Depends(get_current_user)):
    """Update a team member's role. Admin only."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    try:
        return user_service.update_role(admin_tenant_id=user.tenant_id, target_user_id=body.user_id, new_role=body.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@v1.post("/users/invite", tags=["RBAC"])
async def invite_team_member(body: InviteRequest, user: UserAuth = Depends(get_current_user)):
    """Invite a new team member to current tenant. Admin only."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    import secrets
    password = body.password if body.password else secrets.token_urlsafe(12)
    try:
        result = user_service.invite_user(
            email=body.email, password=password, name=body.name,
            tenant_id=user.tenant_id, role=body.role,
        )
        result["temp_password"] = password
        # Send invite email
        email_result = email_notification_service.send_invite(
            to_email=body.email, inviter_name="Admin", temp_password=password, role=body.role,
        )
        result["email_sent"] = email_result.get("sent", False)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@v1.delete("/users/{user_id}", tags=["RBAC"])
async def remove_team_member(user_id: str, user: UserAuth = Depends(get_current_user)):
    """Remove a team member from tenant. Admin only."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    try:
        return user_service.delete_user(admin_tenant_id=user.tenant_id, target_user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))




# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------
class ForgotPasswordRequest(PydanticBaseModel):
    email: str

@v1.post("/auth/forgot-password", tags=["Auth"])
async def forgot_password(body: ForgotPasswordRequest):
    """Send a temporary password via email."""
    import secrets
    from shared.db.session import get_session
    from sqlalchemy import text
    from modules.rechnungsverarbeitung.src.auth.jwt_auth import hash_password

    with get_session() as s:
        row = s.execute(text("SELECT id, name, email FROM users WHERE email = :e"), {"e": body.email.lower().strip()}).fetchone()
        if not row:
            return {"message": "Falls ein Konto existiert, wird eine E-Mail gesendet."}

        temp_pw = secrets.token_urlsafe(10)
        import bcrypt
        hashed = bcrypt.hashpw(temp_pw[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        s.execute(text("UPDATE users SET password_hash = :pw WHERE id = :id"), {"pw": hashed, "id": row[0]})
        s.commit()

    email_notification_service.send_invite(
        to_email=row[2], inviter_name="BelegFlow AI", temp_password=temp_pw, role="password-reset",
    )
    return {"message": "Falls ein Konto existiert, wird eine E-Mail gesendet."}


app.include_router(v1)
