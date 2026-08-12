from __future__ import annotations

import os
import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect, text


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


def _is_textual(column_type) -> bool:
    name = type(column_type).__name__.lower()
    rendered = str(column_type).lower()
    return any(token in name or token in rendered for token in ("char", "string", "text", "varchar"))


def test_alembic_head_owns_modular_identity_and_invoice_contract():
    engine = _engine()
    inspector = inspect(engine)

    assert {"users", "invoices", "invoice_events"}.issubset(set(inspector.get_table_names()))

    users = {column["name"]: column for column in inspector.get_columns("users")}
    required_users = {
        "id",
        "email",
        "password_hash",
        "name",
        "company",
        "tenant_id",
        "role",
        "created_at",
        "updated_at",
    }
    assert required_users.issubset(users)
    for name in ("id", "email", "password_hash", "tenant_id", "role"):
        assert _is_textual(users[name]["type"]), f"users.{name} must be textual"

    pk = inspector.get_pk_constraint("users")
    assert list(pk.get("constrained_columns") or []) == ["id"]
    unique_email = any(
        list(item.get("column_names") or []) == ["email"]
        for item in inspector.get_unique_constraints("users")
    ) or any(
        item.get("unique") and list(item.get("column_names") or []) == ["email"]
        for item in inspector.get_indexes("users")
    )
    assert unique_email, "users.email must be database-unique"

    invoices = {column["name"]: column for column in inspector.get_columns("invoices")}
    required_invoice_columns = {
        "document_id",
        "tenant_id",
        "supplier",
        "total_amount",
        "currency",
        "tax_amount",
        "invoice_number",
        "invoice_date",
        "due_date",
        "extracted_data",
        "status",
    }
    assert required_invoice_columns.issubset(invoices)
    assert _is_textual(invoices["tenant_id"]["type"])


def test_user_service_can_persist_uuid_identity_on_alembic_head():
    from modules.rechnungsverarbeitung.src.invoices.services.user_service import UserService

    service = UserService()
    marker = uuid.uuid4().hex
    email = f"schema-contract-{marker}@example.invalid"
    password = f"FlowCheck-{marker}-A9!"
    created_user_id: str | None = None

    try:
        result = service.register(
            email=email,
            password=password,
            name="Schema Contract",
            company="FlowCheck Test",
        )
        created_user_id = result["user_id"]
        assert isinstance(created_user_id, str)
        uuid.UUID(created_user_id)
        assert result["tenant_id"].startswith("tenant-")

        loaded = service.get_user(created_user_id)
        assert loaded is not None
        assert loaded["id"] == created_user_id
        assert loaded["tenant_id"] == result["tenant_id"]
    finally:
        if created_user_id:
            with _engine().begin() as connection:
                connection.execute(
                    text("DELETE FROM users WHERE id = :id"),
                    {"id": created_user_id},
                )


def test_invoice_orm_can_persist_completed_extraction_contract():
    from modules.rechnungsverarbeitung.src.invoices.db_models import Invoice
    from shared.db.session import get_session

    document_id = uuid.uuid4().hex
    tenant_id = f"tenant-schema-{uuid.uuid4().hex[:8]}"

    try:
        with get_session() as session:
            session.add(
                Invoice(
                    document_id=document_id,
                    tenant_id=tenant_id,
                    document_type="pdf",
                    file_name="schema-test.pdf",
                    mime_type="application/pdf",
                    uploaded_by="schema-contract-test",
                    uploaded_at=datetime.utcnow(),
                    source_system="schema-contract-test",
                    supplier="Test Supplier",
                    total_amount=119.0,
                    currency="EUR",
                    tax_amount=19.0,
                    invoice_number="TEST-1",
                    invoice_date="2026-08-12",
                    due_date="2026-09-11",
                    extracted_data='{"contract":"ok"}',
                    status="suggested",
                )
            )
    finally:
        with _engine().begin() as connection:
            connection.execute(
                text("DELETE FROM invoices WHERE document_id = :document_id"),
                {"document_id": document_id},
            )
