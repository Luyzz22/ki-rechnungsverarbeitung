"""002 - Adopt modular identity and complete invoice runtime contract.

Revision ID: 002_modular_identity
Revises: 001_initial
Create Date: 2026-08-12

This migration is intentionally fail-closed around identity/tenant domains.  It
may adopt an existing text/UUID ``users`` table only when the security-critical
shape matches the modular runtime.  It never casts or renumbers identifiers.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_modular_identity"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CORE_USER_COLUMNS = {
    "id",
    "email",
    "password_hash",
    "tenant_id",
    "role",
}
_TEXT_USER_COLUMNS = _CORE_USER_COLUMNS


class ModularSchemaIncompatible(RuntimeError):
    """Raised without row values when an existing schema cannot be adopted."""


def _is_textual(column_type: sa.types.TypeEngine) -> bool:
    return isinstance(column_type, (sa.String, sa.Text))


def _column_map(inspector: sa.Inspector, table: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspector.get_columns(table)}


def _has_single_id_primary_key(inspector: sa.Inspector, table: str) -> bool:
    pk = inspector.get_pk_constraint(table) or {}
    return list(pk.get("constrained_columns") or []) == ["id"]


def _has_unique_email(inspector: sa.Inspector) -> bool:
    for constraint in inspector.get_unique_constraints("users"):
        if list(constraint.get("column_names") or []) == ["email"]:
            return True
    for index in inspector.get_indexes("users"):
        if index.get("unique") and list(index.get("column_names") or []) == ["email"]:
            return True
    return False


def _assert_existing_users_compatible(bind: sa.Connection, inspector: sa.Inspector) -> None:
    columns = _column_map(inspector, "users")
    missing = sorted(_CORE_USER_COLUMNS - set(columns))
    if missing:
        raise ModularSchemaIncompatible(
            "MODULAR_IDENTITY_SCHEMA_INCOMPATIBLE: missing core users columns: "
            + ",".join(missing)
        )

    wrong_types = sorted(
        name
        for name in _TEXT_USER_COLUMNS
        if not _is_textual(columns[name]["type"])
    )
    if wrong_types:
        raise ModularSchemaIncompatible(
            "MODULAR_IDENTITY_SCHEMA_INCOMPATIBLE: non-text identity columns: "
            + ",".join(wrong_types)
        )

    if not _has_single_id_primary_key(inspector, "users"):
        raise ModularSchemaIncompatible(
            "MODULAR_IDENTITY_SCHEMA_INCOMPATIBLE: users.id must be the single primary key"
        )

    if not _has_unique_email(inspector):
        duplicate_groups = bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM ("
                "SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1"
                ") duplicate_email_groups"
            )
        ).scalar_one()
        if int(duplicate_groups or 0) > 0:
            raise ModularSchemaIncompatible(
                "MODULAR_IDENTITY_SCHEMA_INCOMPATIBLE: duplicate email groups exist"
            )
        op.create_index("uq_users_email", "users", ["email"], unique=True)


def _create_or_adopt_users(bind: sa.Connection) -> None:
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        op.create_table(
            "users",
            sa.Column("id", sa.String(64), nullable=False),
            sa.Column("email", sa.String(320), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("name", sa.String(255), nullable=False, server_default=""),
            sa.Column("company", sa.String(255), nullable=False, server_default=""),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("role", sa.String(32), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id", name="pk_users"),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )
        op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)
        return

    _assert_existing_users_compatible(bind, inspector)

    # Additive fields are safe to adopt without changing identity semantics.
    inspector = sa.inspect(bind)
    columns = _column_map(inspector, "users")
    additive_columns = {
        "name": sa.Column("name", sa.String(255), nullable=True),
        "company": sa.Column("company", sa.String(255), nullable=True),
        "created_at": sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        "updated_at": sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    }
    for name, column in additive_columns.items():
        if name not in columns:
            op.add_column("users", column)

    inspector = sa.inspect(bind)
    tenant_indexed = any(
        "tenant_id" in (index.get("column_names") or [])
        for index in inspector.get_indexes("users")
    )
    if not tenant_indexed:
        op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)


def _complete_invoice_contract(bind: sa.Connection) -> None:
    inspector = sa.inspect(bind)
    if "invoices" not in inspector.get_table_names():
        raise ModularSchemaIncompatible(
            "MODULAR_INVOICE_SCHEMA_INCOMPATIBLE: invoices missing after revision 001"
        )

    columns = _column_map(inspector, "invoices")
    tenant_column = columns.get("tenant_id")
    if tenant_column is None or not _is_textual(tenant_column["type"]):
        raise ModularSchemaIncompatible(
            "MODULAR_INVOICE_SCHEMA_INCOMPATIBLE: invoices.tenant_id must be textual"
        )

    additions = {
        "supplier": sa.Column("supplier", sa.String(256), nullable=True),
        "total_amount": sa.Column("total_amount", sa.Float(), nullable=True),
        "currency": sa.Column("currency", sa.String(8), nullable=True, server_default="EUR"),
        "tax_amount": sa.Column("tax_amount", sa.Float(), nullable=True),
        "invoice_number": sa.Column("invoice_number", sa.String(128), nullable=True),
        "invoice_date": sa.Column("invoice_date", sa.String(32), nullable=True),
        "due_date": sa.Column("due_date", sa.String(32), nullable=True),
        # invoice_processing serializes extraction output to JSON text today.
        "extracted_data": sa.Column("extracted_data", sa.Text(), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("invoices", column)


def upgrade() -> None:
    bind = op.get_bind()
    _create_or_adopt_users(bind)
    _complete_invoice_contract(bind)


def downgrade() -> None:
    # This revision may adopt a pre-existing users table. Automatically dropping
    # it (or columns containing production identity data) would be destructive.
    raise RuntimeError(
        "IRREVERSIBLE_MIGRATION: 002_modular_identity requires an explicit reviewed rollback plan"
    )
