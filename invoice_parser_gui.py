#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung - GUI Version v2.0
Mit Drag & Drop, Fortschrittsbalken und modernem Design
"""

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
import pandas as pd
from datetime import datetime
import threading

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class InvoiceProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 KI-Rechnungsverarbeitung v2.0")
        self.root.geometry("900x700")
        self.root.configure(bg='#1e1e1e')
        
        # Styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", 
                       thickness=25,
                       troughcolor='#2b2b2b',
                       background='#00ff88',
                       bordercolor='#1e1e1e',
                       lightcolor='#00ff88',
                       darkcolor='#00ff88')
        
        self.pdf_files = []
        self.results = []
        self.processing = False
        
        self.create_widgets()
        
    def create_widgets(self):
        # Header Frame
        header_frame = tk.Frame(self.root, bg='#1e1e1e')
        header_frame.pack(pady=20, fill='x')
        
        # Title
        title = tk.Label(
            header_frame,
            text="🤖 KI-RECHNUNGSVERARBEITUNG",
            font=("Arial", 28, "bold"),
            bg='#1e1e1e',
            fg='#00d4ff'
        )
        title.pack()
        
        subtitle = tk.Label(
            header_frame,
            text="Automatische PDF-Extraktion mit ChatGPT API",
            font=("Arial", 13),
            bg='#1e1e1e',
            fg='#888888'
        )
        subtitle.pack(pady=5)
        
        version = tk.Label(
            header_frame,
            text="v2.0",
            font=("Arial", 10),
            bg='#1e1e1e',
            fg='#555555'
        )
        version.pack()
        
        # Separator
        sep1 = tk.Frame(self.root, height=2, bg='#333333')
        sep1.pack(fill='x', padx=50, pady=15)
        
        # File Selection Frame
        file_frame = tk.Frame(self.root, bg='#1e1e1e')
        file_frame.pack(pady=20, padx=50, fill='x')
        
        select_btn = tk.Button(
            file_frame,
            text="📁 PDFs AUSWÄHLEN",
            command=self.select_files,
            font=("Arial", 14, "bold"),
            bg='#00d4ff',
            fg='#1e1e1e',
            padx=30,
            pady=12,
            relief='flat',
            cursor='hand2',
            activebackground='#00b8d4',
            activeforeground='#ffffff'
        )
        select_btn.pack(side='left', padx=10)
        
        self.file_label = tk.Label(
            file_frame,
            text="Keine Dateien ausgewählt",
            font=("Arial", 12),
            bg='#1e1e1e',
            fg='#888888',
            anchor='w'
        )
        self.file_label.pack(side='left', padx=20, fill='x', expand=True)
        
        # Process Button Frame
        btn_frame = tk.Frame(self.root, bg='#1e1e1e')
        btn_frame.pack(pady=20)
        
        self.process_btn = tk.Button(
            btn_frame,
            text="🚀 JETZT VERARBEITEN",
            command=self.start_processing,
            font=("Arial", 16, "bold"),
            bg='#00ff88',
            fg='#1e1e1e',
            padx=50,
            pady=15,
            relief='flat',
            cursor='hand2',
            state='disabled',
            activebackground='#00dd77',
            activeforeground='#1e1e1e'
        )
        self.process_btn.pack()
        
        # Progress Frame
        progress_frame = tk.Frame(self.root, bg='#1e1e1e')
        progress_frame.pack(pady=20, padx=50, fill='x')
        
        self.progress = ttk.Progressbar(
            progress_frame,
            length=800,
            mode='determinate',
            style="TProgressbar"
        )
        self.progress.pack()
        
        # Status Label
        self.status_label = tk.Label(
            self.root,
            text="Bereit für Verarbeitung",
            font=("Arial", 12),
            bg='#1e1e1e',
            fg='#00d4ff'
        )
        self.status_label.pack(pady=10)
        
        # Separator
        sep2 = tk.Frame(self.root, height=2, bg='#333333')
        sep2.pack(fill='x', padx=50, pady=10)
        
        # Results Frame
        results_label = tk.Label(
            self.root,
            text="📊 Live-Log",
            font=("Arial", 14, "bold"),
            bg='#1e1e1e',
            fg='#00d4ff'
        )
        results_label.pack(pady=(10, 5))
        
        self.results_frame = tk.Frame(self.root, bg='#1e1e1e')
        self.results_frame.pack(pady=10, padx=50, fill='both', expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(self.results_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.results_text = tk.Text(
            self.results_frame,
            font=("Courier", 11),
            bg='#0d0d0d',
            fg='#00ff88',
            height=12,
            relief='flat',
            yscrollcommand=scrollbar.set,
            padx=15,
            pady=15
        )
        self.results_text.pack(fill='both', expand=True)
        scrollbar.config(command=self.results_text.yview)
        
        # Initial message
        self.log_message("💡 Bereit! Wähle PDFs aus und klicke 'VERARBEITEN'", color='#00d4ff')
        
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="PDF-Rechnungen auswählen",
            filetypes=[("PDF Dateien", "*.pdf"), ("Alle Dateien", "*.*")]
        )
        
        if files:
            self.pdf_files = list(files)
            count = len(self.pdf_files)
            
            if count == 1:
                text = f"✅ {count} Datei ausgewählt: {Path(files[0]).name}"
            else:
                text = f"✅ {count} Dateien ausgewählt"
            
            self.file_label.config(text=text, fg='#00ff88')
            self.process_btn.config(state='normal')
            self.results_text.delete('1.0', 'end')
            self.log_message(f"\n📁 {count} PDF{'s' if count > 1 else ''} ausgewählt:", color='#00d4ff')
            
            for i, file in enumerate(files, 1):
                filename = Path(file).name
                self.log_message(f"   {i}. {filename}", color='#888888')
    
    def log_message(self, message, color='#00ff88'):
        self.results_text.tag_config(color, foreground=color)
        self.results_text.insert('end', message + '\n', color)
        self.results_text.see('end')
        self.root.update()
    
    def start_processing(self):
        if self.processing:
            return
        
        self.processing = True
        self.process_btn.config(state='disabled', text="⏳ VERARBEITUNG LÄUFT...")
        self.results_text.delete('1.0', 'end')
        self.results = []
        
        # Start in thread
        thread = threading.Thread(target=self.process_invoices)
        thread.daemon = True
        thread.start()
    
    def extract_text_from_pdf(self, pdf_path):
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            self.log_message(f"   ❌ PDF-Fehler: {str(e)[:50]}...", color='#ff4444')
            return None
    
    def extract_invoice_data(self, text, filename):
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
            self.log_message(f"   ❌ API-Fehler: {str(e)[:50]}...", color='#ff4444')
            return None
    
    def process_invoices(self):
        total = len(self.pdf_files)
        self.progress['maximum'] = total
        self.progress['value'] = 0
        
        self.log_message(f"\n{'='*70}", color='#00d4ff')
        self.log_message(f"🚀 STARTE VERARBEITUNG VON {total} RECHNUNG{'EN' if total != 1 else ''}", color='#00d4ff')
        self.log_message(f"{'='*70}\n", color='#00d4ff')
        
        for i, pdf_path in enumerate(self.pdf_files, 1):
            filename = Path(pdf_path).name
            self.status_label.config(text=f"⏳ Verarbeite {i}/{total}: {filename}")
            
            self.log_message(f"[{i}/{total}] 📄 {filename}", color='#00d4ff')
            
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)
            if not text:
                self.progress['value'] = i
                continue
            
            self.log_message(f"   ✓ {len(text)} Zeichen extrahiert", color='#888888')
            self.log_message(f"   🤖 KI analysiert...", color='#ffaa00')
            
            # Extract data with AI
            data = self.extract_invoice_data(text, filename)
            
            if data:
                lieferant = data.get('lieferant', 'N/A')
                betrag = data.get('betrag_brutto', 'N/A')
                self.log_message(f"   ✅ {lieferant} → {betrag}€\n", color='#00ff88')
                self.results.append(data)
            else:
                self.log_message(f"   ❌ Verarbeitung fehlgeschlagen\n", color='#ff4444')
            
            self.progress['value'] = i
            self.root.update()
        
        # Export
        self.finalize_processing(total)
    
    def finalize_processing(self, total):
        if self.results:
            df = pd.DataFrame(self.results)
            output = "rechnungen_export.xlsx"
            df.to_excel(output, index=False)
            
            total_amount = df['betrag_brutto'].sum() if 'betrag_brutto' in df.columns else 0
            avg_amount = df['betrag_brutto'].mean() if 'betrag_brutto' in df.columns else 0
            
            self.log_message(f"\n{'='*70}", color='#00ff88')
            self.log_message(f"✅ VERARBEITUNG ABGESCHLOSSEN!", color='#00ff88')
            self.log_message(f"{'='*70}\n", color='#00ff88')
            
            self.log_message(f"📊 Statistik:", color='#00d4ff')
            self.log_message(f"   • Erfolgreich: {len(self.results)}/{total}", color='#888888')
            self.log_message(f"   • Gesamt: {total_amount:.2f}€", color='#888888')
            self.log_message(f"   • Durchschnitt: {avg_amount:.2f}€", color='#888888')
            self.log_message(f"\n💾 Export: {output}", color='#00d4ff')
            
            self.status_label.config(text="✅ Verarbeitung abgeschlossen!", fg='#00ff88')
            
            messagebox.showinfo(
                "✅ Fertig!",
                f"Verarbeitung abgeschlossen!\n\n"
                f"📊 Erfolgreich: {len(self.results)}/{total}\n"
                f"💰 Gesamt: {total_amount:.2f}€\n"
                f"📈 Durchschnitt: {avg_amount:.2f}€\n\n"
                f"💾 Export: {output}"
            )
        else:
            self.log_message(f"\n❌ KEINE RECHNUNGEN VERARBEITET", color='#ff4444')
            self.status_label.config(text="❌ Fehler bei Verarbeitung", fg='#ff4444')
            
            messagebox.showerror(
                "❌ Fehler",
                "Keine Rechnungen erfolgreich verarbeitet.\n\n"
                "Bitte prüfe:\n"
                "• Sind die PDFs lesbar?\n"
                "• Ist der API-Key gültig?\n"
                "• Ist Guthaben vorhanden?"
            )
        
        self.process_btn.config(state='normal', text="🚀 JETZT VERARBEITEN")
        self.processing = False

def main():
    root = tk.Tk()
    app = InvoiceProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
