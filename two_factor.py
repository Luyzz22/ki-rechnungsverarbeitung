#!/usr/bin/env python3
"""
SBS Deutschland – Two-Factor Authentication (TOTP)
Implementiert zeitbasierte Einmalpasswörter (Google Authenticator kompatibel).
"""

import pyotp
import qrcode
import io
import base64
import logging
from typing import Optional, Dict
from database import get_connection

logger = logging.getLogger(__name__)


def generate_totp_secret() -> str:
    """Generiert ein neues TOTP-Secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "SBS Deutschland") -> str:
    """Generiert die TOTP-URI für QR-Code."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_code(uri: str) -> str:
    """Generiert QR-Code als Base64-String."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp(secret: str, code: str) -> bool:
    """Verifiziert einen TOTP-Code."""
    if not secret or not code:
        return False
    
    totp = pyotp.TOTP(secret)
    # Erlaubt 1 Zeitfenster Toleranz (30 Sekunden vor/nach)
    return totp.verify(code, valid_window=1)


def enable_2fa(user_id: int) -> Dict:
    """
    Aktiviert 2FA für einen User (Schritt 1: Secret generieren).
    User muss danach verify_and_activate_2fa aufrufen.
    """
    secret = generate_totp_secret()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Secret temporär speichern (noch nicht aktiviert)
    cursor.execute("""
        UPDATE users SET totp_secret_pending = ? WHERE id = ?
    """, (secret, user_id))
    
    # Email holen
    cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    email = row[0] if row else "user@example.com"
    
    conn.commit()
    conn.close()
    
    uri = get_totp_uri(secret, email)
    qr_base64 = generate_qr_code(uri)
    
    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "uri": uri
    }


def verify_and_activate_2fa(user_id: int, code: str) -> bool:
    """
    Verifiziert den Code und aktiviert 2FA (Schritt 2).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT totp_secret_pending FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or not row[0]:
        conn.close()
        return False
    
    pending_secret = row[0]
    
    if verify_totp(pending_secret, code):
        # Aktivieren
        cursor.execute("""
            UPDATE users 
            SET totp_secret = ?, totp_secret_pending = NULL, totp_enabled = 1 
            WHERE id = ?
        """, (pending_secret, user_id))
        conn.commit()
        conn.close()
        logger.info(f"2FA aktiviert für User {user_id}")
        return True
    
    conn.close()
    return False


def disable_2fa(user_id: int, code: str) -> bool:
    """Deaktiviert 2FA nach Code-Verifikation."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT totp_secret FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or not row[0]:
        conn.close()
        return False
    
    if verify_totp(row[0], code):
        cursor.execute("""
            UPDATE users 
            SET totp_secret = NULL, totp_enabled = 0 
            WHERE id = ?
        """, (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"2FA deaktiviert für User {user_id}")
        return True
    
    conn.close()
    return False


def check_2fa_required(user_id: int) -> bool:
    """Prüft ob User 2FA aktiviert hat."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT totp_enabled FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    return bool(row and row[0])


def verify_user_2fa(user_id: int, code: str) -> bool:
    """Verifiziert 2FA-Code beim Login."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT totp_secret FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return False
    
    return verify_totp(row[0], code)


def generate_backup_codes(user_id: int, count: int = 10) -> list:
    """Generiert Backup-Codes für 2FA-Recovery."""
    import secrets
    
    codes = [secrets.token_hex(4).upper() for _ in range(count)]
    codes_str = ",".join(codes)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET totp_backup_codes = ? WHERE id = ?", (codes_str, user_id))
    conn.commit()
    conn.close()
    
    return codes


def verify_backup_code(user_id: int, code: str) -> bool:
    """Verifiziert und invalidiert einen Backup-Code."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT totp_backup_codes FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or not row[0]:
        conn.close()
        return False
    
    codes = row[0].split(",")
    code_upper = code.upper().replace("-", "")
    
    if code_upper in codes:
        codes.remove(code_upper)
        cursor.execute("UPDATE users SET totp_backup_codes = ? WHERE id = ?", (",".join(codes), user_id))
        conn.commit()
        conn.close()
        logger.info(f"Backup-Code verwendet für User {user_id}")
        return True
    
    conn.close()
    return False
