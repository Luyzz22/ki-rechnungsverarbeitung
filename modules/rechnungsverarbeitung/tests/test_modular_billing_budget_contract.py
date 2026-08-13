from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


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


def test_alembic_head_owns_modular_billing_and_budget_tables():
    inspector = inspect(_engine())
    tables = set(inspector.get_table_names())
    assert {"subscriptions", "budget_kategorien", "monats_budgets"} <= tables

    subscription_columns = {
        column["name"]: column for column in inspector.get_columns("subscriptions")
    }
    assert subscription_columns["tenant_id"]["nullable"] is False
    assert subscription_columns["invoices_used"]["nullable"] is False

    category_columns = {
        column["name"]: column for column in inspector.get_columns("budget_kategorien")
    }
    monthly_columns = {
        column["name"]: column for column in inspector.get_columns("monats_budgets")
    }
    assert category_columns["tenant_id"]["nullable"] is False
    assert monthly_columns["tenant_id"]["nullable"] is False
    assert monthly_columns["betrag"]["nullable"] is False


def test_subscription_runtime_roundtrip_uses_string_tenant_and_plan_limit():
    from modules.rechnungsverarbeitung.src.invoices.services.subscription_service import (
        SubscriptionService,
    )

    tenant_id = f"tenant-billing-{uuid.uuid4().hex[:12]}"
    service = SubscriptionService()
    service._handle_checkout_completed(
        {
            "metadata": {"tenant_id": tenant_id, "plan_id": "professional"},
            "customer": "cus_schema_contract",
            "subscription": "sub_schema_contract",
        }
    )

    subscription = service.get_tenant_subscription(tenant_id)
    assert subscription["plan"] == "professional"
    assert subscription["status"] == "active"
    assert subscription["invoices_limit"] == 500
    assert subscription["invoices_used"] == 0

    service.increment_usage(tenant_id)
    usage = service.get_usage(tenant_id)
    assert usage == {
        "plan": "professional",
        "status": "active",
        "used": 1,
        "limit": 500,
    }

    with _engine().connect() as connection:
        row = connection.execute(
            text(
                "SELECT id, tenant_id, invoices_limit, invoices_used "
                "FROM subscriptions WHERE tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        ).one()
    assert isinstance(row[0], str)
    assert row[1] == tenant_id
    assert row[2] == 500
    assert row[3] == 1


def test_subscription_tenant_is_unique():
    tenant_id = f"tenant-billing-unique-{uuid.uuid4().hex[:12]}"
    with _engine().begin() as connection:
        connection.execute(
            text(
                "INSERT INTO subscriptions "
                "(id, tenant_id, plan, status, invoices_limit, invoices_used) "
                "VALUES (:id, :tenant_id, 'starter', 'active', 50, 0)"
            ),
            {"id": str(uuid.uuid4()), "tenant_id": tenant_id},
        )

    with pytest.raises(IntegrityError):
        with _engine().begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO subscriptions "
                    "(id, tenant_id, plan, status, invoices_limit, invoices_used) "
                    "VALUES (:id, :tenant_id, 'starter', 'active', 50, 0)"
                ),
                {"id": str(uuid.uuid4()), "tenant_id": tenant_id},
            )


def test_budget_upsert_is_tenant_scoped_and_cross_tenant_fk_fails_closed():
    tenant_a = f"tenant-budget-a-{uuid.uuid4().hex[:10]}"
    tenant_b = f"tenant-budget-b-{uuid.uuid4().hex[:10]}"
    category_name = f"IT-{uuid.uuid4().hex[:8]}"

    with _engine().begin() as connection:
        category_a = connection.execute(
            text(
                "INSERT INTO budget_kategorien "
                "(tenant_id, name, beschreibung, konten_mapping, aktiv) "
                "VALUES (:tenant_id, :name, '', '[]', TRUE) RETURNING id"
            ),
            {"tenant_id": tenant_a, "name": category_name},
        ).scalar_one()
        category_b = connection.execute(
            text(
                "INSERT INTO budget_kategorien "
                "(tenant_id, name, beschreibung, konten_mapping, aktiv) "
                "VALUES (:tenant_id, :name, '', '[]', TRUE) RETURNING id"
            ),
            {"tenant_id": tenant_b, "name": category_name},
        ).scalar_one()

        assert category_a != category_b

        endpoint_upsert = text("""
            INSERT INTO monats_budgets
                (tenant_id, kategorie_id, jahr, monat, betrag, notiz)
            VALUES (:t, :k, :j, :m, :b, :n)
            ON CONFLICT (tenant_id, kategorie_id, jahr, monat)
            DO UPDATE SET betrag = :b, notiz = :n
        """)
        connection.execute(
            endpoint_upsert,
            {"t": tenant_a, "k": category_a, "j": 2026, "m": 8, "b": 1000, "n": "initial"},
        )
        connection.execute(
            endpoint_upsert,
            {"t": tenant_a, "k": category_a, "j": 2026, "m": 8, "b": 1250, "n": "updated"},
        )

    with _engine().connect() as connection:
        row = connection.execute(
            text(
                "SELECT betrag, notiz FROM monats_budgets "
                "WHERE tenant_id = :t AND kategorie_id = :k AND jahr = 2026 AND monat = 8"
            ),
            {"t": tenant_a, "k": category_a},
        ).one()
    assert float(row[0]) == 1250.0
    assert row[1] == "updated"

    with pytest.raises(IntegrityError):
        with _engine().begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO monats_budgets "
                    "(tenant_id, kategorie_id, jahr, monat, betrag) "
                    "VALUES (:tenant_id, :category_id, 2026, 9, 99)"
                ),
                {"tenant_id": tenant_b, "category_id": category_a},
            )
