#!/usr/bin/env python3
"""
SBS Deutschland – Shared Authentication
JWT-basiertes SSO für alle SBS Apps (Invoice, Contract, etc.)
"""

import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Shared Secret (gleich auf allen Apps)
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "sbs-deutschland-shared-secret-2025"))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7  # 7 Tage
COOKIE_NAME = "sbs_auth_token"
COOKIE_DOMAIN = ".sbsdeutschland.com"  # Gilt für alle Subdomains


def create_sso_token(user_id: int, email: str, name: str = None, extra: Dict = None) -> str:
    """
    Erstellt JWT Token für SSO.
    
    Args:
        user_id: User ID aus der Datenbank
        email: User Email
        name: User Name (optional)
        extra: Zusätzliche Claims (optional)
        
    Returns:
        JWT Token String
    """
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "email": email,
        "name": name or email.split("@")[0],
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iss": "sbs-deutschland",
        "aud": ["app.sbsdeutschland.com", "contract.sbsdeutschland.com"],
    }
    
    if extra:
        payload.update(extra)
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_sso_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifiziert JWT Token.
    
    Args:
        token: JWT Token String
        
    Returns:
        Payload Dict oder None bei Fehler
    """
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token, 
            JWT_SECRET, 
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False}  # Audience-Check optional
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("SSO Token abgelaufen")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Ungültiger SSO Token: {e}")
        return None


def get_sso_cookie_settings() -> Dict[str, Any]:
    """
    Returns Cookie-Settings für SSO.
    Gilt für alle *.sbsdeutschland.com Subdomains.
    """
    return {
        "key": COOKIE_NAME,
        "httponly": True,
        "secure": True,  # Nur HTTPS
        "samesite": "lax",
        "domain": COOKIE_DOMAIN,
        "max_age": JWT_EXPIRY_HOURS * 3600,
        "path": "/",
    }


def extract_token_from_request(request) -> Optional[str]:
    """
    Extrahiert Token aus Request (Cookie oder Header).
    
    Args:
        request: FastAPI Request
        
    Returns:
        Token String oder None
    """
    # 1. Cookie prüfen
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    
    # 2. Authorization Header prüfen
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    return None


def get_current_user(request) -> Optional[Dict[str, Any]]:
    """
    Holt aktuellen User aus Request.
    
    Args:
        request: FastAPI Request
        
    Returns:
        User Dict oder None
    """
    token = extract_token_from_request(request)
    if not token:
        return None
    
    return verify_sso_token(token)


# FastAPI Dependency
async def require_sso_auth(request):
    """
    FastAPI Dependency für SSO Auth.
    Wirft HTTPException wenn nicht authentifiziert.
    """
    from fastapi import HTTPException
    
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    
    return user


# Decorator für geschützte Routes
def sso_protected(func):
    """Decorator für SSO-geschützte Endpoints"""
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(
                url=f"https://app.sbsdeutschland.com/login?next={request.url}",
                status_code=303
            )
        request.state.user = user
        return await func(request, *args, **kwargs)
    return wrapper


if __name__ == "__main__":
    # Test
    token = create_sso_token(1, "test@example.com", "Test User")
    print(f"Token: {token[:50]}...")
    
    payload = verify_sso_token(token)
    print(f"Payload: {payload}")
