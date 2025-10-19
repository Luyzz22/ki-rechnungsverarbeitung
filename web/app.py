#!/usr/bin/env python3
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
        "job_id": job_id,
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
    
    # Export
    exported_files = {}
    if results:
        try:
            manager = ExportManager()
            exported_files = manager.export_all(results, ['xlsx', 'csv'])
        except Exception as e:
            print(f"Export error: {e}")
    
    # Update job with results
    processing_jobs[job_id].update({
        "status": "completed",
        "results": results,
        "stats": stats,
        "failed": failed,
        "exported_files": exported_files,
        "completed_at": datetime.now().isoformat()
    })


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
