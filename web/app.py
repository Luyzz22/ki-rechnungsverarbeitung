from fastapi.responses import HTMLResponse, RedirectResponse
from database import create_password_reset_token, verify_reset_token, reset_password
# FIXED (was broken): from database import create_password_reset_token, verify_reset_token, reset_password\nfrom fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Form
#!/usr/bin/env python3
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
"""
KI-Rechnungsverarbeitung - Web Interface
FastAPI Backend v1.0
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import save_job, save_invoices, get_job, get_all_jobs, get_statistics, get_invoices_by_job
from notifications import send_sendgrid_email
from category_ai import predict_category
from logging.handlers import RotatingFileHandler
import sys
import json

# Logging Setup
log_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File Handler
file_handler = RotatingFileHandler(
    '/var/www/invoice-app/logs/app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Root Logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# App Logger
app_logger = logging.getLogger('invoice_app')
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="web/templates")
from fastapi import Request
import shutil
from typing import List
import uuid
from datetime import datetime
from datetime import datetime, timedelta
import asyncio

# Import your existing modules
from invoice_core import Config, InvoiceProcessor, calculate_statistics
from export import ExportManager
from dashboard import generate_dashboard
from datev_exporter import export_to_datev
from notifications import send_notifications, check_low_confidence

# FastAPI App
app = FastAPI(
    title="KI-Rechnungsverarbeitung Web",
    description="Automatische Rechnungsverarbeitung mit KI",
    version="1.0.0"
)

# === Exception Handlers ===
from exceptions import (
    JobNotFoundError,
    InvoiceAppError, NotFoundError, ValidationError,
    ProcessingError, AuthError, QuotaExceededError
)
from fastapi.responses import JSONResponse
from logging_utils import LogContext, log_job_event, log_error_with_context
from models import Invoice, InvoiceStatus, Job, JobStatus
from schemas import JobStatusResponse, JobResultsResponse, UserResponse, SuccessResponse, ErrorResponse
from einvoice import generate_xrechnung, export_xrechnung_file, validate_xrechnung as validate_xrechnung_new
from rate_limiter import check_rate_limit, get_client_ip
from api_keys import validate_api_key, create_api_key, list_api_keys, revoke_api_key
from audit import log_audit, AuditAction, get_audit_logs
from audit import get_audit_stats
from webhooks import create_webhook, get_webhooks, delete_webhook, trigger_webhooks, WebhookEvent
from system_alerts import get_system_status, run_system_check

@app.exception_handler(InvoiceAppError)
async def invoice_app_error_handler(request, exc: InvoiceAppError):
    """Handler für alle App-Exceptions"""
    app_logger.error(f"{exc.code}: {exc.message}", extra=exc.details)
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc: NotFoundError):
    app_logger.warning(f"Not found: {exc.message}")
    return JSONResponse(status_code=404, content=exc.to_dict())

@app.exception_handler(ValidationError)
async def validation_handler(request, exc: ValidationError):
    app_logger.warning(f"Validation error: {exc.message}")
    return JSONResponse(status_code=422, content=exc.to_dict())

@app.middleware("http")
async def add_security_headers(request, call_next):
    """Fügt Security Headers zu allen Responses hinzu"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

@app.middleware("http")
async def log_requests(request, call_next):
    """Log alle HTTP Requests mit Timing"""
    import time
    start_time = time.time()
    app_logger.info(f"Request: {request.method} {request.url.path} from {request.client.host}")
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    app_logger.info(f"Response: {response.status_code} in {duration_ms:.1f}ms")
    if duration_ms > 1000:
        app_logger.warning(f"Slow request: {request.url.path} took {duration_ms:.1f}ms")
    return response

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
@app.get("/landing")
async def landing_page():
    """Landing Page für Marketing"""
    return FileResponse("web/static/landing/index.html")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Initialize
config = Config()
processor = InvoiceProcessor(config)

# In-memory storage for results (in production: use database)
processing_jobs = {}
app_start_time = __import__("time").time()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    redirect = require_login(request)
    if redirect:
        return redirect
    """Main upload page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/upload", tags=["Jobs"])
async def upload_files(request: Request, files: List[UploadFile] = File(default=[])):
    app_logger.info(f"Upload request: {len(files) if files else 0} files from user")
    """
    Rechnungs-Upload mit Subscription-Prüfung:
    - Admins: Unbegrenzter Zugang
    - User mit aktivem Plan: Bis zum Limit
    - User ohne Plan: Redirect zu Preisseite
    """

    # 1) Nur eingeloggte User dürfen hochladen
    if "user_id" not in request.session:
        return JSONResponse(
            status_code=401,
            content={"error": "Bitte melden Sie sich an", "redirect": "/login"},
        )

    user_id = request.session["user_id"]
    
    # 2) Subscription-Check (Admins haben unbegrenzten Zugang)
    from database import check_invoice_limit
    limit_status = check_invoice_limit(user_id)
    
    if not limit_status.get('allowed') and not limit_status.get('is_admin'):
        reason = limit_status.get('reason', 'unknown')
        if reason == 'no_subscription':
            return JSONResponse(
                status_code=402,
                content={
                    "error": "Kein aktiver Plan",
                    "message": "Bitte wählen Sie einen Plan um Rechnungen zu verarbeiten.",
                    "redirect": "/landing/preise.html"
                }
            )
        elif reason == 'limit_reached':
            return JSONResponse(
                status_code=402,
                content={
                    "error": "Limit erreicht",
                    "message": limit_status.get('message', 'Monatliches Limit erreicht.'),
                    "redirect": "/landing/preise.html"
                }
            )
    # Rate Limiting: 10 Uploads pro Minute
    check_rate_limit(request, "upload")

    # 2) Job-ID & Upload-Ordner
    job_id = str(uuid.uuid4())
    log_job_event(app_logger, job_id, "created", user_id=user_id, file_count=len(files))
    upload_path = UPLOAD_DIR / job_id
    upload_path.mkdir(exist_ok=True)

    uploaded_files = []
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

    for file in files:
        # Nur PDFs verarbeiten
        if not file.filename.lower().endswith(".pdf"):
            continue

        file_path = upload_path / file.filename

        # Optional: rudimentärer Größen-Check (wenn verfügbar)
        size = getattr(file, "size", None)
        if size is not None and size > MAX_FILE_SIZE:
            # Im DEV: einfach überspringen
            continue

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        uploaded_files.append(
            {
                "filename": file.filename,
                "size": file_path.stat().st_size,
            }
        )

    # 3) Wenn keine einzige gültige Datei dabei war
    if not uploaded_files:
        return JSONResponse(
            status_code=400,
            content={"error": "Keine gültigen PDF-Dateien hochgeladen."},
        )

    # 4) Job in processing_jobs ablegen (RAM – wird von /api/process genutzt)
    processing_jobs[job_id] = {
        "user_id": user_id,
        "status": JobStatus.UPLOADED.value,
        "files": uploaded_files,
        "created_at": datetime.now().isoformat(),
        "path": str(upload_path),
        "total": len(uploaded_files),
        "successful": 0,
        "failed": [],
        "failed_count": 0,
        "total_amount": 0.0,
        "stats": {},
    }

    # 5) DEV-"Subscription"-Info (Frontend-kompatibel, aber ohne Limit)
    dev_limit = {
        "plan": "dev-unlimited",
        "used": 0,
        "limit": 1_000_000,
        "remaining": 1_000_000 - len(uploaded_files),
    }

    return {
        "success": True,
        "batch_id": job_id,
        "job_id": job_id,
        "files_uploaded": len(uploaded_files),
        "files": uploaded_files,
        "subscription": dev_limit,
    }
@app.post("/api/process/{job_id}", tags=["Jobs"])
async def process_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Process uploaded PDFs
    Returns immediately, processing happens in background
    """
    if job_id not in processing_jobs:
        raise JobNotFoundError(job_id)
    
    job = processing_jobs[job_id]
    
    if job["status"] == "processing":
        return {"status": "already_processing"}
    
    # Update status
    processing_jobs[job_id]["status"] = "processing"
    
    # Process in background
    background_tasks.add_task(process_invoices_background, job_id)
    
    return {
        "success": True,
        "job_id": job_id,
        "status": JobStatus.PROCESSING.value,
        "message": "Processing started" 
    }

async def process_invoices_background(job_id: str):
    log_job_event(app_logger, job_id, "processing_started")
    """Background task to process invoices with parallel processing"""
    job = processing_jobs[job_id]
    upload_path = Path(job["path"])
    
    results = []
    failed = []
    
    # Get all PDFs
    pdf_files = list(upload_path.glob("*.pdf"))
    total_files = len(pdf_files)
    
    # Update job with total count
    processing_jobs[job_id]["total"] = total_files
    processing_jobs[job_id]["processed"] = 0
    
    # Process PDFs in parallel (8 threads)
    def process_single_pdf(pdf_path):
        try:
            data = processor.process_invoice(pdf_path)
            # Invoice-Model für Validierung und Standardwerte
            invoice = Invoice.from_dict(data)
            invoice.filename = pdf_path.name
            return ("success", invoice.to_dict(), pdf_path.name)
        except Exception as e:
            return ("error", str(e), pdf_path.name)
    
    # Use ThreadPoolExecutor for parallel processing
    max_workers = min(8, total_files) if total_files > 0 else 1
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pdf = {executor.submit(process_single_pdf, pdf): pdf for pdf in pdf_files}
        
        for future in as_completed(future_to_pdf):
            status, data, filename = future.result()
            
            if status == "success" and data:
                results.append(data)
            else:
                failed.append(filename if status == "success" else f"{filename}: {data}")
                app_logger.warning(f"Invoice failed: {filename} - {data if status != 'success' else 'empty result'}", extra={"job_id": job_id, "filename": filename})
            
            # Update progress
            processing_jobs[job_id]["processed"] = len(results) + len(failed)
            processing_jobs[job_id]["progress"] = int((len(results) + len(failed)) / total_files * 100) if total_files > 0 else 100
    
    # Calculate statistics
    stats = calculate_statistics(results) if results else None
    
    # Füge Rechnungsanzahl hinzu
    if stats:
        stats['total_invoices'] = len(results)
    
    # Export (XLSX, CSV, DATEV)
    exported_files = {}
    if results:
        try:
            # Standard Exports
            manager = ExportManager()
            exported_files = manager.export_all(results, ['xlsx', 'csv'])
            
            # DATEV Export
            from datev_exporter import export_to_datev
            datev_config = config.config.get('datev', {})
            if datev_config.get('enabled', False):
                datev_file = export_to_datev(results, datev_config)
                exported_files['datev'] = datev_file
            
        except Exception as e:
            app_logger.error(f"Export error: {e}")
    
    # Email Notification
    try:
        from notifications import send_notifications, check_low_confidence
        notification_config = config.config.get('notifications', {})
        if notification_config.get('email', {}).get('enabled', False):
            send_notifications(config.config, stats, exported_files)
    except Exception as e:
        app_logger.error(f"Notification error: {e}")
    
    # Update job with results
    processing_jobs[job_id].update({
        "status": JobStatus.COMPLETED.value,
        "results": results,
        "stats": stats,
        "failed": failed,
        "exported_files": exported_files,
        "completed_at": datetime.now().isoformat(),
        "total_amount": stats.get('total_brutto', 0) if stats else 0,
        "total": total_files,
        "successful": len(results)
    })
    log_job_event(app_logger, job_id, "completed", total=total_files, successful=len(results), failed=len(failed))
    
    # Save to database
    logger.info(f"💾 Saving job {job_id} with {len(results)} results")
    save_job(job_id, processing_jobs[job_id], processing_jobs[job_id].get("user_id"))
    logger.info(f"✅ Job saved, now saving invoices")
    # --- E-Rechnungs-Metadaten anreichern ---------------------------
    enriched_results = []
    for invoice in results:
        source_format = invoice.get("source_format") or "pdf"
        einvoice_raw_xml = (
            invoice.get("einvoice_raw_xml")
            or invoice.get("raw_xml")
            or invoice.get("xml")
            or ""
        )
        einvoice_profile = invoice.get("einvoice_profile", "")
        is_valid, message, detected_profile = validate_einvoice(einvoice_raw_xml)
        if detected_profile and not einvoice_profile:
            einvoice_profile = detected_profile
        invoice["source_format"] = source_format
        invoice["einvoice_raw_xml"] = einvoice_raw_xml
        invoice["einvoice_profile"] = einvoice_profile
        invoice["einvoice_valid"] = bool(is_valid)
        invoice["einvoice_validation_message"] = message or ""
        enriched_results.append(invoice)
    # ---------------------------------------------------------------
    if results:
        logger.info(f"💾 Saving {len(results)} invoices to database")
        save_invoices(job_id, enriched_results)
        # Low-Confidence Warnung prüfen
        check_low_confidence(job_id, enriched_results, config.config if config else None)
        logger.info(f"✅ Invoices saved successfully")
        
        # Check for duplicates (Hash + AI)
        from database import get_invoices_for_job
        from duplicate_detection import get_duplicates_for_invoice, detect_all_duplicates
        saved_invoices = get_invoices_by_job(job_id)
        duplicate_count = 0
        similar_count = 0
        
        for inv in saved_invoices:
            # Check existing duplicates from hash
            duplicates = get_duplicates_for_invoice(inv['id'])
            if duplicates:
                duplicate_count += len(duplicates)
            
            # Run AI similarity check (only if no hash duplicate found)
            if not duplicates:
                dup_results = detect_all_duplicates(dict(inv), job.get('user_id'))
                if dup_results['similar']:
                    similar_count += len(dup_results['similar'])
                    # Save AI-detected similarities
                    from duplicate_detection import save_duplicate_detection
                    for sim in dup_results['similar']:
                        save_duplicate_detection(inv['id'], sim['id'], method='ai', confidence=sim['confidence'])
        
        total_issues = duplicate_count + similar_count
        if total_issues > 0:
            logger.warning(f"⚠️ {duplicate_count} exact + {similar_count} similar duplicate(s) detected!")
            processing_jobs[job_id]['duplicates_detected'] = total_issues
    else:
        logger.warning("⚠️ No results to save!")
    
    # Auto-Kategorisierung
    try:
        from database import assign_category_to_invoice, get_invoices_by_job
        # Hole die gespeicherten Invoices mit IDs
        saved_invoices = get_invoices_by_job(job_id)
        for invoice in saved_invoices:
            category_id, confidence, reasoning = predict_category(invoice, job.get("user_id"))
            assign_category_to_invoice(invoice['id'], category_id, confidence, 'ai')
            logger.info(f"📊 Invoice {invoice['id']}: Category {category_id} (conf: {confidence:.2f})")
    except Exception as e:
        logger.warning(f"Auto-categorization failed: {e}")

    
    # Track invoice usage
    if results and job.get("user_id"):
        from database import increment_invoice_usage
        increment_invoice_usage(job["user_id"], len(results))
    
    # Schedule cleanup of uploaded PDFs (nach 60 Minuten)
    asyncio.create_task(cleanup_uploads(upload_path, delay_minutes=60))
@app.get("/api/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
async def get_status(job_id: str):
    """Get processing status"""
    if job_id not in processing_jobs:
        raise JobNotFoundError(job_id)
    
    job = processing_jobs[job_id]
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "files_count": len(job["files"]),
        "processed": job.get("successful", 0),
        "total": job.get("total", len(job["files"])),
        "created_at": job["created_at"]
    }


@app.get("/api/results/{job_id}", tags=["Jobs"])
async def get_results(job_id: str):
    """Get processing results"""
    if job_id not in processing_jobs:
        raise JobNotFoundError(job_id)
    
    job = processing_jobs[job_id]
    
    if job["status"] != "completed":
        return {
            "job_id": job_id,
            "status": job["status"],
            "message": "Processing not complete yet"
        }
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "stats": job.get("stats"),
        "results_count": len(job.get("results", [])),
        "failed_count": len(job.get("failed", [])),
        "exported_files": job.get("exported_files", {})
    }


@app.get("/api/download/{job_id}/{format}", tags=["Export"])
async def download_export(job_id: str, format: str):
    """Download exported file"""
    from database import get_job
    
    # Try RAM first, then DB
    if job_id in processing_jobs:
        job = processing_jobs[job_id]
    else:
        job = get_job(job_id)
        if not job:
            raise JobNotFoundError(job_id)
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Processing not complete")
    
    exported_files = job.get("exported_files", {})
    
    if format not in exported_files:
        raise HTTPException(status_code=404, detail=f"Format {format} not found")
    
    file_path = exported_files[format]
    
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type='application/octet-stream',
        filename=Path(file_path).name
    )


@app.get("/results/{job_id}", response_class=HTMLResponse)
async def results_page(request: Request, job_id: str):
    """Results page - with DB fallback"""
    from database import get_job
    
    # Try RAM first (for active jobs)
    if job_id in processing_jobs:
        job = processing_jobs[job_id]
    else:
        # Fallback to DB (for completed jobs)
        job = get_job(job_id)
        if not job:
            raise JobNotFoundError(job_id)
    
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "job_id": job_id,
            "job": job
        }
    )



def _get_backup_info():
    """Holt Backup-Status für Health-Check"""
    try:
        from backup import get_backup_status
        return get_backup_status()
    except Exception:
        return {"error": "Backup-Modul nicht verfügbar"}

@app.get("/health", tags=["System"])
async def health_check(request: Request):
    """
    Health check endpoint mit HTML-Dashboard für Browser
    und JSON für Monitoring / Uptime-Checks.
    """
    import time
    import json
    from database import get_connection

    # DB-Check
    db_status = "healthy"
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Uptime seit App-Start
    uptime_seconds = time.time() - app_start_time if "app_start_time" in globals() else 0
    uptime_hours = round(uptime_seconds / 3600, 1)

    backup_info = _get_backup_info()

    data = {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "1.0.0",
        "database": db_status,
        "jobs_in_memory": len(processing_jobs),
        "uptime_hours": uptime_hours,
        "backup": backup_info,
    }

    # JSON-Variante für Monitoring (UptimeRobot, k8s-Probes, etc.)
    accept = (request.headers.get("accept") or "")
    if "application/json" in accept and "text/html" not in accept:
        return JSONResponse(data)

    # Für Browser: hübsches HTML-Dashboard via Template
    backup_json = json.dumps(backup_info, indent=2, ensure_ascii=False)
    raw_json = json.dumps(data, indent=2, ensure_ascii=False)

    return templates.TemplateResponse(
        "health.html",
        {
            "request": request,
            "data": data,
            "backup_json": backup_json,
            "raw_json": raw_json,
        },
    )


@app.get("/api/health", tags=["System"])
async def health_check_json():
    """Health check - JSON only (für Monitoring/Tests)"""
    import time
    from database import get_connection
    
    db_status = "healthy"
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    uptime_seconds = time.time() - app_start_time if "app_start_time" in globals() else 0
    uptime_hours = round(uptime_seconds / 3600, 1)
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "1.0.0",
        "database": db_status,
        "jobs_in_memory": len(processing_jobs),
        "uptime_hours": uptime_hours,
        "backup": _get_backup_info()
    }

@app.get("/api/system/status", tags=["System"])
async def system_status():
    """Detaillierter System-Status mit Alerts"""
    return get_system_status()

@app.post("/api/system/check", tags=["System"])
async def trigger_system_check(request: Request):
    """Manueller System-Check (nur Admin)"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    alerts = run_system_check()
    return {"alerts": alerts, "count": len(alerts)}
@app.post("/api/send-email/{job_id}", tags=["Notifications"])
async def send_email_route(job_id: str, request: Request):
    """Send files via email"""
    try:
        body = await request.json()
        emails = body.get('emails', [])
        
        if not emails:
            return {"success": False, "error": "Keine Email-Adressen angegeben"}
        
        if job_id not in processing_jobs:
            return {"success": False, "error": "Job nicht gefunden"}
        
        job = processing_jobs[job_id]
        
        if job["status"] != "completed":
            return {"success": False, "error": "Verarbeitung noch nicht abgeschlossen"}
        
        # Email senden
        
        stats = job.get("stats")
        exported_files = job.get("exported_files", {})
        
        # Temporäre Email-Config mit Custom-Empfängern
        email_config = config.config.copy()
        email_config['notifications']['email']['to_addresses'] = emails
        
        # Sende Email
        from notifications import send_notifications, check_low_confidence
        result = send_notifications(email_config, stats, exported_files)
        
        if result.get('email'):
            return {"success": True}
        else:
            return {"success": False, "error": "Email konnte nicht gesendet werden"}
            
    except Exception as e:
        print(f"Email error: {e}")
        return {"success": False, "error": str(e)}

async def cleanup_uploads(upload_path: Path, delay_minutes: int = 60):
    """
    Löscht Upload-Ordner nach X Minuten (DSGVO-Compliance)
    """
    await asyncio.sleep(delay_minutes * 60)  # Warte X Minuten
    
    try:
        if upload_path.exists():
            shutil.rmtree(upload_path)
            print(f"🗑️  Auto-Cleanup: {upload_path} gelöscht (nach {delay_minutes} Min)")
    except Exception as e:
        print(f"⚠️  Cleanup-Fehler: {e}")


@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    from email_scheduler import email_scheduler
    email_scheduler.start()



# =====================================================
# PASSWORD RESET ROUTES
# =====================================================






def require_login(request: Request):
    """Prüft, ob ein Benutzer eingeloggt ist.

    Rückgabe:
      - None, wenn eingeloggt
      - RedirectResponse auf /login, wenn nicht
    """
    from fastapi.responses import RedirectResponse

    # Session auslesen
    try:
        user_id = request.session.get("user_id")
    except Exception:
        user_id = None

    if user_id:
        return None

    # Zielseite merken
    next_url = str(request.url.path or "/")
    if request.url.query:
        next_url += "?" + str(request.url.query)

    login_url = f"/login?next={next_url}"
    return RedirectResponse(url=login_url, status_code=303)


def require_admin(request: Request):
    """Prüft ob User Admin ist. Gibt None wenn OK, sonst Redirect/Error."""
    from fastapi.responses import RedirectResponse
    from database import get_connection
    
    # Erst Login prüfen
    login_check = require_login(request)
    if login_check:
        return login_check
    
    # Admin-Status prüfen
    user_id = request.session.get("user_id")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        # Nicht Admin - zurück zur History mit Fehlermeldung
        return RedirectResponse(url="/history?error=admin_required", status_code=303)
    
    return None

def is_admin_user(user_id: int) -> bool:
    """Hilfsfunktion: Prüft ob User Admin ist."""
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row[0])

    if not user_id:
        from fastapi.responses import RedirectResponse
        next_url = request.url.path
        return RedirectResponse(url=f"/login?next={next_url}", status_code=303)
    return None


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):

    redirect = require_login(request)
    if redirect:
        return redirect
    """Dashboard with job history"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    jobs = get_all_jobs(limit=50, user_id=request.session["user_id"])
    stats = get_statistics(user_id=request.session["user_id"])
    
    return templates.TemplateResponse("history.html", {
        "request": request,
        "jobs": jobs,
        "stats": stats
    })

@app.get("/job_old/{job_id}", response_class=HTMLResponse)
async def job_details_page_old(request: Request, job_id: str):
    # Detailed job view mit RAM + DB Fallback
    from database import (
        get_job,
        get_invoices_by_job,
        get_plausibility_warnings_for_job,
        get_invoice_categories,
        get_duplicates_for_job,
    )

    # 1) Erst im RAM nachschauen (frisch verarbeitete Jobs)
    job = processing_jobs.get(job_id)

    # 2) Falls nicht im RAM, aus der Datenbank laden
    if not job:
        job = get_job(job_id)

    # 3) Wenn weder RAM noch DB etwas kennen → echter 404
    if not job:
        raise JobNotFoundError(job_id)

    # 4) Rechnungen zum Job aus der DB laden
    invoices = get_invoices_by_job(job_id)

    # Kategorien zu den Rechnungen anhängen
    for inv in invoices:
        inv["categories"] = get_invoice_categories(inv["id"])

    # 5) Aussteller-Statistik berechnen
    aussteller_stats = {}
    for inv in invoices:
        name = inv.get("rechnungsaussteller", "Unbekannt")
        stats = aussteller_stats.setdefault(
            name, {"name": name, "count": 0, "total": 0}
        )
        stats["count"] += 1
        stats["total"] += inv.get("betrag_brutto", 0) or 0

    aussteller_list = sorted(
        aussteller_stats.values(), key=lambda x: x["total"], reverse=True
    )

    # 6) Duplikate & Plausibilitätsprüfungen laden
    duplicates = get_duplicates_for_job(job_id)
    plausibility_warnings = get_plausibility_warnings_for_job(job_id)

    # 7) Template rendern
    return templates.TemplateResponse(
        "job_details.html",
        {
            "request": request,
            "job_id": job_id,
            "job": job,
            "invoices": invoices,
            "aussteller_stats": aussteller_list,
            "plausibility_warnings": plausibility_warnings,
            "duplicates": duplicates,
        },
    )


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Expense analytics dashboard"""
    redirect = require_login(request)
    if redirect:
        return redirect
    
    from database import get_analytics_data, get_analytics_insights, get_confidence_distribution, get_method_distribution
    
    user_id = request.session.get("user_id")
    data = get_analytics_data(user_id=user_id)
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "stats": data['stats'],
        "monthly_labels": data['monthly_labels'],
        "monthly_values": data['monthly_values'],
        "top_suppliers": data['top_suppliers'],
        "weekday_data": data['weekday_data'],
        "insights": get_analytics_insights(user_id=user_id),
        "confidence_distribution": get_confidence_distribution(user_id=user_id)["distribution"],
        "method_distribution": get_method_distribution(user_id=user_id)["distribution"]
    })

@app.get("/admin", response_class=HTMLResponse, tags=["Admin"])
async def admin_page(request: Request):
    """Admin Dashboard - nur für Admins"""
    admin_check = require_admin(request)
    if admin_check:
        return admin_check
    
    # Admin-Stats sammeln
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices")
    total_invoices = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(SUM(betrag_brutto), 0) FROM invoices")
    total_amount = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE DATE(created_at) = DATE('now')")
    invoices_today = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE DATE(created_at) = DATE('now')")
    jobs_today = cursor.fetchone()[0]
    
    conn.close()
    
    stats = {
        "total_users": total_users,
        "total_invoices": total_invoices,
        "total_jobs": total_jobs,
        "total_amount": total_amount,
        "invoices_today": invoices_today,
        "jobs_today": jobs_today,
        "new_users_week": 0
    }
    
    # Health-Check
    import requests as req
    try:
        health = req.get("http://localhost:8000/health", timeout=2).json()
    except:
        health = {"database": "unknown", "uptime_hours": 0, "backup": {"total_backups": 0}, "jobs_in_memory": 0}
    
    # Audit-Logs
    audit_logs = get_audit_logs(limit=20)
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "stats": stats,
        "health": health,
        "audit_logs": audit_logs
    })

@app.get("/admin/users", response_class=HTMLResponse, tags=["Admin"])
async def admin_users_page(request: Request):
    """User Management - nur für Admins"""
    admin_check = require_admin(request)
    if admin_check:
        return admin_check
    
    from database import get_connection
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.*, COUNT(i.id) as invoice_count
        FROM users u
        LEFT JOIN jobs j ON u.id = j.user_id
        LEFT JOIN invoices i ON j.job_id = i.job_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """)
    users = cursor.fetchall()
    
    conn.row_factory = None
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE created_at > datetime('now', '-7 days')")
    new_this_week = cursor.fetchone()[0]
    conn.close()
    
    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "users": users,
        "new_this_week": new_this_week
    })

@app.post("/api/admin/users", tags=["Admin"])
async def create_user(request: Request):
    """Neuen User anlegen"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    from database import get_connection
    import hashlib
    
    data = await request.json()
    password_hash = hashlib.sha256(data["password"].encode()).hexdigest()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (data.get("name"), data["email"], password_hash))
    conn.commit()
    conn.close()
    
    return {"success": True}

@app.put("/api/admin/users/{user_id}", tags=["Admin"])
async def update_user_admin(user_id: int, request: Request):
    """User bearbeiten"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    from database import get_connection
    data = await request.json()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = ?, email = ? WHERE id = ?",
        (data.get("name"), data["email"], user_id))
    conn.commit()
    conn.close()
    
    return {"success": True}

@app.post("/api/admin/users/{user_id}/toggle", tags=["Admin"])
async def toggle_user_status(user_id: int, request: Request):
    """User aktivieren/deaktivieren"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    from database import get_connection
    data = await request.json()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (data["is_active"], user_id))
    conn.commit()
    conn.close()
    
    return {"success": True}


@app.get("/exports", response_class=HTMLResponse, tags=["Export"])
async def export_history_page(request: Request):
    """Export-Historie anzeigen"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/login?next=/exports", status_code=303)
    
    from database import get_export_history, get_export_stats
    
    user_id = request.session["user_id"]
    exports = get_export_history(user_id)
    stats = get_export_stats(user_id)
    
    return templates.TemplateResponse("export_history.html", {
        "request": request,
        "exports": exports,
        "stats": stats
    })

@app.get("/api/invoice/{invoice_id}")
async def get_invoice(invoice_id: int):
    """Get single invoice for editing"""
    from database import get_invoice_by_id
    
    invoice = get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice

@app.put("/api/invoice/{invoice_id}")
async def update_invoice_endpoint(invoice_id: int, request: Request):
    """Update invoice with corrections and save for learning"""
    from database import get_invoice_by_id, update_invoice, save_correction
    
    # Get current invoice
    current = get_invoice_by_id(invoice_id)
    if not current:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get updates from request
    updates = await request.json()
    
    # Save corrections for learning
    supplier = current.get('rechnungsaussteller', '')
    for field, new_value in updates.items():
        old_value = current.get(field, '')
        if str(old_value) != str(new_value):
            save_correction(invoice_id, supplier, field, str(old_value), str(new_value))
    
    # Update invoice
    update_invoice(invoice_id, updates)
    
    return {"success": True, "message": "Invoice updated and corrections saved for learning"}

@app.get("/api/supplier/{supplier}/patterns")
async def get_supplier_patterns_endpoint(supplier: str):
    """Get learned patterns for a supplier"""
    from database import get_supplier_patterns
    from urllib.parse import unquote
    
    supplier = unquote(supplier)
    patterns = get_supplier_patterns(supplier)
    
    return patterns

@app.get("/api/invoice/{invoice_id}")
async def get_invoice(invoice_id: int):
    """Get single invoice for editing"""
    from database import get_invoice_by_id
    
    invoice = get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice

@app.put("/api/invoice/{invoice_id}")
async def update_invoice_endpoint(invoice_id: int, request: Request):
    """Update invoice with corrections and save for learning"""
    from database import get_invoice_by_id, update_invoice, save_correction
    
    # Get current invoice
    current = get_invoice_by_id(invoice_id)
    if not current:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get updates from request
    updates = await request.json()
    
    # Save corrections for learning
    supplier = current.get('rechnungsaussteller', '')
    for field, new_value in updates.items():
        old_value = current.get(field, '')
        if str(old_value) != str(new_value):
            save_correction(invoice_id, supplier, field, str(old_value), str(new_value))
    
    # Update invoice
    update_invoice(invoice_id, updates)
    
    return {"success": True, "message": "Invoice updated and corrections saved for learning"}

@app.get("/api/supplier/{supplier}/patterns")
async def get_supplier_patterns_endpoint(supplier: str):
    """Get learned patterns for a supplier"""
    from database import get_supplier_patterns
    from urllib.parse import unquote
    
    supplier = unquote(supplier)
    patterns = get_supplier_patterns(supplier)
    
    return patterns


@app.get("/upload-progress", response_class=HTMLResponse)
async def upload_progress_page(request: Request):
    """Upload page with real-time progress"""
    return templates.TemplateResponse("upload_progress.html", {"request": request})

@app.get("/email-config", response_class=HTMLResponse)
async def email_config_page(request: Request):
    """Email inbox configuration page"""
    from database import get_email_config
    
    config = get_email_config()
    
    return templates.TemplateResponse("email_config.html", {
        "request": request,
        "config": config
    })

@app.post("/api/email-config")
async def save_email_config_endpoint(request: Request):
    """Save email inbox configuration"""
    from database import save_email_config
    
    try:
        config = await request.json()
        save_email_config(config)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/email-config/test")
async def test_email_connection(request: Request):
    """Test IMAP connection"""
    import imaplib
    
    try:
        config = await request.json()
        
        # Try to connect
        conn = imaplib.IMAP4_SSL(
            config['imap_server'],
            config.get('imap_port', 993)
        )
        conn.login(config['username'], config['password'])
        conn.logout()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/email-config/check-now")
async def check_emails_now():
    """Manually trigger email check"""
    try:
        from email_fetcher import check_inbox_and_process
        check_inbox_and_process()
        return {"success": True, "message": "Email check completed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# === WebSocket Endpoint ===
from websocket_handler import manager

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job updates"""
    await websocket.accept()
    await manager.connect(websocket, job_id)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, job_id)

# Session Management
from starlette.middleware.sessions import SessionMiddleware
import secrets

from email_scheduler import email_scheduler
# Add session middleware (muss nach app = FastAPI() kommen)
app.add_middleware(SessionMiddleware, secret_key='sbs-invoice-app-secret-key-2025', domain='.sbsdeutschland.com')

# -------------------------------------------------
# Login-Helper & globale Login-Pflicht
# -------------------------------------------------

def require_login(request: Request):
    """Prüft, ob ein Benutzer eingeloggt ist.

    Rückgabe:
      - None, wenn eingeloggt
      - RedirectResponse auf /login, wenn nicht
    """
    from fastapi.responses import RedirectResponse

    # Session auslesen
    try:
        user_id = request.session.get("user_id")
    except Exception:
        user_id = None

    if user_id:
        return None

    # Zielseite merken
    next_url = str(request.url.path or "/")
    if request.url.query:
        next_url += "?" + str(request.url.query)

    login_url = f"/login?next={next_url}"
    return RedirectResponse(url=login_url, status_code=303)


    if not user_id:
        login_url = f"/login?next={request.url.path}"
        return RedirectResponse(url=login_url, status_code=303)

    return None




@app.get("/demo", response_class=HTMLResponse)
async def demo_page(request: Request):
    """Öffentliche Schwarzes-Loch-Demo ohne Login."""
    return templates.TemplateResponse("demo.html", {"request": request})

@app.post("/demo", response_class=HTMLResponse)
async def demo_start(request: Request):
    """
    Startet die Demo und leitet auf eine statische Demo-Job-Seite um.
    Hochgeladene Dateien werden in dieser kostenlosen Demo nicht dauerhaft gespeichert.
    """
    return RedirectResponse(url="/jobs/demo", status_code=303)

@app.get("/jobs/demo", response_class=HTMLResponse)
async def demo_job(request: Request):
    """
    Statische Job-Seite für die kostenlose Demo mit zwei Beispielrechnungen.
    """
    return templates.TemplateResponse(
        "demo_job.html",
        {"request": request}
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })

@app.post("/login")
async def login_submit(request: Request):
    """Verarbeitet das Login-Formular.

    - prüft Credentials
    - setzt Session
    - leitet auf gewünschte Seite weiter
    """
    from fastapi.responses import RedirectResponse
    # Rate Limiting: 5 Login-Versuche pro Minute
    check_rate_limit(request, "auth")
    from database import verify_user
    import logging

    logger = logging.getLogger("invoice_app")

    form = await request.form()
    email = (form.get("email") or "").strip()
    password = form.get("password") or ""
    next_url = form.get("next") or request.query_params.get("next") or "/history"

    logger.info(f"LOGIN_DEBUG: POST /login email={email}, next={next_url}")

    user = verify_user(email, password)

    if not user:
        logger.info("LOGIN_DEBUG: ungültige Credentials")
        log_audit(AuditAction.LOGIN_FAILED, user_email=email, ip_address=request.client.host)
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Ungültige Email oder Passwort",
                "next": next_url,
                "email": email,
            },
            status_code=400,
        )

    # Session setzen
    try:
        request.session["user_id"] = user["id"]
        request.session["user_name"] = user.get("name") or email.split("@")[0]
        logger.info(f"LOGIN_DEBUG: Session gesetzt user_id={user['id']}")
    except Exception as exc:
        logger.error(f"LOGIN_DEBUG: Fehler beim Setzen der Session: {exc}")

    # Sicherheit: nur interne relative Pfade
    if not next_url.startswith("/") or "://" in next_url:
        next_url = "/history"

    logger.info(f"LOGIN_DEBUG: redirect -> {next_url}")
    log_audit(AuditAction.LOGIN, user_id=user["id"], user_email=email, ip_address=request.client.host)
    return RedirectResponse(url=next_url, status_code=303)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Register page"""
    return templates.TemplateResponse("register.html", {
        "request": request,
        "error": None
    })

@app.post("/register")
async def register_submit(request: Request):
    """Handle registration"""
    from database import create_user, email_exists
    
    form = await request.form()
    name = form.get('name', '')
    email = form.get('email', '')
    company = form.get('company', '')
    password = form.get('password', '')
    password2 = form.get('password2', '')
    
    # Validation
    if not email or not password:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Email und Passwort sind erforderlich"
        })
    
    if password != password2:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Passwörter stimmen nicht überein"
        })
    
    # Enterprise Passwort-Anforderungen
    if len(password) < 8:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Passwort muss mindestens 8 Zeichen haben"
        })
    
    import re
    if not re.search(r'[A-Z]', password):
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Passwort muss mindestens einen Großbuchstaben enthalten"
        })
    
    if not re.search(r'[a-z]', password):
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Passwort muss mindestens einen Kleinbuchstaben enthalten"
        })
    
    if not re.search(r'[0-9]', password):
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Passwort muss mindestens eine Zahl enthalten"
        })
    
    if email_exists(email):
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Email ist bereits registriert"
        })
    
    # Create user
    user_id = create_user(email, password, name, company)
    
    # Auto-login
    request.session['user_id'] = user_id
    request.session['user_name'] = name or email.split('@')[0]
    request.session['user_email'] = email
    
    from starlette.responses import RedirectResponse
    next_url = request.query_params.get('next', '/')
    return RedirectResponse(url=next_url, status_code=303)

@app.get("/logout")
async def logout(request: Request):
    """
    Logout und Redirect auf die SBS Homepage.
    """
    # Session leeren, falls vorhanden
    try:
        session = getattr(request, "session", None)
        if isinstance(session, dict):
            session.pop("user_id", None)
            session.pop("user_name", None)
            session.pop("user_email", None)
    except AssertionError:
        # Keine SessionMiddleware aktiv – nichts zu tun
        pass

    return RedirectResponse(
        url="https://sbsdeutschland.com/sbshomepage/",
        status_code=303,
    )

@app.get("/api/user", tags=["Auth"])
async def get_current_user(request: Request):
    """Get current logged in user"""
    if 'user_id' in request.session:
        # Admin-Status prüfen
        is_admin = is_admin_user(request.session.get('user_id', 0))
        return {
            "logged_in": True,
            "name": request.session.get('user_name', ''),
            "email": request.session.get('user_email', ''),
            "is_admin": is_admin
        }
    return {"logged_in": False, "is_admin": False}

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Profile settings page"""
    if 'user_id' not in request.session:
        from starlette.responses import RedirectResponse
        return RedirectResponse(url='/login', status_code=303)
    
    from database import get_user_by_id
    user = get_user_by_id(request.session['user_id'])
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user
    })

@app.put("/api/profile")
async def update_profile(request: Request):
    """Update user profile"""
    if 'user_id' not in request.session:
        return {"success": False, "error": "Not logged in"}
    
    try:
        data = await request.json()
        # TODO: Update user in database
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/api/profile/password")
async def change_password(request: Request):
    """Change user password"""
    if 'user_id' not in request.session:
        return {"success": False, "error": "Not logged in"}
    
    try:
        data = await request.json()
        # TODO: Verify old password and update
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === API Keys Management ===
@app.get("/api/keys", tags=["API Keys"])
async def get_api_keys(request: Request):
    """Liste alle API-Keys des Users"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    keys = list_api_keys(request.session["user_id"])
    return {"keys": keys}

@app.post("/api/keys", tags=["API Keys"])
async def create_new_api_key(request: Request):
    """Erstellt einen neuen API-Key"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    name = data.get("name", "API Key")
    permissions = data.get("permissions", "read")
    
    result = create_api_key(
        user_id=request.session["user_id"],
        name=name,
        permissions=permissions
    )
    
    return {"success": True, "key": result}

@app.delete("/api/keys/{key_id}", tags=["API Keys"])
async def delete_api_key(key_id: int, request: Request):
    """Widerruft einen API-Key"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    success = revoke_api_key(key_id, request.session["user_id"])
    return {"success": success}


# === Webhooks Management ===
@app.get("/api/webhooks", tags=["Webhooks"])
async def get_user_webhooks(request: Request):
    """Liste alle Webhooks des Users"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    webhooks = get_webhooks(request.session["user_id"])
    return {"webhooks": webhooks}

@app.post("/api/webhooks", tags=["Webhooks"])
async def create_new_webhook(request: Request):
    """Erstellt einen neuen Webhook"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    url = data.get("url")
    events = data.get("events", ["job.completed"])
    name = data.get("name", "Webhook")
    
    if not url:
        return JSONResponse({"error": "URL required"}, status_code=400)
    
    result = create_webhook(
        user_id=request.session["user_id"],
        url=url,
        events=events,
        name=name
    )
    
    return {"success": True, "webhook": result}

@app.delete("/api/webhooks/{webhook_id}", tags=["Webhooks"])
async def delete_user_webhook(webhook_id: int, request: Request):
    """Löscht einen Webhook"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    success = delete_webhook(webhook_id, request.session["user_id"])
    return {"success": success}

# === Two-Factor Authentication ===
from two_factor import (
    enable_2fa, verify_and_activate_2fa, disable_2fa,
    check_2fa_required, verify_user_2fa, generate_backup_codes
)

@app.get("/api/2fa/setup", tags=["Auth"])
async def setup_2fa(request: Request):
    """Startet 2FA-Setup und gibt QR-Code zurück"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    result = enable_2fa(request.session["user_id"])
    return result

@app.post("/api/2fa/verify", tags=["Auth"])
async def verify_2fa_setup(request: Request):
    """Verifiziert Code und aktiviert 2FA"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    code = data.get("code", "")
    
    if verify_and_activate_2fa(request.session["user_id"], code):
        backup_codes = generate_backup_codes(request.session["user_id"])
        return {"success": True, "backup_codes": backup_codes}
    
    return JSONResponse({"error": "Invalid code"}, status_code=400)

@app.post("/api/2fa/disable", tags=["Auth"])
async def disable_2fa_endpoint(request: Request):
    """Deaktiviert 2FA"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    code = data.get("code", "")
    
    if disable_2fa(request.session["user_id"], code):
        return {"success": True}
    
    return JSONResponse({"error": "Invalid code"}, status_code=400)

@app.get("/api/2fa/status", tags=["Auth"])
async def get_2fa_status(request: Request):
    """Prüft ob 2FA aktiviert ist"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    enabled = check_2fa_required(request.session["user_id"])
    return {"enabled": enabled}

# === Organizations / Multi-Tenancy ===
from organizations import (
    create_organization, get_organization, get_user_organizations,
    add_member, remove_member, get_org_members, switch_organization,
    get_current_org, check_permission, OrgRole, get_org_stats
)

@app.get("/api/organizations", tags=["Organizations"])
async def list_organizations(request: Request):
    """Liste aller Organisationen des Users"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    orgs = get_user_organizations(request.session["user_id"])
    current = get_current_org(request.session["user_id"])
    return {"organizations": orgs, "current": current}

@app.post("/api/organizations", tags=["Organizations"])
async def create_org(request: Request):
    """Erstellt neue Organisation"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    name = data.get("name", "").strip()
    
    if not name:
        return JSONResponse({"error": "Name required"}, status_code=400)
    
    org = create_organization(name, request.session["user_id"])
    return {"success": True, "organization": org}

@app.post("/api/organizations/{org_id}/switch", tags=["Organizations"])
async def switch_org(org_id: int, request: Request):
    """Wechselt aktive Organisation"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    if switch_organization(request.session["user_id"], org_id):
        return {"success": True}
    return JSONResponse({"error": "Not a member"}, status_code=403)

@app.get("/api/organizations/{org_id}/members", tags=["Organizations"])
async def list_org_members(org_id: int, request: Request):
    """Liste Mitglieder einer Organisation"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    if not check_permission(request.session["user_id"], org_id, OrgRole.VIEWER):
        return JSONResponse({"error": "No permission"}, status_code=403)
    
    members = get_org_members(org_id)
    return {"members": members}

@app.post("/api/organizations/{org_id}/members", tags=["Organizations"])
async def add_org_member(org_id: int, request: Request):
    """Fügt Mitglied hinzu"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    if not check_permission(request.session["user_id"], org_id, OrgRole.ADMIN):
        return JSONResponse({"error": "Admin required"}, status_code=403)
    
    data = await request.json()
    user_id = data.get("user_id")
    role = data.get("role", OrgRole.MEMBER)
    
    if add_member(org_id, user_id, role):
        return {"success": True}
    return JSONResponse({"error": "Failed"}, status_code=400)

@app.get("/api/organizations/{org_id}/stats", tags=["Organizations"])
async def org_stats(org_id: int, request: Request):
    """Statistiken der Organisation"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    if not check_permission(request.session["user_id"], org_id, OrgRole.VIEWER):
        return JSONResponse({"error": "No permission"}, status_code=403)
    
    stats = get_org_stats(org_id)
    org = get_organization(org_id)
    return {"organization": org, "stats": stats}

# === Scheduled Reports ===
from scheduled_reports import (
    create_scheduled_report, get_user_reports, delete_report,
    toggle_report, ReportType, Schedule
)

@app.get("/api/reports/scheduled", tags=["Reports"])
async def list_scheduled_reports(request: Request):
    """Liste aller geplanten Berichte"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    reports = get_user_reports(request.session["user_id"])
    return {"reports": reports}

@app.post("/api/reports/scheduled", tags=["Reports"])
async def create_report(request: Request):
    """Erstellt neuen geplanten Bericht"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    
    report = create_scheduled_report(
        user_id=request.session["user_id"],
        name=data.get("name", "Bericht"),
        report_type=data.get("report_type", ReportType.SUMMARY),
        schedule=data.get("schedule", Schedule.WEEKLY),
        recipients=data.get("recipients", []),
        filters=data.get("filters", {})
    )
    
    return {"success": True, "report": report}

@app.delete("/api/reports/scheduled/{report_id}", tags=["Reports"])
async def remove_report(report_id: int, request: Request):
    """Löscht geplanten Bericht"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    success = delete_report(report_id, request.session["user_id"])
    return {"success": success}

@app.post("/api/reports/scheduled/{report_id}/toggle", tags=["Reports"])
async def toggle_scheduled_report(report_id: int, request: Request):
    """Aktiviert/deaktiviert Bericht"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    active = data.get("active", True)
    
    success = toggle_report(report_id, request.session["user_id"], active)
    return {"success": success}


# === Auto-Kontierung ===
from auto_accounting import (
    suggest_account, suggest_account_with_llm, batch_suggest_accounts,
    learn_from_correction, SKR03_ACCOUNTS
)

@app.post("/api/accounting/suggest", tags=["Accounting"])
async def suggest_booking_account(request: Request):
    """KI-Kontenvorschlag für eine Rechnung"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    skr = data.get("skr", "SKR03")
    
    result = suggest_account_with_llm(data, skr)
    return result

@app.post("/api/accounting/suggest/batch", tags=["Accounting"])
async def suggest_accounts_batch(request: Request):
    """KI-Kontenvorschläge für mehrere Rechnungen"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    invoices = data.get("invoices", [])
    skr = data.get("skr", "SKR03")
    
    results = batch_suggest_accounts(invoices, request.session["user_id"], skr)
    return {"suggestions": results}

@app.post("/api/accounting/learn", tags=["Accounting"])
async def learn_account_mapping(request: Request):
    """Lernt aus User-Korrektur"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    learn_from_correction(
        request.session["user_id"],
        data.get("invoice", {}),
        data.get("account")
    )
    return {"success": True}

@app.get("/api/accounting/accounts", tags=["Accounting"])
async def list_accounts(request: Request):
    """Liste aller verfügbaren Konten"""
    accounts = [
        {"account": k, "name": v["name"]}
        for k, v in SKR03_ACCOUNTS.items()
    ]
    return {"accounts": sorted(accounts, key=lambda x: x["account"])}

# === SEPA-XML Export ===
from sepa_export import generate_sepa_xml, export_invoices_to_sepa, validate_iban

@app.post("/api/export/sepa", tags=["Export"])
async def export_sepa_xml(request: Request):
    """Generiert SEPA-XML für Zahlungen"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    invoices = data.get("invoices", [])
    debtor = data.get("debtor", {})
    
    if not debtor.get("iban"):
        return JSONResponse({"error": "Absender-IBAN erforderlich"}, status_code=400)
    
    result = export_invoices_to_sepa(invoices, debtor)
    
    if not result.get("success"):
        return JSONResponse({"error": result.get("error"), "warnings": result.get("warnings", [])}, status_code=400)
    
    return {
        "success": True,
        "count": result["count"],
        "total": result["total"],
        "warnings": result["warnings"],
        "xml": result["xml"]
    }

@app.post("/api/job/{job_id}/export/sepa", tags=["Export"])
async def export_job_sepa(job_id: str, request: Request):
    """Exportiert Job-Rechnungen als SEPA-XML"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    debtor = data.get("debtor", {})
    
    if not debtor.get("iban"):
        return JSONResponse({"error": "Absender-IBAN erforderlich"}, status_code=400)
    
    invoices = get_invoices_by_job(job_id)
    if not invoices:
        return JSONResponse({"error": "Keine Rechnungen gefunden"}, status_code=404)
    
    result = export_invoices_to_sepa(invoices, debtor)
    
    if not result.get("success"):
        return JSONResponse({"error": result.get("error"), "warnings": result.get("warnings", [])}, status_code=400)
    
    from database import log_export
    log_export(request.session["user_id"], job_id, "sepa", f"sepa_{job_id[:8]}.xml", len(result["xml"]), result["count"], result["total"])
    
    return Response(
        content=result["xml"],
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=sepa_{job_id[:8]}.xml"}
    )
# === Dashboard Widgets ===
from dashboard_widgets import (
    get_user_widgets, add_widget, update_widget, remove_widget,
    reorder_widgets, get_widget_data, WidgetType
)

@app.get("/api/dashboard/widgets", tags=["Dashboard"])
async def list_widgets(request: Request):
    """Liste aller Widgets des Users"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    widgets = get_user_widgets(request.session["user_id"])
    return {"widgets": widgets}

@app.post("/api/dashboard/widgets", tags=["Dashboard"])
async def create_widget(request: Request):
    """Fügt neues Widget hinzu"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    widget = add_widget(
        request.session["user_id"],
        data.get("widget_type"),
        data.get("size", "medium"),
        data.get("config", {})
    )
    return {"success": True, "widget": widget}

@app.put("/api/dashboard/widgets/{widget_id}", tags=["Dashboard"])
async def edit_widget(widget_id: int, request: Request):
    """Aktualisiert Widget"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    success = update_widget(widget_id, request.session["user_id"], data)
    return {"success": success}

@app.delete("/api/dashboard/widgets/{widget_id}", tags=["Dashboard"])
async def delete_widget(widget_id: int, request: Request):
    """Entfernt Widget"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    success = remove_widget(widget_id, request.session["user_id"])
    return {"success": success}

@app.post("/api/dashboard/widgets/reorder", tags=["Dashboard"])
async def reorder_dashboard(request: Request):
    """Sortiert Widgets neu"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    data = await request.json()
    success = reorder_widgets(request.session["user_id"], data.get("widget_ids", []))
    return {"success": success}

@app.get("/api/dashboard/widgets/{widget_id}/data", tags=["Dashboard"])
async def widget_data(widget_id: int, request: Request):
    """Holt Daten für ein Widget"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    from dashboard_widgets import get_user_widgets
    widgets = get_user_widgets(request.session["user_id"])
    widget = next((w for w in widgets if w["id"] == widget_id), None)
    
    if not widget:
        return JSONResponse({"error": "Widget not found"}, status_code=404)
    
    data = get_widget_data(widget["widget_type"], request.session["user_id"], widget.get("config"))
    return data

# CORS für Cross-Domain API Requests
from starlette.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sbsdeutschland.com", "https://app.sbsdeutschland.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Stripe Integration
import stripe

import os
from dotenv import load_dotenv
load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

STRIPE_PRICES = {
    'starter': 'price_starter_monthly',  # Wird später ersetzt
    'professional': 'price_professional_monthly',
    'enterprise': 'price_enterprise_monthly'
}

@app.post("/api/checkout/create-session")
async def create_checkout_session(request: Request):
    """Create Stripe checkout session"""
    if 'user_id' not in request.session:
        return {"error": "Not logged in"}
    
    try:
        data = await request.json()
        plan = data.get('plan', 'starter')
        
        # Price IDs (in cents)
        prices = {
            'starter': 6900,
            'professional': 17900,
            'enterprise': 44900
        }
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': f'SBS KI-Rechnungsverarbeitung - {plan.title()}',
                        'description': f'Monatliches Abonnement'
                    },
                    'unit_amount': prices.get(plan, 6900),
                    'recurring': {'interval': 'month'}
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://app.sbsdeutschland.com/checkout/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://sbsdeutschland.com/preise',
            metadata={
                'user_id': str(request.session['user_id']),
                'plan': plan
            }
        )
        
        return {"sessionId": session.id, "url": session.url}
    except Exception as e:
        return {"error": str(e)}

@app.get("/checkout/success", response_class=HTMLResponse)
async def checkout_success(request: Request, session_id: str = None):
    """Handle successful checkout"""
    from database import create_subscription
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid':
                user_id = int(session.metadata.get('user_id'))
                plan = session.metadata.get('plan')
                
                create_subscription(
                    user_id=user_id,
                    plan=plan,
                    stripe_customer_id=session.customer,
                    stripe_subscription_id=session.subscription
                )
        except Exception as e:
            print(f"Error processing checkout: {e}")
    
    return templates.TemplateResponse("checkout_success.html", {
        "request": request
    })

@app.get("/api/subscription/status")
async def get_subscription_status(request: Request):
    """Get current subscription status and usage"""
    if 'user_id' not in request.session:
        return {"error": "Not logged in"}
    
    from database import check_invoice_limit
    status = check_invoice_limit(request.session['user_id'])
    return status

@app.post("/api/subscription/cancel")
async def cancel_subscription(request: Request):
    """Cancel user's subscription"""
    if 'user_id' not in request.session:
        return {"error": "Not logged in"}
    
    user_id = request.session['user_id']
    
    # Get subscription
    from database import get_user_subscription
    subscription = get_user_subscription(user_id)
    
    if not subscription:
        return {"error": "Kein aktives Abonnement gefunden"}
    
    try:
        # Cancel in Stripe
        stripe.Subscription.modify(
            subscription['stripe_subscription_id'],
            cancel_at_period_end=True
        )
        
        # Update database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE subscriptions 
            SET status = 'canceling' 
            WHERE id = ?
        ''', (subscription['id'],))
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Abonnement wird zum Ende der Laufzeit gekündigt"}
    except Exception as e:
        return {"error": str(e)}

# Stripe Webhook Endpoint
@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    # Webhook secret (muss in Stripe Dashboard konfiguriert werden)
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        else:
            # Fallback ohne Signatur-Verifizierung (nur für Tests)
            import json
            event = json.loads(payload)
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"error": str(e)}, 400
    
    event_type = event.get('type', event.get('type'))
    data = event.get('data', {}).get('object', {})
    
    print(f"Stripe Webhook: {event_type}")
    
    # Handle different event types
    if event_type == 'checkout.session.completed':
        # Payment successful - already handled in success page
        pass
        
    elif event_type == 'invoice.payment_succeeded':
        # Subscription renewed successfully
        subscription_id = data.get('subscription')
        if subscription_id:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE subscriptions 
                SET status = 'active', invoices_used = 0
                WHERE stripe_subscription_id = ?
            ''', (subscription_id,))
            conn.commit()
            conn.close()
            print(f"Subscription renewed: {subscription_id}")
            
    elif event_type == 'invoice.payment_failed':
        # Payment failed
        subscription_id = data.get('subscription')
        customer_email = data.get('customer_email')
        if subscription_id:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE subscriptions 
                SET status = 'payment_failed'
                WHERE stripe_subscription_id = ?
            ''', (subscription_id,))
            conn.commit()
            conn.close()
            print(f"Payment failed for: {subscription_id}, email: {customer_email}")
            
    elif event_type == 'customer.subscription.deleted':
        # Subscription cancelled
        subscription_id = data.get('id')
        if subscription_id:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE subscriptions 
                SET status = 'cancelled'
                WHERE stripe_subscription_id = ?
            ''', (subscription_id,))
            conn.commit()
            conn.close()
            print(f"Subscription cancelled: {subscription_id}")
            
    elif event_type == 'customer.subscription.updated':
        # Subscription updated (plan change, etc.)
        subscription_id = data.get('id')
        status = data.get('status')
        cancel_at_period_end = data.get('cancel_at_period_end')
        
        if subscription_id:
            new_status = 'canceling' if cancel_at_period_end else status
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE subscriptions 
                SET status = ?
                WHERE stripe_subscription_id = ?
            ''', (new_status, subscription_id,))
            conn.commit()
            conn.close()
            print(f"Subscription updated: {subscription_id}, status: {new_status}")
    
    return {"received": True}

# Email notifications for subscriptions
def send_subscription_email(to_email: str, subject: str, body: str):
    """Send subscription-related emails"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Gmail SMTP settings
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_user = "luisschenk2202@gmail.com"
        smtp_password = os.getenv('GMAIL_APP_PASSWORD', '')
        
        if not smtp_password:
            print("No GMAIL_APP_PASSWORD set")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        print(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_welcome_email(email: str, name: str, plan: str):
    """Send welcome email after subscription"""
    plan_names = {'starter': 'Starter', 'professional': 'Professional', 'enterprise': 'Enterprise'}
    subject = f"Willkommen bei SBS KI-Rechnungsverarbeitung - {plan_names.get(plan, plan)}"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #003856; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">Willkommen bei SBS!</h1>
        </div>
        <div style="padding: 30px;">
            <p>Hallo {name},</p>
            <p>vielen Dank für Ihr Abonnement des <strong>{plan_names.get(plan, plan)}</strong> Plans!</p>
            <p>Sie können jetzt sofort mit der KI-Rechnungsverarbeitung starten:</p>
            <p style="text-align: center;">
                <a href="https://app.sbsdeutschland.com/" style="background: #ffb900; color: #003856; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold;">Jetzt starten</a>
            </p>
            <p>Bei Fragen stehen wir Ihnen gerne zur Verfügung.</p>
            <p>Mit freundlichen Grüßen,<br>Ihr SBS Deutschland Team</p>
        </div>
        <div style="background: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #666;">
            SBS Deutschland GmbH & Co. KG · Weinheim
        </div>
    </body>
    </html>
    """
    send_subscription_email(email, subject, body)

def send_cancellation_email(email: str, name: str):
    """Send email when subscription is cancelled"""
    subject = "Ihr SBS Abonnement wurde gekündigt"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #003856; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">Kündigung bestätigt</h1>
        </div>
        <div style="padding: 30px;">
            <p>Hallo {name},</p>
            <p>Ihr Abonnement wurde gekündigt und läuft zum Ende der aktuellen Abrechnungsperiode aus.</p>
            <p>Sie können den Service bis dahin weiter nutzen.</p>
            <p>Wir würden uns freuen, Sie bald wieder begrüßen zu dürfen!</p>
            <p style="text-align: center;">
                <a href="https://sbsdeutschland.com/preise" style="background: #ffb900; color: #003856; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold;">Erneut abonnieren</a>
            </p>
            <p>Mit freundlichen Grüßen,<br>Ihr SBS Deutschland Team</p>
        </div>
    </body>
    </html>
    """
    send_subscription_email(email, subject, body)

# PDF Invoice Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from io import BytesIO

def generate_invoice_pdf(invoice_data: dict) -> bytes:
    """Generate PDF invoice for subscription"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    elements = []
    
    # Header
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#003856'))
    elements.append(Paragraph("SBS Deutschland", header_style))
    elements.append(Paragraph("Smart Business Service · Weinheim", styles['Normal']))
    elements.append(Spacer(1, 1*cm))
    
    # Invoice title
    elements.append(Paragraph(f"Rechnung Nr. {invoice_data.get('invoice_number', 'N/A')}", styles['Heading2']))
    elements.append(Paragraph(f"Datum: {invoice_data.get('date', 'N/A')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Customer info
    elements.append(Paragraph("<b>Rechnungsempfänger:</b>", styles['Normal']))
    elements.append(Paragraph(invoice_data.get('customer_name', ''), styles['Normal']))
    elements.append(Paragraph(invoice_data.get('customer_email', ''), styles['Normal']))
    elements.append(Spacer(1, 1*cm))
    
    # Items table
    plan_names = {'starter': 'Starter', 'professional': 'Professional', 'enterprise': 'Enterprise'}
    plan_prices = {'starter': '69,00 €', 'professional': '179,00 €', 'enterprise': '449,00 €'}
    
    plan = invoice_data.get('plan', 'starter')
    
    data = [
        ['Beschreibung', 'Betrag'],
        [f'KI-Rechnungsverarbeitung - {plan_names.get(plan, plan)} (Monatlich)', plan_prices.get(plan, '0,00 €')],
    ]
    
    table = Table(data, colWidths=[12*cm, 4*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003856')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 1*cm))
    
    # Footer
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
    elements.append(Paragraph("SBS Deutschland GmbH & Co. KG · Weinheim", footer_style))
    elements.append(Paragraph("Diese Rechnung wurde maschinell erstellt und ist ohne Unterschrift gültig.", footer_style))
    
    doc.build(elements)
    return buffer.getvalue()

@app.get("/api/invoice/{subscription_id}")
async def download_invoice(request: Request, subscription_id: int):
    """Download invoice PDF for a subscription"""
    if 'user_id' not in request.session:
        return {"error": "Not logged in"}
    
    from database import get_user_subscription, get_user_by_id
    
    user = get_user_by_id(request.session['user_id'])
    subscription = get_user_subscription(request.session['user_id'])
    
    if not subscription or subscription['id'] != subscription_id:
        return {"error": "Subscription not found"}
    
    from datetime import datetime
    invoice_data = {
        'invoice_number': f"SBS-{subscription_id}-{datetime.now().strftime('%Y%m')}",
        'date': datetime.now().strftime('%d.%m.%Y'),
        'customer_name': user.get('name', ''),
        'customer_email': user.get('email', ''),
        'plan': subscription.get('plan', 'starter')
    }
    
    pdf_bytes = generate_invoice_pdf(invoice_data)
    
    from fastapi.responses import Response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Rechnung_{invoice_data['invoice_number']}.pdf"}
    )

# Contact Form Endpoint
@app.post("/api/contact")
async def contact_form(request: Request):
    """Handle contact form submissions"""
    try:
        data = await request.json()
        
        name = data.get('name', '')
        email = data.get('email', '')
        phone = data.get('phone', '')
        company = data.get('company', '')
        service = data.get('service', '')
        message = data.get('message', '')
        
        # Send email to SBS
        subject = f"Kontaktanfrage: {service} - {name}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Neue Kontaktanfrage</h2>
            <table style="border-collapse: collapse;">
                <tr><td style="padding: 8px; font-weight: bold;">Service:</td><td style="padding: 8px;">{service}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Name:</td><td style="padding: 8px;">{name}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Email:</td><td style="padding: 8px;">{email}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Telefon:</td><td style="padding: 8px;">{phone or '-'}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Unternehmen:</td><td style="padding: 8px;">{company or '-'}</td></tr>
            </table>
            <h3>Nachricht:</h3>
            <p style="background: #f5f5f5; padding: 16px; border-radius: 8px;">{message}</p>
        </body>
        </html>
        """
        
        # Send to SBS email
        import threading; threading.Thread(target=send_subscription_email, args=("luisschenk2202@gmail.com", subject, body)).start()
        
        # Send confirmation to customer
        confirm_subject = "Ihre Anfrage bei SBS Deutschland"
        confirm_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #003856; color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0;">Vielen Dank!</h1>
            </div>
            <div style="padding: 30px;">
                <p>Hallo {name},</p>
                <p>vielen Dank für Ihre Anfrage. Wir haben Ihre Nachricht erhalten und werden uns innerhalb von 24 Stunden bei Ihnen melden.</p>
                <p><strong>Ihre Anfrage:</strong></p>
                <p style="background: #f5f5f5; padding: 16px; border-radius: 8px;">{message}</p>
                <p>Mit freundlichen Grüßen,<br>Ihr SBS Deutschland Team</p>
            </div>
            <div style="background: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                SBS Deutschland GmbH & Co. KG · Weinheim
            </div>
        </body>
        </html>
        """
        threading.Thread(target=send_subscription_email, args=(email, confirm_subject, confirm_body)).start()
        
        return {"success": True, "message": "Nachricht gesendet"}
    except Exception as e:
        print(f"Contact form error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/test", response_class=HTMLResponse)
async def test_upload_page(request: Request):
    return templates.TemplateResponse("test_upload.html", {"request": request})



# Zusätzliche Navigationsseiten (leichte Placeholder)

@app.get("/copilot", response_class=HTMLResponse)
async def copilot_page(request: Request):
    """
    Vollbild-Finance-Copilot-Seite.
    """
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("copilot.html", {"request": request})


@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):

    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("account.html", {"request": request})

@app.get("/team", response_class=HTMLResponse)
async def team_page(request: Request):
    """Team & Rollen Verwaltung"""
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("team.html", {"request": request})

@app.get("/audit-log", response_class=HTMLResponse)
async def audit_log_page(request: Request):
    """Audit-Log Seite - Protokoll aller Systemaktivitäten"""
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("audit_log.html", {"request": request})


@app.get("/accounting", response_class=HTMLResponse)
async def accounting_page(request: Request):
    """Auto-Kontierung Seite"""
    redirect = require_login(request)
    if redirect:
        return redirect
    
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT job_id, upload_path, total_files, created_at 
        FROM jobs WHERE user_id = ? AND status = 'completed' 
        ORDER BY created_at DESC LIMIT 20
    """, (request.session["user_id"],))
    jobs = [{"job_id": r[0], "filename": r[1] or "Upload", "invoice_count": r[2], "created_at": r[3]} for r in cursor.fetchall()]
    conn.close()
    
    return templates.TemplateResponse("accounting.html", {"request": request, "jobs": jobs})

@app.post("/api/duplicate/{detection_id}/review")
async def review_duplicate(detection_id: int, request: Request):
    """Mark duplicate as reviewed"""
    if "user_id" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    body = await request.json()
    is_duplicate = body.get('is_duplicate', False)
    
    from duplicate_detection import mark_duplicate_reviewed
    mark_duplicate_reviewed(detection_id, request.session['user_id'], is_duplicate)
    
    return {"status": "ok", "message": "Reviewed successfully"}




def validate_einvoice(xml_string: str):
    """
    Sehr einfache E-Rechnungs-Erkennung / -Validierung:
    - Versucht XML zu parsen
    - Erkannt werden grob XRechnung / ZUGFeRD / Factur-X anhand Namespace / Text
    - Gibt (is_valid, message, detected_profile) zurück
    """
    xml = (xml_string or "").strip()
    if not xml:
        return False, "Kein XML übergeben – PDF- oder Basis-Rechnung.", ""

    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml)
    except Exception as e:
        return False, f"XML nicht parsbar: {e}", ""

    text_lower = xml.lower()

    # Heuristik für Profile / Formate
    profile = ""

    # XRechnung / EN16931 / CII
    if (
        "xrechnung" in text_lower
        or "urn:cen.eu:en16931:2017" in text_lower
        or "crossindustryinvoice" in root.tag.lower()
    ):
        profile = "XRechnung / EN16931 (CII)"

    # ZUGFeRD / Factur-X
    if (
        "zugferd" in text_lower
        or "factur-x" in text_lower
        or "crossindustrydocument" in root.tag.lower()
    ):
        if profile:
            profile += " + ZUGFeRD/Factur-X"
        else:
            profile = "ZUGFeRD / Factur-X"

    # einfache Minimal-Checks
    # -> wenn wir irgendein Profil erkannt haben und das XML syntaktisch OK ist, werten wir es als 'valid'
    if profile:
        return True, f"E-Rechnung erkannt ({profile}), XML syntaktisch gültig.", profile

    # Fallback: generische XML-Rechnung
    return True, "XML syntaktisch gültig, aber kein spezifisches E-Rechnungs-Profil erkannt.", ""

# === Plausibility API ===
@app.post("/api/plausibility/{check_id}/review")
async def review_plausibility(check_id: int, request: Request):
    """Review a plausibility check"""
    data = await request.json()
    status = data.get('status')
    
    if status not in ['reviewed', 'ignored']:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE plausibility_checks
        SET status = ?, reviewed_at = ?
        WHERE id = ?
    ''', (status, datetime.now().isoformat(), check_id))
    
    conn.commit()
    conn.close()
    
    return {"status": "ok"}

# === Analytics Dashboard ===
@app.get("/analytics/costs")
async def analytics_costs(request: Request):
    """Analytics Dashboard für API-Kosten - Nur für Admins"""
    admin_check = require_admin(request)
    if admin_check:
        return admin_check
    
    from cost_tracker import get_monthly_costs
    import sqlite3
    
    monthly_costs = get_monthly_costs()
    
    # Hole alle Jobs mit Kosten
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            j.job_id,
            j.created_at,
            j.total_files,
            COALESCE(SUM(ac.cost_usd), 0) as total_cost
        FROM jobs j
        LEFT JOIN api_costs ac ON j.job_id = ac.job_id
        WHERE j.user_id = ?
        GROUP BY j.job_id
        ORDER BY j.created_at DESC
        LIMIT 50
    ''', (request.session["user_id"],))
    
    jobs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    # Berechne Gesamt-Statistiken
    total_cost = sum(m['total_cost'] for m in monthly_costs)
    total_invoices = sum(j['total_files'] for j in jobs if j['total_files'])
    avg_cost_per_invoice = total_cost / total_invoices if total_invoices > 0 else 0
    
    return templates.TemplateResponse("analytics_costs.html", {
        "request": request,
        "monthly_costs": monthly_costs,
        "jobs": jobs,
        "total_cost": total_cost,
        "total_invoices": total_invoices,
        "avg_cost_per_invoice": avg_cost_per_invoice
    })

# === Advanced Export Routes ===
@app.get("/api/job/{job_id}/export/comprehensive")
async def export_comprehensive_excel(job_id: str, request: Request):
    """Download umfassendes Excel mit allen Daten"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    from advanced_export import create_comprehensive_excel
    
    try:
        excel_bytes = create_comprehensive_excel(job_id)
        
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_report_{job_id[:8]}.xlsx"
            }
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/job/{job_id}/export/zip")
async def export_job_zip(job_id: str, request: Request):
    """Download komplettes Paket als ZIP"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    from advanced_export import create_zip_export
    
    try:
        zip_bytes = create_zip_export(job_id)
        
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_package_{job_id[:8]}.zip"
            }
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/job/{job_id}/export/xrechnung")
async def export_job_xrechnung(job_id: str, request: Request):
    """Download Rechnungen als XRechnung XML (EN16931)"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    from database import get_invoices_by_job, log_export
    import zipfile
    import io
    
    try:
        invoices = get_invoices_by_job(job_id)
        if not invoices:
            return JSONResponse({"error": "Keine Rechnungen gefunden"}, status_code=404)
        
        # ZIP mit allen XRechnungen erstellen
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for inv in invoices:
                xml_content = generate_xrechnung(inv)
                inv_nr = (inv.get("invoice_number") or inv.get("rechnungsnummer") or "unknown").replace("/", "-")
                filename = f"xrechnung_{inv_nr}.xml"
                zf.writestr(filename, xml_content)
        
        zip_buffer.seek(0)
        log_audit(AuditAction.EXPORT_XRECHNUNG, user_id=request.session["user_id"], resource_type="job", resource_id=job_id, ip_address=request.client.host)
        log_export(request.session["user_id"], job_id, "xrechnung", f"xrechnung_{job_id[:8]}.zip", len(zip_buffer.getvalue()), len(invoices), sum(i.get("betrag_brutto", 0) or 0 for i in invoices))
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=xrechnung_{job_id[:8]}.zip"}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/job/{job_id}/export/zugferd", tags=["Export"])
async def export_job_zugferd(job_id: str, request: Request):
    """Download Rechnungen als ZUGFeRD-PDF (PDF/A-3 mit XML)"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    from database import get_invoices_by_job, log_export
    from zugferd import create_zugferd_from_invoice
    import zipfile
    import io
    
    try:
        invoices = get_invoices_by_job(job_id)
        if not invoices:
            return JSONResponse({"error": "Keine Rechnungen gefunden"}, status_code=404)
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for inv in invoices:
                pdf_bytes = create_zugferd_from_invoice(inv)
                if pdf_bytes:
                    inv_nr = (inv.get("rechnungsnummer") or "unknown").replace("/", "-")
                    zf.writestr(f"zugferd_{inv_nr}.pdf", pdf_bytes)
        
        zip_buffer.seek(0)
        log_audit(AuditAction.EXPORT_XRECHNUNG, user_id=request.session["user_id"], resource_type="job", resource_id=job_id, ip_address=request.client.host)
        log_export(request.session["user_id"], job_id, "zugferd", f"zugferd_{job_id[:8]}.zip", len(zip_buffer.getvalue()), len(invoices), sum(i.get("betrag_brutto", 0) or 0 for i in invoices))
        
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=zugferd_{job_id[:8]}.zip"}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# === Überschriebene Job-Detail-Seite mit RAM + DB Fallback ===
@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_details_page(request: Request, job_id: str):
    """
    Detailed job view from in-memory jobs (laufende Session) UND Datenbank.
    - Zuerst wird in processing_jobs geschaut (aktuelle Verarbeitung)
    - Fallback: get_job(job_id) aus der Datenbank
    """
    from database import (
        get_job,
        get_invoices_by_job,
        get_plausibility_warnings_for_job,
        get_invoice_categories,
        get_duplicates_for_job,
    )

    # 1) RAM: laufender oder gerade fertig verarbeiteter Job
    job = processing_jobs.get(job_id)

    # 2) Fallback: Datenbank (History / ältere Jobs)
    if not job:
        job = get_job(job_id)

    if not job:
        raise JobNotFoundError(job_id)

    # Rechnungen aus der DB holen (inkl. IDs etc.)
    invoices = get_invoices_by_job(job_id)

    # Header-Zahlen (Rechnungen, Erfolgreich, Gesamtvolumen) aus echten Daten ableiten
    # Besonders wichtig für frische Jobs aus processing_jobs, wo total_files evtl. fehlt
    if not job.get("total_files"):
        job["total_files"] = len(invoices)
    if not job.get("successful"):
        # Wenn erfolgreich noch 0 ist, setzen wir es auf die Anzahl verarbeiteter Rechnungen
        job["successful"] = len(invoices)
    if not job.get("total_amount"):
        # Gesamt-Bruttobetrag aus den Rechnungen summieren
        job["total_amount"] = sum(
            (inv.get("betrag_brutto") or 0) for inv in invoices
        )

    # Kategorien anreichern
    for inv in invoices:
        inv["categories"] = get_invoice_categories(inv["id"])

    # Aussteller-Statistik
    aussteller_stats = {}
    for inv in invoices:
        name = inv.get("rechnungsaussteller", "Unbekannt")
        if name not in aussteller_stats:
            aussteller_stats[name] = {"name": name, "count": 0, "total": 0}
        aussteller_stats[name]["count"] += 1
        aussteller_stats[name]["total"] += inv.get("betrag_brutto", 0) or 0

    aussteller_list = sorted(
        aussteller_stats.values(),
        key=lambda x: x["total"],
        reverse=True,
    )

    # Header-Kacheln / Statistiken robust aus den Rechnungen ableiten
    stats = job.get("stats") or {}
    # Falls in der DB als JSON-String gespeichert
    if isinstance(stats, str):
        import json as _json
        try:
            stats = _json.loads(stats)
        except Exception:
            stats = {}

    # Anzahl Rechnungen immer aus der echten Liste ableiten
    stats.setdefault("total_invoices", len(invoices))
    job["stats"] = stats

    # Sicherstellen, dass die Header-Kacheln immer korrekte Werte anzeigen
    if not job.get("total_files"):
        job["total_files"] = len(invoices)
    if not job.get("successful"):
        job["successful"] = len(invoices)

    # Fallback für Header-Kacheln: auch RAM-Jobs haben korrekte Werte
    if not job.get("total_files"):
        job["total_files"] = len(invoices)
    if not job.get("successful"):
        job["successful"] = len(invoices)
    if not job.get("total_amount"):
        job["total_amount"] = sum(inv.get("betrag_brutto", 0) or 0 for inv in invoices)

    # total_files / successful / total_amount notfalls ausrechnen
    if not job.get("total_files"):
        job["total_files"] = len(invoices)
    if not job.get("successful"):
        job["successful"] = len(invoices)
    if not job.get("total_amount"):
        job["total_amount"] = sum(inv.get("betrag_brutto", 0) or 0 for inv in invoices)

    duplicates = get_duplicates_for_job(job_id)
    plausibility_warnings = get_plausibility_warnings_for_job(job_id)

    return templates.TemplateResponse(
        "job_details.html",
        {
            "request": request,
            "job_id": job_id,
            "job": job,
            "invoices": invoices,
            "aussteller_stats": aussteller_list,
            "plausibility_warnings": plausibility_warnings,
            "duplicates": duplicates,
        },
    )

def send_password_reset_email(to_email: str, token: str):
    """Sendet die Passwort-Zurücksetzen-E-Mail via SendGrid."""
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@sbsdeutschland.com")

    logger.info(
        f"📧 [RESET] SENDGRID_API_KEY present: {bool(api_key)} length={len(api_key) if api_key else 0}"
    )
    logger.info(
        f"📧 [RESET] Using from_email='{from_email}', to_email='{to_email}'"
    )

    if not api_key:
        logger.error("❌ SENDGRID_API_KEY not set – cannot send password reset email")
        raise RuntimeError("SENDGRID_API_KEY not set")

    # Basis-URL deiner App
    base_url = os.getenv("APP_BASE_URL", "https://app.sbsdeutschland.com")

    # 🔑 HIER: Token als Query-Parameter anfügen
    reset_url = f"{base_url}/password-reset/confirm?token={token}"
    logger.info(f"📧 [RESET] reset_url='{reset_url}'")

    html_content = f"""
        <h1>Passwort zurücksetzen</h1>
        <p>Sie haben angefordert, Ihr Passwort zurückzusetzen.</p>
        <p>Klicken Sie auf den folgenden Button, um ein neues Passwort zu vergeben:</p>
        <p>
            <a href='{reset_url}' style='display:inline-block;padding:12px 24px;
               background-color:#003856;color:#ffffff;text-decoration:none;
               border-radius:6px;font-weight:bold;'>
                Passwort zurücksetzen
            </a>
        </p>
        <p>Oder öffnen Sie diesen Link in Ihrem Browser:</p>
        <p><a href='{reset_url}'>{reset_url}</a></p>
        <p>Wenn Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren.</p>
    """

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject="Passwort zurücksetzen – SBS Deutschland",
        html_content=html_content,
    )

    sg = SendGridAPIClient(api_key)
    response = sg.send(message)
    logger.info(f"📧 [RESET] SendGrid response: status_code={response.status_code}")

    if response.status_code >= 400:
        raise RuntimeError(f"SendGrid error: status_code={response.status_code}")

    return True


# ====================
# Password reset routes
# ====================

def send_password_reset_email(to_email: str, token: str):
    """Sendet die Passwort-Zurücksetzen-E-Mail via SendGrid."""
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@sbsdeutschland.com")

    logger.info(
        "📧 [RESET] SENDGRID_API_KEY present: %s length=%s",
        bool(api_key),
        len(api_key) if api_key else 0,
    )
    logger.info(
        "📧 [RESET] Using from_email='%s', to_email='%s'",
        from_email,
        to_email,
    )

    if not api_key:
        logger.error("❌ SENDGRID_API_KEY not set – cannot send password reset email")
        raise RuntimeError("SENDGRID_API_KEY not configured")

    reset_url = f"https://app.sbsdeutschland.com/password-reset/confirm?token={token}"

    html_content = f"""
    <p>Sie haben angefordert, Ihr Passwort zurückzusetzen.</p>
    <p>Klicken Sie auf den folgenden Button, um ein neues Passwort zu vergeben:</p>
    <p>
        <a href='{reset_url}' style='display:inline-block;padding:10px 20px;
           background:#003856;color:#ffffff;text-decoration:none;border-radius:4px;'>
           Passwort zurücksetzen
        </a>
    </p>
    <p>Oder öffnen Sie diesen Link in Ihrem Browser:<br>{reset_url}</p>
    """

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject="Passwort zurücksetzen – SBS Deutschland",
        html_content=html_content,
    )

    sg = SendGridAPIClient(api_key)
    response = sg.send(message)
    logger.info(
        "📧 [RESET] SendGrid response: status_code=%s",
        getattr(response, "status_code", None),
    )
    if getattr(response, "status_code", None) and response.status_code >= 400:
        raise RuntimeError(f"SendGrid error: status_code={response.status_code}")


@app.get("/password-reset/request", response_class=HTMLResponse)
async def password_reset_request_page(request: Request):
    """Zeigt Formular zum Anfordern eines Reset-Links."""
    return templates.TemplateResponse(
        "password_reset_request.html",
        {"request": request, "error": None, "success": None},
    )


@app.post("/password-reset/request", response_class=HTMLResponse)
async def password_reset_request_submit(request: Request, email: str = Form(...)):
    """Verarbeitet Formular: erstellt Token, sendet E-Mail."""
    logger.info("🔐 Password reset requested for: %s", email)
    token = create_password_reset_token(email)
    logger.info("🔑 Token created (not None): %s", token is not None)

    generic_success = "E-Mail wurde gesendet! Prüfen Sie Ihr Postfach."

    if not token:
        # Kein User zu dieser Mail – nach außen trotzdem Erfolgsmeldung
        logger.warning("🔐 Password reset requested for unknown email: %s", email)
        return templates.TemplateResponse(
            "password_reset_request.html",
            {"request": request, "error": None, "success": generic_success},
        )

    try:
        send_password_reset_email(email, token)
        return templates.TemplateResponse(
            "password_reset_request.html",
            {"request": request, "error": None, "success": generic_success},
        )
    except Exception as e:
        logger.exception("❌ Fehler beim Versenden der Reset-E-Mail: %s", e)
        error = "Beim Versenden der E-Mail ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut."
        return templates.TemplateResponse(
            "password_reset_request.html",
            {"request": request, "error": error, "success": None},
        )


@app.get("/password-reset/confirm", response_class=HTMLResponse)
async def password_reset_confirm_page(request: Request):
    """Formular zum Setzen eines neuen Passworts (über ?token=...)."""
    token = request.query_params.get("token") or ""
    logger.info("🔐 [RESET-CONFIRM-GET] called with token=%s", token)

    token_valid = False
    error = None

    if token:
        user_id = verify_reset_token(token)
        logger.info("🔐 [RESET-CONFIRM-GET] verify_reset_token -> %s", user_id)
        token_valid = user_id is not None
        if not token_valid:
            error = "Der Link ist ungültig oder abgelaufen."
    else:
        error = "Der Link ist ungültig oder abgelaufen."

    return templates.TemplateResponse(
        "password_reset_confirm.html",
        {
            "request": request,
            "token": token,
            "token_valid": token_valid,
            "error": error,
            "success": None,
        },
    )


@app.post("/password-reset/confirm", response_class=HTMLResponse)
async def password_reset_confirm_submit(
    request: Request,
    token: str = Form(...),
    new_password: str | None = Form(None),
    confirm_password: str | None = Form(None),
    password: str | None = Form(None),
    password_confirm: str | None = Form(None),
):
    """Verarbeitet das Formular: setzt neues Passwort, wenn Token gültig."""
    logger.info("🔐 [RESET-CONFIRM-POST] called with token=%s", token)

    # Alternativen Feldnamen auflösen (je nach Template-Version)
    if new_password is None:
        new_password = password
    if confirm_password is None:
        confirm_password = password_confirm

    if not new_password or not confirm_password:
        error = "Bitte füllen Sie beide Passwort-Felder aus."
        return templates.TemplateResponse(
            "password_reset_confirm.html",
            {
                "request": request,
                "token": token,
                "token_valid": True,
                "error": error,
                "success": None,
            },
        )

    if new_password != confirm_password:
        error = "Die Passwörter stimmen nicht überein."
        return templates.TemplateResponse(
            "password_reset_confirm.html",
            {
                "request": request,
                "token": token,
                "token_valid": True,
                "error": error,
                "success": None,
            },
        )

    if len(new_password) < 8:
        error = "Das Passwort muss mindestens 8 Zeichen lang sein."
        return templates.TemplateResponse(
            "password_reset_confirm.html",
            {
                "request": request,
                "token": token,
                "token_valid": True,
                "error": error,
                "success": None,
            },
        )

    try:
        ok = reset_password(token, new_password)
        logger.info("🔐 [RESET-CONFIRM-POST] reset_password result=%s", ok)
    except Exception as e:
        logger.exception("❌ [RESET-CONFIRM-POST] reset_password raised: %s", e)
        ok = False

    if not ok:
        error = "Der Link ist ungültig oder abgelaufen."
        return templates.TemplateResponse(
            "password_reset_confirm.html",
            {
                "request": request,
                "token": token,
                "token_valid": False,
                "error": error,
                "success": None,
            },
        )

    success = "Ihr Passwort wurde erfolgreich geändert. Sie können sich jetzt anmelden."
    return templates.TemplateResponse(
        "password_reset_confirm.html",
        {
            "request": request,
            "token": token,
            "token_valid": False,
            "error": None,
            "success": success,
        },
    )


@app.get("/logout")
async def logout(request: Request):
    """
    Logout und Redirect auf die SBS Homepage.
    """
    # Session leeren, falls vorhanden
    try:
        session = getattr(request, "session", None)
        if isinstance(session, dict):
            session.pop("user_id", None)
            session.pop("user_name", None)
            session.pop("user_email", None)
    except AssertionError:
        # Keine SessionMiddleware aktiv – nichts zu tun
        pass

    return RedirectResponse(
        url="https://sbsdeutschland.com/sbshomepage/",
        status_code=303,
    )

@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def demo_job_page(request: Request, job_id: str):
    """
    Öffentliche Demo-Seite für einen Job. Hier kann die kostenlose Demo
    ohne Login den Status einsehen (aktuell noch Platzhalter).
    """
    return templates.TemplateResponse("demo_job.html", {
        "request": request,
        "job_id": job_id,
    })

# --------------------------------------------------------------------
# Analytics API – Finance Snapshot
# --------------------------------------------------------------------
from fastapi import Query

@app.get("/api/analytics/finance-snapshot")
async def api_finance_snapshot(request: Request, days: int = 90):
    """
    Liefert einen kompakten Finance-Überblick für Dashboard - gefiltert nach User.
    """
    from analytics_service import get_finance_snapshot
    
    # User-ID aus Session
    user_id = request.session.get("user_id")
    
    # Sicherheitsnetz für days
    if days < 1:
        days = 1
    if days > 365:
        days = 365

    snapshot = get_finance_snapshot(days=days, user_id=user_id)
    return snapshot

# ============================================================
# Finance Copilot LLM Engine (CFO-Level)
# ============================================================
from typing import Any, Dict, List, Tuple
from openai import OpenAI
import os
import math

_finance_copilot_client: OpenAI | None = None


def _get_finance_copilot_client() -> OpenAI:
    """Lazy-initialisierter OpenAI-Client für den Finance Copilot."""
    global _finance_copilot_client
    if _finance_copilot_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        _finance_copilot_client = OpenAI(api_key=api_key)
    return _finance_copilot_client


FINANCE_COPILOT_SYSTEM = """
Du bist der „Finance Copilot“ einer B2B SaaS Plattform für KI-Rechnungsverarbeitung
(SBS Deutschland). Deine Zielgruppe sind CFOs, Head of Finance und Controller in
mittelständischen Unternehmen und Tech-Scaleups.

Rolle:
- Du agierst auf dem Niveau eines erfahrenen CFOs eines Tech-Konzerns.
- Du kennst typische Kennzahlen (Brutto/Netto, MwSt, Lieferanten-Konzentration,
  Zahlungsziele, Working Capital, Runway, Budget-Abweichungen, etc.).
- Du arbeitest strikt datengetrieben auf Basis des bereitgestellten Snapshots.

Regeln:
- Antworte IMMER auf Deutsch.
- Sei klar, strukturiert und handlungsorientiert – keine Marketing-Texte.
- Wenn eine Kennzahl im Snapshot fehlt, spekuliere nicht, sondern erkläre, was fehlt.
- Mache bei Unsicherheit explizite Annahmen („Unter der Annahme, dass ...“).
- Rechne nachvollziehbar (Prozente, Vergleichswerte).
- Bleibe innerhalb der Zahlen des Snapshots – keine externen Daten verwenden.

Output-Struktur (wenn passend):
1. Executive Summary (2–4 Bulletpoints)
2. Kennzahlen-Überblick (konkrete EUR/%, Zeitraum)
3. Treiber & Muster (Lieferanten, Peaks, Ausreißer)
4. Risiken & Chancen (Klumpenrisiken, Einsparpotenziale)
5. Konkrete Empfehlungen (To-dos, Verantwortlichkeiten, nächste Analysen)

Sprich den Nutzer mit „Sie“ an.
"""


def _short_eur(value: float | None) -> str:
    if value is None:
        return "n/a"
    try:
        v = float(value)
    except Exception:
        return str(value)
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.2f} Mio. €"
    if abs(v) >= 1_000:
        return f"{v/1_000:.1f} Tsd. €"
    return f"{v:.2f} €"


def _build_snapshot_summary(snapshot: Dict[str, Any], days: int) -> str:
    kpis = snapshot.get("kpis") or {}
    top_vendors = snapshot.get("top_vendors") or []
    monthly = (
        snapshot.get("monthly_trend")
        or snapshot.get("monthly_totals")
        or snapshot.get("monthly")  # Fallback
        or []
    )

    meta = snapshot.get("meta") or {}
    start_date = meta.get("start_date")
    end_date = meta.get("end_date")

    total_gross = (
        kpis.get("total_gross")
        or kpis.get("total_brutto")
        or 0
    )
    total_net = (
        kpis.get("total_net")
        or kpis.get("total_netto")
        or 0
    )
    total_vat = (
        kpis.get("total_vat")
        or kpis.get("total_mwst")
        or 0
    )
    total_invoices = kpis.get("total_invoices") or 0
    duplicates = (
        kpis.get("duplicates_count")
        or kpis.get("duplicates")
        or 0
    )

    lines: List[str] = []
    lines.append(f"- Zeitraum: letzte {days} Tage")
    if start_date and end_date:
        lines.append(f"- Exakter Zeitraum: {start_date} bis {end_date}")
    lines.append(f"- Gesamt Brutto: {_short_eur(total_gross)}")
    lines.append(f"- Gesamt Netto: {_short_eur(total_net)}")
    lines.append(f"- Gesamt MwSt.: {_short_eur(total_vat)}")
    lines.append(f"- Anzahl Rechnungen: {int(total_invoices) if total_invoices else 0}")
    lines.append(f"- (Heuristische) Dubletten: {int(duplicates) if duplicates else 0}")

    if top_vendors:
        lines.append("")
        lines.append("Top-Lieferanten nach Bruttobetrag:")
        top5 = top_vendors[:5]
        for i, v in enumerate(top5, start=1):
            name = (
                v.get("rechnungsaussteller")
                or v.get("name")
                or v.get("supplier")
                or "Unbekannter Lieferant"
            )
            gross = (
                v.get("total_gross")
                or v.get("total_brutto")
                or v.get("total")
                or 0
            )
            count = v.get("invoice_count") or v.get("count") or 0
            share = ""
            if total_gross:
                pct = 100 * float(gross) / float(total_gross)
                share = f" ({pct:.1f} % vom Gesamtbrutto)"
            lines.append(
                f"  {i}. {name}: {_short_eur(gross)} aus {int(count)} Rechnungen{share}"
            )

    if monthly:
        lines.append("")
        lines.append("Monatliche Brutto-Ausgaben (vereinfacht):")
        for row in monthly[-6:]:  # letzte 6 Monate
            label = (
                row.get("year_month")
                or row.get("monat")
                or row.get("label")
                or row.get("month")
                or "n/a"
            )
            gross = (
                row.get("total_gross")
                or row.get("total_brutto")
                or row.get("total")
                or row.get("value")
                or 0
            )
            lines.append(f"  - {label}: {_short_eur(gross)}")

    return "\n".join(lines)


def _suggest_followups(question: str, snapshot: Dict[str, Any], days: int) -> List[str]:
    kpis = snapshot.get("kpis") or {}
    top_vendors = snapshot.get("top_vendors") or []
    total_gross = float(kpis.get("total_gross") or kpis.get("total_brutto") or 0) or 0.0

    suggestions: List[str] = []

    q_lower = (question or "").lower()
    if "kosten" in q_lower or "ausgaben" in q_lower or "spend" in q_lower:
        suggestions.append(
            "Welche drei Kostenblöcke sollten wir kurzfristig um 10–15 % reduzieren?"
        )
        suggestions.append(
            "Welche wiederkehrenden Kosten wachsen aktuell am stärksten?"
        )
    if "lieferant" in q_lower or "supplier" in q_lower:
        suggestions.append("Wie hoch ist unser Klumpenrisiko bei den Top-Lieferanten?")
        suggestions.append(
            "Welche Alternativ-Lieferanten sollten wir für kritische Services prüfen?"
        )
    if "cash" in q_lower or "liquid" in q_lower or "runway" in q_lower:
        suggestions.append(
            "Wie wirkt sich unser aktuelles Ausgabenniveau auf den Cash-Runway aus?"
        )
        suggestions.append(
            "Wo können wir Zahlungsziele oder Zahlungsrhythmen optimieren?"
        )

    # Konzentrationsrisiko bei Lieferanten
    if top_vendors and total_gross > 0:
        v0 = top_vendors[0]
        name0 = (
            v0.get("rechnungsaussteller")
            or v0.get("name")
            or v0.get("supplier")
            or "Top-Lieferant"
        )
        gross0 = float(
            v0.get("total_gross")
            or v0.get("total_brutto")
            or v0.get("total")
            or 0
        )
        share0 = 100 * gross0 / total_gross if total_gross else 0
        if share0 >= 30:
            suggestions.append(
                f"Wie können wir das Abhängigkeitsrisiko vom Lieferanten „{name0}“ "
                f"({share0:.1f} % der Ausgaben im Zeitraum) reduzieren?"
            )

    # Generische Enterprise-SaaS-Fragen
    suggestions.extend(
        [
            "Wie entwickeln sich unsere wiederkehrenden (OPEX) vs. einmaligen (CAPEX) Ausgaben?",
            f"Welche drei Maßnahmen würden Sie im Zeitraum der letzten {days} Tage priorisieren, um unsere Profitabilität zu verbessern?",
            "Welche Warnsignale sehen Sie in den Daten, die wir mit dem Management teilen sollten?",
        ]
    )

    # Duplikate entfernen, Reihenfolge stabil halten
    unique: List[str] = []
    seen = set()
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique[:6]


def run_finance_copilot_llm(
    question: str,
    days: int,
    snapshot: Dict[str, Any],
    focus: str | None = None,
) -> Tuple[str, List[str]]:
    """
    Erzeugt eine CFO-taugliche Antwort auf Basis des Finance-Snapshots.
    Gibt (answer, suggested_questions) zurück.
    """
    if not question or not question.strip():
        raise ValueError("question_required")

    focus = (focus or "auto").strip().lower()
    snapshot_summary = _build_snapshot_summary(snapshot, days)

    user_prompt = f"""
Nutzerfrage:
„{question.strip()}“

Spezifischer Fokus: {focus or "auto"}

Daten-Snapshot aus der KI-Rechnungsverarbeitung:
{snapshot_summary}

Aufgabe:
- Beantworte die Frage ausschließlich auf Basis dieses Snapshots.
- Nutze die Output-Struktur (Executive Summary, Kennzahlen, Treiber, Risiken, Empfehlungen),
  sofern sinnvoll.
- Quantifiziere Effekte immer, wenn möglich (z.B. „Reduktion um 8–12 % = ca. 25–40 Tsd. € pro Jahr“).
- Referenziere konkrete Lieferanten, Monate oder Muster, falls im Snapshot erkennbar.
"""

    client = _get_finance_copilot_client()
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": FINANCE_COPILOT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.25,
        max_tokens=1200,
    )

    answer = (resp.choices[0].message.content or "").strip()
    suggested = _suggest_followups(question, snapshot, days)

    return answer, suggested


# ---------------------------------------------------------------------------
# Finance Copilot API (V1)
# Nutzt die deterministische Logik aus finance_copilot.generate_finance_answer
# und liefert:
# - eine natürlichsprachliche Antwort
# - die zugrunde liegenden KPIs
# - Vorschlagsfragen für das UI
# ---------------------------------------------------------------------------

from pydantic import BaseModel
from finance_copilot import generate_finance_answer


class FinanceCopilotRequest(BaseModel):
    question: str | None = None
    days: int | None = 90
    focus: str | None = None


class FinanceCopilotResponse(BaseModel):
    answer: str
    question: str
    days: int
    snapshot: dict
    suggested_questions: list


@app.post("/api/copilot/finance/query", response_model=FinanceCopilotResponse)
async def api_finance_copilot_query(payload: FinanceCopilotRequest):
    """
    Finance Copilot Endpoint (V2 – LLM-basiert, CFO-Level)
    """
    question = (payload.question or "").strip()
    days = int(payload.days or 90)
    focus = (payload.focus or "auto").strip() or "auto"

    if not question:
        raise HTTPException(status_code=400, detail="question_required")

    # Sicherheitsnetz für days
    if days < 1:
        days = 1
    if days > 365:
        days = 365

    # Snapshot aus Analytics-Layer laden
    try:
        from analytics_service import get_finance_snapshot
        snapshot = get_finance_snapshot(days=days)
    except Exception as exc:  # noqa: F841
        app_logger.exception("Finance copilot snapshot error")
        raise HTTPException(status_code=500, detail="snapshot_error")

    # LLM-Antwort erzeugen
    try:
        answer, suggested = run_finance_copilot_llm(
            question=question,
            days=days,
            snapshot=snapshot,
            focus=focus,
        )
    except Exception as exc:  # noqa: F841
        app_logger.exception("Finance copilot LLM error")
        raise HTTPException(
            status_code=500,
            detail=(
                "Finance Copilot konnte nicht antworten. "
                "Bitte versuchen Sie es später erneut."
            ),
        )

    return FinanceCopilotResponse(
        answer=answer,
        question=question,
        days=days,
        snapshot=snapshot,
        suggested_questions=suggested,
    )

# ============================================================
# TEAM & ROLLEN API
# ============================================================

@app.get("/api/team/members", tags=["Team"])
async def get_team_members(request: Request):
    """Team-Mitglieder laden - Admins sehen alle, normale User nur sich selbst"""
    if "user_id" not in request.session:
        return {"error": "Not logged in"}
    
    user_id = request.session["user_id"]
    user_is_admin = is_admin_user(user_id)
    
    from database import get_connection
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    # Admins sehen alle User, normale User nur sich selbst
    if user_is_admin:
        cursor.execute("""
            SELECT 
                u.id, u.name, u.email, u.is_admin, u.is_active,
                u.created_at, u.last_login,
                GROUP_CONCAT(r.display_name) as roles,
                GROUP_CONCAT(r.color) as role_colors,
                GROUP_CONCAT(r.id) as role_ids
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            GROUP BY u.id
            ORDER BY u.is_admin DESC, u.name ASC
        """)
    else:
        cursor.execute("""
            SELECT 
                u.id, u.name, u.email, u.is_admin, u.is_active,
                u.created_at, u.last_login,
                GROUP_CONCAT(r.display_name) as roles,
                GROUP_CONCAT(r.color) as role_colors,
                GROUP_CONCAT(r.id) as role_ids
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.id = ?
            GROUP BY u.id
        """, (user_id,))
    members = cursor.fetchall()
    
    # Rollen-Liste für Dropdown
    cursor.execute("SELECT id, name, display_name, description, color FROM roles ORDER BY id")
    roles = cursor.fetchall()
    
    conn.close()
    
    return {"members": members, "roles": roles}


@app.post("/api/team/role", tags=["Team"])
async def assign_role(request: Request):
    """Rolle einem User zuweisen oder entfernen"""
    # Nur Admins dürfen Rollen ändern
    admin_check = require_admin(request)
    if admin_check:
        return {"error": "Nur Admins können Rollen ändern"}
    
    data = await request.json()
    user_id = data.get("user_id")
    role_id = data.get("role_id")
    action = data.get("action", "add")  # add oder remove
    
    if not user_id or not role_id:
        return {"error": "user_id und role_id erforderlich"}
    
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if action == "add":
            cursor.execute("""
                INSERT OR IGNORE INTO user_roles (user_id, role_id, assigned_by)
                VALUES (?, ?, ?)
            """, (user_id, role_id, request.session["user_id"]))
        else:
            cursor.execute("""
                DELETE FROM user_roles WHERE user_id = ? AND role_id = ?
            """, (user_id, role_id))
        
        conn.commit()
        conn.close()
        return {"success": True, "message": "Rolle aktualisiert"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.post("/api/team/invite", tags=["Team"])
async def invite_team_member(request: Request):
    """Neues Team-Mitglied per Email einladen"""
    admin_check = require_admin(request)
    if admin_check:
        return {"error": "Nur Admins können einladen"}
    
    import secrets
    from datetime import datetime, timedelta
    
    data = await request.json()
    email = data.get("email", "").strip().lower()
    role_id = data.get("role_id", 3)  # Default: Viewer
    
    if not email or "@" not in email:
        return {"error": "Gültige E-Mail-Adresse erforderlich"}
    
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    
    # Prüfen ob User schon existiert
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return {"error": "User mit dieser E-Mail existiert bereits"}
    
    # Prüfen ob Einladung schon existiert
    cursor.execute("SELECT id FROM team_invitations WHERE email = ? AND status = 'pending'", (email,))
    if cursor.fetchone():
        conn.close()
        return {"error": "Einladung für diese E-Mail bereits gesendet"}
    
    # Einladung erstellen
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(days=7)).isoformat()
    
    cursor.execute("""
        INSERT INTO team_invitations (email, role_id, invited_by, token, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (email, role_id, request.session["user_id"], token, expires_at))
    
    conn.commit()
    conn.close()
    
    # TODO: Email mit Einladungslink senden
    invite_link = f"https://app.sbsdeutschland.com/register?invite={token}"
    
    return {
        "success": True, 
        "message": f"Einladung erstellt",
        "invite_link": invite_link
    }


@app.get("/api/team/invitations", tags=["Team"])
async def get_invitations(request: Request):
    """Alle offenen Einladungen laden"""
    if "user_id" not in request.session:
        return {"error": "Not logged in"}
    
    from database import get_connection
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ti.*, r.display_name as role_name, u.name as invited_by_name
        FROM team_invitations ti
        JOIN roles r ON ti.role_id = r.id
        JOIN users u ON ti.invited_by = u.id
        WHERE ti.status = 'pending'
        ORDER BY ti.created_at DESC
    """)
    invitations = cursor.fetchall()
    conn.close()
    
    return {"invitations": invitations}


@app.delete("/api/team/invitation/{invitation_id}", tags=["Team"])
async def cancel_invitation(invitation_id: int, request: Request):
    """Einladung zurückziehen"""
    admin_check = require_admin(request)
    if admin_check:
        return {"error": "Nur Admins können Einladungen verwalten"}
    
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM team_invitations WHERE id = ?", (invitation_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Einladung gelöscht"}


@app.put("/api/team/member/{user_id}/status", tags=["Team"])
async def update_member_status(user_id: int, request: Request):
    """User aktivieren/deaktivieren"""
    admin_check = require_admin(request)
    if admin_check:
        return {"error": "Nur Admins können User-Status ändern"}
    
    # Sich selbst nicht deaktivieren
    if user_id == request.session["user_id"]:
        return {"error": "Sie können sich nicht selbst deaktivieren"}
    
    data = await request.json()
    is_active = data.get("is_active", True)
    
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": f"User {'aktiviert' if is_active else 'deaktiviert'}"}


# ============================================================
# AUDIT-LOG API
# ============================================================

@app.get("/api/audit-log", tags=["Audit"])
async def get_audit_log(
    request: Request,
    page: int = 1,
    limit: int = 50,
    action: str = "",
    days: str = "7"
):
    """Audit-Log Einträge laden - Admins sehen alles, andere nur eigene"""
    if "user_id" not in request.session:
        return {"error": "Not logged in"}
    
    user_id = request.session["user_id"]
    is_admin = is_admin_user(user_id)
    
    from database import get_connection
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    # Base Query
    where_clauses = []
    params = []
    
    # Nicht-Admins sehen nur eigene Einträge
    if not is_admin:
        where_clauses.append("user_id = ?")
        params.append(user_id)
    
    # Action Filter
    if action:
        where_clauses.append("action LIKE ?")
        params.append(f"%{action}%")
    
    # Days Filter
    if days and days.isdigit():
        where_clauses.append("timestamp >= datetime('now', ?)")
        params.append(f"-{days} days")
    
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # Total Count (gefiltert)
    cursor.execute(f"SELECT COUNT(*) as count FROM audit_log {where_sql}", params)
    total = cursor.fetchone()['count']
    
    # Stats - für Admins global, für andere nur eigene
    if is_admin:
        cursor.execute("SELECT COUNT(*) as count FROM audit_log WHERE DATE(timestamp) = DATE('now')")
        today = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM audit_log WHERE action = 'auth.login' AND timestamp >= datetime('now', '-7 days')")
        logins_7d = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM audit_log WHERE action = 'auth.login_failed'")
        failed_logins = cursor.fetchone()['count']
    else:
        cursor.execute("SELECT COUNT(*) as count FROM audit_log WHERE user_id = ? AND DATE(timestamp) = DATE('now')", (user_id,))
        today = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM audit_log WHERE user_id = ? AND action = 'auth.login' AND timestamp >= datetime('now', '-7 days')", (user_id,))
        logins_7d = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM audit_log WHERE user_id = ? AND action = 'auth.login_failed'", (user_id,))
        failed_logins = cursor.fetchone()['count']
    
    # Paginated Results
    offset = (page - 1) * limit
    cursor.execute(f"""
        SELECT * FROM audit_log 
        {where_sql}
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
    """, params + [limit, offset])
    entries = cursor.fetchall()
    
    conn.close()
    
    return {
        "entries": entries,
        "stats": {
            "total": total,
            "today": today,
            "logins_7d": logins_7d,
            "failed_logins": failed_logins
        },
        "page": page,
        "limit": limit,
        "is_admin": is_admin
    }


def log_audit_event(user_id: int = None, user_email: str = None, action: str = "", 
                    resource_type: str = None, resource_id: str = None, 
                    details: str = None, ip_address: str = None, user_agent: str = None):
    """Hilfsfunktion zum Loggen von Audit-Events"""
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_log (user_id, user_email, action, resource_type, resource_id, details, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, user_email, action, resource_type, resource_id, details, ip_address, user_agent))
    conn.commit()
    conn.close()
