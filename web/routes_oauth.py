"""
SSO/OAuth Routes for SBS Deutschland
Enterprise Single Sign-On: Google, Microsoft Entra ID
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["oauth"])

# ============================================================
# GOOGLE OAUTH
# ============================================================
@router.get("/google")
async def google_login(request: Request):
    """Initiate Google OAuth login"""
    from web.oauth_config import get_oauth
    oauth = get_oauth()
    
    redirect_uri = request.url_for('google_callback')
    # Store next URL in session for post-login redirect
    next_url = request.query_params.get('next', '/dashboard')
    request.session['oauth_next'] = next_url
    
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    from web.oauth_config import get_oauth
    oauth = get_oauth()
    
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            logger.error("Google OAuth: No user info received")
            return RedirectResponse(url='/login?error=oauth_failed', status_code=303)
        
        # Process OAuth user
        user_id = await process_oauth_user(
            provider='google',
            oauth_id=user_info['sub'],
            email=user_info['email'],
            name=user_info.get('name', ''),
            picture=user_info.get('picture')
        )
        
        if user_id:
            request.session['user_id'] = user_id
            request.session['oauth_provider'] = 'google'
            next_url = request.session.pop('oauth_next', '/dashboard')
            logger.info(f"Google OAuth login successful: {user_info['email']}")
            return RedirectResponse(url=next_url, status_code=303)
        else:
            return RedirectResponse(url='/login?error=oauth_user_failed', status_code=303)
            
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        return RedirectResponse(url='/login?error=oauth_failed', status_code=303)


# ============================================================
# MICROSOFT ENTRA ID
# ============================================================
@router.get("/microsoft")
async def microsoft_login(request: Request):
    """Initiate Microsoft OAuth login"""
    from web.oauth_config import get_oauth
    oauth = get_oauth()
    
    redirect_uri = request.url_for('microsoft_callback')
    next_url = request.query_params.get('next', '/dashboard')
    request.session['oauth_next'] = next_url
    
    return await oauth.microsoft.authorize_redirect(request, redirect_uri)


@router.get("/microsoft/callback")
async def microsoft_callback(request: Request):
    """Handle Microsoft OAuth callback"""
    from web.oauth_config import get_oauth
    oauth = get_oauth()
    
    try:
        token = await oauth.microsoft.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            logger.error("Microsoft OAuth: No user info received")
            return RedirectResponse(url='/login?error=oauth_failed', status_code=303)
        
        user_id = await process_oauth_user(
            provider='microsoft',
            oauth_id=user_info['sub'],
            email=user_info.get('email') or user_info.get('preferred_username'),
            name=user_info.get('name', ''),
            picture=None
        )
        
        if user_id:
            request.session['user_id'] = user_id
            request.session['oauth_provider'] = 'microsoft'
            next_url = request.session.pop('oauth_next', '/dashboard')
            logger.info(f"Microsoft OAuth login successful: {user_info.get('email')}")
            return RedirectResponse(url=next_url, status_code=303)
        else:
            return RedirectResponse(url='/login?error=oauth_user_failed', status_code=303)
            
    except Exception as e:
        logger.error(f"Microsoft OAuth error: {e}")
        return RedirectResponse(url='/login?error=oauth_failed', status_code=303)


# ============================================================
# SHARED: Process OAuth User (Create or Link)
# ============================================================
async def process_oauth_user(provider: str, oauth_id: str, email: str, name: str, picture: str = None) -> int:
    """
    Create or retrieve user from OAuth login.
    
    Logic:
    1. Check if OAuth account already linked → return user_id
    2. Check if email exists → link OAuth to existing account
    3. Create new user with OAuth
    """
    import sqlite3
    from database import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Check existing OAuth link
        cursor.execute("""
            SELECT id FROM users 
            WHERE oauth_provider = ? AND oauth_id = ?
        """, (provider, oauth_id))
        existing = cursor.fetchone()
        
        if existing:
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = ? WHERE id = ?
            """, (datetime.now().isoformat(), existing['id']))
            conn.commit()
            return existing['id']
        
        # 2. Check if email exists (link OAuth to existing account)
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        email_user = cursor.fetchone()
        
        if email_user:
            # Link OAuth to existing account
            cursor.execute("""
                UPDATE users 
                SET oauth_provider = ?, oauth_id = ?, oauth_email = ?, last_login = ?
                WHERE id = ?
            """, (provider, oauth_id, email, datetime.now().isoformat(), email_user['id']))
            conn.commit()
            logger.info(f"Linked {provider} OAuth to existing user: {email}")
            return email_user['id']
        
        # 3. Create new user
        cursor.execute("""
            INSERT INTO users (email, password_hash, name, oauth_provider, oauth_id, oauth_email, 
                             email_verified, created_at, last_login, is_active)
            VALUES (?, '', ?, ?, ?, ?, 1, ?, ?, 1)
        """, (email, name, provider, oauth_id, email, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        
        new_user_id = cursor.lastrowid
        logger.info(f"Created new user via {provider} OAuth: {email} (ID: {new_user_id})")
        return new_user_id
        
    except Exception as e:
        logger.error(f"OAuth user processing error: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


# ============================================================
# SSO STATUS ENDPOINT (for Admin UI)
# ============================================================
@router.get("/sso/status")
async def sso_status(request: Request):
    """Check which SSO providers are configured"""
    import os
    return {
        "google": bool(os.getenv('GOOGLE_CLIENT_ID')),
        "microsoft": bool(os.getenv('MICROSOFT_CLIENT_ID')),
        "okta": bool(os.getenv('OKTA_CLIENT_ID')),
    }
