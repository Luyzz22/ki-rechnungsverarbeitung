#!/usr/bin/env python3
"""
SBS Deutschland – API Key Management
Generierung, Validierung und Verwaltung von API-Keys.
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from database import get_connection

logger = logging.getLogger(__name__)

# Prefix für API-Keys
KEY_PREFIX = "sbs_"
KEY_LENGTH = 32


def generate_api_key() -> tuple:
    """
    Generiert einen neuen API-Key.
    
    Returns:
        (full_key, key_hash, key_prefix)
        - full_key: Wird nur einmal angezeigt!
        - key_hash: Für DB-Speicherung
        - key_prefix: Für Anzeige (sbs_abc123...)
    """
    # Zufälliger Key
    random_part = secrets.token_hex(KEY_LENGTH)
    full_key = f"{KEY_PREFIX}{random_part}"
    
    # Hash für sichere Speicherung
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    
    # Prefix für Anzeige (erste 8 Zeichen nach sbs_)
    key_prefix = f"{KEY_PREFIX}{random_part[:8]}..."
    
    return full_key, key_hash, key_prefix


def create_api_key(
    user_id: int,
    name: str,
    permissions: str = "read",
    rate_limit: int = 100,
    expires_days: int = None
) -> Dict:
    """
    Erstellt einen neuen API-Key für einen User.
    
    Args:
        user_id: User-ID
        name: Beschreibender Name (z.B. "DATEV Integration")
        permissions: "read", "write", "admin"
        rate_limit: Requests pro Stunde
        expires_days: Ablauf in Tagen (None = nie)
        
    Returns:
        Dict mit key (NUR EINMAL SICHTBAR!), id, prefix
    """
    full_key, key_hash, key_prefix = generate_api_key()
    
    expires_at = None
    if expires_days:
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO api_keys (user_id, key_hash, key_prefix, name, permissions, rate_limit, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, key_hash, key_prefix, name, permissions, rate_limit, expires_at))
    
    key_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"API-Key erstellt: {key_prefix} für User {user_id}")
    
    return {
        "id": key_id,
        "key": full_key,  # NUR EINMAL ANZEIGEN!
        "prefix": key_prefix,
        "name": name,
        "permissions": permissions,
        "rate_limit": rate_limit,
        "expires_at": expires_at
    }


def validate_api_key(api_key: str) -> Optional[Dict]:
    """
    Validiert einen API-Key.
    
    Args:
        api_key: Der vollständige API-Key
        
    Returns:
        Dict mit User-Info oder None wenn ungültig
    """
    if not api_key or not api_key.startswith(KEY_PREFIX):
        return None
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ak.*, u.email as user_email
        FROM api_keys ak
        JOIN users u ON ak.user_id = u.id
        WHERE ak.key_hash = ? AND ak.is_active = 1
    """, (key_hash,))
    
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None
    
    # Ablauf prüfen
    if result.get('expires_at'):
        expires = datetime.fromisoformat(result['expires_at'])
        if datetime.now() > expires:
            conn.close()
            logger.warning(f"API-Key abgelaufen: {result['key_prefix']}")
            return None
    
    # Last used aktualisieren
    cursor.execute("""
        UPDATE api_keys SET last_used_at = ? WHERE id = ?
    """, (datetime.now().isoformat(), result['id']))
    
    conn.commit()
    conn.close()
    
    return {
        "user_id": result['user_id'],
        "user_email": result['user_email'],
        "key_id": result['id'],
        "key_prefix": result['key_prefix'],
        "permissions": result['permissions'],
        "rate_limit": result['rate_limit']
    }


def revoke_api_key(key_id: int, user_id: int) -> bool:
    """
    Widerruft einen API-Key.
    
    Args:
        key_id: ID des Keys
        user_id: User-ID (zur Berechtigung)
        
    Returns:
        True wenn erfolgreich
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE api_keys SET is_active = 0 
        WHERE id = ? AND user_id = ?
    """, (key_id, user_id))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected:
        logger.info(f"API-Key {key_id} widerrufen")
    
    return affected > 0


def list_api_keys(user_id: int) -> List[Dict]:
    """
    Listet alle API-Keys eines Users.
    
    Args:
        user_id: User-ID
        
    Returns:
        Liste der Keys (ohne Hash!)
    """
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, key_prefix, name, permissions, rate_limit, 
               created_at, last_used_at, expires_at, is_active
        FROM api_keys
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    
    keys = cursor.fetchall()
    conn.close()
    
    return keys


def get_api_key_stats(key_id: int) -> Dict:
    """Holt Statistiken für einen API-Key."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT key_prefix, name, permissions, rate_limit,
               created_at, last_used_at, is_active
        FROM api_keys WHERE id = ?
    """, (key_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result
