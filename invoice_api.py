# invoice_api.py
import base64
import json
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

router = APIRouter(prefix="/api/v1", tags=["invoice"])

INVOICE_API_KEY = os.getenv("INVOICE_API_KEY")


class InvoiceProcessRequest(BaseModel):
    file: str          # Base64-String
    metadata: Dict[str, Any] | None = None


@router.post("/process")
async def process_invoice(request: Request):
    # Optional: API-Key-Auth über Header x-api-key
    if INVOICE_API_KEY:
        client_key = request.headers.get("x-api-key")
        if not client_key or client_key != INVOICE_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

    # Body parsen
    try:
        payload = await request.json()
        data = InvoiceProcessRequest(**payload)
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    # PDF aus Base64 dekodieren
    try:
        pdf_bytes = base64.b64decode(data.file)
    except Exception:
        raise HTTPException(status_code=400, detail="file must be valid base64")

    # TODO: hier deine bestehende OCR + KI-Extraktion aufrufen
    # Beispiel: result = extract_invoice(pdf_bytes, metadata=data.metadata)
    extracted_data = {
        "documentId": data.metadata.get("documentId") if data.metadata else None,
        "amount": 123.45,
        "currency": "EUR",
        "vendor": "Demo Lieferant GmbH",
        "confidence": 0.97,
    }

    return {
        "status": "success",
        "data": extracted_data,
    }
