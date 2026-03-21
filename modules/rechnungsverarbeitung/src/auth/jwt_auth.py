"""JWT Authentication & API Key Auth for SBS Nexus Finance API."""
from __future__ import annotations

import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Config
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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
    return bcrypt.hashpw(password[:72].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    import bcrypt
    return bcrypt.checkpw(plain[:72].encode('utf-8'), hashed.encode('utf-8'))

# --- Tokens ---
def create_access_token(user_id: str, tenant_id: str, role: str = "user") -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: str, tenant_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_tokens(user_id: str, tenant_id: str, role: str = "user") -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id, tenant_id, role),
        refresh_token=create_refresh_token(user_id, tenant_id),
    )

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

# --- API Keys ---
VALID_API_KEYS: dict[str, dict] = {}

def _load_api_keys():
    key = os.getenv("SBS_API_KEY", "")
    if key:
        VALID_API_KEYS[key] = {"tenant_id": "sbs-master", "role": "admin", "user_id": "api-key-admin"}

_load_api_keys()

def generate_api_key() -> str:
    return f"sbs_{secrets.token_hex(24)}"

# --- Dependencies ---
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> UserAuth:
    # Try API Key first
    if api_key and api_key in VALID_API_KEYS:
        info = VALID_API_KEYS[api_key]
        return UserAuth(user_id=info["user_id"], tenant_id=info["tenant_id"], role=info["role"])

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

    raise HTTPException(status_code=401, detail="Missing authentication", headers={"WWW-Authenticate": "Bearer"})

def require_role(role: str):
    async def check(user: UserAuth = Depends(get_current_user)):
        if user.role != role and user.role != "admin":
            raise HTTPException(status_code=403, detail=f"Role '{role}' required")
        return user
    return check

# Legacy compatibility — extract tenant from auth or fallback to header
async def get_tenant_from_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    x_tenant_id: Optional[str] = None,
) -> str:
    try:
        user = await get_current_user(credentials, api_key)
        return user.tenant_id
    except HTTPException:
        if x_tenant_id:
            return x_tenant_id
        raise HTTPException(status_code=401, detail="Authentication required")
