"""Authenticated audit-identity hardening for the modular production runtime.

The legacy-sized API module still contains several route calls that pass historic
``uploaded_by`` placeholders or accept a client supplied transition actor.  The
production composition installs this compatibility layer fail-closed so that
human/service audit identity is always derived from ``UserAuth.user_id`` while
explicit technical actors (for example ``ai:<model>``) remain distinguishable.

This module also adapts a small set of stale keyword names in the oversized API
module (``uploaded_by`` -> tenant-scoped service contracts).  It does not trust
those legacy values for authorization or tenant selection.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import event

from modules.rechnungsverarbeitung.src.invoices.db_models import Invoice, InvoiceEvent
from shared.audit_identity import (
    AuditIdentityError,
    bind_authenticated_actor,
    canonical_audit_actor,
    get_authenticated_actor,
)
from shared.tenant.context import TenantContext


_INSTALLED = False


def _tenant_id() -> str:
    """Resolve tenant exclusively from the already authenticated request context."""
    return TenantContext.get_current_tenant()


def _annotate_datev_metadata(file_path: str, actor: str | None) -> None:
    """Add trusted initiator metadata without changing the deterministic CSV hash."""
    if not actor:
        return
    meta_path = Path(file_path).with_suffix(".meta.json")
    if not meta_path.exists():
        return
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return
        payload["initiated_by"] = actor
        meta_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError, TypeError):
        # Audit persistence in InvoiceEvent remains authoritative.  Failure to
        # enrich an auxiliary DATEV metadata file must not corrupt the export.
        return


def _install_model_identity_guards() -> None:
    """Override spoofable ORM audit fields when trusted request identity exists."""

    def bind_uploaded_by(_target, value, _oldvalue, _initiator):
        return get_authenticated_actor() or value

    def bind_actor(_target, value, _oldvalue, _initiator):
        return canonical_audit_actor(value)

    event.listen(Invoice.uploaded_by, "set", bind_uploaded_by, retval=True)
    event.listen(InvoiceEvent.uploaded_by, "set", bind_uploaded_by, retval=True)
    event.listen(InvoiceEvent.actor, "set", bind_actor, retval=True)


def install_audit_actor_hardening(api_main: Any) -> None:
    """Install authenticated actor binding exactly once on the production API."""
    global _INSTALLED
    if _INSTALLED:
        return

    original_resolve_tenant = api_main._resolve_tenant_for_authenticated_request

    def resolve_tenant_and_bind_actor(x_tenant_id, user):
        tenant_id = original_resolve_tenant(x_tenant_id, user)
        try:
            bind_authenticated_actor(user.user_id)
        except AuditIdentityError as exc:
            # Authenticated requests without a stable subject are invalid for
            # tenant-mutating operations and must fail closed.
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return tenant_id

    api_main._resolve_tenant_for_authenticated_request = resolve_tenant_and_bind_actor

    original_process_invoice_upload = api_main.process_invoice_upload

    def process_invoice_upload_with_actor(*args, **kwargs):
        actor = get_authenticated_actor()
        if actor:
            kwargs["uploaded_by"] = actor
        return original_process_invoice_upload(*args, **kwargs)

    api_main.process_invoice_upload = process_invoice_upload_with_actor

    original_transition = api_main.state_machine.transition

    def transition_with_actor(*args, actor=None, **kwargs):
        return original_transition(
            *args,
            actor=canonical_audit_actor(actor),
            **kwargs,
        )

    api_main.state_machine.transition = transition_with_actor

    original_notify_transition = api_main.notification_service.notify_transition

    def notify_transition_with_actor(
        *,
        document_id: str,
        file_name: str,
        from_status: str,
        to_status: str,
        actor: str | None = None,
        details: dict[str, Any] | None = None,
        tenant_id: str = "",
        uploaded_by: str | None = None,
    ) -> bool:
        del uploaded_by  # historic placeholder; never an identity source
        return original_notify_transition(
            document_id=document_id,
            file_name=file_name,
            from_status=from_status,
            to_status=to_status,
            actor=canonical_audit_actor(actor),
            details=details,
            tenant_id=tenant_id or _tenant_id(),
        )

    api_main.notification_service.notify_transition = notify_transition_with_actor

    original_create_package = api_main.evidence_service.create_package

    def create_package_with_actor(
        *,
        document_id: str,
        audit_chain,
        tenant_id: str | None = None,
        uploaded_by: str | None = None,
        artifacts=None,
        metadata: dict[str, Any] | None = None,
    ):
        del uploaded_by  # client/legacy value cannot select identity or tenant
        actor = get_authenticated_actor()
        safe_metadata = dict(metadata or {})
        if actor:
            safe_metadata["initiated_by"] = actor
        return original_create_package(
            document_id=document_id,
            tenant_id=tenant_id or _tenant_id(),
            audit_chain=audit_chain,
            artifacts=artifacts,
            metadata=safe_metadata,
        )

    api_main.evidence_service.create_package = create_package_with_actor

    original_export_invoice = api_main.datev_service.export_invoice

    def export_invoice_with_actor(
        *,
        document_id: str,
        tenant_id: str | None = None,
        uploaded_by: str | None = None,
        kontierung: dict[str, Any],
        invoice_data: dict[str, Any] | None = None,
    ):
        del uploaded_by  # historic placeholder; tenant comes from TenantContext
        result = original_export_invoice(
            document_id=document_id,
            tenant_id=tenant_id or _tenant_id(),
            kontierung=kontierung,
            invoice_data=invoice_data,
        )
        _annotate_datev_metadata(result.file_path, get_authenticated_actor())
        return result

    api_main.datev_service.export_invoice = export_invoice_with_actor

    original_export_batch = api_main.datev_service.export_batch

    def export_batch_with_actor(
        *,
        invoices: list[dict[str, Any]],
        tenant_id: str | None = None,
        uploaded_by: str | None = None,
    ):
        del uploaded_by
        result = original_export_batch(
            tenant_id=tenant_id or _tenant_id(),
            invoices=invoices,
        )
        _annotate_datev_metadata(result.file_path, get_authenticated_actor())
        return result

    api_main.datev_service.export_batch = export_batch_with_actor

    original_validate_structured = api_main.erechnung_hub.validate_structured_invoice

    def validate_structured_with_tenant(
        *,
        document_id: str,
        xml_content: bytes,
        tenant_id: str | None = None,
        uploaded_by: str | None = None,
    ):
        del uploaded_by
        return original_validate_structured(
            document_id=document_id,
            tenant_id=tenant_id or _tenant_id(),
            xml_content=xml_content,
        )

    api_main.erechnung_hub.validate_structured_invoice = validate_structured_with_tenant

    _install_model_identity_guards()
    _INSTALLED = True
