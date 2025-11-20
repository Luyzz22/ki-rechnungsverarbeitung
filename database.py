#!/usr/bin/env python3
"""
SQLite Database für Job-Persistenz
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "jobs.db"

def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Jobs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            created_at TEXT,
            completed_at TEXT,
            status TEXT DEFAULT 'uploaded',
            total_files INTEGER DEFAULT 0,
            successful INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            total_amount REAL DEFAULT 0,
            total_netto REAL DEFAULT 0,
            total_mwst REAL DEFAULT 0,
            average_amount REAL DEFAULT 0,
            exported_files TEXT,
            upload_path TEXT,
            failed_list TEXT
        )
    ''')
    
    # Results table (individual invoices)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            rechnungsnummer TEXT,
            datum TEXT,
            faelligkeitsdatum TEXT,
            zahlungsziel_tage INTEGER,
            rechnungsaussteller TEXT,
            rechnungsaussteller_adresse TEXT,
            rechnungsempfaenger TEXT,
            rechnungsempfaenger_adresse TEXT,
            kundennummer TEXT,
            betrag_brutto REAL,
            betrag_netto REAL,
            mwst_betrag REAL,
            mwst_satz REAL,
            waehrung TEXT,
            iban TEXT,
            bic TEXT,
            steuernummer TEXT,
            ust_idnr TEXT,
            zahlungsbedingungen TEXT,
            artikel TEXT,
            verwendungszweck TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def save_job(job_id: str, job_data: Dict):
    """Save or update a job"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Prepare data
    exported_files = json.dumps(job_data.get('exported_files', {}))
    failed_list = json.dumps(job_data.get('failed', []))
    
    cursor.execute('''
        INSERT OR REPLACE INTO jobs (
            job_id, created_at, completed_at, status, total_files,
            successful, failed_count, total_amount, total_netto, total_mwst,
            average_amount, exported_files, upload_path, failed_list
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        job_id,
        job_data.get('created_at', datetime.now().isoformat()),
        job_data.get('completed_at'),
        job_data.get('status', 'uploaded'),
        job_data.get('total', 0),
        job_data.get('successful', 0),
        len(job_data.get('failed', [])),
        job_data.get('total_amount', 0),
        job_data.get('stats', {}).get('total_netto', 0) if job_data.get('stats') else 0,
        job_data.get('stats', {}).get('total_mwst', 0) if job_data.get('stats') else 0,
        job_data.get('stats', {}).get('average_brutto', 0) if job_data.get('stats') else 0,
        exported_files,
        job_data.get('path', ''),
        failed_list
    ))
    
    conn.commit()
    conn.close()

def save_invoices(job_id: str, results: List[Dict]):
    """Save invoice results for a job"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Delete existing invoices for this job (in case of re-processing)
    cursor.execute('DELETE FROM invoices WHERE job_id = ?', (job_id,))
    
    for invoice in results:
        cursor.execute('''
            INSERT INTO invoices (
                job_id, rechnungsnummer, datum, faelligkeitsdatum, zahlungsziel_tage,
                rechnungsaussteller, rechnungsaussteller_adresse, rechnungsempfaenger,
                rechnungsempfaenger_adresse, kundennummer, betrag_brutto, betrag_netto,
                mwst_betrag, mwst_satz, waehrung, iban, bic, steuernummer, ust_idnr,
                zahlungsbedingungen, artikel, verwendungszweck
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_id,
            invoice.get('rechnungsnummer', ''),
            invoice.get('datum', ''),
            invoice.get('faelligkeitsdatum', ''),
            invoice.get('zahlungsziel_tage', 0),
            invoice.get('rechnungsaussteller', ''),
            invoice.get('rechnungsaussteller_adresse', ''),
            invoice.get('rechnungsempfänger', invoice.get('rechnungsempfaenger', '')),
            invoice.get('rechnungsempfänger_adresse', invoice.get('rechnungsempfaenger_adresse', '')),
            invoice.get('kundennummer', ''),
            invoice.get('betrag_brutto', 0),
            invoice.get('betrag_netto', 0),
            invoice.get('mwst_betrag', 0),
            invoice.get('mwst_satz', 0),
            invoice.get('waehrung', 'EUR'),
            invoice.get('iban', ''),
            invoice.get('bic', ''),
            invoice.get('steuernummer', ''),
            invoice.get('ust_idnr', ''),
            invoice.get('zahlungsbedingungen', ''),
            json.dumps(invoice.get('artikel', [])),
            invoice.get('verwendungszweck', '')
        ))
    
    conn.commit()
    conn.close()

def get_job(job_id: str) -> Optional[Dict]:
    """Get a job by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
    
    job = dict(row)
    job['exported_files'] = json.loads(job['exported_files'] or '{}')
    job['failed'] = json.loads(job['failed_list'] or '[]')
    
    # Get invoices
    cursor.execute('SELECT * FROM invoices WHERE job_id = ?', (job_id,))
    invoices = [dict(r) for r in cursor.fetchall()]
    job['results'] = invoices
    
    conn.close()
    return job

def get_all_jobs(limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get all jobs, newest first"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM jobs 
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    jobs = []
    for row in cursor.fetchall():
        job = dict(row)
        job['exported_files'] = json.loads(job['exported_files'] or '{}')
        job['failed'] = json.loads(job['failed_list'] or '[]')
        jobs.append(job)
    
    conn.close()
    return jobs

def get_statistics() -> Dict:
    """Get overall statistics"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total jobs
    cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = "completed"')
    total_jobs = cursor.fetchone()[0]
    
    # Total invoices
    cursor.execute('SELECT COUNT(*) FROM invoices')
    total_invoices = cursor.fetchone()[0]
    
    # Total amount
    cursor.execute('SELECT SUM(total_amount) FROM jobs WHERE status = "completed"')
    total_amount = cursor.fetchone()[0] or 0
    
    # Success rate
    cursor.execute('SELECT SUM(successful), SUM(total_files) FROM jobs WHERE status = "completed"')
    row = cursor.fetchone()
    successful = row[0] or 0
    total_files = row[1] or 0
    success_rate = (successful / total_files * 100) if total_files > 0 else 0
    
    # Average per invoice
    avg_per_invoice = (total_amount / total_invoices) if total_invoices > 0 else 0
    
    # Jobs per day (last 30 days)
    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count, SUM(total_amount) as amount
        FROM jobs 
        WHERE status = "completed" 
        AND created_at >= DATE('now', '-30 days')
        GROUP BY DATE(created_at)
        ORDER BY date
    ''')
    daily_data = [dict(r) for r in cursor.fetchall()]
    
    # Top Rechnungsaussteller
    cursor.execute('''
        SELECT rechnungsaussteller, COUNT(*) as count, SUM(betrag_brutto) as total
        FROM invoices
        WHERE rechnungsaussteller != ''
        GROUP BY rechnungsaussteller
        ORDER BY count DESC
        LIMIT 5
    ''')
    top_aussteller = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        'total_jobs': total_jobs,
        'total_invoices': total_invoices,
        'total_amount': round(total_amount, 2),
        'success_rate': round(success_rate, 1),
        'avg_per_invoice': round(avg_per_invoice, 2),
        'daily_data': daily_data,
        'top_aussteller': top_aussteller
    }

# Initialize on import
init_database()

def get_analytics_data():
    """Get comprehensive analytics data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Basic stats
    cursor.execute('SELECT COUNT(*) FROM invoices')
    total_invoices = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(betrag_brutto), SUM(betrag_netto), SUM(mwst_betrag) FROM invoices')
    row = cursor.fetchone()
    total_brutto = row[0] or 0
    total_netto = row[1] or 0
    total_mwst = row[2] or 0
    
    # Unique suppliers
    cursor.execute('SELECT COUNT(DISTINCT rechnungsaussteller) FROM invoices WHERE rechnungsaussteller != ""')
    unique_suppliers = cursor.fetchone()[0]
    
    # Average per invoice
    avg_per_invoice = (total_brutto / total_invoices) if total_invoices > 0 else 0
    
    # Monthly data
    cursor.execute('''
        SELECT strftime('%Y-%m', datum) as month, SUM(betrag_brutto) as total
        FROM invoices
        WHERE datum != '' AND datum IS NOT NULL
        GROUP BY month
        ORDER BY month
        LIMIT 12
    ''')
    monthly_data = cursor.fetchall()
    monthly_labels = [r[0] for r in monthly_data] if monthly_data else []
    monthly_values = [r[1] or 0 for r in monthly_data] if monthly_data else []
    
    # Top suppliers
    cursor.execute('''
        SELECT rechnungsaussteller as name, COUNT(*) as count, SUM(betrag_brutto) as total
        FROM invoices
        WHERE rechnungsaussteller != '' AND rechnungsaussteller IS NOT NULL
        GROUP BY rechnungsaussteller
        ORDER BY total DESC
        LIMIT 10
    ''')
    top_suppliers = [dict(r) for r in cursor.fetchall()]
    
    # Weekday distribution
    cursor.execute('''
        SELECT strftime('%w', datum) as weekday, COUNT(*) as count
        FROM invoices
        WHERE datum != '' AND datum IS NOT NULL
        GROUP BY weekday
    ''')
    weekday_raw = {int(r[0]): r[1] for r in cursor.fetchall()}
    weekday_data = [weekday_raw.get((i + 1) % 7, 0) for i in range(7)]
    
    conn.close()
    
    return {
        'stats': {
            'total_invoices': total_invoices,
            'total_amount': round(total_brutto, 2),
            'total_netto': round(total_netto, 2),
            'total_mwst': round(total_mwst, 2),
            'avg_per_invoice': round(avg_per_invoice, 2),
            'unique_suppliers': unique_suppliers
        },
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
        'top_suppliers': top_suppliers,
        'weekday_data': weekday_data
    }

def get_analytics_data():
    """Get comprehensive analytics data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Basic stats
    cursor.execute('SELECT COUNT(*) FROM invoices')
    total_invoices = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(betrag_brutto), SUM(betrag_netto), SUM(mwst_betrag) FROM invoices')
    row = cursor.fetchone()
    total_brutto = row[0] or 0
    total_netto = row[1] or 0
    total_mwst = row[2] or 0
    
    # Unique suppliers
    cursor.execute('SELECT COUNT(DISTINCT rechnungsaussteller) FROM invoices WHERE rechnungsaussteller != ""')
    unique_suppliers = cursor.fetchone()[0]
    
    # Average per invoice
    avg_per_invoice = (total_brutto / total_invoices) if total_invoices > 0 else 0
    
    # Monthly data
    cursor.execute('''
        SELECT strftime('%Y-%m', datum) as month, SUM(betrag_brutto) as total
        FROM invoices
        WHERE datum != '' AND datum IS NOT NULL
        GROUP BY month
        ORDER BY month
        LIMIT 12
    ''')
    monthly_data = cursor.fetchall()
    monthly_labels = [r[0] for r in monthly_data] if monthly_data else []
    monthly_values = [r[1] or 0 for r in monthly_data] if monthly_data else []
    
    # Top suppliers
    cursor.execute('''
        SELECT rechnungsaussteller as name, COUNT(*) as count, SUM(betrag_brutto) as total
        FROM invoices
        WHERE rechnungsaussteller != '' AND rechnungsaussteller IS NOT NULL
        GROUP BY rechnungsaussteller
        ORDER BY total DESC
        LIMIT 10
    ''')
    top_suppliers = [dict(r) for r in cursor.fetchall()]
    
    # Weekday distribution
    cursor.execute('''
        SELECT strftime('%w', datum) as weekday, COUNT(*) as count
        FROM invoices
        WHERE datum != '' AND datum IS NOT NULL
        GROUP BY weekday
    ''')
    weekday_raw = {int(r[0]): r[1] for r in cursor.fetchall()}
    weekday_data = [weekday_raw.get((i + 1) % 7, 0) for i in range(7)]
    
    conn.close()
    
    return {
        'stats': {
            'total_invoices': total_invoices,
            'total_amount': round(total_brutto, 2),
            'total_netto': round(total_netto, 2),
            'total_mwst': round(total_mwst, 2),
            'avg_per_invoice': round(avg_per_invoice, 2),
            'unique_suppliers': unique_suppliers
        },
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
        'top_suppliers': top_suppliers,
        'weekday_data': weekday_data
    }

def init_feedback_table():
    """Initialize feedback/corrections table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            supplier TEXT,
            field_name TEXT,
            original_value TEXT,
            corrected_value TEXT,
            invoice_id INTEGER,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        )
    ''')
    
    # Supplier patterns table - learned patterns per supplier
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplier_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier TEXT UNIQUE,
            patterns TEXT,
            confidence REAL DEFAULT 0,
            invoice_count INTEGER DEFAULT 0,
            last_updated TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize feedback tables
init_feedback_table()

def save_correction(invoice_id: int, supplier: str, field_name: str, original_value: str, corrected_value: str):
    """Save a user correction for learning"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO corrections (supplier, field_name, original_value, corrected_value, invoice_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (supplier, field_name, original_value, corrected_value, invoice_id))
    
    conn.commit()
    conn.close()
    
    # Update supplier patterns
    update_supplier_patterns(supplier)

def update_supplier_patterns(supplier: str):
    """Update learned patterns for a supplier based on corrections"""
    import json
    from datetime import datetime
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all corrections for this supplier
    cursor.execute('''
        SELECT field_name, corrected_value, COUNT(*) as count
        FROM corrections
        WHERE supplier = ?
        GROUP BY field_name, corrected_value
        ORDER BY count DESC
    ''', (supplier,))
    
    corrections = cursor.fetchall()
    
    # Build patterns
    patterns = {}
    for field, value, count in corrections:
        if field not in patterns:
            patterns[field] = []
        patterns[field].append({'value': value, 'count': count})
    
    # Count total invoices for this supplier
    cursor.execute('SELECT COUNT(*) FROM invoices WHERE rechnungsaussteller = ?', (supplier,))
    invoice_count = cursor.fetchone()[0]
    
    # Calculate confidence (more corrections = higher confidence)
    total_corrections = sum(c[2] for c in corrections)
    confidence = min(total_corrections / 10, 1.0)  # Max confidence at 10 corrections
    
    # Save patterns
    cursor.execute('''
        INSERT OR REPLACE INTO supplier_patterns (supplier, patterns, confidence, invoice_count, last_updated)
        VALUES (?, ?, ?, ?, ?)
    ''', (supplier, json.dumps(patterns), confidence, invoice_count, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def get_supplier_patterns(supplier: str) -> dict:
    """Get learned patterns for a supplier"""
    import json
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT patterns, confidence FROM supplier_patterns WHERE supplier = ?', (supplier,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return {
            'patterns': json.loads(row[0]),
            'confidence': row[1]
        }
    return {'patterns': {}, 'confidence': 0}

def update_invoice(invoice_id: int, updates: dict):
    """Update invoice with corrected values"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Build UPDATE query dynamically
    set_clauses = []
    values = []
    for field, value in updates.items():
        set_clauses.append(f"{field} = ?")
        values.append(value)
    
    values.append(invoice_id)
    
    query = f"UPDATE invoices SET {', '.join(set_clauses)} WHERE id = ?"
    cursor.execute(query, values)
    
    conn.commit()
    conn.close()

def get_invoice_by_id(invoice_id: int) -> dict:
    """Get single invoice by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return dict(row)
    return None

def init_feedback_table():
    """Initialize feedback/corrections table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            supplier TEXT,
            field_name TEXT,
            original_value TEXT,
            corrected_value TEXT,
            invoice_id INTEGER,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        )
    ''')
    
    # Supplier patterns table - learned patterns per supplier
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplier_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier TEXT UNIQUE,
            patterns TEXT,
            confidence REAL DEFAULT 0,
            invoice_count INTEGER DEFAULT 0,
            last_updated TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize feedback tables
init_feedback_table()

def save_correction(invoice_id: int, supplier: str, field_name: str, original_value: str, corrected_value: str):
    """Save a user correction for learning"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO corrections (supplier, field_name, original_value, corrected_value, invoice_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (supplier, field_name, original_value, corrected_value, invoice_id))
    
    conn.commit()
    conn.close()
    
    # Update supplier patterns
    update_supplier_patterns(supplier)

def update_supplier_patterns(supplier: str):
    """Update learned patterns for a supplier based on corrections"""
    import json
    from datetime import datetime
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all corrections for this supplier
    cursor.execute('''
        SELECT field_name, corrected_value, COUNT(*) as count
        FROM corrections
        WHERE supplier = ?
        GROUP BY field_name, corrected_value
        ORDER BY count DESC
    ''', (supplier,))
    
    corrections = cursor.fetchall()
    
    # Build patterns
    patterns = {}
    for field, value, count in corrections:
        if field not in patterns:
            patterns[field] = []
        patterns[field].append({'value': value, 'count': count})
    
    # Count total invoices for this supplier
    cursor.execute('SELECT COUNT(*) FROM invoices WHERE rechnungsaussteller = ?', (supplier,))
    invoice_count = cursor.fetchone()[0]
    
    # Calculate confidence (more corrections = higher confidence)
    total_corrections = sum(c[2] for c in corrections)
    confidence = min(total_corrections / 10, 1.0)  # Max confidence at 10 corrections
    
    # Save patterns
    cursor.execute('''
        INSERT OR REPLACE INTO supplier_patterns (supplier, patterns, confidence, invoice_count, last_updated)
        VALUES (?, ?, ?, ?, ?)
    ''', (supplier, json.dumps(patterns), confidence, invoice_count, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def get_supplier_patterns(supplier: str) -> dict:
    """Get learned patterns for a supplier"""
    import json
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT patterns, confidence FROM supplier_patterns WHERE supplier = ?', (supplier,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return {
            'patterns': json.loads(row[0]),
            'confidence': row[1]
        }
    return {'patterns': {}, 'confidence': 0}

def update_invoice(invoice_id: int, updates: dict):
    """Update invoice with corrected values"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Build UPDATE query dynamically
    set_clauses = []
    values = []
    for field, value in updates.items():
        set_clauses.append(f"{field} = ?")
        values.append(value)
    
    values.append(invoice_id)
    
    query = f"UPDATE invoices SET {', '.join(set_clauses)} WHERE id = ?"
    cursor.execute(query, values)
    
    conn.commit()
    conn.close()

def get_invoice_by_id(invoice_id: int) -> dict:
    """Get single invoice by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return dict(row)
    return None

def init_email_inbox_table():
    """Initialize email inbox configuration table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_inbox_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enabled INTEGER DEFAULT 0,
            email_address TEXT,
            imap_server TEXT,
            imap_port INTEGER DEFAULT 993,
            username TEXT,
            password TEXT,
            folder TEXT DEFAULT 'INBOX',
            filter_from TEXT,
            filter_subject TEXT,
            auto_process INTEGER DEFAULT 1,
            last_check TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_processed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            from_address TEXT,
            subject TEXT,
            received_at TEXT,
            processed_at TEXT,
            job_id TEXT,
            status TEXT,
            attachments_count INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

init_email_inbox_table()

def get_email_config():
    """Get email inbox configuration"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM email_inbox_config ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_email_config(config: dict):
    """Save email inbox configuration"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Delete existing config
    cursor.execute('DELETE FROM email_inbox_config')
    
    cursor.execute('''
        INSERT INTO email_inbox_config 
        (enabled, email_address, imap_server, imap_port, username, password, folder, filter_from, filter_subject, auto_process)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        config.get('enabled', 0),
        config.get('email_address', ''),
        config.get('imap_server', ''),
        config.get('imap_port', 993),
        config.get('username', ''),
        config.get('password', ''),
        config.get('folder', 'INBOX'),
        config.get('filter_from', ''),
        config.get('filter_subject', ''),
        config.get('auto_process', 1)
    ))
    
    conn.commit()
    conn.close()

def save_processed_email(message_id: str, from_addr: str, subject: str, job_id: str, attachments: int):
    """Save record of processed email"""
    from datetime import datetime
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO email_processed 
        (message_id, from_address, subject, received_at, processed_at, job_id, status, attachments_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (message_id, from_addr, subject, datetime.now().isoformat(), datetime.now().isoformat(), job_id, 'processed', attachments))
    
    conn.commit()
    conn.close()

def is_email_processed(message_id: str) -> bool:
    """Check if email was already processed"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM email_processed WHERE message_id = ?', (message_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def init_users_table():
    """Initialize users table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            company TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Add user_id to jobs table if not exists
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'user_id' not in columns:
        cursor.execute('ALTER TABLE jobs ADD COLUMN user_id INTEGER')
    
    conn.commit()
    conn.close()

init_users_table()

def create_user(email: str, password: str, name: str = '', company: str = '') -> int:
    """Create new user, returns user_id"""
    import hashlib
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO users (email, password_hash, name, company)
        VALUES (?, ?, ?, ?)
    ''', (email, password_hash, name, company))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return user_id

def verify_user(email: str, password: str) -> dict:
    """Verify user credentials, returns user dict or None"""
    import hashlib
    from datetime import datetime
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, email, name, company, is_active 
        FROM users 
        WHERE email = ? AND password_hash = ?
    ''', (email, password_hash))
    
    row = cursor.fetchone()
    
    if row and row[4]:  # is_active
        # Update last login
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                      (datetime.now().isoformat(), row[0]))
        conn.commit()
        conn.close()
        return {'id': row[0], 'email': row[1], 'name': row[2], 'company': row[3]}
    
    conn.close()
    return None

def get_user_by_id(user_id: int) -> dict:
    """Get user by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, email, name, company FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return {'id': row[0], 'email': row[1], 'name': row[2], 'company': row[3]}
    return None

def email_exists(email: str) -> bool:
    """Check if email already exists"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def init_users_table():
    """Initialize users table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            company TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Add user_id to jobs table if not exists
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'user_id' not in columns:
        cursor.execute('ALTER TABLE jobs ADD COLUMN user_id INTEGER')
    
    conn.commit()
    conn.close()

init_users_table()

def create_user(email: str, password: str, name: str = '', company: str = '') -> int:
    """Create new user, returns user_id"""
    import hashlib
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO users (email, password_hash, name, company)
        VALUES (?, ?, ?, ?)
    ''', (email, password_hash, name, company))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return user_id

def verify_user(email: str, password: str) -> dict:
    """Verify user credentials, returns user dict or None"""
    import hashlib
    from datetime import datetime
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, email, name, company, is_active 
        FROM users 
        WHERE email = ? AND password_hash = ?
    ''', (email, password_hash))
    
    row = cursor.fetchone()
    
    if row and row[4]:  # is_active
        # Update last login
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                      (datetime.now().isoformat(), row[0]))
        conn.commit()
        conn.close()
        return {'id': row[0], 'email': row[1], 'name': row[2], 'company': row[3]}
    
    conn.close()
    return None

def get_user_by_id(user_id: int) -> dict:
    """Get user by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, email, name, company FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return {'id': row[0], 'email': row[1], 'name': row[2], 'company': row[3]}
    return None

def email_exists(email: str) -> bool:
    """Check if email already exists"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def init_subscriptions_table():
    """Initialize subscriptions table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan TEXT NOT NULL,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            status TEXT DEFAULT 'active',
            invoices_limit INTEGER,
            invoices_used INTEGER DEFAULT 0,
            current_period_start TEXT,
            current_period_end TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_subscriptions_table()

def get_user_subscription(user_id: int) -> dict:
    """Get user's active subscription"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM subscriptions 
        WHERE user_id = ? AND status = 'active' 
        ORDER BY created_at DESC LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_subscription(user_id: int, plan: str, stripe_customer_id: str, stripe_subscription_id: str):
    """Create new subscription"""
    limits = {'starter': 100, 'professional': 600, 'enterprise': 999999}
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO subscriptions 
        (user_id, plan, stripe_customer_id, stripe_subscription_id, invoices_limit, status)
        VALUES (?, ?, ?, ?, ?, 'active')
    ''', (user_id, plan, stripe_customer_id, stripe_subscription_id, limits.get(plan, 100)))
    conn.commit()
    conn.close()

def check_invoice_limit(user_id: int) -> dict:
    """Check if user can process more invoices"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get active subscription
    cursor.execute('''
        SELECT plan, invoices_limit, invoices_used 
        FROM subscriptions 
        WHERE user_id = ? AND status = 'active' 
        ORDER BY created_at DESC LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {
            'allowed': False,
            'reason': 'no_subscription',
            'message': 'Kein aktives Abonnement. Bitte wählen Sie einen Plan.'
        }
    
    plan, limit, used = row[0], row[1], row[2]
    remaining = limit - used
    
    if remaining <= 0:
        return {
            'allowed': False,
            'reason': 'limit_reached',
            'message': f'Monatliches Limit erreicht ({used}/{limit}). Bitte upgraden Sie Ihren Plan.',
            'plan': plan,
            'limit': limit,
            'used': used
        }
    
    return {
        'allowed': True,
        'plan': plan,
        'limit': limit,
        'used': used,
        'remaining': remaining
    }

def increment_invoice_usage(user_id: int, count: int = 1):
    """Increment the invoice usage counter"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE subscriptions 
        SET invoices_used = invoices_used + ?
        WHERE user_id = ? AND status = 'active'
    ''', (count, user_id))
    
    conn.commit()
    conn.close()

def reset_monthly_usage():
    """Reset all usage counters (call monthly via cron)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE subscriptions SET invoices_used = 0 WHERE status = "active"')
    conn.commit()
    conn.close()
