#!/usr/bin/env python3
"""
SBS Deutschland – Multi-Tenancy / Organizations
Verwaltet Mandanten und Benutzer-Zuordnungen.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from database import get_connection

logger = logging.getLogger(__name__)


# Rollen in einer Organisation
class OrgRole:
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


def create_organization(name: str, owner_user_id: int, plan: str = "free") -> Dict:
    """Erstellt eine neue Organisation."""
    import re
    
    # Slug generieren
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Prüfen ob Slug existiert
    cursor.execute("SELECT id FROM organizations WHERE slug = ?", (slug,))
    if cursor.fetchone():
        # Suffix hinzufügen
        import random
        slug = f"{slug}-{random.randint(1000, 9999)}"
    
    cursor.execute("""
        INSERT INTO organizations (name, slug, plan)
        VALUES (?, ?, ?)
    """, (name, slug, plan))
    
    org_id = cursor.lastrowid
    
    # Owner als Mitglied hinzufügen
    cursor.execute("""
        INSERT INTO org_members (org_id, user_id, role)
        VALUES (?, ?, ?)
    """, (org_id, owner_user_id, OrgRole.OWNER))
    
    # User's aktuelle Org setzen
    cursor.execute("UPDATE users SET current_org_id = ? WHERE id = ?", (org_id, owner_user_id))
    
    conn.commit()
    conn.close()
    
    logger.info(f"Organisation erstellt: {name} (ID: {org_id})")
    
    return {
        "id": org_id,
        "name": name,
        "slug": slug,
        "plan": plan
    }


def get_organization(org_id: int) -> Optional[Dict]:
    """Holt Organisation nach ID."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM organizations WHERE id = ?", (org_id,))
    org = cursor.fetchone()
    conn.close()
    
    return org


def get_user_organizations(user_id: int) -> List[Dict]:
    """Holt alle Organisationen eines Users."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.*, om.role
        FROM organizations o
        JOIN org_members om ON o.id = om.org_id
        WHERE om.user_id = ?
        ORDER BY o.name
    """, (user_id,))
    
    orgs = cursor.fetchall()
    conn.close()
    
    return orgs


def add_member(org_id: int, user_id: int, role: str = OrgRole.MEMBER) -> bool:
    """Fügt Mitglied zur Organisation hinzu."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO org_members (org_id, user_id, role)
            VALUES (?, ?, ?)
        """, (org_id, user_id, role))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen: {e}")
        conn.close()
        return False


def remove_member(org_id: int, user_id: int) -> bool:
    """Entfernt Mitglied aus Organisation."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Owner kann nicht entfernt werden
    cursor.execute("""
        SELECT role FROM org_members WHERE org_id = ? AND user_id = ?
    """, (org_id, user_id))
    row = cursor.fetchone()
    
    if row and row[0] == OrgRole.OWNER:
        conn.close()
        return False
    
    cursor.execute("""
        DELETE FROM org_members WHERE org_id = ? AND user_id = ?
    """, (org_id, user_id))
    
    conn.commit()
    conn.close()
    return True


def update_member_role(org_id: int, user_id: int, new_role: str) -> bool:
    """Aktualisiert Rolle eines Mitglieds."""
    if new_role not in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.MEMBER, OrgRole.VIEWER]:
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE org_members SET role = ? WHERE org_id = ? AND user_id = ?
    """, (new_role, org_id, user_id))
    
    conn.commit()
    conn.close()
    return True


def get_org_members(org_id: int) -> List[Dict]:
    """Holt alle Mitglieder einer Organisation."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.id, u.name, u.email, om.role, om.joined_at
        FROM users u
        JOIN org_members om ON u.id = om.user_id
        WHERE om.org_id = ?
        ORDER BY om.role, u.name
    """, (org_id,))
    
    members = cursor.fetchall()
    conn.close()
    
    return members


def switch_organization(user_id: int, org_id: int) -> bool:
    """Wechselt die aktive Organisation eines Users."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Prüfen ob User Mitglied ist
    cursor.execute("""
        SELECT 1 FROM org_members WHERE org_id = ? AND user_id = ?
    """, (org_id, user_id))
    
    if not cursor.fetchone():
        conn.close()
        return False
    
    cursor.execute("UPDATE users SET current_org_id = ? WHERE id = ?", (org_id, user_id))
    conn.commit()
    conn.close()
    
    return True


def get_current_org(user_id: int) -> Optional[Dict]:
    """Holt aktuelle Organisation des Users."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.*, om.role as user_role
        FROM users u
        JOIN organizations o ON u.current_org_id = o.id
        JOIN org_members om ON o.id = om.org_id AND om.user_id = u.id
        WHERE u.id = ?
    """, (user_id,))
    
    org = cursor.fetchone()
    conn.close()
    
    return org


def check_permission(user_id: int, org_id: int, required_role: str = OrgRole.MEMBER) -> bool:
    """Prüft ob User die erforderliche Rolle hat."""
    role_hierarchy = {
        OrgRole.VIEWER: 0,
        OrgRole.MEMBER: 1,
        OrgRole.ADMIN: 2,
        OrgRole.OWNER: 3
    }
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role FROM org_members WHERE org_id = ? AND user_id = ?
    """, (org_id, user_id))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False
    
    user_role = row[0]
    return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)


def get_org_stats(org_id: int) -> Dict:
    """Holt Statistiken einer Organisation."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Mitglieder zählen
    cursor.execute("SELECT COUNT(*) FROM org_members WHERE org_id = ?", (org_id,))
    member_count = cursor.fetchone()[0]
    
    # Jobs zählen (wenn org_id in jobs existiert)
    cursor.execute("""
        SELECT COUNT(*) FROM jobs j
        JOIN org_members om ON j.user_id = om.user_id
        WHERE om.org_id = ?
    """, (org_id,))
    job_count = cursor.fetchone()[0]
    
    # Rechnungen zählen
    cursor.execute("""
        SELECT COUNT(*) FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        JOIN org_members om ON j.user_id = om.user_id
        WHERE om.org_id = ?
    """, (org_id,))
    invoice_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "members": member_count,
        "jobs": job_count,
        "invoices": invoice_count
    }
