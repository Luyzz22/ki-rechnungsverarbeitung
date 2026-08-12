"""003 - Align invoice event persistence with tenant-aware runtime.

Revision ID: 003_invoice_event_tenant
Revises: 002_modular_identity
Create Date: 2026-08-12

The modular API already scopes requests by tenant and creates InvoiceEvent rows
from several transition paths.  This migration preserves the required textual
``tenant_id`` isolation boundary and adds the transitional ``uploaded_by`` audit
metadata used by those routes.  It never rewrites tenant identifiers.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_invoice_event_tenant"
down_revision: Union[str, None] = "002_modular_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class InvoiceEventSchemaIncompatible(RuntimeError):
    """Fail-closed signal that contains schema metadata only, never row data."""


def _is_textual(column_type: sa.types.TypeEngine) -> bool:
    return isinstance(column_type, (sa.String, sa.Text))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "invoice_events" not in inspector.get_table_names():
        raise InvoiceEventSchemaIncompatible(
            "INVOICE_EVENT_SCHEMA_INCOMPATIBLE: invoice_events table is missing"
        )

    columns = {column["name"]: column for column in inspector.get_columns("invoice_events")}
    tenant = columns.get("tenant_id")
    if tenant is None or not _is_textual(tenant["type"]):
        raise InvoiceEventSchemaIncompatible(
            "INVOICE_EVENT_SCHEMA_INCOMPATIBLE: invoice_events.tenant_id must be textual"
        )

    # Revision 001 creates tenant_id NOT NULL.  If a separately provisioned
    # schema drifted to nullable, verify that no NULL rows exist before safely
    # restoring the invariant.  No identifiers are ever emitted.
    if tenant.get("nullable", True):
        null_count = bind.execute(
            sa.text("SELECT COUNT(*) FROM invoice_events WHERE tenant_id IS NULL")
        ).scalar_one()
        if int(null_count or 0) > 0:
            raise InvoiceEventSchemaIncompatible(
                "INVOICE_EVENT_SCHEMA_INCOMPATIBLE: NULL tenant references exist"
            )
        op.alter_column(
            "invoice_events",
            "tenant_id",
            existing_type=tenant["type"],
            nullable=False,
        )

    if "uploaded_by" not in columns:
        op.add_column(
            "invoice_events",
            sa.Column("uploaded_by", sa.String(128), nullable=True),
        )


def downgrade() -> None:
    # An existing deployment may already have provided uploaded_by out-of-band.
    # Dropping an adopted audit column automatically could destroy evidence.
    raise RuntimeError(
        "IRREVERSIBLE_MIGRATION: 003_invoice_event_tenant requires an explicit reviewed rollback plan"
    )
