from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text


_DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
pytestmark = pytest.mark.skipif(
    not _DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")),
    reason="PostgreSQL DATABASE_URL required",
)


def _engine():
    url = _DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return create_engine(url, future=True)


def test_route_style_invoice_event_binds_to_active_tenant_context():
    """Persist the same constructor shape used by transition/kontierung routes."""
    from modules.rechnungsverarbeitung.src.invoices.db_models import InvoiceEvent
    from shared.db.session import get_session
    from shared.tenant.context import TenantContext

    tenant_id = f"tenant-event-{uuid.uuid4().hex[:12]}"
    document_id = uuid.uuid4().hex
    TenantContext.set_current_tenant(tenant_id)

    try:
        with get_session() as session:
            event = InvoiceEvent(
                uploaded_by="batch-upload",
                document_id=document_id,
                event_type="transition_completed",
                status_from="suggested",
                status_to="approved",
                actor="schema-contract-test",
                created_at=datetime.now(timezone.utc),
                details={"contract": "ok"},
            )
            session.add(event)

        with _engine().connect() as connection:
            row = connection.execute(
                text(
                    "SELECT tenant_id, uploaded_by FROM invoice_events "
                    "WHERE document_id = :document_id AND event_type = :event_type"
                ),
                {"document_id": document_id, "event_type": "transition_completed"},
            ).fetchone()
        assert row is not None
        assert row[0] == tenant_id
        assert row[1] == "batch-upload"
    finally:
        with _engine().begin() as connection:
            connection.execute(
                text("DELETE FROM invoice_events WHERE document_id = :document_id"),
                {"document_id": document_id},
            )


def test_invoice_event_tenant_column_is_not_nullable_after_alembic_head():
    from sqlalchemy import inspect

    columns = {
        column["name"]: column
        for column in inspect(_engine()).get_columns("invoice_events")
    }
    assert columns["tenant_id"]["nullable"] is False
    assert "uploaded_by" in columns
