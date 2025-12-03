#!/usr/bin/env python3
"""
SBS Deutschland – Dashboard Widgets
Anpassbare Dashboard-Komponenten für jeden User.
"""

import json
import logging
from typing import Dict, List, Optional
from database import get_connection

logger = logging.getLogger(__name__)


# Verfügbare Widget-Typen
class WidgetType:
    INVOICE_SUMMARY = "invoice_summary"      # Rechnungs-Übersicht
    TOP_SUPPLIERS = "top_suppliers"          # Top-Lieferanten
    MONTHLY_CHART = "monthly_chart"          # Monatlicher Verlauf
    RECENT_JOBS = "recent_jobs"              # Letzte Verarbeitungen
    CONFIDENCE_SCORE = "confidence_score"    # KI-Konfidenz
    QUICK_ACTIONS = "quick_actions"          # Schnellzugriff
    ALERTS = "alerts"                        # Warnungen
    CASH_FLOW = "cash_flow"                  # Cash-Flow Übersicht


# Standard-Widgets für neue User
DEFAULT_WIDGETS = [
    {"type": WidgetType.INVOICE_SUMMARY, "position": 0, "size": "large"},
    {"type": WidgetType.TOP_SUPPLIERS, "position": 1, "size": "medium"},
    {"type": WidgetType.MONTHLY_CHART, "position": 2, "size": "large"},
    {"type": WidgetType.RECENT_JOBS, "position": 3, "size": "medium"},
    {"type": WidgetType.QUICK_ACTIONS, "position": 4, "size": "small"},
]


def get_user_widgets(user_id: int) -> List[Dict]:
    """Holt alle Widgets eines Users."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM dashboard_widgets 
        WHERE user_id = ? AND is_visible = 1
        ORDER BY position
    """, (user_id,))
    
    widgets = cursor.fetchall()
    conn.close()
    
    # Standard-Widgets wenn leer
    if not widgets:
        widgets = init_default_widgets(user_id)
    
    for w in widgets:
        w['config'] = json.loads(w['config']) if w['config'] else {}
    
    return widgets


def init_default_widgets(user_id: int) -> List[Dict]:
    """Initialisiert Standard-Widgets für neuen User."""
    conn = get_connection()
    cursor = conn.cursor()
    
    widgets = []
    for w in DEFAULT_WIDGETS:
        cursor.execute("""
            INSERT INTO dashboard_widgets (user_id, widget_type, position, size)
            VALUES (?, ?, ?, ?)
        """, (user_id, w['type'], w['position'], w['size']))
        
        widgets.append({
            'id': cursor.lastrowid,
            'user_id': user_id,
            'widget_type': w['type'],
            'position': w['position'],
            'size': w['size'],
            'config': {},
            'is_visible': 1
        })
    
    conn.commit()
    conn.close()
    
    return widgets


def add_widget(user_id: int, widget_type: str, size: str = "medium", config: Dict = None) -> Dict:
    """Fügt ein neues Widget hinzu."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Höchste Position ermitteln
    cursor.execute("SELECT MAX(position) FROM dashboard_widgets WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    position = (row[0] or 0) + 1
    
    cursor.execute("""
        INSERT INTO dashboard_widgets (user_id, widget_type, position, size, config)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, widget_type, position, size, json.dumps(config or {})))
    
    widget_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "id": widget_id,
        "widget_type": widget_type,
        "position": position,
        "size": size
    }


def update_widget(widget_id: int, user_id: int, updates: Dict) -> bool:
    """Aktualisiert ein Widget."""
    conn = get_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['position', 'size', 'config', 'is_visible']
    set_parts = []
    values = []
    
    for field in allowed_fields:
        if field in updates:
            set_parts.append(f"{field} = ?")
            value = updates[field]
            if field == 'config':
                value = json.dumps(value)
            values.append(value)
    
    if not set_parts:
        conn.close()
        return False
    
    values.extend([widget_id, user_id])
    
    cursor.execute(f"""
        UPDATE dashboard_widgets 
        SET {', '.join(set_parts)}
        WHERE id = ? AND user_id = ?
    """, values)
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0


def remove_widget(widget_id: int, user_id: int) -> bool:
    """Entfernt ein Widget (setzt is_visible=0)."""
    return update_widget(widget_id, user_id, {'is_visible': 0})


def reorder_widgets(user_id: int, widget_ids: List[int]) -> bool:
    """Sortiert Widgets neu."""
    conn = get_connection()
    cursor = conn.cursor()
    
    for position, widget_id in enumerate(widget_ids):
        cursor.execute("""
            UPDATE dashboard_widgets SET position = ? 
            WHERE id = ? AND user_id = ?
        """, (position, widget_id, user_id))
    
    conn.commit()
    conn.close()
    return True


def get_widget_data(widget_type: str, user_id: int, config: Dict = None) -> Dict:
    """Holt die Daten für ein Widget."""
    config = config or {}
    days = config.get('days', 30)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    data = {"type": widget_type}
    
    if widget_type == WidgetType.INVOICE_SUMMARY:
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(betrag_brutto), 0) as total_brutto,
                COALESCE(SUM(betrag_netto), 0) as total_netto
            FROM invoices i
            JOIN jobs j ON i.job_id = j.job_id
            WHERE j.user_id = ? AND i.created_at > datetime('now', ?)
        """, (user_id, f'-{days} days'))
        row = cursor.fetchone()
        data['summary'] = {
            'count': row[0],
            'total_brutto': round(row[1], 2),
            'total_netto': round(row[2], 2)
        }
    
    elif widget_type == WidgetType.TOP_SUPPLIERS:
        cursor.execute("""
            SELECT rechnungsaussteller, COUNT(*) as cnt, SUM(betrag_brutto) as total
            FROM invoices i
            JOIN jobs j ON i.job_id = j.job_id
            WHERE j.user_id = ? AND i.created_at > datetime('now', ?)
            GROUP BY rechnungsaussteller
            ORDER BY total DESC
            LIMIT 5
        """, (user_id, f'-{days} days'))
        data['suppliers'] = [
            {'name': r[0] or 'Unbekannt', 'count': r[1], 'total': round(r[2] or 0, 2)}
            for r in cursor.fetchall()
        ]
    
    elif widget_type == WidgetType.RECENT_JOBS:
        cursor.execute("""
            SELECT job_id, filename, status, created_at, invoice_count
            FROM jobs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
        """, (user_id,))
        data['jobs'] = [
            {'job_id': r[0], 'filename': r[1], 'status': r[2], 
             'created_at': r[3], 'invoice_count': r[4]}
            for r in cursor.fetchall()
        ]
    
    elif widget_type == WidgetType.CONFIDENCE_SCORE:
        cursor.execute("""
            SELECT 
                AVG(confidence) as avg_conf,
                SUM(CASE WHEN confidence >= 0.8 THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN confidence >= 0.5 AND confidence < 0.8 THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN confidence < 0.5 THEN 1 ELSE 0 END) as low
            FROM invoices i
            JOIN jobs j ON i.job_id = j.job_id
            WHERE j.user_id = ? AND i.created_at > datetime('now', ?)
        """, (user_id, f'-{days} days'))
        row = cursor.fetchone()
        data['confidence'] = {
            'average': round((row[0] or 0) * 100, 1),
            'high': row[1] or 0,
            'medium': row[2] or 0,
            'low': row[3] or 0
        }
    
    elif widget_type == WidgetType.MONTHLY_CHART:
        cursor.execute("""
            SELECT strftime('%Y-%m', i.created_at) as month, SUM(betrag_brutto) as total
            FROM invoices i
            JOIN jobs j ON i.job_id = j.job_id
            WHERE j.user_id = ? AND i.created_at > datetime('now', '-12 months')
            GROUP BY month
            ORDER BY month
        """, (user_id,))
        data['monthly'] = [
            {'month': r[0], 'total': round(r[1] or 0, 2)}
            for r in cursor.fetchall()
        ]
    
    conn.close()
    return data
