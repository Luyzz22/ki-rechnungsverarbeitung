from __future__ import annotations

import importlib

import pytest
import sqlalchemy as sa

from modules.rechnungsverarbeitung.src.invoices.db_models import (
    Invoice,
    InvoiceEvent,
    MODULAR_INVOICE_EVENT_TABLE,
    MODULAR_INVOICE_TABLE,
)

migration = importlib.import_module(
    "alembic.versions.002_namespace_modular_invoice_tables"
)


def _engine_with(sql: str):
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
    return engine


def test_modular_models_do_not_claim_legacy_runtime_tables():
    assert Invoice.__tablename__ == MODULAR_INVOICE_TABLE == "processing_invoices"
    assert InvoiceEvent.__tablename__ == MODULAR_INVOICE_EVENT_TABLE == "processing_invoice_events"
    assert Invoice.__tablename__ != "invoices"
    assert InvoiceEvent.__tablename__ != "invoice_events"


def test_modular_invoice_fingerprint_is_accepted():
    engine = _engine_with(
        """
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY,
            document_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            source_system TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    migration._assert_modular_invoice_shape(engine, "invoices")


def test_legacy_invoice_shape_is_blocked_fail_closed():
    engine = _engine_with(
        """
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY,
            job_id TEXT,
            rechnungsnummer TEXT,
            rechnungsaussteller TEXT,
            betrag_brutto REAL,
            tenant_id INTEGER
        )
        """
    )
    with pytest.raises(RuntimeError, match="POSTGRES_SCHEMA_LIFECYCLE_BLOCKED"):
        migration._assert_modular_invoice_shape(engine, "invoices")


def test_mixed_invoice_shape_is_blocked_fail_closed():
    engine = _engine_with(
        """
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY,
            document_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            source_system TEXT NOT NULL,
            status TEXT NOT NULL,
            job_id TEXT
        )
        """
    )
    with pytest.raises(RuntimeError, match="refusing automatic rename"):
        migration._assert_modular_invoice_shape(engine, "invoices")


def test_modular_event_fingerprint_is_accepted():
    engine = _engine_with(
        """
        CREATE TABLE invoice_events (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    migration._assert_modular_event_shape(engine, "invoice_events")


def test_incomplete_event_shape_is_blocked_fail_closed():
    engine = _engine_with(
        """
        CREATE TABLE invoice_events (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL
        )
        """
    )
    with pytest.raises(RuntimeError, match="POSTGRES_SCHEMA_LIFECYCLE_BLOCKED"):
        migration._assert_modular_event_shape(engine, "invoice_events")
