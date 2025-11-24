"""
Plausibility Check System
Erkennt Anomalien und ungewöhnliche Rechnungen
"""
import sqlite3
import json
import statistics
from typing import List, Dict, Optional
from datetime import datetime, timedelta

def get_historical_stats(aussteller: str, days: int = 90) -> Optional[Dict]:
    """Hole historische Statistiken für einen Aussteller"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT betrag_brutto, betrag_netto, mwst_betrag
        FROM invoices
        WHERE rechnungsaussteller = ?
        AND datum >= ?
        AND betrag_brutto IS NOT NULL
    ''', (aussteller, cutoff_date))
    
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 3:  # Zu wenig Daten
        return None
    
    bruttos = [r[0] for r in rows if r[0]]
    nettos = [r[1] for r in rows if r[1]]
    mwsts = [r[2] for r in rows if r[2]]
    
    return {
        'count': len(rows),
        'brutto_avg': statistics.mean(bruttos),
        'brutto_median': statistics.median(bruttos),
        'brutto_stdev': statistics.stdev(bruttos) if len(bruttos) > 1 else 0,
        'netto_avg': statistics.mean(nettos) if nettos else 0,
        'mwst_avg': statistics.mean(mwsts) if mwsts else 0
    }

def check_amount_outlier(invoice: Dict) -> Optional[Dict]:
    """Prüfe ob Betrag ungewöhnlich ist"""
    aussteller = invoice.get('rechnungsaussteller')
    betrag = invoice.get('betrag_brutto')
    
    if not aussteller or not betrag:
        return None
    
    stats = get_historical_stats(aussteller)
    if not stats:
        return None
    
    # Z-Score berechnen
    if stats['brutto_stdev'] > 0:
        z_score = abs((betrag - stats['brutto_avg']) / stats['brutto_stdev'])
    else:
        z_score = 0
    
    # Anomalie wenn z_score > 2 (95% Konfidenz) oder > 3 (99.7%)
    if z_score > 3:
        severity = 'high'
        confidence = 0.95
    elif z_score > 2:
        severity = 'medium'
        confidence = 0.85
    else:
        return None  # Normal
    
    details = {
        'current_amount': betrag,
        'historical_avg': round(stats['brutto_avg'], 2),
        'historical_median': round(stats['brutto_median'], 2),
        'z_score': round(z_score, 2),
        'sample_size': stats['count']
    }
    
    return {
        'check_type': 'amount_outlier',
        'severity': severity,
        'confidence': confidence,
        'details': json.dumps(details)
    }

def check_unusual_change(invoice: Dict) -> Optional[Dict]:
    """Prüfe ob Betrag stark von letzter Rechnung abweicht"""
    aussteller = invoice.get('rechnungsaussteller')
    betrag = invoice.get('betrag_brutto')
    
    if not aussteller or not betrag:
        return None
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Hole letzte 5 Rechnungen vom gleichen Aussteller
    cursor.execute('''
        SELECT betrag_brutto, datum
        FROM invoices
        WHERE rechnungsaussteller = ?
        AND betrag_brutto IS NOT NULL
        ORDER BY datum DESC
        LIMIT 5
    ''', (aussteller,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 2:
        return None
    
    last_amount = rows[0][0]
    change_pct = abs((betrag - last_amount) / last_amount * 100) if last_amount > 0 else 0
    
    # Warnung wenn >50% Änderung
    if change_pct > 100:
        severity = 'high'
        confidence = 0.8
    elif change_pct > 50:
        severity = 'medium'
        confidence = 0.7
    else:
        return None
    
    details = {
        'current_amount': betrag,
        'last_amount': last_amount,
        'change_percent': round(change_pct, 1),
        'last_date': rows[0][1]
    }
    
    return {
        'check_type': 'unusual_change',
        'severity': severity,
        'confidence': confidence,
        'details': json.dumps(details)
    }

def run_plausibility_checks(invoice_id: int) -> List[Dict]:
    """Führe alle Plausibilitätsprüfungen für eine Rechnung aus"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return []
    
    invoice = dict(row)
    checks = []
    
    # Check 1: Amount Outlier
    result = check_amount_outlier(invoice)
    if result:
        checks.append(result)
    
    # Check 2: Unusual Change
    result = check_unusual_change(invoice)
    if result:
        checks.append(result)
    
    return checks

def save_plausibility_check(invoice_id: int, check: Dict):
    """Speichere Plausibilitätsprüfung in DB"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO plausibility_checks 
        (invoice_id, check_type, severity, confidence, details, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (
        invoice_id,
        check['check_type'],
        check['severity'],
        check['confidence'],
        check['details']
    ))
    
    conn.commit()
    conn.close()

def get_plausibility_checks_for_invoice(invoice_id: int) -> List[Dict]:
    """Hole alle Plausibilitätsprüfungen für eine Rechnung"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM plausibility_checks
        WHERE invoice_id = ?
        ORDER BY severity DESC, confidence DESC
    ''', (invoice_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
