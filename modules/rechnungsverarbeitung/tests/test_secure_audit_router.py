from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from fastapi.routing import iter_route_contexts

from modules.rechnungsverarbeitung.src.api import hardened_app
from modules.rechnungsverarbeitung.src.api import secure_audit_router as secure
from modules.rechnungsverarbeitung.src.auth.jwt_auth import UserAuth


_SECURE_AUDIT_MODULE = "modules.rechnungsverarbeitung.src.api.secure_audit_router"
_SECURE_PATHS = {
    "/api/v1/invoices/upload",
    "/api/v1/invoices/upload-batch",
    "/api/v1/invoices/{document_id}/transition",
}


def _post_routes(path: str) -> list[object]:
    return [
        route
        for route in iter_route_contexts(hardened_app.app.router.routes)
        if getattr(route, "path", None) == path
        and "POST" in (getattr(route, "methods", set()) or set())
    ]


def test_spoofable_audit_paths_have_exactly_one_secure_handler():
    for path in _SECURE_PATHS:
        routes = _post_routes(path)
        assert len(routes) == 1, path
        assert routes[0].endpoint.__module__ == _SECURE_AUDIT_MODULE


def test_audit_cutover_is_idempotent():
    hardened_app._cut_over_secure_audit_routes()

    for path in _SECURE_PATHS:
        routes = _post_routes(path)
        assert len(routes) == 1, path
        assert routes[0].endpoint.__module__ == _SECURE_AUDIT_MODULE


@pytest.mark.asyncio
async def test_single_upload_ignores_client_attribution_and_uses_authenticated_user(monkeypatch):
    captured: dict[str, object] = {}
    user = UserAuth(user_id="user-123", tenant_id="tenant-123", role="user")

    monkeypatch.setattr(
        secure.legacy,
        "_resolve_tenant_for_authenticated_request",
        lambda _header, _user: "tenant-123",
    )
    monkeypatch.setattr(
        secure.legacy,
        "_trusted_context_from_user",
        lambda _user: SimpleNamespace(user_id="user-123"),
    )

    def fake_process_invoice_upload(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            id="doc-1",
            tenant_id="tenant-123",
            status="classified",
            file_name="invoice.pdf",
            document_type="pdf",
        )

    monkeypatch.setattr(secure.legacy, "process_invoice_upload", fake_process_invoice_upload)
    file = SimpleNamespace(
        file=io.BytesIO(b"test"),
        filename="invoice.pdf",
        content_type="application/pdf",
    )

    response = await secure.upload_invoice(user=user, x_tenant_id=None, file=file)

    assert response["document_id"] == "doc-1"
    assert captured["uploaded_by"] == "user-123"


class _FakeSession:
    def __init__(self, invoice):
        self.invoice = invoice
        self.added: list[object] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add(self, value):
        self.added.append(value)


@pytest.mark.asyncio
async def test_transition_replaces_even_ai_prefixed_client_actor(monkeypatch):
    user = UserAuth(user_id="reviewer-7", tenant_id="tenant-7", role="user")
    invoice = SimpleNamespace(status="suggested", processed_at=None, file_name="invoice.pdf")
    session = _FakeSession(invoice)

    monkeypatch.setattr(
        secure.legacy,
        "_resolve_tenant_for_authenticated_request",
        lambda _header, _user: "tenant-7",
    )
    monkeypatch.setattr(secure.legacy, "get_session", lambda: session)
    monkeypatch.setattr(
        secure.legacy,
        "_get_invoice_or_404",
        lambda _session, _document_id, _tenant_id: invoice,
    )
    monkeypatch.setattr(
        secure.legacy.notification_service,
        "notify_transition",
        lambda **_kwargs: True,
    )

    body = secure.legacy.TransitionRequest(
        target_status="approved",
        actor="ai:spoofed-client-actor",
        details={"source": "test"},
    )
    response = await secure.transition_invoice(
        document_id="doc-7",
        body=body,
        user=user,
        x_tenant_id=None,
    )

    assert response.actor == "reviewer-7"
    assert invoice.status == "approved"
    assert len(session.added) == 1
    event = session.added[0]
    assert event.actor == "reviewer-7"
    assert event.uploaded_by == "reviewer-7"
    assert event.tenant_id == "tenant-7"
