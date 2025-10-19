#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung - Core Module v3.0
Shared functions used by all versions
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import yaml

import PyPDF2
from openai import OpenAI
from dotenv import load_dotenv

# Initialize
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('invoice_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration Manager"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load config from YAML or use defaults"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        # Default config
        return {
            'openai': {
                'model': 'gpt-4o-mini',
                'temperature': 0,
                'max_retries': 3,
                'timeout': 30
            },
            'processing': {
                'parallel': True,
                'max_workers': 8,
                'chunk_size': 3500
            },
            'export': {
                'formats': ['xlsx', 'csv'],
                'output_dir': '.',
                'auto_open': True
            },
            'validation': {
                'enabled': True,
                'strict_mode': False
            }
        }
    
    def get(self, key: str, default=None):
        """Get config value by dot notation (e.g., 'openai.model')"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


class InvoiceProcessor:
    """Core Invoice Processing Logic"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY not found in environment!")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """Extract text from PDF with error handling"""
        try:
            logger.info(f"Extracting text from: {pdf_path.name}")
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                if reader.is_encrypted:
                    logger.error(f"PDF is encrypted: {pdf_path.name}")
                    return None
                
                text = ""
                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        text += page_text
                    except Exception as e:
                        logger.warning(f"Error on page {i+1}: {e}")
                        continue
                
                if not text.strip():
                    logger.error(f"No text extracted from: {pdf_path.name}")
                    return None
                
                logger.info(f"Extracted {len(text)} characters")
                return text
                
        except Exception as e:
            logger.error(f"PDF extraction failed for {pdf_path.name}: {e}")
            return None
    
    def extract_invoice_data(self, text: str, filename: str) -> Optional[Dict]:
        """Extract structured data using OpenAI with retry logic"""
        
        max_retries = self.config.get('openai.max_retries', 3)
        chunk_size = self.config.get('processing.chunk_size', 3500)
        
        # Truncate text to avoid token limits
        text_chunk = text[:chunk_size]
        
        prompt = self._build_prompt(text_chunk)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"API call for {filename} (attempt {attempt + 1}/{max_retries})")
                
                response = self.client.chat.completions.create(
                    model=self.config.get('openai.model', 'gpt-4o-mini'),
                    messages=[
                        {
                            "role": "system", 
                            "content": "Du bist ein Experte für Rechnungsverarbeitung. Extrahiere alle relevanten Daten präzise aus der Rechnung. Antworte ausschließlich mit validem JSON."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    temperature=self.config.get('openai.temperature', 0),
                    timeout=self.config.get('openai.timeout', 30)
                )
                
                json_text = response.choices[0].message.content.strip()
                json_text = self._clean_json_response(json_text)
                
                data = json.loads(json_text)
                
                # Add metadata
                data['dateiname'] = filename
                data['verarbeitet_am'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data['text_laenge'] = len(text)
                data['model'] = self.config.get('openai.model', 'gpt-4o-mini')
                
                logger.info(f"Successfully extracted data from {filename}")
                return data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                    
            except Exception as e:
                logger.error(f"API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
        
        logger.error(f"Failed to extract data from {filename} after {max_retries} attempts")
        return None
    
    def _build_prompt(self, text: str) -> str:
        """Build improved prompt for better extraction"""
        return f"""Analysiere diese Rechnung und extrahiere alle verfügbaren Daten als JSON.

RECHNUNGSTEXT:
{text}

WICHTIG:
- Extrahiere nur Daten die wirklich in der Rechnung stehen
- Wenn eine Information fehlt: null verwenden
- Beträge als Dezimalzahlen (Punkt als Trenner)
- Datumsformat: YYYY-MM-DD
- IBAN ohne Leerzeichen

GEWÜNSCHTES JSON-FORMAT:
{{
  "rechnungsnummer": "...",
  "datum": "YYYY-MM-DD",
  "faelligkeitsdatum": "YYYY-MM-DD",
  "lieferant": "...",
  "lieferant_adresse": "...",
  "kundennummer": "...",
  "betrag_brutto": 123.45,
  "betrag_netto": 100.00,
  "mwst_betrag": 23.45,
  "mwst_satz": 19,
  "waehrung": "EUR",
  "iban": "DE...",
  "bic": "...",
  "steuernummer": "...",
  "ust_idnr": "DE...",
  "zahlungsbedingungen": "..."
}}

Antworte NUR mit dem JSON-Objekt, keine zusätzlichen Erklärungen!"""
    
    def _clean_json_response(self, text: str) -> str:
        """Clean AI response to extract valid JSON"""
        # Remove markdown code blocks
        text = text.replace("```json", "").replace("```", "")
        
        # Remove any text before first {
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            text = text[start:end+1]
        
        return text.strip()
    
    def process_invoice(self, pdf_path: Path) -> Optional[Dict]:
        """Process single invoice (extract + validate)"""
        
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            return None
        
        # Extract data
        data = self.extract_invoice_data(text, pdf_path.name)
        if not data:
            return None
        
        # Validate if enabled
        if self.config.get('validation.enabled', True):
            from validation import InvoiceValidator
            validator = InvoiceValidator(
                strict=self.config.get('validation.strict_mode', False)
            )
            is_valid, errors = validator.validate(data)
            
            data['validation'] = {
                'valid': is_valid,
                'errors': errors
            }
            
            if errors:
                logger.warning(f"Validation issues for {pdf_path.name}: {errors}")
        
        return data


def create_output_directory(path: str = "output") -> Path:
    """Create output directory if it doesn't exist"""
    output_dir = Path(path)
    output_dir.mkdir(exist_ok=True)
    return output_dir


def get_pdf_files(directory: str = "test_rechnungen") -> List[Path]:
    """Get all PDF files from directory"""
    folder = Path(directory)
    
    if not folder.exists():
        folder.mkdir()
        logger.info(f"Created directory: {directory}")
        return []
    
    pdfs = list(folder.glob("*.pdf"))
    logger.info(f"Found {len(pdfs)} PDF files in {directory}")
    return pdfs


def format_currency(amount: float, currency: str = "EUR") -> str:
    """Format amount as currency string"""
    if currency == "EUR":
        return f"{amount:.2f}€"
    return f"{amount:.2f} {currency}"


def calculate_statistics(results: List[Dict]) -> Dict:
    """Calculate processing statistics"""
    if not results:
        return {}
    
    total_brutto = sum(r.get('betrag_brutto', 0) for r in results if r.get('betrag_brutto'))
    total_netto = sum(r.get('betrag_netto', 0) for r in results if r.get('betrag_netto'))
    total_mwst = sum(r.get('mwst_betrag', 0) for r in results if r.get('mwst_betrag'))
    
    return {
        'total_invoices': len(results),
        'total_brutto': total_brutto,
        'total_netto': total_netto,
        'total_mwst': total_mwst,
        'average_brutto': total_brutto / len(results) if results else 0,
        'average_netto': total_netto / len(results) if results else 0,
        'currency': results[0].get('waehrung', 'EUR') if results else 'EUR'
    }
