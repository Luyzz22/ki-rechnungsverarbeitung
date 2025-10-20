#!/usr/bin/env python3
"""
Core functionality for invoice processing
Improved version with better supplier/issuer distinction
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
import PyPDF2
from anthropic import Anthropic
from openai import OpenAI


class Config:
    """Configuration management"""

    def __init__(self, config_file: str = 'config.yaml'):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        import yaml

        if not Path(self.config_file).exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get(self, key: str, default=None):
        """Get configuration value by dot notation (e.g., 'ai.model')"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        return value if value is not None else default


class InvoiceProcessor:
    """Process invoices using AI"""

    def __init__(self, config: Config):
        self.config = config

        # Determine which AI provider to use
        self.provider = config.get('ai.provider', 'anthropic')

        if self.provider == 'openai':
            self.api_key = os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            self.client = OpenAI(api_key=self.api_key)
            self.model = config.get('ai.model', 'gpt-4o')
        else:
            self.api_key = os.getenv('ANTHROPIC_API_KEY')
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            self.client = Anthropic(api_key=self.api_key)
            self.model = config.get('ai.model', 'claude-sonnet-4-20250514')

    def process_invoice(self, pdf_path: Path) -> Optional[Dict]:
        """Process a single invoice PDF"""
        try:
            # Extract text from PDF
            text = self._extract_text(pdf_path)

            if not text or len(text.strip()) < 50:
                print(f"⚠️  Zu wenig Text in {pdf_path.name}, versuche OCR...")
                # OCR fallback would go here
                return None

            # Extract data with AI
            data = self._extract_with_ai(text)

            if data:
                data['dateiname'] = pdf_path.name
                return data

            return None

        except Exception as e:
            print(f"❌ Fehler bei {pdf_path.name}: {e}")
            return None

    def _extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF"""
        text = ""

        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

        except Exception as e:
            print(f"Fehler beim Text-Extraktion: {e}")

        return text.strip()

    def _extract_with_ai(self, text: str) -> Optional[Dict]:
        """Extract invoice data using AI with improved prompt"""

        # IMPROVED PROMPT - Better distinction between supplier and issuer
        prompt = f"""Du bist ein Experte für die Analyse von deutschen Rechnungen und Buchhaltung.
KRITISCHE UNTERSCHEIDUNG - SEHR WICHTIG:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Der RECHNUNGSAUSSTELLER ist derjenige, der die Rechnung SCHREIBT und das Geld ERHÄLT
→ Steht meist OBEN im Header, Briefkopf, Absenderzeile
→ Hat meist Kontaktdaten (Tel, Email, IBAN) in der Rechnung
Der LIEFERANT/KUNDE ist derjenige, der die Rechnung EMPFÄNGT und BEZAHLEN muss
→ Steht meist UNTER dem Header bei "An:", "z.H.", in der Empfängeradresse
→ Ist der KUNDE des Rechnungsausstellers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ANALYSIERE SCHRITT FÜR SCHRITT:
SCHRITT 1: Identifiziere die Parteien
→ Wer schreibt die Rechnung? (oben, Header) = RECHNUNGSAUSSTELLER
→ An wen geht sie? (nach "An:", "z.H.") = LIEFERANT/KUNDE
SCHRITT 2: Extrahiere Beträge
→ Netto, Brutto, MwSt., Währung
SCHRITT 3: Extrahiere Datum & Nummern
→ Rechnungsnummer, Datum, Fälligkeitsdatum
SCHRITT 4: Extrahiere weitere Details
→ IBAN, Verwendungszweck, etc.
BEISPIELE ZUR VERDEUTLICHUNG:
Beispiel 1:
"AS-Technik * In der Dell 19 * 69469 Weinheim
An: AMTech GmbH
Anne Frank Str. 14
69221 Dossenheim"
→ Rechnungsaussteller: "AS-Technik"
→ Lieferant: "AMTech GmbH" (wer bezahlt!)
Beispiel 2:
"IT-Support AG, Hauptstraße 1, 10115 Berlin
Rechnung an:
Kunde XY GmbH, Nebenstraße 5, 20095 Hamburg"
→ Rechnungsaussteller: "IT-Support AG"
→ Lieferant: "Kunde XY GmbH" (wer bezahlt!)
TEXT DER RECHNUNG:
{text}
Antworte NUR mit einem gültigen JSON-Objekt (keine Erklärungen davor oder danach):
{{
"rechnungsnummer": "Rechnungsnummer",
"datum": "YYYY-MM-DD",
"faelligkeitsdatum": "YYYY-MM-DD oder null",
"lieferant": "Name des EMPFÄNGERS/KUNDEN (wer die Rechnung bezahlen muss)",
"lieferant_adresse": "Vollständige Adresse des Empfängers",
"rechnungsaussteller": "Name des Rechnungsschreibers (wer das Geld erhält)",
"rechnungsaussteller_adresse": "Vollständige Adresse des Ausstellers",
"betrag_netto": Betrag_als_Zahl,
"betrag_brutto": Betrag_als_Zahl,
"mwst_betrag": Betrag_als_Zahl,
"mwst_satz": Prozentsatz_als_Zahl,
"waehrung": "EUR",
"zahlungsziel_tage": Anzahl_Tage_oder_null,
"iban": "IBAN falls vorhanden oder null",
"bic": "BIC falls vorhanden oder null",
"kundennummer": "Kundennummer falls vorhanden oder null",
"verwendungszweck": "Kurze Beschreibung der Leistung"
}}
WICHTIG: Gib NUR das JSON zurück, keine zusätzlichen Texte!"""
        try:
            if self.provider == 'openai':
                # OpenAI GPT
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }],
                    max_tokens=2048,
                    temperature=0
                )
                response_text = response.choices[0].message.content

            else:
                # Anthropic Claude
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                response_text = message.content[0].text

            # Parse JSON response
            data = self._parse_json_response(response_text)

            return data

        except Exception as e:
            print(f"AI extraction error: {e}")
            return None

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Parse JSON from AI response"""
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)

                # Convert string numbers to float
                for key in ['betrag_netto', 'betrag_brutto', 'mwst_betrag', 'mwst_satz']:
                    if key in data and data[key]:
                        try:
                            # Handle German number format (comma as decimal)
                            if isinstance(data[key], str):
                                data[key] = float(data[key].replace(',', '.').replace(' ', ''))
                        except Exception:
                            data[key] = None

                return data

            return None

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return None


def get_pdf_files(directory: str) -> List[Path]:
    """Get all PDF files from directory"""
    path = Path(directory)
    if not path.exists():
        return []

    return sorted(path.glob("*.pdf"))


def calculate_statistics(results: List[Dict]) -> Dict:
    """Calculate statistics from results"""
    if not results:
        return {
            'total_invoices': 0,
            'total_brutto': 0,
            'total_netto': 0,
            'total_mwst': 0,
            'average_brutto': 0
        }

    total_brutto = sum(r.get('betrag_brutto', 0) or 0 for r in results)
    total_netto = sum(r.get('betrag_netto', 0) or 0 for r in results)
    total_mwst = sum(r.get('mwst_betrag', 0) or 0 for r in results)

    return {
        'total_invoices': len(results),
        'total_brutto': total_brutto,
        'total_netto': total_netto,
        'total_mwst': total_mwst,
        'average_brutto': total_brutto / len(results) if results else 0
    }


if __name__ == "__main__":
    # Quick test
    config = Config()
    processor = InvoiceProcessor(config)
    print("Invoice Processor Ready!")
    print(f"Provider: {processor.provider}")
    print(f"Model: {processor.model}")

