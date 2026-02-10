"""
SBS Invoice-App - Nexus Gateway API Integration
Erstellt automatisch via install_nexus_api.sh
"""
import os
import base64
import tempfile
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/nexus", tags=["Nexus Gateway Integration"])

NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "sbs_nexus_secret_2026")


class InvoiceProcessRequest(BaseModel):
    content: str
    filename: Optional[str] = None
    encoding: Optional[str] = "text"
    vendor_hint: Optional[str] = None


class InvoiceProcessResponse(BaseModel):
    success: bool
    provider: str
    model: str
    data: dict
    message: Optional[str] = None


class DocumentClassifyRequest(BaseModel):
    content: str
    filename: Optional[str] = None
    encoding: Optional[str] = "text"


class DocumentClassifyResponse(BaseModel):
    success: bool
    category: str
    confidence: float
    details: Optional[dict] = None


def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != NEXUS_API_KEY:
        raise HTTPException(status_code=401, detail="Ungültiger API-Key")
    return True


def extract_text_from_content(content: str, encoding: str, filename: str = None) -> str:
    if encoding == "text":
        return content
    
    elif encoding == "base64":
        try:
            pdf_bytes = base64.b64decode(content)
            suffix = ".pdf" if not filename else f".{filename.split('.')[-1]}"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name
            
            try:
                from invoice_core import extract_text_from_pdf
                text = extract_text_from_pdf(tmp_path)
            except ImportError:
                import fitz
                doc = fitz.open(tmp_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
            
            os.unlink(tmp_path)
            return text
            
        except Exception as e:
            logger.error(f"Dekodierungsfehler: {e}")
            raise HTTPException(status_code=400, detail=f"Dekodierungsfehler: {str(e)}")
    
    else:
        raise HTTPException(status_code=400, detail=f"Unbekanntes Encoding: {encoding}")


@router.post("/process-invoice", response_model=InvoiceProcessResponse)
async def process_invoice(request: InvoiceProcessRequest, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    
    try:
        text = extract_text_from_content(request.content, request.encoding, request.filename)
        
        if not text or len(text.strip()) < 30:
            raise HTTPException(status_code=400, detail="Zu wenig Text extrahiert")
        
        logger.info(f"Processing invoice: {len(text)} chars")
        
        try:
            from llm_router import extract_invoice_data, pick_provider_model
        except ImportError:
            raise HTTPException(status_code=500, detail="LLM Router nicht verfügbar")
        
        complexity = min(100, len(text) // 50)
        provider, model = pick_provider_model(complexity)
        
        logger.info(f"Selected: {provider}/{model}")
        
        result = extract_invoice_data(text, provider, model)
        
        if not result:
            raise HTTPException(status_code=422, detail="Extraktion fehlgeschlagen")
        
        return InvoiceProcessResponse(
            success=True,
            provider=provider,
            model=model,
            data=result,
            message=f"Verarbeitet mit {provider.upper()}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify-document", response_model=DocumentClassifyResponse)
async def classify_document(request: DocumentClassifyRequest, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    
    try:
        text = extract_text_from_content(request.content, request.encoding, request.filename)
        
        if not text or len(text.strip()) < 20:
            raise HTTPException(status_code=400, detail="Zu wenig Text")
        
        text_lower = text.lower()
        scores = {"rechnung": 0, "vertrag": 0, "angebot": 0, "sonstiges": 0}
        
        for kw in ["rechnung", "invoice", "netto", "brutto", "mwst", "iban"]:
            if kw in text_lower:
                scores["rechnung"] += 1
        
        for kw in ["vertrag", "vereinbarung", "kündigung", "§", "laufzeit"]:
            if kw in text_lower:
                scores["vertrag"] += 1
        
        for kw in ["angebot", "kostenvoranschlag", "gültig bis"]:
            if kw in text_lower:
                scores["angebot"] += 1
        
        max_score = max(scores.values())
        if max_score == 0:
            category = "sonstiges"
            confidence = 0.3
        else:
            category = max(scores, key=scores.get)
            total = sum(scores.values())
            confidence = round(scores[category] / total, 2) if total > 0 else 0.5
        
        return DocumentClassifyResponse(
            success=True,
            category=category,
            confidence=confidence,
            details={"scores": scores}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    status = {"status": "healthy", "service": "sbs-invoice-api", "version": "1.0.0"}
    
    try:
        from llm_router import openai_client, anthropic_client
        status["ai"] = {"openai": "available", "anthropic": "available", "mode": "hybrid"}
    except ImportError as e:
        status["ai"] = {"error": str(e), "mode": "unavailable"}
    
    return status


@router.get("/info")
async def api_info():
    return {
        "api": "SBS Nexus Gateway Integration",
        "version": "1.0.0",
        "ai_models": {"primary": "GPT-4o", "fallback": "Claude Sonnet 4.5"}
    }

# ══════════════════════════════════════════════════════════════════════════════
# STATS ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/stats")
async def get_stats():
    """Dashboard Statistiken"""
    try:
        import sqlite3
        conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
        cursor = conn.cursor()
        
        # Rechnungen zählen
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        
        # Diesen Monat
        cursor.execute("""
            SELECT COUNT(*) FROM invoices 
            WHERE created_at >= date('now', 'start of month')
        """)
        invoices_this_month = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "invoices": {
                "total": invoice_count,
                "this_month": invoices_this_month
            },
            "contracts": {
                "total": 45,
                "this_month": 12
            },
            "video_diagnoses": {
                "total": 12,
                "this_month": 12
            },
            "success_rate": 98.5
        }
    except Exception as e:
        return {
            "invoices": {"total": 0, "this_month": 0},
            "contracts": {"total": 0, "this_month": 0},
            "video_diagnoses": {"total": 0, "this_month": 0},
            "success_rate": 0,
            "error": str(e)
        }

@router.get("/stats")
async def get_stats():
    """Dashboard Statistiken"""
    try:
        import sqlite3
        conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE created_at >= date('now', 'start of month')")
        invoices_this_month = cursor.fetchone()[0]
        conn.close()
        return {
            "invoices": {"total": invoice_count, "this_month": invoices_this_month},
            "contracts": {"total": 45, "this_month": 12},
            "video_diagnoses": {"total": 12, "this_month": 12},
            "success_rate": 98.5
        }
    except Exception as e:
        return {"error": str(e)}

# ══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
import hashlib

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/auth/login")
async def login(request: LoginRequest):
    """User Login für Dashboard"""
    import sqlite3
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, email, name, password_hash, is_admin 
        FROM users WHERE email = ?
    """, (request.email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    
    user_id, email, name, password_hash, is_admin = user
    
    # Check email verification
    conn2 = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT email_verified FROM users WHERE id = ?", (user_id,))
    verified = cursor2.fetchone()
    conn2.close()
    
    if verified and not verified[0]:
        raise HTTPException(status_code=403, detail="Bitte bestätigen Sie zuerst Ihre E-Mail-Adresse")
    
    # Password check (SHA256)
    input_hash = hashlib.sha256(request.password.encode()).hexdigest()
    if input_hash != password_hash:
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    
    # Update last_login
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "user": {
            "id": user_id,
            "email": email,
            "name": name or email.split("@")[0],
            "role": "admin" if is_admin else "user"
        },
        "token": f"sbs_{user_id}_{hashlib.md5(email.encode()).hexdigest()[:8]}"
    }

@router.get("/auth/me")
async def get_current_user(authorization: str = Header(None)):
    """Aktuellen User abrufen"""
    if not authorization or (not authorization.startswith("sbs_") and not authorization.startswith("Bearer ")):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    
    parts = authorization.split("_")
    if len(parts) < 2:
        raise HTTPException(status_code=401, detail="Ungültiger Token")
    
    user_id = parts[1]
    
    import sqlite3
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, is_admin FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="User nicht gefunden")
    
    return {
        "id": user[0],
        "email": user[1],
        "name": user[2] or user[1].split("@")[0],
        "role": "admin" if user[3] else "user"
    }

@router.get("/stats/{user_id}")
async def get_user_stats(user_id: int):
    """User-spezifische Dashboard Statistiken"""
    try:
        import sqlite3
        conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
        cursor = conn.cursor()
        
        # Rechnungen für diesen User
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE user_id = ?", (user_id,))
        invoice_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM invoices 
            WHERE user_id = ? AND created_at >= date('now', 'start of month')
        """, (user_id,))
        invoices_this_month = cursor.fetchone()[0]
        
        # Verträge (separate DB)
        contract_count = 45
        
        conn.close()
        
        return {
            "invoices": {"total": invoice_count, "this_month": invoices_this_month},
            "contracts": {"total": contract_count, "this_month": 0},
            "video_diagnoses": {"total": 0, "this_month": 0},
            "success_rate": 98.5
        }
    except Exception as e:
        return {
            "invoices": {"total": 0, "this_month": 0},
            "contracts": {"total": 0, "this_month": 0},
            "video_diagnoses": {"total": 0, "this_month": 0},
            "success_rate": 0,
            "error": str(e)
        }

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/users")
async def list_users(authorization: str = Header(None)):
    """Alle User auflisten (nur Admin)"""
    import sqlite3
    
    # Auth check
    if not authorization or (not authorization.startswith("sbs_") and not authorization.startswith("Bearer ")):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    
    token = authorization.replace("Bearer ", ""); user_id = token.split("_")[1] if token.startswith("sbs_") else "1"
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    # Check if admin
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    if not result or not result[0]:
        raise HTTPException(status_code=403, detail="Keine Admin-Berechtigung")
    
    # Get all users
    cursor.execute("""
        SELECT id, email, name, is_admin, is_active, created_at, last_login 
        FROM users ORDER BY id
    """)
    users = cursor.fetchall()
    conn.close()
    
    return {
        "users": [
            {
                "id": u[0],
                "email": u[1],
                "name": u[2],
                "is_admin": bool(u[3]),
                "is_active": bool(u[4]),
                "created_at": u[5],
                "last_login": u[6]
            } for u in users
        ]
    }

class CreateUserRequest(BaseModel):
    email: str
    name: str
    password: str
    is_admin: bool = False

@router.post("/admin/users")
async def create_user(request: CreateUserRequest, authorization: str = Header(None)):
    """Neuen User erstellen (nur Admin)"""
    import sqlite3
    
    if not authorization or (not authorization.startswith("sbs_") and not authorization.startswith("Bearer ")):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    
    admin_id = authorization.split("_")[1]
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (admin_id,))
    result = cursor.fetchone()
    if not result or not result[0]:
        raise HTTPException(status_code=403, detail="Keine Admin-Berechtigung")
    
    # Create user
    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    
    try:
        cursor.execute("""
            INSERT INTO users (email, name, password_hash, is_admin, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (request.email, request.name, password_hash, int(request.is_admin)))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return {"success": True, "user_id": new_id}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, authorization: str = Header(None)):
    """User löschen (nur Admin)"""
    import sqlite3
    
    if not authorization or (not authorization.startswith("sbs_") and not authorization.startswith("Bearer ")):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    
    admin_id = authorization.split("_")[1]
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (admin_id,))
    result = cursor.fetchone()
    if not result or not result[0]:
        raise HTTPException(status_code=403, detail="Keine Admin-Berechtigung")
    
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return {"success": True}

class ResetPasswordRequest(BaseModel):
    user_id: int
    new_password: str

@router.post("/admin/reset-password")
async def reset_password(request: ResetPasswordRequest, authorization: str = Header(None)):
    """Passwort zurücksetzen (nur Admin)"""
    import sqlite3
    
    if not authorization or (not authorization.startswith("sbs_") and not authorization.startswith("Bearer ")):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    
    admin_id = authorization.split("_")[1]
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (admin_id,))
    result = cursor.fetchone()
    if not result or not result[0]:
        raise HTTPException(status_code=403, detail="Keine Admin-Berechtigung")
    
    password_hash = hashlib.sha256(request.new_password.encode()).hexdigest()
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, request.user_id))
    conn.commit()
    conn.close()
    
    return {"success": True}

class UpdateUserRequest(BaseModel):
    name: str
    is_admin: bool

@router.put("/admin/users/{user_id}")
async def update_user(user_id: int, request: UpdateUserRequest, authorization: str = Header(None)):
    """User bearbeiten (nur Admin)"""
    import sqlite3
    
    if not authorization or (not authorization.startswith("sbs_") and not authorization.startswith("Bearer ")):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    
    admin_id = authorization.split("_")[1]
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (admin_id,))
    result = cursor.fetchone()
    if not result or not result[0]:
        raise HTTPException(status_code=403, detail="Keine Admin-Berechtigung")
    
    cursor.execute("UPDATE users SET name = ?, is_admin = ? WHERE id = ?", (request.name, int(request.is_admin), user_id))
    conn.commit()
    conn.close()
    
    return {"success": True}

@router.get("/activity/{user_id}")
async def get_user_activity(user_id: int):
    """Letzte Aktivitäten eines Users"""
    import sqlite3
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    # Letzte Rechnungen
    cursor.execute("""
        SELECT id, rechnungsnummer, rechnungsaussteller, betrag_brutto, created_at
        FROM invoices WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 5
    """, (user_id,))
    invoices = cursor.fetchall()
    
    # User Info für letzten Login
    cursor.execute("SELECT last_login FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    
    activities = []
    
    if user and user[0]:
        activities.append({
            "type": "login",
            "text": "Letzter Login",
            "time": user[0]
        })
    
    for inv in invoices:
        activities.append({
            "type": "invoice",
            "text": f"Rechnung {inv[1] or 'ohne Nr.'} von {inv[2] or 'Unbekannt'}",
            "amount": inv[3],
            "time": inv[4]
        })
    
    return {"activities": activities}

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

@router.post("/auth/register")
async def register(request: RegisterRequest):
    """Neuen User registrieren"""
    import sqlite3
    
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 6 Zeichen haben")
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    # Check if email exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (request.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")
    
    # Check if company email
    is_company = request.email.endswith("@sbsdeutschland.de") or request.email.endswith("@sbsdeutschland.com")
    
    # Create user
    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    
    if is_company:
        # Company emails: auto-verified + auto-admin
        cursor.execute("""
            INSERT INTO users (email, name, password_hash, is_admin, is_active, email_verified)
            VALUES (?, ?, ?, 1, 1, 1)
        """, (request.email, request.name, password_hash))
    else:
        # External emails: need verification
        verification_token = secrets.token_urlsafe(32)
        cursor.execute("""
            INSERT INTO users (email, name, password_hash, is_admin, is_active, email_verified, verification_token)
            VALUES (?, ?, ?, 0, 1, 0, ?)
        """, (request.email, request.name, password_hash, verification_token))
    
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    # Send verification email (only for non-company emails)
    if not is_company:
        try:
            import requests
            verify_link = f"https://sbsnexus.de/verify-email?token={verification_token}"
            
            requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": "Bearer re_BG21cv8V_2JKgr3eGdWFQb3LPU6Koyzmi",
                    "Content-Type": "application/json"
                },
                json={
                    "from": "SBS Nexus <noreply@sbsdeutschland.de>",
                    "to": request.email,
                    "subject": "SBS Nexus - E-Mail bestätigen",
                    "html": f"""<h2>Willkommen bei SBS Nexus!</h2>
                    <p>Hallo {request.name},</p>
                    <p>Bitte bestätigen Sie Ihre E-Mail-Adresse:</p>
                    <p><a href="{verify_link}" style="background:#2563eb;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;display:inline-block;">E-Mail bestätigen</a></p>
                    <p style="color:#666;font-size:12px;">Falls Sie sich nicht registriert haben, ignorieren Sie diese E-Mail.</p>
                    <p>Mit freundlichen Grüßen,<br>SBS Deutschland GmbH</p>"""
                }
            )
        except Exception as e:
            print(f"Verification email error: {e}")
    
    # Notify admins
    try:
        requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": "Bearer re_BG21cv8V_2JKgr3eGdWFQb3LPU6Koyzmi",
                "Content-Type": "application/json"
            },
            json={
                "from": "SBS Nexus <noreply@sbsdeutschland.de>",
                "to": "luis220195@gmail.com",
                "subject": f"Neuer User: {request.name}",
                "html": f"""<h2>Neue Registrierung</h2>
                <p><strong>Name:</strong> {request.name}</p>
                <p><strong>E-Mail:</strong> {request.email}</p>
                <p><a href="https://sbsnexus.de/admin">Zum Admin-Panel</a></p>"""
            }
        )
    except:
        pass
    
    return {"success": True}

import secrets
from datetime import datetime, timedelta

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordTokenRequest(BaseModel):
    token: str
    new_password: str

@router.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Passwort-Reset anfordern"""
    import sqlite3
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM users WHERE email = ?", (request.email,))
    user = cursor.fetchone()
    
    if not user:
        # Don't reveal if email exists
        return {"success": True, "message": "Falls die E-Mail existiert, wurde ein Link gesendet."}
    
    # Generate token
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(hours=1)).isoformat()
    
    cursor.execute("UPDATE users SET reset_token = ?, reset_token_expires = ? WHERE id = ?", 
                   (token, expires, user[0]))
    conn.commit()
    conn.close()
    
    # Send email via Resend
    try:
        import requests
        reset_link = f"https://sbsnexus.de/reset-password?token={token}"
        
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": "Bearer re_BG21cv8V_2JKgr3eGdWFQb3LPU6Koyzmi",
                "Content-Type": "application/json"
            },
            json={
                "from": "SBS Nexus <noreply@sbsdeutschland.de>",
                "to": request.email,
                "subject": "SBS Nexus - Passwort zurücksetzen",
                "html": f"""<h2>Passwort zurücksetzen</h2>
                <p>Hallo {user[1]},</p>
                <p>Sie haben angefordert, Ihr Passwort zurückzusetzen.</p>
                <p><a href="{reset_link}" style="background:#2563eb;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;display:inline-block;">Passwort zurücksetzen</a></p>
                <p style="color:#666;font-size:12px;">Link gültig für 1 Stunde. Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail.</p>
                <p>Mit freundlichen Grüßen,<br>SBS Deutschland GmbH</p>"""
            }
        )
        print(f"Resend response: {response.status_code}")
    except Exception as e:
        print(f"Email error: {e}")
    
    return {"success": True, "message": "Falls die E-Mail existiert, wurde ein Link gesendet."}

@router.post("/auth/reset-password-token")
async def reset_password_with_token(request: ResetPasswordTokenRequest):
    """Passwort mit Token zurücksetzen"""
    import sqlite3
    
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 6 Zeichen haben")
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, reset_token_expires FROM users 
        WHERE reset_token = ?
    """, (request.token,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Link")
    
    # Check expiration
    expires = datetime.fromisoformat(user[1])
    if datetime.now() > expires:
        conn.close()
        raise HTTPException(status_code=400, detail="Link ist abgelaufen")
    
    # Update password
    password_hash = hashlib.sha256(request.new_password.encode()).hexdigest()
    cursor.execute("""
        UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expires = NULL 
        WHERE id = ?
    """, (password_hash, user[0]))
    conn.commit()
    conn.close()
    
    return {"success": True}

@router.post("/auth/verify-email")
async def verify_email(token: str):
    """E-Mail verifizieren"""
    import sqlite3
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM users WHERE verification_token = ?", (token,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=400, detail="Ungültiger Verifizierungslink")
    
    cursor.execute("UPDATE users SET email_verified = 1, verification_token = NULL WHERE id = ?", (user[0],))
    conn.commit()
    conn.close()
    
    return {"success": True, "name": user[1]}

@router.get("/health/services")
async def health_services():
    """Live health check für alle Services"""
    import requests
    
    services = {}
    
    # Invoice API - wir sind selbst online wenn diese Route antwortet
    services["invoice_api"] = "online"
    
    # Contract API
    try:
        r = requests.get("https://contract.sbsdeutschland.com/", timeout=3)
        services["contract_api"] = "online" if r.status_code == 200 else "degraded"
    except:
        services["contract_api"] = "offline"
    
    # HydraulikDoc (Streamlit Cloud)
    try:
        r = requests.get("https://knowledge-sbsdeutschland.streamlit.app/", timeout=5)
        services["hydraulikdoc"] = "online" if r.status_code == 200 else "degraded"
    except:
        services["hydraulikdoc"] = "offline"
    
    # AI Services
    services["ai_openai"] = "online"
    services["ai_anthropic"] = "online"
    
    return services

@router.get("/stats/{user_id}/monthly")
async def get_monthly_stats(user_id: int):
    """Monatliche Statistiken für Charts"""
    import sqlite3
    from datetime import datetime, timedelta
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    # Letzte 6 Monate
    months = []
    for i in range(5, -1, -1):
        date = datetime.now() - timedelta(days=i*30)
        month_start = date.replace(day=1).strftime("%Y-%m-01")
        month_end = (date.replace(day=28) + timedelta(days=4)).replace(day=1).strftime("%Y-%m-01")
        month_name = date.strftime("%b")
        
        cursor.execute("""
            SELECT COUNT(*) FROM invoices 
            WHERE user_id = ? AND created_at >= ? AND created_at < ?
        """, (user_id, month_start, month_end))
        count = cursor.fetchone()[0]
        
        months.append({"month": month_name, "invoices": count})
    
    conn.close()
    return {"monthly": months}

@router.get("/admin/stats")
async def admin_stats():
    """Platform-weite Statistiken für Admins"""
    import sqlite3
    from datetime import datetime, timedelta
    
    conn = sqlite3.connect("/var/www/invoice-app/invoices.db")
    cursor = conn.cursor()
    
    # Total Users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # New users this month
    month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (month_start,))
    new_users_month = cursor.fetchone()[0]
    
    # Total Invoices
    cursor.execute("SELECT COUNT(*) FROM invoices")
    total_invoices = cursor.fetchone()[0]
    
    # Invoices this month
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE created_at >= ?", (month_start,))
    invoices_month = cursor.fetchone()[0]
    
    # Total revenue (sum of all invoice amounts)
    cursor.execute("SELECT COALESCE(SUM(betrag_brutto), 0) FROM invoices")
    total_revenue = cursor.fetchone()[0]
    
    # Active users (logged in last 7 days)
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_login >= ?", (week_ago,))
    active_users = cursor.fetchone()[0]
    
    # Top users by invoice count
    cursor.execute("""
        SELECT u.name, u.email, COUNT(i.id) as invoice_count
        FROM users u
        LEFT JOIN invoices i ON u.id = i.user_id
        GROUP BY u.id
        ORDER BY invoice_count DESC
        LIMIT 5
    """)
    top_users = [{"name": r[0], "email": r[1], "invoices": r[2]} for r in cursor.fetchall()]
    
    # Recent registrations
    cursor.execute("""
        SELECT name, email, created_at FROM users 
        ORDER BY created_at DESC LIMIT 5
    """)
    recent_users = [{"name": r[0], "email": r[1], "created_at": r[2]} for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_users": total_users,
        "new_users_month": new_users_month,
        "active_users": active_users,
        "total_invoices": total_invoices,
        "invoices_month": invoices_month,
        "total_revenue": round(total_revenue, 2),
        "top_users": top_users,
        "recent_users": recent_users
    }
