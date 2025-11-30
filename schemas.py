"""
SBS Deutschland – API Response Schemas
Pydantic Models für strukturierte API-Responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# === Basis-Responses ===

class SuccessResponse(BaseModel):
    """Standard-Erfolgsantwort"""
    status: str = "ok"
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard-Fehlerantwort"""
    error: bool = True
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# === Job-Schemas ===

class JobStatus(str, Enum):
    UPLOADED = "uploaded"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreateResponse(BaseModel):
    """Response nach Job-Erstellung"""
    job_id: str
    status: JobStatus = JobStatus.UPLOADED
    total_files: int = Field(..., alias="total")
    message: str = "Upload erfolgreich"

    class Config:
        populate_by_name = True


class JobStatusResponse(BaseModel):
    """Response für Job-Status-Abfrage"""
    job_id: str
    status: JobStatus
    progress: int = Field(0, ge=0, le=100)
    total: int = 0
    processed: int = 0
    successful: int = 0
    failed_count: int = 0


class JobResultsResponse(BaseModel):
    """Response für Job-Ergebnisse"""
    job_id: str
    status: JobStatus
    results: List[Dict[str, Any]] = []
    stats: Optional[Dict[str, Any]] = None
    exported_files: Dict[str, str] = {}
    failed: List[str] = []


# === Invoice-Schemas ===

class InvoiceResponse(BaseModel):
    """Einzelne Rechnung"""
    id: int
    job_id: str
    filename: str
    invoice_number: str
    invoice_date: Optional[str] = None
    supplier_name: str
    net_amount: float = 0.0
    vat_amount: float = 0.0
    gross_amount: float = 0.0
    currency: str = "EUR"
    category: Optional[str] = None
    status: str = "ok"
    is_duplicate: bool = False


class InvoiceUpdateRequest(BaseModel):
    """Request für Invoice-Update"""
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    supplier_name: Optional[str] = None
    net_amount: Optional[float] = None
    vat_amount: Optional[float] = None
    gross_amount: Optional[float] = None
    category: Optional[str] = None


class InvoiceUpdateResponse(BaseModel):
    """Response nach Invoice-Update"""
    status: str = "ok"
    message: str = "Invoice updated"
    invoice_id: int


# === User-Schemas ===

class UserResponse(BaseModel):
    """User-Daten Response"""
    logged_in: bool
    user_id: Optional[int] = None
    email: Optional[str] = None
    name: Optional[str] = None


class LoginRequest(BaseModel):
    """Login Request"""
    email: str
    password: str


class RegisterRequest(BaseModel):
    """Register Request"""
    email: str
    password: str
    name: Optional[str] = None


# === Statistics-Schemas ===

class StatisticsResponse(BaseModel):
    """Statistik-Response"""
    total_jobs: int = 0
    total_invoices: int = 0
    total_gross: float = 0.0
    total_net: float = 0.0
    total_vat: float = 0.0
    success_rate: float = 0.0


class MonthlySummary(BaseModel):
    """Monatliche Zusammenfassung"""
    month: str
    invoice_count: int
    total_gross: float
    total_net: float
    total_vat: float


# === Export-Schemas ===

class ExportResponse(BaseModel):
    """Export-Download Response"""
    status: str = "ok"
    format: str
    filename: str
    download_url: str
