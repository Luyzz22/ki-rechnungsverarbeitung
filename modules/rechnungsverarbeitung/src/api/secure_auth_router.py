"""Secure authentication, invite and password-action routes.

This router replaces legacy credential-disclosure flows with DB-backed login,
short-lived credential-bound action tokens and one-time password setup/reset.
It is intentionally kept separate from the oversized legacy API module so the
security boundary can be regression-tested before route cutover.
"""
from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from modules.rechnungsverarbeitung.src.auth.jwt_auth import (
    TokenResponse,
    UserAuth,
    get_current_user,
)
from modules.rechnungsverarbeitung.src.auth.password_actions import (
    PasswordActionService,
)
from modules.rechnungsverarbeitung.src.auth.rate_limiter import limiter
from modules.rechnungsverarbeitung.src.invoices.services.email_notifications import (
    EmailService,
)
from modules.rechnungsverarbeitung.src.invoices.services.user_service import (
    UserService,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"])

_user_service = UserService()
_password_actions = PasswordActionService()
_email_service = EmailService()

_GENERIC_RECOVERY_MESSAGE = "Falls ein Konto existiert, wird eine E-Mail gesendet."


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictModel):
    email: str
    password: str


class ForgotPasswordRequest(StrictModel):
    email: str


class PasswordActionRequest(StrictModel):
    token: str
    new_password: str


class InviteRequest(StrictModel):
    email: str
    name: str
    role: str = "editor"


@router.post("/auth/token", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest) -> TokenResponse:
    """Authenticate against the user database; no static/demo credentials."""
    del request
    try:
        result = _user_service.login(email=body.email, password=body.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from exc
    return result["tokens"]


@router.post("/auth/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest) -> dict[str, str]:
    """Issue a reset link without modifying the current password."""
    del request
    issue = _password_actions.issue_for_email(body.email, "password_reset")
    if issue is not None:
        _email_service.send_password_reset(
            to_email=issue.email,
            action_token=issue.token,
        )
    # Identical response for known and unknown accounts to avoid enumeration.
    return {"message": _GENERIC_RECOVERY_MESSAGE}


@router.post("/auth/reset-password")
@limiter.limit("10/minute")
async def reset_password(request: Request, body: PasswordActionRequest) -> dict[str, str]:
    """Consume a one-time password reset action."""
    del request
    try:
        _password_actions.consume(
            token=body.token,
            new_password=body.new_password,
            purpose="password_reset",
        )
    except (ValueError, HTTPException) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is invalid or expired",
        ) from exc
    return {"status": "password_updated"}


@router.post("/auth/accept-invite")
@limiter.limit("10/minute")
async def accept_invite(request: Request, body: PasswordActionRequest) -> dict[str, str]:
    """Consume a one-time invite action and let the invitee choose the password."""
    del request
    try:
        _password_actions.consume(
            token=body.token,
            new_password=body.new_password,
            purpose="invite_accept",
        )
    except (ValueError, HTTPException) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite token is invalid or expired",
        ) from exc
    return {"status": "password_updated"}


@router.post("/users/invite", tags=["RBAC"])
async def invite_team_member(
    body: InviteRequest,
    user: UserAuth = Depends(get_current_user),
) -> dict:
    """Create an invitee with an undisclosed bootstrap credential and send an action link."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    # This high-entropy bootstrap value is only used to establish a credential
    # binding for the action token. It is never returned, logged or emailed.
    bootstrap_secret = secrets.token_urlsafe(32)
    try:
        result = _user_service.invite_user(
            email=body.email,
            password=bootstrap_secret,
            name=body.name,
            tenant_id=user.tenant_id,
            role=body.role,
        )
        issue = _password_actions.issue_for_email(body.email, "invite_accept")
        if issue is None or issue.user_id != result["user_id"] or issue.tenant_id != user.tenant_id:
            raise RuntimeError("invite action issuance failed")

        email_result = _email_service.send_invite(
            to_email=issue.email,
            inviter_name="Admin",
            action_token=issue.token,
            role=body.role,
        )
        if not email_result.get("sent", False):
            # Avoid leaving an inaccessible account that blocks a clean retry.
            _user_service.delete_user(
                admin_tenant_id=user.tenant_id,
                target_user_id=result["user_id"],
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Invitation delivery unavailable",
            )

        return {
            "user_id": result["user_id"],
            "tenant_id": result["tenant_id"],
            "email": result["email"],
            "role": result["role"],
            "email_sent": True,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("secure_invite_failed error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invitation could not be created",
        ) from exc
