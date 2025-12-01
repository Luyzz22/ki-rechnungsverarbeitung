#!/usr/bin/env python3
"""
SBS Deutschland – Audit Log
Protokolliert alle wichtigen Aktionen im System.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict
from database import get_connection

logger = logging.getLogger(__name__)

# Audit-Event Typen
class AuditAction:
    # Auth
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    REGISTER = "auth.register"
    PASSWORD_CHANGE = "auth.password_change"
    
    # Jobs
    JOB_CREATED = "job.created"
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_DELETED = "job.deleted"
    
    # Invoices
    INVOICE_CREATED = "invoice.created"
    INVOICE_UPDATED = "invoice.updated"
    INVOICE_DELETED = "invoice.deleted"
    INVOICE_EXPORTED = "invoice.exported"
    
    # API Keys
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    API_KEY_USED = "api_key.used"
    
    # Export
    EXPORT_EXCEL = "export.excel"
    EXPORT_CSV = "export.csv"
    EXPORT_DATEV = "export.datev"
    EXPORT_XRECHNUNG = "export.xrechnung"
    EXPORT_ZIP = "export.zip"
    
    # Admin
    USER_CREATED = "admin.user_created"
    USER_DELETED = "admin.user_deleted"
    SETTINGS_CHANGED = "admin.settings_changed"


def log_audit(
    action: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """
    Protokolliert eine Audit-Aktion.
    
    Args:
        action: Aktionstyp (z.B. AuditAction.LOGIN)
        user_id: User-ID
        user_email: User-Email
        resource_type: Ressourcentyp (job, invoice, etc.)
        resource_id: Ressourcen-ID
        details: Zusätzliche Details (JSON)
        ip_address: Client-IP
        user_agent: Browser User-Agent
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_log 
            (user_id, user_email, action, resource_type, resource_id, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, user_email, action, resource_type, resource_id, details, ip_address, user_agent))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Audit: {action} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Audit-Log Fehler: {e}")


def get_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """
    Holt Audit-Log Einträge.
    
    Args:
        user_id: Filter nach User
        action: Filter nach Aktion
        resource_type: Filter nach Ressourcentyp
        limit: Max. Anzahl
        offset: Pagination Offset
        
    Returns:
        Liste der Audit-Einträge
    """
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    if action:
        query += " AND action LIKE ?"
        params.append(f"{action}%")
    
    if resource_type:
        query += " AND resource_type = ?"
        params.append(resource_type)
    
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    logs = cursor.fetchall()
    conn.close()
    
    return logs


def get_audit_stats(days: int = 30) -> Dict:
    """Holt Audit-Statistiken der letzten X Tage."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT action, COUNT(*) as count
        FROM audit_log
        WHERE timestamp > datetime('now', ?)
        GROUP BY action
        ORDER BY count DESC
    """, (f'-{days} days',))
    
    actions = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id) as unique_users
        FROM audit_log
        WHERE timestamp > datetime('now', ?)
    """, (f'-{days} days',))
    
    unique_users = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "period_days": days,
        "actions": actions,
        "unique_users": unique_users,
        "total_events": sum(actions.values())
    }
