"""AI-powered Invoice Data Extraction Service.

Extracts structured data from invoice PDFs and images using:
- Google Gemini 2.5 Flash (primary) — multimodal, handles images + PDFs
- Anthropic Claude Sonnet (fallback) — strong at structured extraction
- LlamaIndex (optional) — document indexing for complex multi-page invoices

Extracted fields: supplier, total_amount, currency, tax_amount,
invoice_number, invoice_date, due_date
"""
from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import Any, Optional

from dotenv import load_dotenv
load_dotenv("/var/www/invoice-app/.env")

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Du bist ein Experte für die Analyse von Rechnungen. Extrahiere die folgenden Felder aus dem Rechnungsdokument.

Antworte AUSSCHLIESSLICH als valides JSON-Objekt mit diesen Feldern:
{
  "supplier": "Name des Rechnungsausstellers/Lieferanten",
  "invoice_number": "Rechnungsnummer",
  "invoice_date": "Rechnungsdatum im Format YYYY-MM-DD",
  "due_date": "Fälligkeitsdatum im Format YYYY-MM-DD oder null",
  "total_amount_net": 0.00,
  "tax_amount": 0.00,
  "total_amount_gross": 0.00,
  "currency": "EUR",
  "tax_rate": 19,
  "line_items": [
    {"description": "Beschreibung", "quantity": 1, "unit_price": 0.00, "total": 0.00}
  ],
  "iban": "IBAN falls vorhanden oder null",
  "payment_reference": "Verwendungszweck falls vorhanden oder null"
}

Regeln:
- Alle Beträge als Zahlen (nicht als Strings)
- Datum immer als YYYY-MM-DD
- Wenn ein Feld nicht erkennbar ist, setze null
- Bei Bildern/Scans: OCR-Erkennung durchführen
- Währung ist EUR wenn nicht anders angegeben
"""


@dataclass
class ExtractionResult:
    supplier: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount_net: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount_gross: Optional[float] = None
    currency: str = "EUR"
    tax_rate: Optional[float] = None
    line_items: Optional[list] = None
    iban: Optional[str] = None
    payment_reference: Optional[str] = None
    model: str = "unknown"
    confidence: float = 0.0
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("raw_response", None)
        return d


class AIExtractionService:
    """Extracts structured invoice data using multimodal AI."""

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.llamaindex_key = os.getenv("LLAMAINDEX_API_KEY", "")

    def extract(self, file_content: bytes, file_name: str, mime_type: str) -> ExtractionResult:
        """Extract invoice data from file content.
        
        Tries Gemini 2.5 Flash first (multimodal), falls back to Claude.
        """
        # Try Gemini 2.5 Flash (best for multimodal — PDFs + images)
        if self.gemini_key:
            try:
                result = self._extract_gemini(file_content, file_name, mime_type)
                if result.supplier or result.total_amount_gross:
                    logger.info(f"extraction_success: gemini | {file_name} | {result.supplier} | {result.total_amount_gross}")
                    return result
            except Exception as e:
                logger.warning(f"gemini_extraction_failed: {e}")

        # Fallback to Claude (strong at structured data extraction)
        if self.anthropic_key:
            try:
                result = self._extract_claude(file_content, file_name, mime_type)
                if result.supplier or result.total_amount_gross:
                    logger.info(f"extraction_success: claude | {file_name} | {result.supplier} | {result.total_amount_gross}")
                    return result
            except Exception as e:
                logger.warning(f"claude_extraction_failed: {e}")

        logger.warning(f"extraction_failed: no AI could extract data from {file_name}")
        return ExtractionResult(model="none", confidence=0.0)

    def _extract_gemini(self, content: bytes, file_name: str, mime_type: str) -> ExtractionResult:
        """Use Google Gemini 2.5 Flash for multimodal extraction."""
        from google import genai

        client = genai.Client(api_key=self.gemini_key)

        # Build multimodal content
        parts = []

        if mime_type.startswith("image/") or mime_type == "application/pdf":
            b64 = base64.b64encode(content).decode("utf-8")
            parts.append(genai.types.Part.from_bytes(data=content, mime_type=mime_type))

        parts.append(genai.types.Part.from_text(text=EXTRACTION_PROMPT))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=parts,
        )

        raw = response.text.strip()
        parsed = self._parse_json(raw)

        return ExtractionResult(
            supplier=parsed.get("supplier"),
            invoice_number=parsed.get("invoice_number"),
            invoice_date=parsed.get("invoice_date"),
            due_date=parsed.get("due_date"),
            total_amount_net=self._to_float(parsed.get("total_amount_net")),
            tax_amount=self._to_float(parsed.get("tax_amount")),
            total_amount_gross=self._to_float(parsed.get("total_amount_gross")),
            currency=parsed.get("currency", "EUR"),
            tax_rate=self._to_float(parsed.get("tax_rate")),
            line_items=parsed.get("line_items"),
            iban=parsed.get("iban"),
            payment_reference=parsed.get("payment_reference"),
            model="gemini-2.5-flash",
            confidence=0.9 if parsed.get("supplier") else 0.3,
            raw_response=raw,
        )

    def _extract_claude(self, content: bytes, file_name: str, mime_type: str) -> ExtractionResult:
        """Use Anthropic Claude for extraction."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.anthropic_key)

        messages_content = []

        # Claude supports images and PDFs
        if mime_type.startswith("image/"):
            b64 = base64.b64encode(content).decode("utf-8")
            messages_content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime_type, "data": b64},
            })
        elif mime_type == "application/pdf":
            b64 = base64.b64encode(content).decode("utf-8")
            messages_content.append({
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
            })

        messages_content.append({"type": "text", "text": EXTRACTION_PROMPT})

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": messages_content}],
        )

        raw = response.content[0].text.strip()
        parsed = self._parse_json(raw)

        return ExtractionResult(
            supplier=parsed.get("supplier"),
            invoice_number=parsed.get("invoice_number"),
            invoice_date=parsed.get("invoice_date"),
            due_date=parsed.get("due_date"),
            total_amount_net=self._to_float(parsed.get("total_amount_net")),
            tax_amount=self._to_float(parsed.get("tax_amount")),
            total_amount_gross=self._to_float(parsed.get("total_amount_gross")),
            currency=parsed.get("currency", "EUR"),
            tax_rate=self._to_float(parsed.get("tax_rate")),
            line_items=parsed.get("line_items"),
            iban=parsed.get("iban"),
            payment_reference=parsed.get("payment_reference"),
            model="claude-sonnet-4",
            confidence=0.85 if parsed.get("supplier") else 0.3,
            raw_response=raw,
        )

    @staticmethod
    def _to_float(val) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_json(raw: str) -> dict:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:])
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {}
