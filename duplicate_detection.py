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


def check_duplicate_by_hash(invoice: dict, user_id: int = None, conn=None) -> Optional[Dict]:
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
    if should_close:
        conn.close()
    
    if result:
        logger.info(f"🔍 Duplicate detected: {result['rechnungsaussteller']} - {result['betrag_brutto']}€")
        return dict(result)
    
    return None


def save_duplicate_detection(invoice_id: int, duplicate_of_id: int, method: str = 'hash', confidence: float = 1.0, conn=None):
    """Save duplicate detection to database"""
    from database import get_connection
    
    should_close = conn is None
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO duplicate_detections (invoice_id, duplicate_of_id, detection_method, confidence)
        VALUES (?, ?, ?, ?)
    ''', (invoice_id, duplicate_of_id, method, confidence))
    
    conn.commit()
    if should_close:
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
    if should_close:
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
    if should_close:
        conn.close()
    
    logger.info(f"✅ Duplicate reviewed: {detection_id} -> {status}")


def check_similarity_ai(invoice: dict, user_id: int = None) -> List[Dict]:
    """
    Use Claude to detect similar invoices
    Returns: list of similar invoices with confidence scores
    """
    import sqlite3
    from anthropic import Anthropic
    import os
    
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    # Get recent invoices from same supplier
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    aussteller = invoice.get('rechnungsaussteller', '')
    
    if user_id:
        cursor.execute('''
            SELECT i.id, i.rechnungsnummer, i.datum, i.betrag_brutto, i.rechnungsaussteller
            FROM invoices i
            JOIN jobs j ON i.job_id = j.job_id
            WHERE j.user_id = ? 
            AND LOWER(i.rechnungsaussteller) LIKE LOWER(?)
            ORDER BY i.datum DESC
            LIMIT 20
        ''', (user_id, f'%{aussteller}%'))
    else:
        cursor.execute('''
            SELECT id, rechnungsnummer, datum, betrag_brutto, rechnungsaussteller
            FROM invoices
            WHERE LOWER(rechnungsaussteller) LIKE LOWER(?)
            ORDER BY datum DESC
            LIMIT 20
        ''', (f'%{aussteller}%',))
    
    existing_invoices = [dict(row) for row in cursor.fetchall()]
    if should_close:
        conn.close()
    
    if not existing_invoices:
        return []
    
    # Ask Claude to compare
    prompt = f"""Analysiere ob diese Rechnung ein Duplikat ist:

NEUE RECHNUNG:
- Aussteller: {invoice.get('rechnungsaussteller')}
- Nummer: {invoice.get('rechnungsnummer')}
- Datum: {invoice.get('datum')}
- Betrag: {invoice.get('betrag_brutto')}€

EXISTIERENDE RECHNUNGEN:
{json.dumps(existing_invoices, indent=2, ensure_ascii=False)}

Prüfe ob die neue Rechnung ein Duplikat oder sehr ähnlich zu einer existierenden ist.
Berücksichtige:
- Gleiche Rechnungsnummer = 100% Duplikat
- Gleiches Datum + gleicher Betrag = sehr wahrscheinlich
- Ähnlicher Betrag (±5€) + nahes Datum (±3 Tage) = möglich
- Unterschiedliche Nummer aber alles andere gleich = verdächtig

Antworte NUR mit JSON:
{
  "is_duplicate": true/false,
  "similar_to": [invoice_id1, invoice_id2],
  "confidence": 0.0-1.0,
  "reason": "Kurze Erklärung"
}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text.strip()
        # Remove markdown code blocks if present
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        result = json.loads(result_text)
        
        logger.info(f"🤖 AI similarity check: {result['confidence']:.2f} - {result['reason']}")
        
        similar = []
        if result.get('is_duplicate') or result.get('confidence', 0) > 0.7:
            for inv_id in result.get('similar_to', []):
                similar.append({
                    'id': inv_id,
                    'confidence': result['confidence'],
                    'reason': result['reason']
                })
        
        return similar
        
    except Exception as e:
        logger.error(f"AI similarity check failed: {e}")
        return []


def detect_all_duplicates(invoice: dict, user_id: int = None) -> Dict:
    """
    Complete duplicate detection: hash + AI
    Returns: {'hash_duplicate': {...}, 'similar': [...]}
    """
    results = {
        'hash_duplicate': None,
        'similar': []
    }
    
    # 1. Hash-based check (fast, exact)
    hash_dup = check_duplicate_by_hash(invoice, user_id)
    if hash_dup:
        results['hash_duplicate'] = hash_dup
        logger.warning(f"🔴 Exact duplicate found: Invoice #{hash_dup['id']}")
    
    # 2. AI-based similarity (slower, fuzzy)
    similar = check_similarity_ai(invoice, user_id)
    if similar:
        results['similar'] = similar
        logger.warning(f"🟡 {len(similar)} similar invoice(s) found")
    
    return results
