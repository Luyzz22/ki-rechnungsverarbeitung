"""001 - Initial schema: invoices + invoice_events

Revision ID: 001_initial
Revises:
Create Date: 2026-02-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False, server_default="invoice"),
        sa.Column("file_name", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("uploaded_by", sa.String(128), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("source_system", sa.String(128), nullable=False, server_default="sbs-nexus"),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_document_id", "invoices", ["document_id"], unique=True)
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])

    op.create_table(
        "invoice_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("status_from", sa.String(), nullable=True),
        sa.Column("status_to", sa.String(), nullable=True),
        sa.Column("actor", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_events_tenant_id", "invoice_events", ["tenant_id"])
    op.create_index("ix_invoice_events_document_id", "invoice_events", ["document_id"])


def downgrade() -> None:
    op.drop_table("invoice_events")
    op.drop_table("invoices")
