"""Safe structured logging helpers for AI/OCR paths."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any


REDACTED = "[REDACTED]"
MAX_STRING_LENGTH = 120

REDACTED_KEYS = {
    "invoice_text",
    "document_text",
    "ocr_text",
    "prompt",
    "response",
    "content",
    "body",
    "base64",
    "file",
    "file_name",
    "filename",
    "api_key",
    "token",
    "authorization",
    "email",
    "iban",
    "invoice_number",
    "rechnungsnummer",
    "tax_id",
    "vat_id",
    "supplier_name",
    "supplier",
    "raw_response",
}

_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b", re.IGNORECASE)
_API_KEY_RE = re.compile(r"\b(?:sk-|sk-ant-|AIza)[A-Za-z0-9_\-]{16,}\b")
_INVOICE_NUMBER_RE = re.compile(
    r"\b(?:RE|RG|INV|INVOICE|RECHNUNG)[\s:_-]*[A-Z0-9][A-Z0-9/_-]{2,}\b",
    re.IGNORECASE,
)
_BASE64_RE = re.compile(r"\b(?:[A-Za-z0-9+/]{20,}={0,2})\b")


def hash_identifier(value: Any) -> str:
    """Return a stable short SHA-256 hash for IDs used in logs."""
    if value is None:
        return ""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def _is_sensitive_key(key: Any) -> bool:
    key_text = str(key).strip().lower()
    if key_text in REDACTED_KEYS:
        return True
    return any(part in key_text for part in ("api_key", "authorization", "base64", "token"))


def _sanitize_string(value: str, *, max_length: int = MAX_STRING_LENGTH) -> str | dict[str, Any]:
    redacted = _EMAIL_RE.sub(REDACTED, value)
    redacted = _IBAN_RE.sub(REDACTED, redacted)
    redacted = _API_KEY_RE.sub(REDACTED, redacted)
    redacted = _INVOICE_NUMBER_RE.sub(REDACTED, redacted)
    redacted = _BASE64_RE.sub(REDACTED, redacted)

    if len(redacted) > max_length:
        return {
            "truncated": True,
            "length": len(redacted),
            "sha256": hashlib.sha256(redacted.encode("utf-8")).hexdigest()[:16],
        }
    return redacted


def sanitize_for_log(value: Any, *, max_string_length: int = MAX_STRING_LENGTH) -> Any:
    """Recursively redact sensitive keys and long strings."""
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                sanitized[key_text] = REDACTED
            elif key_text.lower().endswith("_id") and item is not None:
                sanitized[f"{key_text}_hash"] = hash_identifier(item)
            else:
                sanitized[key_text] = sanitize_for_log(item, max_string_length=max_string_length)
        return sanitized

    if isinstance(value, str):
        return _sanitize_string(value, max_length=max_string_length)

    if isinstance(value, bytes):
        return {
            "bytes": len(value),
            "sha256": hashlib.sha256(value).hexdigest()[:16],
        }

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [sanitize_for_log(item, max_string_length=max_string_length) for item in value[:20]]

    return value


def safe_log(
    logger: logging.Logger,
    level: int,
    event: str,
    **metadata: Any,
) -> None:
    """Write a single structured, PII-free log event."""
    payload = sanitize_for_log(metadata)
    logger.log(level, "%s %s", event, json.dumps(payload, ensure_ascii=True, sort_keys=True))


def log_inference_event(
    logger: logging.Logger,
    *,
    event: str,
    provider: str,
    model: str | None = None,
    data_class: str | None = None,
    inference_profile: str | None = None,
    policy_decision: str | None = None,
    duration_ms: float | None = None,
    error_code: str | None = None,
    invoice_id: Any | None = None,
    level: int = logging.INFO,
    **metadata: Any,
) -> None:
    """Log allowed metadata for an inference/OCR event."""
    safe_metadata: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "data_class": data_class,
        "inference_profile": inference_profile,
        "policy_decision": policy_decision,
        "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
        "error_code": error_code,
        "invoice_id_hash": hash_identifier(invoice_id) if invoice_id is not None else None,
    }
    safe_metadata.update(metadata)
    safe_log(logger, level, event, **safe_metadata)
