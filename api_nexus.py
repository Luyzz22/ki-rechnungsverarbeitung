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
    
    # Password check (SHA256)
    input_hash = hashlib.sha256(request.password.encode()).hexdigest()
    if input_hash != password_hash:
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    
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
    if not authorization or not authorization.startswith("sbs_"):
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
    if not authorization or not authorization.startswith("sbs_"):
        raise HTTPException(status_code=401, detail="Nicht authentifiziert")
    
    user_id = authorization.split("_")[1]
    
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
    
    if not authorization or not authorization.startswith("sbs_"):
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
    
    if not authorization or not authorization.startswith("sbs_"):
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
    
    if not authorization or not authorization.startswith("sbs_"):
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
    
    if not authorization or not authorization.startswith("sbs_"):
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
