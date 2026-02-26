#!/usr/bin/env python3
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
import pandas as pd
from datetime import datetime
import subprocess
import platform

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"❌ PDF Error: {e}")
        return None

def extract_invoice_data(text, filename):
    prompt = f"""Extrahiere aus dieser Rechnung Daten als JSON:

{text[:3500]}

Format (nur JSON, keine Erklärungen):
{{
  "rechnungsnummer": "...",
  "datum": "YYYY-MM-DD",
  "lieferant": "...",
  "betrag_brutto": 123.45,
  "betrag_netto": 100.00,
  "mwst_betrag": 23.45,
  "iban": "..."
}}

Wenn Info fehlt: null setzen
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Du extrahierst Rechnungsdaten. Antworte nur mit JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        json_text = response.choices[0].message.content.strip()
        json_text = json_text.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(json_text)
        data['dateiname'] = filename
        data['verarbeitet_am'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return data
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

def process_invoice(pdf_path):
    print(f"\n📄 {pdf_path.name}")
    
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return None
    
    print(f"   Text: {len(text)} Zeichen")
    
    data = extract_invoice_data(text, pdf_path.name)
    
    if data:
        print(f"   ✅ {data.get('lieferant', '?')}")
        print(f"   💰 {data.get('betrag_brutto', '?')}€")
    
    return data

def main():
    print("\n" + "="*60)
    print("🤖 KI-RECHNUNGSVERARBEITUNG v1.0")
    print("="*60 + "\n")
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Fehler: OPENAI_API_KEY nicht in .env gefunden!")
        return
    
    folder = Path("test_rechnungen")
    if not folder.exists():
        folder.mkdir()
        print("✅ Ordner 'test_rechnungen' erstellt")
        print("→ Füge PDFs hinzu und starte neu!\n")
        return
    
    pdfs = list(folder.glob("*.pdf"))
    
    if not pdfs:
        print("❌ Keine PDFs in 'test_rechnungen' gefunden!")
        print("→ Kopiere PDFs rein und starte neu!\n")
        return
    
    print(f"🚀 Verarbeite {len(pdfs)} Rechnungen...\n")
    
    results = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}]", end="")
        data = process_invoice(pdf)
        if data:
            results.append(data)
    
    if results:
        df = pd.DataFrame(results)
        output = "rechnungen_export.xlsx"
        df.to_excel(output, index=False)
        
        print(f"\n{'='*60}")
        print(f"✅ Fertig! {len(results)} Rechnungen verarbeitet")
        print(f"📊 Export: {output}")
        
        if 'betrag_brutto' in df.columns:
            total = df['betrag_brutto'].sum()
            print(f"💰 Gesamt: {total:.2f}€")
        
        # Excel automatisch öffnen
        try:
            if platform.system() == 'Darwin':  # Mac
                subprocess.run(['open', output])
            elif platform.system() == 'Windows':
                os.startfile(output)
            else:  # Linux
                subprocess.run(['xdg-open', output])
            
            print("📂 Excel wurde geöffnet!")
        except Exception as e:
            print(f"⚠️  Excel konnte nicht geöffnet werden: {e}")
        
        print("="*60 + "\n")
    else:
        print("\n❌ Keine Rechnungen erfolgreich verarbeitet\n")

if __name__ == "__main__":
    main()
