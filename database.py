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
