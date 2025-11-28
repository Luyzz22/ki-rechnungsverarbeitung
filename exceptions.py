"""
SBS Deutschland – Custom Exceptions
Strukturierte Fehlerbehandlung für die Invoice-App.
"""

from typing import Optional, Dict, Any


class InvoiceAppError(Exception):
    """Basis-Exception für alle App-Fehler"""
    
    def __init__(
        self, 
        message: str, 
        code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Für JSON-Response"""
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


# === Ressourcen nicht gefunden ===

class NotFoundError(InvoiceAppError):
    """Ressource nicht gefunden"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "NOT_FOUND", 404, details)


class InvoiceNotFoundError(NotFoundError):
    """Rechnung nicht gefunden"""
    def __init__(self, invoice_id: int):
        super().__init__(
            f"Rechnung mit ID {invoice_id} nicht gefunden",
            {"invoice_id": invoice_id}
        )


class JobNotFoundError(NotFoundError):
    """Job nicht gefunden"""
    def __init__(self, job_id: str):
        super().__init__(
            f"Job mit ID {job_id} nicht gefunden",
            {"job_id": job_id}
        )


class UserNotFoundError(NotFoundError):
    """Benutzer nicht gefunden"""
    def __init__(self, user_id: int = None, email: str = None):
        identifier = user_id or email
        super().__init__(
            f"Benutzer nicht gefunden: {identifier}",
            {"user_id": user_id, "email": email}
        )


# === Validierungsfehler ===

class ValidationError(InvoiceAppError):
    """Validierungsfehler"""
    def __init__(self, message: str, field: str = None, details: Optional[Dict] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", 422, details)


class InvalidFileTypeError(ValidationError):
    """Ungültiger Dateityp"""
    def __init__(self, filename: str, allowed_types: list):
        super().__init__(
            f"Dateityp nicht erlaubt: {filename}",
            "file",
            {"filename": filename, "allowed_types": allowed_types}
        )


class FileTooLargeError(ValidationError):
    """Datei zu groß"""
    def __init__(self, filename: str, size: int, max_size: int):
        super().__init__(
            f"Datei zu groß: {filename} ({size / 1024 / 1024:.1f} MB, max: {max_size / 1024 / 1024:.0f} MB)",
            "file",
            {"filename": filename, "size": size, "max_size": max_size}
        )


# === Duplikate ===

class DuplicateError(InvoiceAppError):
    """Duplikat erkannt"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "DUPLICATE", 409, details)


class DuplicateInvoiceError(DuplicateError):
    """Doppelte Rechnung"""
    def __init__(self, invoice_number: str, original_id: int):
        super().__init__(
            f"Rechnung {invoice_number} existiert bereits",
            {"invoice_number": invoice_number, "original_id": original_id}
        )


class DuplicateEmailError(DuplicateError):
    """E-Mail bereits registriert"""
    def __init__(self, email: str):
        super().__init__(
            f"E-Mail bereits registriert: {email}",
            {"email": email}
        )


# === Verarbeitungsfehler ===

class ProcessingError(InvoiceAppError):
    """Fehler bei der Verarbeitung"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "PROCESSING_ERROR", 500, details)


class OCRError(ProcessingError):
    """Fehler bei der Texterkennung"""
    def __init__(self, filename: str, reason: str = None):
        super().__init__(
            f"OCR-Fehler bei {filename}: {reason or 'Unbekannt'}",
            {"filename": filename, "reason": reason}
        )


class ExtractionError(ProcessingError):
    """Fehler bei der Datenextraktion"""
    def __init__(self, filename: str, missing_fields: list = None):
        super().__init__(
            f"Extraktion fehlgeschlagen: {filename}",
            {"filename": filename, "missing_fields": missing_fields or []}
        )


class ExportError(ProcessingError):
    """Fehler beim Export"""
    def __init__(self, format: str, reason: str = None):
        super().__init__(
            f"Export-Fehler ({format}): {reason or 'Unbekannt'}",
            {"format": format, "reason": reason}
        )


# === Authentifizierung ===

class AuthError(InvoiceAppError):
    """Authentifizierungsfehler"""
    def __init__(self, message: str = "Nicht authentifiziert"):
        super().__init__(message, "AUTH_ERROR", 401)


class PermissionError(InvoiceAppError):
    """Keine Berechtigung"""
    def __init__(self, message: str = "Keine Berechtigung"):
        super().__init__(message, "PERMISSION_DENIED", 403)


# === Limits ===

class QuotaExceededError(InvoiceAppError):
    """Kontingent überschritten"""
    def __init__(self, current: int, limit: int, resource: str = "invoices"):
        super().__init__(
            f"Kontingent überschritten: {current}/{limit} {resource}",
            "QUOTA_EXCEEDED",
            429,
            {"current": current, "limit": limit, "resource": resource}
        )


class RateLimitError(InvoiceAppError):
    """Rate Limit erreicht"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            f"Zu viele Anfragen. Bitte {retry_after}s warten.",
            "RATE_LIMIT",
            429,
            {"retry_after": retry_after}
        )
