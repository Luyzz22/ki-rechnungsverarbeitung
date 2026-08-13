"""Authenticated audit-identity routes for security-sensitive invoice actions.

Client-provided attribution must never become the authoritative audit identity.
These routes derive the human actor from the authenticated JWT/API-key principal
and intentionally do not accept ``X-User-ID`` or a client-controlled transition
actor as an authorization/audit source.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile

from modules.rechnungsverarbeitung.src.api import main as legacy
from modules.rechnungsverarbeitung.src.auth.jwt_auth import UserAuth, get_current_user

router = APIRouter(tags=["v1"])


def _authenticated_actor(user: UserAuth) -> str:
    """Return the canonical server-authenticated audit principal."""
    actor = str(user.user_id).strip()
    if not actor:
        raise HTTPException(status_code=401, detail="Authenticated user identity is required")
    return actor


@router.post("/invoices/upload")
async def upload_invoice(
    user: UserAuth = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    file: UploadFile = File(...),
):
    """Upload with attribution derived exclusively from authenticated identity."""
    legacy._resolve_tenant_for_authenticated_request(x_tenant_id, user)
    organization_context = legacy._trusted_context_from_user(user)
    actor = _authenticated_actor(user)
    metadata = legacy.process_invoice_upload(
        file_stream=file.file,
        file_name=file.filename or "upload.pdf",
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=actor,
        organization_context=organization_context,
    )
    return {
        "document_id": metadata.id,
        "tenant_id": metadata.tenant_id,
        "status": metadata.status,
        "file_name": metadata.file_name,
        "document_type": metadata.document_type,
    }


@router.post("/invoices/upload-batch")
async def upload_batch(
    request: Request,
    user: UserAuth = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Batch upload with one authenticated actor for every persisted invoice."""
    legacy._resolve_tenant_for_authenticated_request(x_tenant_id, user)
    organization_context = legacy._trusted_context_from_user(user)
    actor = _authenticated_actor(user)
    form = await request.form()
    files = form.getlist("files")
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Max 20 files per batch")

    results: list[dict[str, object]] = []
    for file in files:
        try:
            file_name = getattr(file, "filename", None) or "upload.pdf"
            metadata = legacy.process_invoice_upload(
                file_stream=file.file,
                file_name=file_name,
                mime_type=getattr(file, "content_type", None) or "application/pdf",
                uploaded_by=actor,
                organization_context=organization_context,
            )
            results.append(
                {
                    "file_name": file_name,
                    "document_id": metadata.id,
                    "status": metadata.status,
                    "success": True,
                }
            )
        except Exception as exc:
            # Preserve the existing batch contract without leaking raw exception text.
            results.append(
                {
                    "file_name": getattr(file, "filename", "unknown"),
                    "success": False,
                    "error": type(exc).__name__,
                }
            )

    return {
        "total": len(files),
        "successful": sum(1 for result in results if result["success"]),
        "failed": sum(1 for result in results if not result["success"]),
        "results": results,
    }


@router.post(
    "/invoices/{document_id}/transition",
    response_model=legacy.TransitionResponse,
)
async def transition_invoice(
    document_id: str,
    body: legacy.TransitionRequest,
    user: UserAuth = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Execute a transition using the authenticated principal as human actor."""
    tenant_id = legacy._resolve_tenant_for_authenticated_request(x_tenant_id, user)
    actor = _authenticated_actor(user)

    with legacy.get_session() as session:
        invoice = legacy._get_invoice_or_404(session, document_id, tenant_id)
        try:
            result = legacy.state_machine.transition(
                document_id=document_id,
                current_status=invoice.status,
                target_status=body.target_status,
                actor=actor,
                details=body.details,
            )
        except legacy.TransitionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        invoice.status = result.to_status.value
        if result.to_status.value in ("exported", "archived"):
            invoice.processed_at = datetime.utcnow()

        event = legacy.InvoiceEvent(
            uploaded_by=actor,
            tenant_id=tenant_id,
            document_id=document_id,
            event_type=result.event_type,
            status_from=result.from_status.value,
            status_to=result.to_status.value,
            actor=actor,
            created_at=result.timestamp,
            details=result.details,
        )
        session.add(event)

        file_name = invoice.file_name or document_id
        legacy.notification_service.notify_transition(
            document_id=document_id,
            file_name=file_name,
            from_status=result.from_status.value,
            to_status=result.to_status.value,
            actor=actor,
            details=result.details,
            uploaded_by=actor,
        )

    return legacy.TransitionResponse(
        document_id=document_id,
        from_status=result.from_status.value,
        to_status=result.to_status.value,
        event_type=result.event_type,
        actor=actor,
        timestamp=result.timestamp.isoformat(),
    )
