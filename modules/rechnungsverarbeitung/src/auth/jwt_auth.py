"""JWT Authentication & API Key Auth for SBS Nexus Finance API."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# --- Security hotfix: fail-closed JWT secret resolution -------------------
# See docs/FLOWCHECK_SECURITY_HOTFIX_PLAN.md (F-05).
# Lazy resolution avoids import-time crashes in tests/CI; the modular API
# fails closed at first JWT operation when JWT_SECRET_KEY is missing in
# production. ENVIRONMENT=development allows a clearly insecure fallback.
_DEV_JWT_SECRET_FALLBACK = "DEV-INSECURE-JWT-SECRET-CHANGE-ME"  # noqa: S105
_jwt_secret_cache: Optional[str] = None


def _resolve_jwt_secret() -> str:
    global _jwt_secret_cache
    if _jwt_secret_cache is not None:
        return _jwt_secret_cache
    value = os.getenv("JWT_SECRET_KEY")
    if value:
        _jwt_secret_cache = value
        return value
    env = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "").strip().lower()
    if env in ("development", "dev"):
        logger.warning(
            "SECURITY: JWT_SECRET_KEY is not set; using insecure development fallback. "
            "This MUST NOT be used in production."
        )
        _jwt_secret_cache = _DEV_JWT_SECRET_FALLBACK
        return _jwt_secret_cache
    raise RuntimeError(
        "SECURITY: JWT_SECRET_KEY is not configured. Set the environment variable, "
        "or run with ENVIRONMENT=development for a clearly insecure development fallback."
    )


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
PASSWORD_ACTION_DEFAULT_EXPIRE_MINUTES = 30
PASSWORD_ACTION_MAX_EXPIRE_MINUTES = 24 * 60
_PASSWORD_ACTION_PURPOSES = frozenset({"invite_accept", "password_reset"})

# Reserved identities belonging to a retired static demo route. They are never
# valid token subjects, including in development/test. Keeping this guard in the
# token factory makes the legacy route fail closed until the route itself is
# removed from the oversized API module.
_RESERVED_DEMO_USER_ID = "demo-user"
_RESERVED_DEMO_TENANT_ID = "test-ai-live"


def _assert_token_identity_allowed(user_id: str, tenant_id: str) -> None:
    """Permanently block retired demo identities from receiving JWTs."""
    if user_id != _RESERVED_DEMO_USER_ID and tenant_id != _RESERVED_DEMO_TENANT_ID:
        return
    logger.warning("SECURITY: blocked retired demo token identity")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# --- Models ---
class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: str = "user"
    exp: int
    iat: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


class UserAuth(BaseModel):
    user_id: str
    tenant_id: str
    role: str = "user"


# --- Password ---
def hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    import bcrypt

    return bcrypt.checkpw(plain[:72].encode("utf-8"), hashed.encode("utf-8"))


# --- Tokens ---
def create_access_token(user_id: str, tenant_id: str, role: str = "user") -> str:
    _assert_token_identity_allowed(user_id, tenant_id)
    now = int(time.time())
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "type": "access",
    }
    return jwt.encode(payload, _resolve_jwt_secret(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str, tenant_id: str) -> str:
    _assert_token_identity_allowed(user_id, tenant_id)
    now = int(time.time())
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "type": "refresh",
    }
    return jwt.encode(payload, _resolve_jwt_secret(), algorithm=ALGORITHM)


def create_tokens(user_id: str, tenant_id: str, role: str = "user") -> TokenResponse:
    _assert_token_identity_allowed(user_id, tenant_id)
    return TokenResponse(
        access_token=create_access_token(user_id, tenant_id, role),
        refresh_token=create_refresh_token(user_id, tenant_id),
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _resolve_jwt_secret(), algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


def _password_credential_binding(password_hash: str) -> str:
    """Bind a password action token to the current credential without exposing its hash."""
    if not password_hash:
        raise ValueError("password_hash is required")
    return hmac.new(
        _resolve_jwt_secret().encode("utf-8"),
        password_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_password_action_token(
    user_id: str,
    tenant_id: str,
    password_hash: str,
    purpose: str,
    *,
    expires_minutes: int = PASSWORD_ACTION_DEFAULT_EXPIRE_MINUTES,
) -> str:
    """Create a short-lived credential-bound token for invite/reset password setup.

    The token is invalidated automatically after the user's password hash changes.
    The consuming service must still perform the password update atomically so that
    concurrent replays cannot both succeed.
    """
    _assert_token_identity_allowed(user_id, tenant_id)
    if purpose not in _PASSWORD_ACTION_PURPOSES:
        raise ValueError("Unsupported password action purpose")
    if expires_minutes <= 0 or expires_minutes > PASSWORD_ACTION_MAX_EXPIRE_MINUTES:
        raise ValueError("Invalid password action expiry")

    now = int(time.time())
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + expires_minutes * 60,
        "type": "password_action",
        "purpose": purpose,
        "credential_binding": _password_credential_binding(password_hash),
        "jti": secrets.token_urlsafe(24),
    }
    return jwt.encode(payload, _resolve_jwt_secret(), algorithm=ALGORITHM)


def decode_password_action_token(token: str, expected_purpose: str) -> dict:
    """Decode a password action token and enforce its exact purpose."""
    if expected_purpose not in _PASSWORD_ACTION_PURPOSES:
        raise ValueError("Unsupported password action purpose")

    payload = decode_token(token)
    required = ("sub", "tenant_id", "credential_binding", "jti")
    if (
        payload.get("type") != "password_action"
        or payload.get("purpose") != expected_purpose
        or any(not payload.get(field) for field in required)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password action token")
    return payload


def password_action_matches_current_credential(payload: dict, password_hash: str) -> bool:
    """Return whether an action token is still bound to the current password hash."""
    presented = str(payload.get("credential_binding") or "")
    if not presented or not password_hash:
        return False
    expected = _password_credential_binding(password_hash)
    return secrets.compare_digest(presented, expected)


# --- API Keys ---
_ALLOWED_API_KEY_ROLES = frozenset({"user", "viewer", "editor", "admin", "service"})


def _resolve_api_key_identity(api_key: str) -> Optional[UserAuth]:
    """Resolve a matching API key only to an explicitly configured tenant identity."""
    configured_key = os.getenv("SBS_API_KEY", "")
    if not configured_key or not secrets.compare_digest(api_key, configured_key):
        return None

    tenant_id = os.getenv("SBS_API_KEY_TENANT_ID", "").strip()
    user_id = os.getenv("SBS_API_KEY_USER_ID", "").strip()
    role = os.getenv("SBS_API_KEY_ROLE", "").strip().lower()

    if not tenant_id or not user_id or role not in _ALLOWED_API_KEY_ROLES:
        logger.error(
            "SECURITY: SBS_API_KEY matched but its scoped identity configuration is incomplete or invalid"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key authentication unavailable",
        )

    return UserAuth(user_id=user_id, tenant_id=tenant_id, role=role)


def generate_api_key() -> str:
    return f"sbs_{secrets.token_hex(24)}"


# --- Dependencies ---
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> UserAuth:
    # API keys are tenant-scoped and require an explicit configured identity.
    if api_key:
        api_key_user = _resolve_api_key_identity(api_key)
        if api_key_user is not None:
            return api_key_user

    # Try Bearer token
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return UserAuth(
            user_id=payload["sub"],
            tenant_id=payload["tenant_id"],
            role=payload.get("role", "user"),
        )

    raise HTTPException(
        status_code=401,
        detail="Missing authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(role: str):
    async def check(user: UserAuth = Depends(get_current_user)):
        if user.role != role and user.role != "admin":
            raise HTTPException(status_code=403, detail=f"Role '{role}' required")
        return user

    return check


# Legacy compatibility — authenticated tenant remains canonical.
async def get_tenant_from_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    x_tenant_id: Optional[str] = None,
) -> str:
    """Resolve tenant only from authenticated identity; never trust a header fallback."""
    user = await get_current_user(credentials, api_key)
    if x_tenant_id is not None:
        requested_tenant = x_tenant_id.strip()
        if requested_tenant and requested_tenant != user.tenant_id:
            raise HTTPException(status_code=403, detail="X-Tenant-ID does not match authenticated tenant")
    return user.tenant_id
