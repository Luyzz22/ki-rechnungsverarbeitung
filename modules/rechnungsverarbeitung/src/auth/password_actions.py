"""Credential-bound password action workflows for invites and resets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text

from shared.db.session import get_session
from modules.rechnungsverarbeitung.src.auth.jwt_auth import (
    create_password_action_token,
    decode_password_action_token,
    hash_password,
    password_action_matches_current_credential,
)
from modules.rechnungsverarbeitung.src.invoices.services.user_service import (
    validate_password_strength,
)


@dataclass(frozen=True)
class PasswordActionIssue:
    user_id: str
    tenant_id: str
    email: str
    token: str
    purpose: str


class PasswordActionService:
    """Issue and consume short-lived, credential-bound password actions."""

    def issue_for_email(self, email: str, purpose: str) -> Optional[PasswordActionIssue]:
        normalized_email = email.lower().strip()
        with get_session() as session:
            row = session.execute(
                text(
                    "SELECT id, tenant_id, email, password_hash "
                    "FROM users WHERE email = :email"
                ),
                {"email": normalized_email},
            ).fetchone()

        if not row:
            return None

        token = create_password_action_token(
            user_id=str(row[0]),
            tenant_id=str(row[1]),
            password_hash=str(row[3]),
            purpose=purpose,
        )
        return PasswordActionIssue(
            user_id=str(row[0]),
            tenant_id=str(row[1]),
            email=str(row[2]),
            token=token,
            purpose=purpose,
        )

    def consume(self, token: str, new_password: str, purpose: str) -> dict[str, str]:
        """Atomically replace the password exactly once for the token's current credential."""
        validate_password_strength(new_password)
        payload = decode_password_action_token(token, purpose)
        user_id = str(payload["sub"])
        tenant_id = str(payload["tenant_id"])

        with get_session() as session:
            row = session.execute(
                text(
                    "SELECT password_hash FROM users "
                    "WHERE id = :user_id AND tenant_id = :tenant_id"
                ),
                {"user_id": user_id, "tenant_id": tenant_id},
            ).fetchone()
            if not row or not password_action_matches_current_credential(payload, str(row[0])):
                raise ValueError("Password action token is invalid or already used")

            old_hash = str(row[0])
            new_hash = hash_password(new_password)
            result = session.execute(
                text(
                    "UPDATE users SET password_hash = :new_hash, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = :user_id AND tenant_id = :tenant_id "
                    "AND password_hash = :old_hash"
                ),
                {
                    "new_hash": new_hash,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "old_hash": old_hash,
                },
            )
            if result.rowcount != 1:
                session.rollback()
                raise ValueError("Password action token is invalid or already used")
            session.commit()

        return {"user_id": user_id, "tenant_id": tenant_id, "status": "password_updated"}
