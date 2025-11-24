"""
Duplicate Detection System
- Hash-based detection
- KI-based similarity detection
"""
import hashlib
import json
from typing import Optional, Tuple, List, Dict
import logging

logger = logging.getLogger(__name__)


def generate_invoice_hash(invoice: dict) -> str:
    """Generate hash for duplicate detection"""
    # Use key fields that identify a unique invoice
    key_fields = [
        str(invoice.get('rechnungsnummer', '')).strip().lower(),
        str(invoice.get('rechnungsaussteller', '')).strip().lower(),
        str(invoice.get('betrag_brutto', 0)),
        str(invoice.get('datum', '')),
    ]
    
    # Create hash
    content = '|'.join(key_fields)
    return hashlib.sha256(content.encode()).hexdigest()


def check_duplicate_by_hash(invoice: dict, user_id: int = None) -> Optional[Dict]:
    """
    Check if invoice is duplicate based on hash
    Returns: dict with duplicate info or None
    """
    import sqlite3
    
    content_hash = generate_invoice_hash(invoice)
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find existing invoice with same hash
    if user_id:
        cursor.execute('''
            SELECT i.id, i.rechnungsnummer, i.datum, i.rechnungsaussteller, i.betrag_brutto, i.job_id
            FROM invoices i
            JOIN jobs j ON i.job_id = j.job_id
            WHERE i.content_hash = ? AND j.user_id = ?
            LIMIT 1
        ''', (content_hash, user_id))
    else:
        cursor.execute('''
            SELECT id, rechnungsnummer, datum, rechnungsaussteller, betrag_brutto, job_id
            FROM invoices
            WHERE content_hash = ?
            LIMIT 1
        ''', (content_hash,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        logger.info(f"🔍 Duplicate detected: {result['rechnungsaussteller']} - {result['betrag_brutto']}€")
        return dict(result)
    
    return None


def save_duplicate_detection(invoice_id: int, duplicate_of_id: int, method: str = 'hash', confidence: float = 1.0):
    """Save duplicate detection to database"""
    import sqlite3
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO duplicate_detections (invoice_id, duplicate_of_id, detection_method, confidence)
        VALUES (?, ?, ?, ?)
    ''', (invoice_id, duplicate_of_id, method, confidence))
    
    conn.commit()
    conn.close()
    
    logger.info(f"📝 Saved duplicate detection: {invoice_id} -> {duplicate_of_id}")


def get_duplicates_for_invoice(invoice_id: int) -> List[Dict]:
    """Get all duplicates for an invoice"""
    import sqlite3
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            dd.*,
            i.rechnungsnummer,
            i.datum,
            i.rechnungsaussteller,
            i.betrag_brutto
        FROM duplicate_detections dd
        JOIN invoices i ON dd.duplicate_of_id = i.id
        WHERE dd.invoice_id = ? AND dd.status = 'pending'
        ORDER BY dd.detected_at DESC
    ''', (invoice_id,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results


def mark_duplicate_reviewed(detection_id: int, user_id: int, is_duplicate: bool):
    """Mark a duplicate detection as reviewed"""
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    status = 'confirmed' if is_duplicate else 'false_positive'
    
    cursor.execute('''
        UPDATE duplicate_detections
        SET status = ?, reviewed_by = ?, reviewed_at = ?
        WHERE id = ?
    ''', (status, user_id, datetime.now().isoformat(), detection_id))
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Duplicate reviewed: {detection_id} -> {status}")
