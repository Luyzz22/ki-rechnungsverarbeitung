"""
SBS Deutschland – Domain Models
Zentrale Datenstrukturen für Invoice und Job.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class JobStatus(str, Enum):
    """Status eines Verarbeitungs-Jobs"""
    UPLOADED = "uploaded"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class InvoiceStatus(str, Enum):
    """Status einer einzelnen Rechnung"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    DUPLICATE = "duplicate"


class PlausibilityLevel(str, Enum):
    """Plausibilitätsstufe"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class Invoice:
    """Repräsentiert eine verarbeitete Rechnung"""
    id: Optional[int] = None
    job_id: Optional[str] = None
    filename: str = ""
    
    # Extrahierte Daten
    invoice_number: str = ""
    invoice_date: str = ""
    supplier_name: str = ""
    supplier_address: str = ""
    
    # Beträge
    net_amount: float = 0.0
    vat_amount: float = 0.0
    vat_rate: float = 19.0
    gross_amount: float = 0.0
    currency: str = "EUR"
    
    # Kategorisierung
    category: str = ""
    category_confidence: float = 0.0
    
    # Status & Validierung
    status: InvoiceStatus = InvoiceStatus.OK
    plausibility: PlausibilityLevel = PlausibilityLevel.UNKNOWN
    plausibility_score: float = 0.0
    is_duplicate: bool = False
    duplicate_of: Optional[int] = None
    
    # Metadaten
    created_at: Optional[str] = None
    processed_at: Optional[str] = None
    raw_text: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für JSON/DB"""
        data = asdict(self)
        # Enums zu Strings
        data['status'] = self.status.value if isinstance(self.status, Enum) else self.status
        data['plausibility'] = self.plausibility.value if isinstance(self.plausibility, Enum) else self.plausibility
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Invoice':
        """Erstellt Invoice aus Dictionary"""
        # Status-Enums konvertieren
        if 'status' in data and isinstance(data['status'], str):
            try:
                data['status'] = InvoiceStatus(data['status'])
            except ValueError:
                data['status'] = InvoiceStatus.OK
        
        if 'plausibility' in data and isinstance(data['plausibility'], str):
            try:
                data['plausibility'] = PlausibilityLevel(data['plausibility'])
            except ValueError:
                data['plausibility'] = PlausibilityLevel.UNKNOWN
        
        # Nur bekannte Felder übernehmen
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    @property
    def is_valid(self) -> bool:
        """Prüft ob Rechnung gültig ist"""
        return (
            self.status == InvoiceStatus.OK and
            not self.is_duplicate and
            self.invoice_number != "" and
            self.gross_amount > 0
        )


@dataclass
class Job:
    """Repräsentiert einen Verarbeitungs-Job"""
    job_id: str = ""
    user_id: Optional[int] = None
    
    # Status
    status: JobStatus = JobStatus.PENDING
    
    # Zähler
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    
    # Aggregierte Werte
    total_net: float = 0.0
    total_vat: float = 0.0
    total_gross: float = 0.0
    
    # Export-Dateien
    exported_files: Dict[str, str] = field(default_factory=dict)
    
    # Zeitstempel
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # E-Mail Benachrichtigung
    notification_email: str = ""
    notification_sent: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für JSON/DB"""
        data = asdict(self)
        data['status'] = self.status.value if isinstance(self.status, Enum) else self.status
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Erstellt Job aus Dictionary"""
        if 'status' in data and isinstance(data['status'], str):
            try:
                data['status'] = JobStatus(data['status'])
            except ValueError:
                data['status'] = JobStatus.PENDING
        
        # exported_files kann JSON-String sein
        if 'exported_files' in data and isinstance(data['exported_files'], str):
            import json
            try:
                data['exported_files'] = json.loads(data['exported_files'])
            except:
                data['exported_files'] = {}
        
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    @property
    def progress_percent(self) -> float:
        """Fortschritt in Prozent"""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100
    
    @property
    def is_complete(self) -> bool:
        """Prüft ob Job abgeschlossen"""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED)


# Typ-Aliase für bessere Lesbarkeit
InvoiceList = List[Invoice]
JobDict = Dict[str, Any]
