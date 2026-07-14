"""
Duplicate Detection System
- Hash-based detection
- KI-based similarity detection
"""
import hashlib
import sqlite3
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
    from database import get_connection
    import logging
    
    logger = logging.getLogger(__name__)
    content_hash = generate_invoice_hash(invoice)
    
    should_close = conn is None
    if conn is None:
        conn = get_connection()
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

def compute_file_hash(content: bytes) -> str:
    """SHA-256 der Upload-Datei – layoutunabhängige Duplikatserkennung.

    Fängt Re-Uploads derselben Datei auch dann, wenn die Extraktion (Aussteller
    im Briefkopf-Logo → NULL) keinen verlässlichen Feld-Fingerprint liefert."""
    return hashlib.sha256(content).hexdigest()


def _resolve_invoice_file(datei_pfad, job_upload_path):
    """Findet die zu einer Rechnung gehörende Datei für den Hash-Backfill.

    Bevorzugt ``datei_pfad``; fällt sonst auf das Upload-Verzeichnis des Jobs
    zurück (klassischer Flow speicherte den Pfad nur dort). Gibt den Pfad zur
    ersten passenden Datei zurück oder ``None``."""
    import os

    if datei_pfad and os.path.isfile(datei_pfad):
        return datei_pfad
    # jobs.upload_path ist ein GETEILTES Verzeichnis. Bei Mehr-Datei-Jobs lässt
    # sich Zeile→Datei nicht eindeutig zuordnen – dann NICHT raten (sonst bekämen
    # alle Rechnungen des Jobs denselben Hash → falsche Datei-Hash-Duplikate).
    # Nur verwenden, wenn genau EINE passende Datei im Verzeichnis liegt.
    if job_upload_path and os.path.isdir(job_upload_path):
        exts = (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".xml")
        eligible = [os.path.join(job_upload_path, n) for n in sorted(os.listdir(job_upload_path))
                    if n.lower().endswith(exts) and os.path.isfile(os.path.join(job_upload_path, n))]
        if len(eligible) == 1:
            return eligible[0]
    return None


def backfill_datei_hashes(limit: int = 1000) -> int:
    """Berechnet ``datei_hash`` für Bestandsrechnungen ohne Hash (einmalig,
    idempotent). Best effort: nutzt ``datei_pfad`` ODER das jobs.upload_path des
    zugehörigen Jobs (klassischer Flow). Fehler brechen weder Migration noch
    Start. Gibt die Anzahl gefüllter Zeilen zurück."""
    from database import get_connection

    filled = 0
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT i.id, i.datei_pfad, j.upload_path "
            "FROM invoices i LEFT JOIN jobs j ON i.job_id = j.job_id "
            "WHERE (i.datei_hash IS NULL OR i.datei_hash = '') "
            "LIMIT ?",
            (int(limit),),
        )
        rows = cur.fetchall()
        for row in rows:
            try:
                path = _resolve_invoice_file(row["datei_pfad"], row["upload_path"])
                if path:
                    with open(path, "rb") as fh:
                        h = compute_file_hash(fh.read())
                    cur.execute("UPDATE invoices SET datei_hash = ? WHERE id = ?", (h, row["id"]))
                    filled += 1
            except Exception as exc:  # pragma: no cover - einzelne Datei defekt/fehlt
                logger.debug("backfill datei_hash id=%s übersprungen: %s", row["id"], exc)
        conn.commit()
        conn.close()
        if filled:
            logger.info("backfill_datei_hashes: %d Zeilen gefüllt", filled)
    except Exception as exc:  # pragma: no cover - darf Start nie sprengen
        logger.warning("backfill_datei_hashes übersprungen: %s", exc)
    return filled


def check_duplicate_by_file_hash(datei_hash: str, tenant_id: int,
                                 exclude_invoice_id: Optional[int] = None, conn=None) -> Optional[Dict]:
    """Findet eine frühere Rechnung DESSELBEN Tenants mit identischem Datei-Hash."""
    if not datei_hash:
        return None
    from database import get_connection

    should_close = conn is None
    if conn is None:
        conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    sql = (
        "SELECT i.id, i.rechnungsnummer, i.datum, i.rechnungsaussteller, i.betrag_brutto "
        "FROM invoices i LEFT JOIN jobs j ON i.job_id = j.job_id "
        "WHERE i.datei_hash = ? AND COALESCE(i.tenant_id, j.user_id) = ? "
        "AND COALESCE(i.deleted, 0) = 0"
    )
    params = [datei_hash, int(tenant_id)]
    if exclude_invoice_id is not None:
        sql += " AND i.id <> ?"
        params.append(int(exclude_invoice_id))
    sql += " ORDER BY i.id ASC LIMIT 1"
    cursor.execute(sql, params)
    row = cursor.fetchone()
    if should_close:
        conn.close()
    return dict(row) if row else None


def _normalize_date(value) -> Optional[str]:
    """Bringt gängige Datumsformate auf YYYY-MM-DD (format-tolerant für den
    Duplikat-Guard). Unparsbares → None (= „unbekannt", schließt NICHT aus)."""
    import re
    s = str(value or "").strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r"^(\d{1,2})[.](\d{1,2})[.](\d{4})", s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return None


def check_duplicate_by_fields(invoice: dict, tenant_id: int,
                              exclude_invoice_id: Optional[int] = None, conn=None) -> Optional[Dict]:
    """NULL-sicherer Feld-Match: primär (tenant, rechnungsnummer, betrag_brutto).

    ``rechnungsaussteller``/``datum`` werden NUR verschärfend genutzt, wenn sie
    beidseitig vorhanden sind – so kippt der Match nicht (wie beim alten
    content_hash) allein daran, dass der Aussteller im Briefkopf-Logo steht und
    darum NULL ist. Ohne Nummer UND Betrag ist kein verlässlicher Feld-Match
    möglich → None (kein False Positive)."""
    nummer = str(invoice.get("rechnungsnummer") or "").strip()
    brutto = invoice.get("betrag_brutto")
    if not nummer or brutto is None:
        return None
    from database import get_connection

    should_close = conn is None
    if conn is None:
        conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    params = [int(tenant_id), nummer.lower(), float(brutto)]
    sql = (
        "SELECT i.id, i.rechnungsnummer, i.datum, i.rechnungsaussteller, i.betrag_brutto "
        "FROM invoices i LEFT JOIN jobs j ON i.job_id = j.job_id "
        "WHERE COALESCE(i.tenant_id, j.user_id) = ? "
        "AND LOWER(TRIM(COALESCE(i.rechnungsnummer, ''))) = ? "
        "AND ABS(COALESCE(i.betrag_brutto, 0) - ?) < 0.01 "
        "AND COALESCE(i.deleted, 0) = 0"
    )
    if exclude_invoice_id is not None:
        sql += " AND i.id <> ?"
        params.append(int(exclude_invoice_id))
    # Verschärfung: Aussteller nur, wenn im NEUEN Beleg vorhanden. Dann muss der
    # Altbeleg denselben Aussteller haben ODER selbst keinen (NULL-tolerant –
    # Briefkopf-Logo-Fall). Sind beide Aussteller bekannt und verschieden, ist es
    # KEIN Duplikat (verschiedene Lieferanten nutzen dieselben simplen Nummern).
    aussteller = str(invoice.get("rechnungsaussteller") or "").strip()
    if aussteller:
        sql += (" AND (COALESCE(TRIM(i.rechnungsaussteller), '') = '' "
                "OR LOWER(TRIM(i.rechnungsaussteller)) = ?)")
        params.append(aussteller.lower())
    sql += " ORDER BY i.id ASC"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    if should_close:
        conn.close()

    # Datums-Guard FORMAT-TOLERANT und in Python (nicht als harte SQL-Gleichheit):
    # Das Datum wird auf YYYY-MM-DD normalisiert. Ein Kandidat wird NUR
    # ausgeschlossen, wenn BEIDE Daten vorhanden sind UND sich nach Normalisierung
    # unterscheiden (verhindert False Positives bei wiederkehrenden Belegen mit
    # gleicher simpler Nummer + gleichem Betrag, aber anderem Datum). Format-
    # Abweichungen (Doc 36/41: "29.09.2025" vs. "2025-09-29") gelten als gleich.
    new_date = _normalize_date(invoice.get("datum"))
    fallback = None
    for row in rows:
        stored = _normalize_date(row["datum"])
        if new_date and stored:
            if new_date == stored:
                return dict(row)          # exakter (normalisierter) Datumstreffer
            continue                      # beide bekannt & verschieden → kein Duplikat
        if fallback is None:              # mind. eine Seite ohne Datum → kompatibel
            fallback = row
    return dict(fallback) if fallback else None


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
        from invoice_extraction import get_anthropic_extraction_model
        response = client.messages.create(
            model=get_anthropic_extraction_model(),
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
