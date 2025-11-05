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

# Setup directories
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

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
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload PDF files
    Returns job_id for tracking
    """
    job_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / job_id
    upload_path.mkdir(exist_ok=True)
    
    uploaded_files = []
    
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
    
    # Store job info
    processing_jobs[job_id] = {
        "status": "uploaded",
        "files": uploaded_files,
        "created_at": datetime.now().isoformat(),
        "path": str(upload_path)
    }
    
    return {
        "success": True,
        "batch_id": job_id,
        "job_id": job_id,  # Für Kompatibilität behalten
        "files_uploaded": len(uploaded_files),
        "files": uploaded_files
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
    """Background task to process invoices"""
    job = processing_jobs[job_id]
    upload_path = Path(job["path"])
    
    results = []
    failed = []
    
    # Get all PDFs
    pdf_files = list(upload_path.glob("*.pdf"))
    
    # Process each PDF
    for pdf_path in pdf_files:
        try:
            data = processor.process_invoice(pdf_path)
            if data:
                results.append(data)
            else:
                failed.append(pdf_path.name)
        except Exception as e:
            failed.append(f"{pdf_path.name}: {str(e)}")
    
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
        "completed_at": datetime.now().isoformat()
    })
    
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
