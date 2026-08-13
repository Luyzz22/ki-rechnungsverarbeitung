from __future__ import annotations

from modules.rechnungsverarbeitung.src.api import hardened_app  # noqa: F401
from modules.rechnungsverarbeitung.src.api import main as api_main
from modules.rechnungsverarbeitung.src.auth.jwt_auth import UserAuth
from modules.rechnungsverarbeitung.src.invoices.db_models import InvoiceEvent
from shared.audit_identity import bind_authenticated_actor, reset_authenticated_actor
from shared.tenant.context import TenantContext


def test_authenticated_user_becomes_transition_actor():
    baseline = bind_authenticated_actor("baseline")
    try:
        user = UserAuth(user_id="user-123", tenant_id="tenant-123", role="user")
        assert api_main._resolve_tenant_for_authenticated_request(None, user) == "tenant-123"
        result = api_main.state_machine.transition(
            document_id="doc-1",
            current_status="suggested",
            target_status="approved",
            actor="request-value",
        )
        assert result.actor == "user-123"
    finally:
        reset_authenticated_actor(baseline)


def test_invoice_event_human_identity_is_bound_to_request_actor():
    token = bind_authenticated_actor("user-456")
    TenantContext.set_current_tenant("tenant-456")
    try:
        event = InvoiceEvent(
            document_id="doc-2",
            event_type="invoice_approved",
            status_from="suggested",
            status_to="approved",
            actor="request-value",
            uploaded_by="request-value",
        )
        assert event.actor == "user-456"
        assert event.uploaded_by == "user-456"
    finally:
        reset_authenticated_actor(token)


def test_technical_ai_actor_remains_explicit():
    token = bind_authenticated_actor("user-789")
    TenantContext.set_current_tenant("tenant-789")
    try:
        result = api_main.state_machine.transition(
            document_id="doc-3",
            current_status="classified",
            target_status="suggested",
            actor="ai:model-test",
        )
        assert result.actor == "ai:model-test"
    finally:
        reset_authenticated_actor(token)
