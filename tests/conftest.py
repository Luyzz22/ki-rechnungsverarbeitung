"""
Test-Fixtures für SBS Invoice App
"""

import pytest
import sqlite3
import sys
import os

# Parent directory für imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Erstellt eine temporäre Test-Datenbank"""
    db_path = tmp_path / "test.db"
    
    # database.py auf Test-DB umleiten
    def mock_get_connection():
        return sqlite3.connect(str(db_path))
    
    monkeypatch.setattr(database, "get_connection", mock_get_connection)
    
    # Tabellen erstellen
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            user_id INTEGER,
            status TEXT DEFAULT 'pending',
            total_files INTEGER DEFAULT 0,
            processed_files INTEGER DEFAULT 0,
            successful_files INTEGER DEFAULT 0,
            failed_files INTEGER DEFAULT 0,
            total_net REAL DEFAULT 0,
            total_vat REAL DEFAULT 0,
            total_gross REAL DEFAULT 0,
            created_at TEXT,
            completed_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            filename TEXT,
            invoice_number TEXT,
            invoice_date TEXT,
            supplier_name TEXT,
            net_amount REAL DEFAULT 0,
            vat_amount REAL DEFAULT 0,
            gross_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'ok',
            is_duplicate INTEGER DEFAULT 0,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    return db_path


@pytest.fixture
def sample_jobs(test_db):
    """Fügt Test-Jobs ein"""
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    
    jobs = [
        ("job-001", 1, "completed", 5, 5, 5, 0, "2025-01-15T10:00:00"),
        ("job-002", 1, "completed", 3, 3, 2, 1, "2025-01-16T11:00:00"),
        ("job-003", 1, "processing", 10, 5, 5, 0, "2025-01-17T12:00:00"),
        ("job-004", 2, "completed", 2, 2, 2, 0, "2025-01-18T13:00:00"),
    ]
    
    for job in jobs:
        cursor.execute("""
            INSERT INTO jobs (job_id, user_id, status, total_files, processed_files, 
                            successful_files, failed_files, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, job)
    
    conn.commit()
    conn.close()
    
    return jobs


@pytest.fixture
def sample_invoices(test_db, sample_jobs):
    """Fügt Test-Rechnungen ein"""
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    
    invoices = [
        ("job-001", "invoice1.pdf", "INV-001", "2025-01-10", "Lieferant A", 100.0, 19.0, 119.0),
        ("job-001", "invoice2.pdf", "INV-002", "2025-01-11", "Lieferant A", 200.0, 38.0, 238.0),
        ("job-001", "invoice3.pdf", "INV-003", "2025-01-12", "Lieferant B", 150.0, 28.5, 178.5),
        ("job-002", "invoice4.pdf", "INV-004", "2025-02-01", "Lieferant C", 500.0, 95.0, 595.0),
        ("job-002", "invoice5.pdf", "INV-001", "2025-02-02", "Lieferant A", 100.0, 19.0, 119.0),  # Duplikat
        ("job-004", "invoice6.pdf", "INV-006", "2025-02-15", "Lieferant B", 300.0, 57.0, 357.0),
    ]
    
    for inv in invoices:
        cursor.execute("""
            INSERT INTO invoices (job_id, filename, invoice_number, invoice_date,
                                supplier_name, net_amount, vat_amount, gross_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, inv)
    
    conn.commit()
    conn.close()
    
    return invoices
