"""User Management Service — Registration, Authentication, Tenant Isolation."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from shared.db.session import get_session
from modules.rechnungsverarbeitung.src.auth.jwt_auth import (
    hash_password, verify_password, create_tokens, TokenResponse,
)

logger = logging.getLogger(__name__)


class UserService:
    """Manages user registration, authentication, and tenant assignment."""

    def register(self, email: str, password: str, name: str, company: str = "") -> dict[str, Any]:
        """Register a new user and create their tenant."""
        with get_session() as s:
            existing = s.execute(
                text("SELECT id FROM users WHERE email = :e"), {"e": email.lower()}
            ).fetchone()
            if existing:
                raise ValueError("E-Mail bereits registriert")

            user_id = str(uuid.uuid4())
            tenant_id = f"tenant-{user_id[:8]}"

            s.execute(text("""
                INSERT INTO users (id, email, password_hash, name, company, tenant_id, role, created_at)
                VALUES (:id, :email, :pw, :name, :company, :tid, :role, :now)
            """), {
                "id": user_id,
                "email": email.lower().strip(),
                "pw": hash_password(password),
                "name": name.strip(),
                "company": company.strip(),
                "tid": tenant_id,
                "role": "admin",
                "now": datetime.utcnow(),
            })
            s.commit()

        logger.info(f"user_registered: {email} tenant={tenant_id}")
        return {"user_id": user_id, "tenant_id": tenant_id, "email": email.lower(), "name": name, "role": "admin"}

    def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate user and return tokens."""
        with get_session() as s:
            row = s.execute(
                text("SELECT id, email, password_hash, name, company, tenant_id, role FROM users WHERE email = :e"),
                {"e": email.lower().strip()},
            ).fetchone()

        if not row:
            raise ValueError("Ungueltige Anmeldedaten")
        if not verify_password(password, row[2]):
            raise ValueError("Ungueltige Anmeldedaten")

        tokens = create_tokens(user_id=row[0], tenant_id=row[5], role=row[6])
        return {
            "tokens": tokens,
            "user": {"id": row[0], "email": row[1], "name": row[3], "company": row[4], "tenant_id": row[5], "role": row[6]},
        }

    def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        """Get user profile."""
        with get_session() as s:
            row = s.execute(
                text("SELECT id, email, name, company, tenant_id, role, created_at FROM users WHERE id = :id"),
                {"id": user_id},
            ).fetchone()
        if not row:
            return None
        return {"id": row[0], "email": row[1], "name": row[2], "company": row[3], "tenant_id": row[4], "role": row[5], "created_at": row[6].isoformat() if row[6] else None}

    def list_users(self, tenant_id: str) -> list[dict[str, Any]]:
        """List all users in a tenant."""
        with get_session() as s:
            rows = s.execute(
                text("SELECT id, email, name, role, created_at FROM users WHERE tenant_id = :t ORDER BY created_at"),
                {"t": tenant_id},
            ).fetchall()
        return [{"id": r[0], "email": r[1], "name": r[2], "role": r[3], "created_at": r[4].isoformat() if r[4] else None} for r in rows]

    def invite_user(self, email: str, password: str, name: str, tenant_id: str, role: str = "user") -> dict[str, Any]:
        """Invite a user to an existing tenant."""
        with get_session() as s:
            existing = s.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email.lower()}).fetchone()
            if existing:
                raise ValueError("E-Mail bereits registriert")

            user_id = str(uuid.uuid4())
            s.execute(text("""
                INSERT INTO users (id, email, password_hash, name, company, tenant_id, role, created_at)
                VALUES (:id, :email, :pw, :name, '', :tid, :role, :now)
            """), {
                "id": user_id, "email": email.lower().strip(), "pw": hash_password(password),
                "name": name.strip(), "tid": tenant_id, "role": role, "now": datetime.utcnow(),
            })
            s.commit()
        return {"user_id": user_id, "tenant_id": tenant_id, "email": email.lower(), "role": role}

    VALID_ROLES = {"admin", "editor", "viewer"}

    def update_role(self, admin_tenant_id: str, target_user_id: str, new_role: str) -> dict[str, Any]:
        """Update a user's role. Only admins can do this."""
        if new_role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role: {new_role}. Valid: {', '.join(self.VALID_ROLES)}")

        with get_session() as s:
            target = s.execute(
                text("SELECT id, tenant_id, role FROM users WHERE id = :id"),
                {"id": target_user_id},
            ).fetchone()

            if not target:
                raise ValueError("User not found")
            if target[1] != admin_tenant_id:
                raise ValueError("Cannot modify users from other tenants")

            s.execute(
                text("UPDATE users SET role = :role, updated_at = :now WHERE id = :id"),
                {"role": new_role, "id": target_user_id, "now": datetime.utcnow()},
            )
            s.commit()

        return {"user_id": target_user_id, "new_role": new_role}

    def delete_user(self, admin_tenant_id: str, target_user_id: str) -> dict[str, Any]:
        """Remove a user from tenant. Only admins can do this."""
        with get_session() as s:
            target = s.execute(
                text("SELECT id, email, tenant_id, role FROM users WHERE id = :id"),
                {"id": target_user_id},
            ).fetchone()

            if not target:
                raise ValueError("User not found")
            if target[2] != admin_tenant_id:
                raise ValueError("Cannot delete users from other tenants")
            if target[3] == "admin":
                admin_count = s.execute(
                    text("SELECT COUNT(*) FROM users WHERE tenant_id = :t AND role = 'admin'"),
                    {"t": admin_tenant_id},
                ).scalar()
                if admin_count <= 1:
                    raise ValueError("Cannot delete the last admin")

            s.execute(text("DELETE FROM users WHERE id = :id"), {"id": target_user_id})
            s.commit()

        return {"deleted": target_user_id, "email": target[1]}
