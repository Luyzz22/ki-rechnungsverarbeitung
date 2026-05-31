"""Pytest-Fixtures für die Enterprise-Features (Phase 4 + 5)."""

import os
import sqlite3
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402
import enterprise_db  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Temporäre SQLite-DB mit Basis- und Enterprise-Schema.

    Liefert die Tenant-ID des angelegten Test-Users zurück.
    """
    db_path = tmp_path / "test_enterprise.db"

    # Alle Module nutzen `from database import get_connection`; get_connection
    # ermittelt den Pfad zur Laufzeit über database._ensure_db_path. Patchen wir
    # diese Funktion, greifen ALLE Module auf die Test-DB zu.
    monkeypatch.setattr(database, "_ensure_db_path", lambda: db_path)

    def _conn():
        return database.get_connection()

    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            rechnungsnummer TEXT,
            datum TEXT,
            rechnungsaussteller TEXT,
            betrag_brutto REAL,
            betrag_netto REAL,
            status TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            name TEXT,
            company TEXT,
            password_hash TEXT,
            is_active INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()

    enterprise_db.init_enterprise_schema()

    # Test-User (= Tenant 1) + ein zweiter Tenant zur Isolationsprüfung
    conn = _conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (id, email, name) VALUES (1, 'test@sbs.de', 'Test User')")
    cur.execute("INSERT INTO users (id, email, name) VALUES (2, 'other@sbs.de', 'Other Tenant')")
    conn.commit()
    conn.close()
    return 1


def _add_invoice(supplier, amount, days_ago=0, tenant=1, manual=0, invoice_no=None):
    """Hilfsfunktion: legt Job + Rechnung für einen Tenant an."""
    created = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
    conn = database.get_connection()
    cur = conn.cursor()
    job_id = f"job-{tenant}-{supplier}-{amount}-{days_ago}-{invoice_no or ''}"
    cur.execute(
        "INSERT OR IGNORE INTO jobs (job_id, user_id, created_at) VALUES (?, ?, ?)",
        (job_id, tenant, created),
    )
    cur.execute(
        """
        INSERT INTO invoices
            (job_id, rechnungsnummer, datum, rechnungsaussteller, betrag_brutto, created_at, manual_correction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (job_id, invoice_no or "R-1", created[:10], supplier, amount, created, manual),
    )
    invoice_id = cur.lastrowid
    conn.commit()
    conn.close()
    return invoice_id


@pytest.fixture
def add_invoice():
    return _add_invoice
