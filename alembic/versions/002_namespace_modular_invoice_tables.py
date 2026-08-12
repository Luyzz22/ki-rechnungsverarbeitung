"""002 - Namespace modular invoice tables away from legacy runtime tables.

Revision ID: 002_namespace_modular_invoice_tables
Revises: 001_initial

The repository has two persistence contracts:
- legacy ``database.py`` owns ``invoices`` and uses integer user/tenant keys;
- the modular SQLAlchemy stack uses string tenant identifiers.

Those contracts must not share one physical PostgreSQL table.  This migration
renames only tables that match the known modular fingerprint.  Ambiguous or
legacy-shaped tables fail closed and require an explicit offline migration.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_namespace_modular_invoice_tables"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_INVOICE_TABLE = "invoices"
MODULAR_INVOICE_TABLE = "processing_invoices"
LEGACY_EVENT_TABLE = "invoice_events"
MODULAR_EVENT_TABLE = "processing_invoice_events"

_MODULAR_INVOICE_REQUIRED = {
    "id",
    "document_id",
    "tenant_id",
    "document_type",
    "uploaded_at",
    "source_system",
    "status",
}
_LEGACY_INVOICE_MARKERS = {
    "job_id",
    "rechnungsnummer",
    "rechnungsaussteller",
    "betrag_brutto",
}
_MODULAR_EVENT_REQUIRED = {
    "id",
    "tenant_id",
    "document_id",
    "event_type",
    "created_at",
}


def _table_names(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _columns(bind, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _assert_modular_invoice_shape(bind, table: str) -> None:
    columns = _columns(bind, table)
    if not _MODULAR_INVOICE_REQUIRED.issubset(columns):
        raise RuntimeError(
            "POSTGRES_SCHEMA_LIFECYCLE_BLOCKED: invoices table does not match "
            "the modular Alembic fingerprint; manual migration required"
        )
    if columns.intersection(_LEGACY_INVOICE_MARKERS):
        raise RuntimeError(
            "POSTGRES_SCHEMA_LIFECYCLE_BLOCKED: invoices table contains legacy "
            "runtime columns; refusing automatic rename"
        )


def _assert_modular_event_shape(bind, table: str) -> None:
    columns = _columns(bind, table)
    if not _MODULAR_EVENT_REQUIRED.issubset(columns):
        raise RuntimeError(
            "POSTGRES_SCHEMA_LIFECYCLE_BLOCKED: invoice_events table does not "
            "match the modular Alembic fingerprint; manual migration required"
        )


def upgrade() -> None:
    bind = op.get_bind()
    tables = _table_names(bind)

    if MODULAR_INVOICE_TABLE in tables and LEGACY_INVOICE_TABLE in tables:
        pass
    elif MODULAR_INVOICE_TABLE in tables:
        pass
    elif LEGACY_INVOICE_TABLE in tables:
        _assert_modular_invoice_shape(bind, LEGACY_INVOICE_TABLE)
        op.rename_table(LEGACY_INVOICE_TABLE, MODULAR_INVOICE_TABLE)
    else:
        raise RuntimeError(
            "POSTGRES_SCHEMA_LIFECYCLE_BLOCKED: expected Alembic invoice table missing"
        )

    tables = _table_names(bind)
    if MODULAR_EVENT_TABLE in tables and LEGACY_EVENT_TABLE in tables:
        pass
    elif MODULAR_EVENT_TABLE in tables:
        pass
    elif LEGACY_EVENT_TABLE in tables:
        _assert_modular_event_shape(bind, LEGACY_EVENT_TABLE)
        op.rename_table(LEGACY_EVENT_TABLE, MODULAR_EVENT_TABLE)
    else:
        raise RuntimeError(
            "POSTGRES_SCHEMA_LIFECYCLE_BLOCKED: expected Alembic invoice_events table missing"
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _table_names(bind)

    if LEGACY_INVOICE_TABLE in tables:
        raise RuntimeError(
            "POSTGRES_SCHEMA_LIFECYCLE_BLOCKED: cannot downgrade because legacy "
            "invoices already exists"
        )
    if MODULAR_INVOICE_TABLE in tables:
        _assert_modular_invoice_shape(bind, MODULAR_INVOICE_TABLE)
        op.rename_table(MODULAR_INVOICE_TABLE, LEGACY_INVOICE_TABLE)

    tables = _table_names(bind)
    if LEGACY_EVENT_TABLE in tables:
        raise RuntimeError(
            "POSTGRES_SCHEMA_LIFECYCLE_BLOCKED: cannot downgrade because "
            "invoice_events already exists"
        )
    if MODULAR_EVENT_TABLE in tables:
        _assert_modular_event_shape(bind, MODULAR_EVENT_TABLE)
        op.rename_table(MODULAR_EVENT_TABLE, LEGACY_EVENT_TABLE)
