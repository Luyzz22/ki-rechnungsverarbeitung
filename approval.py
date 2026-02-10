#!/usr/bin/env python3
"""
SBS Deutschland – Invoice Approval Module v1.0
Enterprise-Grade Rechnungsfreigabe-Workflow

Features:
- Multi-Level Approval basierend auf Beträgen
- Automatische Zuweisung nach Regeln
- Delegation & Vertretung
- Vollständiger Audit Trail
- Email-Benachrichtigungen
"""

from audit import log_audit, AuditAction
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Status-Konstanten
class InvoiceStatus(str, Enum):
    PENDING = "pending"           # Neu eingegangen, wartet auf Zuweisung
    ASSIGNED = "assigned"         # Zugewiesen, wartet auf Freigabe
    IN_REVIEW = "in_review"       # Wird geprüft
    APPROVED = "approved"         # Freigegeben
    REJECTED = "rejected"         # Abgelehnt
    ON_HOLD = "on_hold"           # Zurückgestellt
    PAID = "paid"                 # Bezahlt

class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    SCHEDULED = "scheduled"
    PAID = "paid"
    OVERDUE = "overdue"

class ApprovalAction(str, Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    ESCALATED = "escalated"
    COMMENTED = "commented"
    PAID = "paid"

@dataclass
class ApprovalRule:
    id: int
    name: str
    min_amount: float
    max_amount: Optional[float]
    required_role: str
    auto_approve: bool
    priority: int


class ApprovalManager:
    """Manages invoice approval workflows"""
    
    def __init__(self, db_path: str = "invoices.db"):
        self.db_path = db_path
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # =========================================================================
    # INVOICE STATUS MANAGEMENT
    # =========================================================================
    
    def get_invoice_status(self, invoice_id: int) -> Optional[Dict]:
        """Holt den aktuellen Status einer Rechnung"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.id, i.rechnungsnummer, i.rechnungsaussteller, i.betrag_brutto,
                   i.status, i.assigned_to, i.approved_by, i.approved_at,
                   i.rejected_by, i.rejected_at, i.approval_comment,
                   i.payment_status, i.paid_at,
                   u_assigned.name as assigned_to_name,
                   u_approved.name as approved_by_name
            FROM invoices i
            LEFT JOIN users u_assigned ON i.assigned_to = u_assigned.id
            LEFT JOIN users u_approved ON i.approved_by = u_approved.id
            WHERE i.id = ?
        """, (invoice_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def update_status(self, invoice_id: int, new_status: str, user_id: int,
                      comment: str = None, ip_address: str = None,
                      user_agent: str = None) -> bool:
        """Aktualisiert den Status einer Rechnung mit Audit Trail"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Hole alten Status
        cursor.execute("SELECT status FROM invoices WHERE id = ?", (invoice_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        old_status = row['status']
        
        # Update Invoice
        now = datetime.now().isoformat()
        
        if new_status == InvoiceStatus.APPROVED:
            cursor.execute("""
                UPDATE invoices 
                SET status = ?, approved_by = ?, approved_at = ?, approval_comment = ?
                WHERE id = ?
            """, (new_status, user_id, now, comment, invoice_id))
        elif new_status == InvoiceStatus.REJECTED:
            cursor.execute("""
                UPDATE invoices 
                SET status = ?, rejected_by = ?, rejected_at = ?, approval_comment = ?
                WHERE id = ?
            """, (new_status, user_id, now, comment, invoice_id))
        else:
            cursor.execute("""
                UPDATE invoices SET status = ?, approval_comment = ? WHERE id = ?
            """, (new_status, comment, invoice_id))
        
        # Audit Trail
        action = ApprovalAction.APPROVED if new_status == InvoiceStatus.APPROVED else \
                 ApprovalAction.REJECTED if new_status == InvoiceStatus.REJECTED else \
                 ApprovalAction.ASSIGNED if new_status == InvoiceStatus.ASSIGNED else \
                 "status_change"
        
        cursor.execute("""
            INSERT INTO approval_history 
            (invoice_id, user_id, action, old_status, new_status, comment, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (invoice_id, user_id, action, old_status, new_status, comment, ip_address, user_agent))
        
        
        # Zentrales Audit Log  
        audit_action = AuditAction.INVOICE_UPDATED
        log_audit(audit_action, user_id=user_id, resource_type="invoice", resource_id=str(invoice_id),
                  details=f'{{"action": "{action}", "old_status": "{old_status}", "new_status": "{new_status}"}}',
                  ip_address=ip_address)
        
        conn.commit()
        conn.close()
        
        # Webhook für Approval Events
        try:
            from api_nexus import fire_webhook_event
            if new_status == "approved":
                fire_webhook_event("invoice.approved", {
                    "invoice_id": invoice_id,
                    "approved_by": user_id,
                    "comment": comment
                })
            elif new_status == "rejected":
                fire_webhook_event("invoice.rejected", {
                    "invoice_id": invoice_id,
                    "rejected_by": user_id,
                    "comment": comment
                })
        except:
            pass
        
        logger.info(f"Invoice {invoice_id} status changed: {old_status} -> {new_status} by user {user_id}")
        return True
    
    def assign_invoice(self, invoice_id: int, assignee_id: int, 
                       assigned_by: int, comment: str = None) -> bool:
        """Weist eine Rechnung einem Benutzer zur Freigabe zu"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE invoices 
            SET status = ?, assigned_to = ?
            WHERE id = ?
        """, (InvoiceStatus.ASSIGNED, assignee_id, invoice_id))
        
        # Audit
        cursor.execute("""
            INSERT INTO approval_history 
            (invoice_id, user_id, action, new_status, comment)
            VALUES (?, ?, ?, ?, ?)
        """, (invoice_id, assigned_by, ApprovalAction.ASSIGNED, 
              InvoiceStatus.ASSIGNED, f"Assigned to user {assignee_id}. {comment or ''}"))
        
        conn.commit()
        conn.close()
        return True
    
    # =========================================================================
    # APPROVAL RULES
    # =========================================================================
    
    def get_applicable_rule(self, amount: float, org_id: int = None) -> Optional[ApprovalRule]:
        """Findet die passende Freigabe-Regel für einen Betrag"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM approval_rules 
            WHERE is_active = 1 
            AND (org_id IS NULL OR org_id = ?)
            AND min_amount <= ?
            AND (max_amount IS NULL OR max_amount >= ?)
            ORDER BY priority DESC
            LIMIT 1
        """, (org_id, amount, amount))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ApprovalRule(
                id=row['id'],
                name=row['name'],
                min_amount=row['min_amount'],
                max_amount=row['max_amount'],
                required_role=row['required_role'],
                auto_approve=bool(row['auto_approve']),
                priority=row['priority']
            )
        return None
    
    def get_all_rules(self, org_id: int = None) -> List[Dict]:
        """Holt alle Freigabe-Regeln"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM approval_rules 
            WHERE org_id IS NULL OR org_id = ?
            ORDER BY min_amount ASC
        """, (org_id,))
        
        rules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rules
    
    def create_rule(self, name: str, min_amount: float, max_amount: Optional[float],
                    required_role: str, auto_approve: bool = False,
                    org_id: int = None, created_by: int = None) -> int:
        """Erstellt eine neue Freigabe-Regel"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO approval_rules 
            (org_id, name, min_amount, max_amount, required_role, auto_approve, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (org_id, name, min_amount, max_amount, required_role, 
              1 if auto_approve else 0, created_by))
        
        rule_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return rule_id
    
    def update_rule(self, rule_id: int, **kwargs) -> bool:
        """Aktualisiert eine Freigabe-Regel"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        allowed_fields = ['name', 'min_amount', 'max_amount', 'required_role', 
                          'auto_approve', 'is_active', 'priority']
        
        updates = []
        values = []
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if updates:
            values.append(rule_id)
            cursor.execute(f"""
                UPDATE approval_rules SET {', '.join(updates)} WHERE id = ?
            """, values)
            conn.commit()
        
        conn.close()
        return True
    
    def delete_rule(self, rule_id: int) -> bool:
        """Löscht eine Freigabe-Regel (soft delete)"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE approval_rules SET is_active = 0 WHERE id = ?", (rule_id,))
        conn.commit()
        conn.close()
        return True
    
    # =========================================================================
    # WORKFLOW AUTOMATION
    # =========================================================================
    
    def process_new_invoice(self, invoice_id: int, amount: float, 
                            org_id: int = None, created_by: int = None) -> Dict:
        """
        Verarbeitet eine neue Rechnung gemäß den Freigabe-Regeln.
        Returns: {'status': 'auto_approved'|'assigned'|'pending', 'assigned_to': user_id}
        """
        result = {'status': 'pending', 'assigned_to': None, 'rule': None}
        
        # Finde passende Regel
        rule = self.get_applicable_rule(amount, org_id)
        
        if not rule:
            # Keine Regel gefunden -> bleibt pending
            logger.warning(f"No approval rule found for invoice {invoice_id} with amount {amount}")
            return result
        
        result['rule'] = rule.name
        
        # Auto-Approve?
        if rule.auto_approve:
            self.update_status(invoice_id, InvoiceStatus.APPROVED, 
                              created_by or 0, "Auto-approved by rule")
            result['status'] = 'auto_approved'
            return result
        
        # Finde passenden Approver
        approver = self._find_approver(rule.required_role, org_id)
        
        if approver:
            self.assign_invoice(invoice_id, approver['id'], created_by or 0,
                              f"Auto-assigned by rule: {rule.name}")
            result['status'] = 'assigned'
            result['assigned_to'] = approver['id']
            result['assigned_to_name'] = approver['name']
        else:
            logger.warning(f"No approver found for role {rule.required_role}")
        
        return result
    
    def _find_approver(self, required_role: str, org_id: int = None) -> Optional[Dict]:
        """Findet einen verfügbaren Approver für eine Rolle"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Mapping von Rollen zu Bedingungen
        role_conditions = {
            'user': "can_approve = 1",
            'team_lead': "can_approve = 1 AND approval_limit >= 500",
            'manager': "can_approve = 1 AND approval_limit >= 2000",
            'cfo': "can_approve = 1 AND approval_limit >= 10000",
            'ceo': "can_approve = 1 AND approval_limit >= 50000",
            'admin': "is_admin = 1",
        }
        
        condition = role_conditions.get(required_role, "can_approve = 1")
        
        # Prüfe auf aktive Delegationen
        today = datetime.now().isoformat()
        
        cursor.execute(f"""
            SELECT u.id, u.name, u.email
            FROM users u
            WHERE u.is_active = 1 AND {condition}
            AND NOT EXISTS (
                SELECT 1 FROM approval_delegations d 
                WHERE d.delegator_id = u.id 
                AND d.is_active = 1
                AND d.valid_from <= ?
                AND d.valid_until >= ?
            )
            ORDER BY u.approval_limit ASC
            LIMIT 1
        """, (today, today))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    # =========================================================================
    # QUEUES & DASHBOARDS
    # =========================================================================
    
    def get_pending_approvals(self, user_id: int) -> List[Dict]:
        """Holt alle Rechnungen, die auf Freigabe durch einen User warten"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.*, 
                   u_created.name as created_by_name,
                   j.filename as pdf_filename
            FROM invoices i
            LEFT JOIN users u_created ON i.assigned_to = u_created.id
            LEFT JOIN jobs j ON i.job_id = j.job_id
            WHERE i.assigned_to = ?
            AND i.status IN ('assigned', 'in_review')
            ORDER BY i.created_at DESC
        """, (user_id,))
        
        invoices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return invoices
    
    def get_approval_queue(self, user_id: int = None, status: str = None,
                           limit: int = 50, offset: int = 0) -> Tuple[List[Dict], int]:
        """Holt die Freigabe-Queue mit Filtern"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Build query
        where_clauses = []
        params = []
        
        if user_id:
            where_clauses.append("j.user_id = ?")
            params.append(user_id)
        
        if status:
            where_clauses.append("i.status = ?")
            params.append(status)
        else:
            where_clauses.append("i.status IN ('pending', 'assigned', 'in_review')")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Count
        cursor.execute(f"SELECT COUNT(*) FROM invoices i JOIN jobs j ON i.job_id = j.job_id WHERE {where_sql}", params)
        total = cursor.fetchone()[0]
        
        # Data
        cursor.execute(f"""
            SELECT i.*, 
                   u_assigned.name as assigned_to_name,
                   u_approved.name as approved_by_name
            FROM invoices i
            JOIN jobs j ON i.job_id = j.job_id
            LEFT JOIN users u_assigned ON i.assigned_to = u_assigned.id
            LEFT JOIN users u_approved ON i.approved_by = u_approved.id
            WHERE {where_sql}
            ORDER BY 
                CASE i.status 
                    WHEN 'pending' THEN 1 
                    WHEN 'assigned' THEN 2 
                    WHEN 'in_review' THEN 3 
                    ELSE 4 
                END,
                i.betrag_brutto DESC,
                i.created_at ASC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        
        invoices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return invoices, total
    
    def get_approval_stats(self, user_id: int = None, days: int = 30) -> Dict:
        """Holt Statistiken für das Approval Dashboard"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        stats = {}
        
        # Counts by status (filtered by user)
        if user_id:
            cursor.execute("""
                SELECT i.status, COUNT(*) as count, SUM(i.betrag_brutto) as total
                FROM invoices i
                JOIN jobs j ON i.job_id = j.job_id
                WHERE i.created_at >= ? AND j.user_id = ?
                GROUP BY i.status
            """, (since, user_id))
        else:
            cursor.execute("""
                SELECT status, COUNT(*) as count, SUM(betrag_brutto) as total
                FROM invoices
                WHERE created_at >= ?
                GROUP BY status
            """, (since,))
        
        stats['by_status'] = {row['status']: {'count': row['count'], 'total': row['total'] or 0} 
                             for row in cursor.fetchall()}
        
        # Pending count (filtered by user)
        if user_id:
            cursor.execute("""
                SELECT COUNT(*) FROM invoices i
                JOIN jobs j ON i.job_id = j.job_id
                WHERE i.status IN ('pending', 'assigned', 'in_review') AND j.user_id = ?
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM invoices 
                WHERE status IN ('pending', 'assigned', 'in_review')
            """)
        stats['pending_count'] = cursor.fetchone()[0]
        
        # Average approval time (filtered by user)
        if user_id:
            cursor.execute("""
                SELECT AVG(julianday(i.approved_at) - julianday(i.created_at)) as avg_days
                FROM invoices i
                JOIN jobs j ON i.job_id = j.job_id
                WHERE i.status = 'approved' AND i.approved_at IS NOT NULL AND i.created_at >= ? AND j.user_id = ?
            """, (since, user_id))
        else:
            cursor.execute("""
                SELECT AVG(julianday(approved_at) - julianday(created_at)) as avg_days
                FROM invoices
                WHERE status = 'approved' AND approved_at IS NOT NULL AND created_at >= ?
            """, (since,))
        row = cursor.fetchone()
        stats['avg_approval_days'] = round(row['avg_days'] or 0, 1)
        
        # Top approvers
        if not user_id:
            cursor.execute("""
                SELECT u.name, COUNT(*) as approved_count
                FROM invoices i
                JOIN users u ON i.approved_by = u.id
                WHERE i.approved_at >= ?
                GROUP BY i.approved_by
                ORDER BY approved_count DESC
                LIMIT 5
            """, (since,))
            stats['top_approvers'] = [dict(row) for row in cursor.fetchall()]
        
        # Overdue invoices
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) FROM invoices 
            WHERE faelligkeitsdatum < ? 
            AND payment_status != 'paid'
            AND status = 'approved'
        """, (today,))
        stats['overdue_count'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    # =========================================================================
    # AUDIT & HISTORY
    # =========================================================================
    
    def get_invoice_history(self, invoice_id: int) -> List[Dict]:
        """Holt die komplette Historie einer Rechnung"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT h.*, u.name as user_name, u.email as user_email
            FROM approval_history h
            LEFT JOIN users u ON h.user_id = u.id
            WHERE h.invoice_id = ?
            ORDER BY h.created_at ASC
        """, (invoice_id,))
        
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return history
    
    def add_comment(self, invoice_id: int, user_id: int, comment: str,
                    ip_address: str = None) -> bool:
        """Fügt einen Kommentar zu einer Rechnung hinzu"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO approval_history 
            (invoice_id, user_id, action, comment, ip_address)
            VALUES (?, ?, ?, ?, ?)
        """, (invoice_id, user_id, ApprovalAction.COMMENTED, comment, ip_address))
        
        conn.commit()
        conn.close()
        return True
    
    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================
    
    def bulk_approve(self, invoice_ids: List[int], user_id: int, 
                     comment: str = None) -> Dict:
        """Genehmigt mehrere Rechnungen auf einmal"""
        results = {'approved': [], 'failed': []}
        
        for inv_id in invoice_ids:
            try:
                if self.can_user_approve(user_id, inv_id):
                    self.update_status(inv_id, InvoiceStatus.APPROVED, user_id, comment)
                    results['approved'].append(inv_id)
                else:
                    results['failed'].append({'id': inv_id, 'reason': 'No permission'})
            except Exception as e:
                results['failed'].append({'id': inv_id, 'reason': str(e)})
        
        return results
    
    def can_user_approve(self, user_id: int, invoice_id: int) -> bool:
        """Prüft ob ein User eine Rechnung genehmigen darf"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute("""
            SELECT is_admin, can_approve, approval_limit 
            FROM users WHERE id = ?
        """, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return False
        
        # Admin kann alles
        if user['is_admin']:
            conn.close()
            return True
        
        # Kann nicht genehmigen?
        if not user['can_approve']:
            conn.close()
            return False
        
        # Check amount against limit
        cursor.execute("SELECT betrag_brutto FROM invoices WHERE id = ?", (invoice_id,))
        invoice = cursor.fetchone()
        
        if not invoice:
            conn.close()
            return False
        
        conn.close()
        return invoice['betrag_brutto'] <= user['approval_limit']


# Singleton instance
_approval_manager = None

def get_approval_manager(db_path: str = "invoices.db") -> ApprovalManager:
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager(db_path)
    return _approval_manager
