"""004 - Own modular billing and tenant-safe budget persistence.

Revision ID: 004_billing_budget
Revises: 003_invoice_event_tenant
Create Date: 2026-08-13

The modular API already reads/writes ``subscriptions``, ``budget_kategorien``
and ``monats_budgets``.  This revision makes those runtime contracts explicit
Alembic-owned PostgreSQL schema.  Existing legacy tables are adopted only when
their tenant/identity domains are compatible; ambiguous legacy shapes fail
closed and no tenant or billing identifiers are rewritten.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_billing_budget"
down_revision: Union[str, None] = "003_invoice_event_tenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class ModularBillingBudgetSchemaIncompatible(RuntimeError):
    """Fail-closed schema error that never includes row-level identifiers."""


def _is_textual(column_type: sa.types.TypeEngine) -> bool:
    return isinstance(column_type, (sa.String, sa.Text))


def _is_integer(column_type: sa.types.TypeEngine) -> bool:
    return isinstance(column_type, sa.Integer)


def _is_numeric(column_type: sa.types.TypeEngine) -> bool:
    return isinstance(column_type, (sa.Integer, sa.Numeric, sa.Float))


def _column_map(inspector: sa.Inspector, table: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspector.get_columns(table)}


def _has_single_id_primary_key(inspector: sa.Inspector, table: str) -> bool:
    pk = inspector.get_pk_constraint(table) or {}
    return list(pk.get("constrained_columns") or []) == ["id"]


def _has_unique_columns(inspector: sa.Inspector, table: str, columns: list[str]) -> bool:
    expected = list(columns)
    for constraint in inspector.get_unique_constraints(table):
        if list(constraint.get("column_names") or []) == expected:
            return True
    for index in inspector.get_indexes(table):
        if index.get("unique") and list(index.get("column_names") or []) == expected:
            return True
    return False


def _has_foreign_key(
    inspector: sa.Inspector,
    table: str,
    constrained_columns: list[str],
    referred_table: str,
    referred_columns: list[str],
) -> bool:
    for fk in inspector.get_foreign_keys(table):
        if (
            list(fk.get("constrained_columns") or []) == constrained_columns
            and fk.get("referred_table") == referred_table
            and list(fk.get("referred_columns") or []) == referred_columns
        ):
            return True
    return False


def _count(bind: sa.Connection, statement: str) -> int:
    return int(bind.execute(sa.text(statement)).scalar_one() or 0)


def _ensure_not_nullable(
    bind: sa.Connection,
    table: str,
    column_name: str,
    existing_type: sa.types.TypeEngine,
) -> None:
    null_count = _count(
        bind,
        f'SELECT COUNT(*) FROM "{table}" WHERE "{column_name}" IS NULL',
    )
    if null_count:
        raise ModularBillingBudgetSchemaIncompatible(
            f"MODULAR_SCHEMA_INCOMPATIBLE: NULL values exist in {table}.{column_name}"
        )
    op.alter_column(
        table,
        column_name,
        existing_type=existing_type,
        nullable=False,
    )


def _create_or_adopt_subscriptions(bind: sa.Connection) -> None:
    inspector = sa.inspect(bind)
    if "subscriptions" not in inspector.get_table_names():
        op.create_table(
            "subscriptions",
            sa.Column("id", sa.String(64), nullable=False),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("plan", sa.String(32), nullable=False, server_default="starter"),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("stripe_customer_id", sa.String(255), nullable=True),
            sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
            sa.Column("invoices_limit", sa.Integer(), nullable=True),
            sa.Column("invoices_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
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
            sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
            sa.UniqueConstraint("tenant_id", name="uq_subscriptions_tenant_id"),
        )
        return

    columns = _column_map(inspector, "subscriptions")
    for required in ("id", "tenant_id"):
        if required not in columns:
            raise ModularBillingBudgetSchemaIncompatible(
                f"MODULAR_BILLING_SCHEMA_INCOMPATIBLE: subscriptions.{required} is missing"
            )
    if not _is_textual(columns["id"]["type"]):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BILLING_SCHEMA_INCOMPATIBLE: subscriptions.id must be textual"
        )
    if not _is_textual(columns["tenant_id"]["type"]):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BILLING_SCHEMA_INCOMPATIBLE: subscriptions.tenant_id must be textual"
        )
    if not _has_single_id_primary_key(inspector, "subscriptions"):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BILLING_SCHEMA_INCOMPATIBLE: subscriptions.id must be the single primary key"
        )

    if columns["tenant_id"].get("nullable", True):
        _ensure_not_nullable(bind, "subscriptions", "tenant_id", columns["tenant_id"]["type"])

    inspector = sa.inspect(bind)
    columns = _column_map(inspector, "subscriptions")
    additions = {
        "plan": sa.Column("plan", sa.String(32), nullable=False, server_default="starter"),
        "status": sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        "stripe_customer_id": sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        "stripe_subscription_id": sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        "invoices_limit": sa.Column("invoices_limit", sa.Integer(), nullable=True),
        "invoices_used": sa.Column("invoices_used", sa.Integer(), nullable=False, server_default="0"),
        "current_period_start": sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        "current_period_end": sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        "created_at": sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        "updated_at": sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("subscriptions", column)

    inspector = sa.inspect(bind)
    columns = _column_map(inspector, "subscriptions")
    for textual in ("plan", "status"):
        if not _is_textual(columns[textual]["type"]):
            raise ModularBillingBudgetSchemaIncompatible(
                f"MODULAR_BILLING_SCHEMA_INCOMPATIBLE: subscriptions.{textual} must be textual"
            )
        if columns[textual].get("nullable", True):
            _ensure_not_nullable(bind, "subscriptions", textual, columns[textual]["type"])
    if not _is_integer(columns["invoices_used"]["type"]):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BILLING_SCHEMA_INCOMPATIBLE: subscriptions.invoices_used must be integer"
        )
    if columns["invoices_used"].get("nullable", True):
        _ensure_not_nullable(
            bind,
            "subscriptions",
            "invoices_used",
            columns["invoices_used"]["type"],
        )

    inspector = sa.inspect(bind)
    if not _has_unique_columns(inspector, "subscriptions", ["tenant_id"]):
        duplicate_tenants = _count(
            bind,
            "SELECT COUNT(*) FROM ("
            "SELECT tenant_id FROM subscriptions GROUP BY tenant_id HAVING COUNT(*) > 1"
            ") duplicate_tenants",
        )
        if duplicate_tenants:
            raise ModularBillingBudgetSchemaIncompatible(
                "MODULAR_BILLING_SCHEMA_INCOMPATIBLE: duplicate subscription tenant groups exist"
            )
        op.create_unique_constraint(
            "uq_subscriptions_tenant_id",
            "subscriptions",
            ["tenant_id"],
        )


def _create_or_adopt_budget_categories(bind: sa.Connection) -> None:
    inspector = sa.inspect(bind)
    if "budget_kategorien" not in inspector.get_table_names():
        op.create_table(
            "budget_kategorien",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("beschreibung", sa.Text(), nullable=True),
            sa.Column("konten_mapping", sa.Text(), nullable=True),
            sa.Column("aktiv", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "erstellt_am",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id", name="pk_budget_kategorien"),
            sa.UniqueConstraint(
                "tenant_id",
                "name",
                name="uq_budget_kategorien_tenant_name",
            ),
            sa.UniqueConstraint(
                "tenant_id",
                "id",
                name="uq_budget_kategorien_tenant_id_id",
            ),
        )
        op.create_index(
            "ix_budget_kategorien_tenant_id",
            "budget_kategorien",
            ["tenant_id"],
            unique=False,
        )
        return

    columns = _column_map(inspector, "budget_kategorien")
    required = {"id", "tenant_id", "name"}
    missing = sorted(required - set(columns))
    if missing:
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: budget_kategorien missing tenant-safe columns: "
            + ",".join(missing)
        )
    if not _is_integer(columns["id"]["type"]):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: budget_kategorien.id must be integer"
        )
    if not _is_textual(columns["tenant_id"]["type"]):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: budget_kategorien.tenant_id must be textual"
        )
    if not _is_textual(columns["name"]["type"]):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: budget_kategorien.name must be textual"
        )
    if not _has_single_id_primary_key(inspector, "budget_kategorien"):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: budget_kategorien.id must be the single primary key"
        )

    for name in ("tenant_id", "name"):
        if columns[name].get("nullable", True):
            _ensure_not_nullable(bind, "budget_kategorien", name, columns[name]["type"])

    inspector = sa.inspect(bind)
    columns = _column_map(inspector, "budget_kategorien")
    additions = {
        "beschreibung": sa.Column("beschreibung", sa.Text(), nullable=True),
        "konten_mapping": sa.Column("konten_mapping", sa.Text(), nullable=True),
        "aktiv": sa.Column("aktiv", sa.Boolean(), nullable=False, server_default=sa.true()),
        "erstellt_am": sa.Column(
            "erstellt_am",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("budget_kategorien", column)

    inspector = sa.inspect(bind)
    columns = _column_map(inspector, "budget_kategorien")
    if not isinstance(columns["aktiv"]["type"], sa.Boolean):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: budget_kategorien.aktiv must be boolean"
        )
    if columns["aktiv"].get("nullable", True):
        _ensure_not_nullable(bind, "budget_kategorien", "aktiv", columns["aktiv"]["type"])

    inspector = sa.inspect(bind)
    if not _has_unique_columns(inspector, "budget_kategorien", ["tenant_id", "name"]):
        duplicate_names = _count(
            bind,
            "SELECT COUNT(*) FROM ("
            "SELECT tenant_id, name FROM budget_kategorien "
            "GROUP BY tenant_id, name HAVING COUNT(*) > 1"
            ") duplicate_budget_names",
        )
        if duplicate_names:
            raise ModularBillingBudgetSchemaIncompatible(
                "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: duplicate tenant/category groups exist"
            )
        op.create_unique_constraint(
            "uq_budget_kategorien_tenant_name",
            "budget_kategorien",
            ["tenant_id", "name"],
        )

    inspector = sa.inspect(bind)
    if not _has_unique_columns(inspector, "budget_kategorien", ["tenant_id", "id"]):
        op.create_unique_constraint(
            "uq_budget_kategorien_tenant_id_id",
            "budget_kategorien",
            ["tenant_id", "id"],
        )


def _create_or_adopt_monthly_budgets(bind: sa.Connection) -> None:
    inspector = sa.inspect(bind)
    if "monats_budgets" not in inspector.get_table_names():
        op.create_table(
            "monats_budgets",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("kategorie_id", sa.Integer(), nullable=False),
            sa.Column("jahr", sa.Integer(), nullable=False),
            sa.Column("monat", sa.Integer(), nullable=False),
            sa.Column("betrag", sa.Numeric(18, 2), nullable=False),
            sa.Column("notiz", sa.Text(), nullable=True),
            sa.Column(
                "erstellt_am",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "aktualisiert_am",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id", name="pk_monats_budgets"),
            sa.UniqueConstraint(
                "tenant_id",
                "kategorie_id",
                "jahr",
                "monat",
                name="uq_monats_budgets_tenant_category_period",
            ),
            sa.ForeignKeyConstraint(
                ["tenant_id", "kategorie_id"],
                ["budget_kategorien.tenant_id", "budget_kategorien.id"],
                name="fk_monats_budgets_tenant_category",
                ondelete="CASCADE",
            ),
            sa.CheckConstraint("monat BETWEEN 1 AND 12", name="ck_monats_budgets_monat"),
        )
        op.create_index(
            "ix_monats_budgets_tenant_period",
            "monats_budgets",
            ["tenant_id", "jahr", "monat"],
            unique=False,
        )
        return

    columns = _column_map(inspector, "monats_budgets")
    required = {"id", "tenant_id", "kategorie_id", "jahr", "monat", "betrag"}
    missing = sorted(required - set(columns))
    if missing:
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: monats_budgets missing canonical columns: "
            + ",".join(missing)
        )
    if not _has_single_id_primary_key(inspector, "monats_budgets"):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: monats_budgets.id must be the single primary key"
        )
    if not _is_textual(columns["tenant_id"]["type"]):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: monats_budgets.tenant_id must be textual"
        )
    for name in ("id", "kategorie_id", "jahr", "monat"):
        if not _is_integer(columns[name]["type"]):
            raise ModularBillingBudgetSchemaIncompatible(
                f"MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: monats_budgets.{name} must be integer"
            )
    if not _is_numeric(columns["betrag"]["type"]):
        raise ModularBillingBudgetSchemaIncompatible(
            "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: monats_budgets.betrag must be numeric"
        )

    for name in ("tenant_id", "kategorie_id", "jahr", "monat", "betrag"):
        if columns[name].get("nullable", True):
            _ensure_not_nullable(bind, "monats_budgets", name, columns[name]["type"])

    inspector = sa.inspect(bind)
    columns = _column_map(inspector, "monats_budgets")
    additions = {
        "notiz": sa.Column("notiz", sa.Text(), nullable=True),
        "erstellt_am": sa.Column(
            "erstellt_am",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        "aktualisiert_am": sa.Column(
            "aktualisiert_am",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("monats_budgets", column)

    inspector = sa.inspect(bind)
    if not _has_unique_columns(
        inspector,
        "monats_budgets",
        ["tenant_id", "kategorie_id", "jahr", "monat"],
    ):
        duplicate_periods = _count(
            bind,
            "SELECT COUNT(*) FROM ("
            "SELECT tenant_id, kategorie_id, jahr, monat FROM monats_budgets "
            "GROUP BY tenant_id, kategorie_id, jahr, monat HAVING COUNT(*) > 1"
            ") duplicate_budget_periods",
        )
        if duplicate_periods:
            raise ModularBillingBudgetSchemaIncompatible(
                "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: duplicate tenant/category/period groups exist"
            )
        op.create_unique_constraint(
            "uq_monats_budgets_tenant_category_period",
            "monats_budgets",
            ["tenant_id", "kategorie_id", "jahr", "monat"],
        )

    inspector = sa.inspect(bind)
    if not _has_foreign_key(
        inspector,
        "monats_budgets",
        ["tenant_id", "kategorie_id"],
        "budget_kategorien",
        ["tenant_id", "id"],
    ):
        mismatches = _count(
            bind,
            "SELECT COUNT(*) FROM monats_budgets mb "
            "LEFT JOIN budget_kategorien bk "
            "ON bk.tenant_id = mb.tenant_id AND bk.id = mb.kategorie_id "
            "WHERE bk.id IS NULL",
        )
        if mismatches:
            raise ModularBillingBudgetSchemaIncompatible(
                "MODULAR_BUDGET_SCHEMA_INCOMPATIBLE: cross-tenant or orphan monthly budget references exist"
            )
        op.create_foreign_key(
            "fk_monats_budgets_tenant_category",
            "monats_budgets",
            "budget_kategorien",
            ["tenant_id", "kategorie_id"],
            ["tenant_id", "id"],
            ondelete="CASCADE",
        )


def upgrade() -> None:
    bind = op.get_bind()
    _create_or_adopt_subscriptions(bind)
    _create_or_adopt_budget_categories(bind)
    _create_or_adopt_monthly_budgets(bind)


def downgrade() -> None:
    # Revision 004 may adopt pre-existing billing/budget tables containing
    # production records. Automatic destructive rollback would risk deleting
    # tenant and billing evidence, so rollback requires an explicit reviewed plan.
    raise RuntimeError(
        "IRREVERSIBLE_MIGRATION: 004_billing_budget requires an explicit reviewed rollback plan"
    )
