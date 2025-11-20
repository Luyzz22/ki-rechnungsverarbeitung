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

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import save_job, save_invoices, get_job, get_all_jobs, get_statistics
from logging.handlers import RotatingFileHandler
import sys

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
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
from notifications import send_notifications

# FastAPI App
app = FastAPI(
    title="KI-Rechnungsverarbeitung Web",
    description="Automatische Rechnungsverarbeitung mit KI",
    version="1.0.0"
)
@app.middleware("http")
async def log_requests(request, call_next):
    """Log alle HTTP Requests"""
    app_logger.info(f"Request: {request.method} {request.url.path} from {request.client.host}")
    response = await call_next(request)
    app_logger.info(f"Response: {response.status_code}")
    return response

# Setup directories
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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main upload page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/upload")
async def upload_files(request: Request, files: List[UploadFile] = File(default=[])):
    print(f"Upload request received, files count: {len(files) if files else 0}")
    """
    Upload PDF files with subscription limit check
    Returns job_id for tracking
    """
    # Check if user is logged in
    if 'user_id' not in request.session:
        return JSONResponse(
            status_code=401,
            content={"error": "Bitte melden Sie sich an", "redirect": "/login"}
        )
    
    # Check subscription limit
    from database import check_invoice_limit
    limit_check = check_invoice_limit(request.session['user_id'])
    
    if not limit_check.get('allowed'):
        return JSONResponse(
            status_code=403,
            content={
                "error": limit_check.get('message'),
                "reason": limit_check.get('reason'),
                "redirect": "https://sbsdeutschland.com/preise" if limit_check.get('reason') == 'no_subscription' else None
            }
        )
    
    job_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / job_id
    upload_path.mkdir(exist_ok=True)
    
    uploaded_files = []
    skipped_files = []
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            continue
            
        file_path = upload_path / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        uploaded_files.append({
            "filename": file.filename,
            "size": file_path.stat().st_size
        })
    
    # Check if enough quota
    remaining = limit_check.get('remaining', 0)
    if len(uploaded_files) > remaining:
        return JSONResponse(
            status_code=403,
            content={
                "error": f"Nicht genug Kontingent. Verbleibend: {remaining}, Hochgeladen: {len(uploaded_files)}",
                "remaining": remaining
            }
        )
    
    # Store job info
    processing_jobs[job_id] = {
        "user_id": request.session.get("user_id"),
        "status": "uploaded",
        "files": uploaded_files,
        "created_at": datetime.now().isoformat(),
        "path": str(upload_path)
    }
    
    return {
        "success": True,
        "batch_id": job_id,
        "job_id": job_id,
        "files_uploaded": len(uploaded_files),
        "files": uploaded_files,
        "subscription": {
            "plan": limit_check.get('plan'),
            "used": limit_check.get('used'),
            "limit": limit_check.get('limit'),
            "remaining": remaining - len(uploaded_files)
        }
    }

@app.post("/api/process/{job_id}")
async def process_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Process uploaded PDFs
    Returns immediately, processing happens in background
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
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
        "status": "processing",
        "message": "Processing started" 
    }

async def process_invoices_background(job_id: str):
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
            return ("success", data, pdf_path.name)
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
            print(f"Export error: {e}")
    
    # Email Notification
    try:
        from notifications import send_notifications
        notification_config = config.config.get('notifications', {})
        if notification_config.get('email', {}).get('enabled', False):
            send_notifications(config.config, stats, exported_files)
    except Exception as e:
        print(f"Notification error: {e}")
    
    # Update job with results
    processing_jobs[job_id].update({
        "status": "completed",
        "results": results,
        "stats": stats,
        "failed": failed,
        "exported_files": exported_files,
        "completed_at": datetime.now().isoformat(),
        "total_amount": stats.get('total_brutto', 0) if stats else 0,
        "total": total_files,
        "successful": len(results)
    })
    
    # Save to database
    save_job(job_id, processing_jobs[job_id], processing_jobs[job_id].get("user_id"))
    if results:
        save_invoices(job_id, results)
    
    # Track invoice usage
    if results and job.get("user_id"):
        from database import increment_invoice_usage
        increment_invoice_usage(job["user_id"], len(results))
    
    # Schedule cleanup of uploaded PDFs (nach 60 Minuten)
    asyncio.create_task(cleanup_uploads(upload_path, delay_minutes=60))
@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get processing status"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "files_count": len(job["files"]),
        "created_at": job["created_at"]
    }


@app.get("/api/results/{job_id}")
async def get_results(job_id: str):
    """Get processing results"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
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


@app.get("/api/download/{job_id}/{format}")
async def download_export(job_id: str, format: str):
    """Download exported file"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
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
    """Results page"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "job_id": job_id,
            "job": job
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "jobs_count": len(processing_jobs)
    }
@app.post("/api/send-email/{job_id}")
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
        from notifications import send_notifications
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
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

@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_details_page(request: Request, job_id: str):
    """Detailed job view from database"""
    from database import get_job
    
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get invoices for this job
    invoices = job.get('results', [])
    
    # Calculate aussteller statistics
    aussteller_stats = {}
    for inv in invoices:
        name = inv.get('rechnungsaussteller', 'Unbekannt')
        if name not in aussteller_stats:
            aussteller_stats[name] = {'name': name, 'count': 0, 'total': 0}
        aussteller_stats[name]['count'] += 1
        aussteller_stats[name]['total'] += inv.get('betrag_brutto', 0) or 0
    
    aussteller_list = sorted(aussteller_stats.values(), key=lambda x: x['total'], reverse=True)
    
    return templates.TemplateResponse("job_details.html", {
        "request": request,
        "job_id": job_id,
        "job": job,
        "invoices": invoices,
        "aussteller_stats": aussteller_list
    })

@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_details_page(request: Request, job_id: str):
    """Detailed job view from database"""
    from database import get_job
    
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get invoices for this job
    invoices = job.get('results', [])
    
    # Calculate aussteller statistics
    aussteller_stats = {}
    for inv in invoices:
        name = inv.get('rechnungsaussteller', 'Unbekannt')
        if name not in aussteller_stats:
            aussteller_stats[name] = {'name': name, 'count': 0, 'total': 0}
        aussteller_stats[name]['count'] += 1
        aussteller_stats[name]['total'] += inv.get('betrag_brutto', 0) or 0
    
    aussteller_list = sorted(aussteller_stats.values(), key=lambda x: x['total'], reverse=True)
    
    return templates.TemplateResponse("job_details.html", {
        "request": request,
        "job_id": job_id,
        "job": job,
        "invoices": invoices,
        "aussteller_stats": aussteller_list
    })

@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_details_page(request: Request, job_id: str):
    """Detailed job view from database"""
    from database import get_job
    
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get invoices for this job
    invoices = job.get('results', [])
    
    # Calculate aussteller statistics
    aussteller_stats = {}
    for inv in invoices:
        name = inv.get('rechnungsaussteller', 'Unbekannt')
        if name not in aussteller_stats:
            aussteller_stats[name] = {'name': name, 'count': 0, 'total': 0}
        aussteller_stats[name]['count'] += 1
        aussteller_stats[name]['total'] += inv.get('betrag_brutto', 0) or 0
    
    aussteller_list = sorted(aussteller_stats.values(), key=lambda x: x['total'], reverse=True)
    
    return templates.TemplateResponse("job_details.html", {
        "request": request,
        "job_id": job_id,
        "job": job,
        "invoices": invoices,
        "aussteller_stats": aussteller_list
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Expense analytics dashboard"""
    from database import get_analytics_data
    
    data = get_analytics_data()
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "stats": data['stats'],
        "monthly_labels": data['monthly_labels'],
        "monthly_values": data['monthly_values'],
        "top_suppliers": data['top_suppliers'],
        "weekday_data": data['weekday_data']
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

# Session Management
from starlette.middleware.sessions import SessionMiddleware
import secrets

# Add session middleware (muss nach app = FastAPI() kommen)
app.add_middleware(SessionMiddleware, secret_key='sbs-invoice-app-secret-key-2025', domain='.sbsdeutschland.com')

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })

@app.post("/login")
async def login_submit(request: Request):
    """Handle login"""
    from database import verify_user
    
    form = await request.form()
    email = form.get('email', '')
    password = form.get('password', '')
    
    user = verify_user(email, password)
    
    if user:
        request.session['user_id'] = user['id']
        request.session['user_name'] = user['name'] or user['email'].split('@')[0]
        request.session['user_email'] = user['email']
        
        from starlette.responses import RedirectResponse
        next_url = request.query_params.get('next', '/')
    return RedirectResponse(url=next_url, status_code=303)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Ungültige Email oder Passwort"
    })

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
    
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Passwort muss mindestens 6 Zeichen haben"
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
    """Logout user"""
    request.session.clear()
    from starlette.responses import RedirectResponse
    next_url = request.query_params.get('next', '/')
    return RedirectResponse(url=next_url, status_code=303)

@app.get("/api/user")
async def get_current_user(request: Request):
    """Get current logged in user"""
    if 'user_id' in request.session:
        return {
            "logged_in": True,
            "name": request.session.get('user_name', ''),
            "email": request.session.get('user_email', '')
        }
    return {"logged_in": False}

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

