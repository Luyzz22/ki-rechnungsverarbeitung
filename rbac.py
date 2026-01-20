#!/usr/bin/env python3
"""
SBS Deutschland – Role-Based Access Control (RBAC)
Enterprise-grade Berechtigungssystem
"""

import json
import logging
from functools import wraps
from typing import Optional, List, Dict, Set
from database import get_connection

logger = logging.getLogger(__name__)

# ============================================================
# PERMISSION DEFINITIONS
# ============================================================

class Permission:
    """Alle verfügbaren Permissions im System"""
    # Invoices
    INVOICE_UPLOAD = "invoice.upload"
    INVOICE_VIEW = "invoice.view"
    INVOICE_EDIT = "invoice.edit"
    INVOICE_DELETE = "invoice.delete"
    INVOICE_APPROVE = "invoice.approve"
    
    # Export
    EXPORT_CSV = "export.csv"
    EXPORT_EXCEL = "export.excel"
    EXPORT_DATEV = "export.datev"
    EXPORT_SEPA = "export.sepa"
    
    # Analytics & Reports
    ANALYTICS_VIEW = "analytics.view"
    REPORTS_CREATE = "reports.create"
    
    # Finance
    BUDGET_VIEW = "budget.view"
    BUDGET_EDIT = "budget.edit"
    PAYMENTS_VIEW = "payments.view"
    PAYMENTS_MANAGE = "payments.manage"
    
    # Admin
    USERS_VIEW = "users.view"
    USERS_MANAGE = "users.manage"
    ROLES_MANAGE = "roles.manage"
    SETTINGS_VIEW = "settings.view"
    SETTINGS_MANAGE = "settings.manage"
    AUDIT_VIEW = "audit.view"
    BILLING_MANAGE = "billing.manage"
    
    # All permission
    ALL = "all"


# Default Role Permissions
DEFAULT_ROLE_PERMISSIONS = {
    "owner": {
        "all": True  # Full access including billing
    },
    "admin": {
        "permissions": [
            Permission.INVOICE_UPLOAD, Permission.INVOICE_VIEW, Permission.INVOICE_EDIT,
            Permission.INVOICE_DELETE, Permission.INVOICE_APPROVE,
            Permission.EXPORT_CSV, Permission.EXPORT_EXCEL, Permission.EXPORT_DATEV, Permission.EXPORT_SEPA,
            Permission.ANALYTICS_VIEW, Permission.REPORTS_CREATE,
            Permission.BUDGET_VIEW, Permission.BUDGET_EDIT,
            Permission.PAYMENTS_VIEW, Permission.PAYMENTS_MANAGE,
            Permission.USERS_VIEW, Permission.USERS_MANAGE, Permission.ROLES_MANAGE,
            Permission.SETTINGS_VIEW, Permission.SETTINGS_MANAGE,
            Permission.AUDIT_VIEW
        ]
    },
    "manager": {
        "permissions": [
            Permission.INVOICE_UPLOAD, Permission.INVOICE_VIEW, Permission.INVOICE_EDIT,
            Permission.INVOICE_APPROVE,
            Permission.EXPORT_CSV, Permission.EXPORT_EXCEL, Permission.EXPORT_DATEV,
            Permission.ANALYTICS_VIEW, Permission.REPORTS_CREATE,
            Permission.BUDGET_VIEW,
            Permission.PAYMENTS_VIEW,
            Permission.USERS_VIEW
        ]
    },
    "member": {
        "permissions": [
            Permission.INVOICE_UPLOAD, Permission.INVOICE_VIEW, Permission.INVOICE_EDIT,
            Permission.EXPORT_CSV, Permission.EXPORT_EXCEL,
            Permission.ANALYTICS_VIEW,
            Permission.BUDGET_VIEW,
            Permission.PAYMENTS_VIEW
        ]
    },
    "viewer": {
        "permissions": [
            Permission.INVOICE_VIEW,
            Permission.ANALYTICS_VIEW,
            Permission.BUDGET_VIEW
        ]
    }
}


# ============================================================
# CORE FUNCTIONS
# ============================================================

def get_user_roles(user_id: int) -> List[Dict]:
    """Holt alle Rollen eines Users"""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.id, r.name, r.display_name, r.permissions, r.color
        FROM roles r
        JOIN user_roles ur ON r.id = ur.role_id
        WHERE ur.user_id = ?
    """, (user_id,))
    
    roles = cursor.fetchall()
    conn.close()
    
    return roles


def get_user_permissions(user_id: int) -> Set[str]:
    """Sammelt alle Permissions eines Users aus allen seinen Rollen"""
    roles = get_user_roles(user_id)
    permissions = set()
    
    for role in roles:
        perms_raw = role.get('permissions', '{}')
        
        # Parse JSON permissions
        try:
            if isinstance(perms_raw, str):
                perms = json.loads(perms_raw)
            else:
                perms = perms_raw
        except json.JSONDecodeError:
            perms = {}
        
        # Check for "all" access
        if perms.get('all') == True:
            permissions.add(Permission.ALL)
            return permissions  # All = everything
        
        # Add individual permissions
        if isinstance(perms, dict):
            # Legacy format: {"upload": true, "analytics": true}
            for key, value in perms.items():
                if value == True:
                    permissions.add(key)
                    # Map legacy to new format
                    legacy_mapping = {
                        'upload': Permission.INVOICE_UPLOAD,
                        'history': Permission.INVOICE_VIEW,
                        'analytics': Permission.ANALYTICS_VIEW,
                        'export': Permission.EXPORT_DATEV,
                        'accounting': Permission.INVOICE_EDIT,
                    }
                    if key in legacy_mapping:
                        permissions.add(legacy_mapping[key])
        
        elif isinstance(perms, list):
            # New format: ["invoice.upload", "invoice.view"]
            permissions.update(perms)
    
    return permissions


def has_permission(user_id: int, permission: str) -> bool:
    """Prüft ob User eine bestimmte Permission hat"""
    # Fallback: Prüfe is_admin Flag
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0]:  # is_admin = True
        return True
    
    # Check RBAC permissions
    user_permissions = get_user_permissions(user_id)
    
    # "all" grants everything
    if Permission.ALL in user_permissions:
        return True
    
    return permission in user_permissions


def has_any_permission(user_id: int, permissions: List[str]) -> bool:
    """Prüft ob User mindestens eine der Permissions hat"""
    return any(has_permission(user_id, p) for p in permissions)


def has_all_permissions(user_id: int, permissions: List[str]) -> bool:
    """Prüft ob User alle Permissions hat"""
    return all(has_permission(user_id, p) for p in permissions)


def get_user_role_names(user_id: int) -> List[str]:
    """Gibt Liste der Rollennamen zurück"""
    roles = get_user_roles(user_id)
    return [r['name'] for r in roles]


def is_admin_or_owner(user_id: int) -> bool:
    """Prüft ob User Admin oder Owner ist"""
    role_names = get_user_role_names(user_id)
    return 'admin' in role_names or 'owner' in role_names or has_permission(user_id, Permission.ALL)


# ============================================================
# ROLE MANAGEMENT
# ============================================================

def assign_role(user_id: int, role_name: str, assigned_by: int = None) -> bool:
    """Weist einem User eine Rolle zu"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get role_id
    cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
    role = cursor.fetchone()
    if not role:
        conn.close()
        logger.error(f"Role {role_name} not found")
        return False
    
    role_id = role[0]
    
    # Check if already assigned
    cursor.execute("SELECT id FROM user_roles WHERE user_id = ? AND role_id = ?", (user_id, role_id))
    if cursor.fetchone():
        conn.close()
        return True  # Already has role
    
    # Assign
    cursor.execute("""
        INSERT INTO user_roles (user_id, role_id, assigned_by)
        VALUES (?, ?, ?)
    """, (user_id, role_id, assigned_by))
    
    conn.commit()
    conn.close()
    
    logger.info(f"Assigned role {role_name} to user {user_id}")
    return True


def remove_role(user_id: int, role_name: str) -> bool:
    """Entfernt eine Rolle von einem User"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM user_roles 
        WHERE user_id = ? AND role_id = (SELECT id FROM roles WHERE name = ?)
    """, (user_id, role_name))
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0


def ensure_default_role(user_id: int):
    """Stellt sicher dass User mindestens 'member' Rolle hat"""
    roles = get_user_roles(user_id)
    if not roles:
        assign_role(user_id, 'member')


# ============================================================
# INITIALIZATION
# ============================================================

def init_rbac_tables():
    """Initialisiert RBAC Tabellen und Standard-Rollen"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Füge fehlende Rollen hinzu
    default_roles = [
        ('owner', 'Owner', 'Vollzugriff inkl. Abrechnung', '{"all": true}', '#7C3AED'),
        ('admin', 'Admin', 'Vollzugriff auf alle Funktionen', '{"all": true}', '#EF4444'),
        ('manager', 'Manager', 'Freigaben, Exporte, Reports', '{"upload": true, "analytics": true, "export": true, "approve": true}', '#F59E0B'),
        ('member', 'Mitarbeiter', 'Upload, Bearbeitung, Ansicht', '{"upload": true, "history": true, "analytics": true}', '#22C55E'),
        ('viewer', 'Viewer', 'Nur Lesezugriff', '{"history": true, "analytics": true}', '#3B82F6'),
    ]
    
    for name, display, desc, perms, color in default_roles:
        cursor.execute("""
            INSERT OR IGNORE INTO roles (name, display_name, description, permissions, color)
            VALUES (?, ?, ?, ?, ?)
        """, (name, display, desc, perms, color))
    
    conn.commit()
    conn.close()
    logger.info("RBAC tables initialized")


# Initialize on import
try:
    init_rbac_tables()
except Exception as e:
    logger.warning(f"RBAC init warning: {e}")


# ============================================================
# ROUTE DECORATORS (für FastAPI)
# ============================================================

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

def require_permission(permission: str, redirect_on_fail: str = None):
    """
    Decorator für FastAPI Routes - prüft Permission.
    
    Usage:
        @app.get("/datev")
        @require_permission(Permission.EXPORT_DATEV)
        async def datev_page(request: Request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_id = request.session.get("user_id")
            
            if not user_id:
                if redirect_on_fail:
                    return RedirectResponse(redirect_on_fail, status_code=303)
                raise HTTPException(status_code=401, detail="Nicht angemeldet")
            
            if not has_permission(user_id, permission):
                if redirect_on_fail:
                    return RedirectResponse(redirect_on_fail, status_code=303)
                raise HTTPException(
                    status_code=403, 
                    detail=f"Keine Berechtigung: {permission}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions):
    """Decorator - User braucht mindestens eine der Permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_id = request.session.get("user_id")
            
            if not user_id:
                raise HTTPException(status_code=401, detail="Nicht angemeldet")
            
            if not has_any_permission(user_id, list(permissions)):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Keine Berechtigung für diese Aktion"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_admin():
    """Decorator - nur für Admins/Owner"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_id = request.session.get("user_id")
            
            if not user_id:
                raise HTTPException(status_code=401, detail="Nicht angemeldet")
            
            if not is_admin_or_owner(user_id):
                raise HTTPException(status_code=403, detail="Admin-Berechtigung erforderlich")
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# HELPER FÜR TEMPLATES
# ============================================================

def get_user_permissions_for_template(user_id: int) -> Dict:
    """
    Gibt Permission-Dict für Templates zurück.
    
    Usage in Jinja2:
        {% if perms.can_approve %}
            <button>Freigeben</button>
        {% endif %}
    """
    if not user_id:
        return {"is_authenticated": False}
    
    permissions = get_user_permissions(user_id)
    is_all = Permission.ALL in permissions
    
    return {
        "is_authenticated": True,
        "is_admin": is_all or is_admin_or_owner(user_id),
        "can_upload": is_all or Permission.INVOICE_UPLOAD in permissions or 'upload' in permissions,
        "can_edit": is_all or Permission.INVOICE_EDIT in permissions,
        "can_delete": is_all or Permission.INVOICE_DELETE in permissions,
        "can_approve": is_all or Permission.INVOICE_APPROVE in permissions or 'approve' in permissions,
        "can_export_datev": is_all or Permission.EXPORT_DATEV in permissions or 'export' in permissions,
        "can_export_sepa": is_all or Permission.EXPORT_SEPA in permissions,
        "can_view_analytics": is_all or Permission.ANALYTICS_VIEW in permissions or 'analytics' in permissions,
        "can_view_budget": is_all or Permission.BUDGET_VIEW in permissions,
        "can_edit_budget": is_all or Permission.BUDGET_EDIT in permissions,
        "can_manage_users": is_all or Permission.USERS_MANAGE in permissions,
        "can_view_audit": is_all or Permission.AUDIT_VIEW in permissions,
        "can_manage_billing": is_all or Permission.BILLING_MANAGE in permissions,
        "roles": get_user_role_names(user_id),
        "raw_permissions": list(permissions)
    }
