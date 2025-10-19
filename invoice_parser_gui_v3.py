#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung - GUI Version v3.0
Mit Parallel Processing, Validation & Multi-Export
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
from datetime import datetime
import subprocess

from invoice_core import Config, InvoiceProcessor, get_pdf_files, calculate_statistics
from export import ExportManager


class InvoiceGUI:
    """Modern GUI for invoice processing"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 KI-Rechnungsverarbeitung v3.0")
        self.root.geometry("900x700")
        
        # Config
        self.config = Config()
        self.processor = InvoiceProcessor(self.config)
        
        # Variables
        self.processing = False
        self.results = []
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        
        # Header
        header = tk.Frame(self.root, bg="#00d4ff", height=80)
        header.pack(fill=tk.X)
        
        title = tk.Label(
            header,
            text="🤖 KI-Rechnungsverarbeitung v3.0",
            font=("Arial", 20, "bold"),
            bg="#00d4ff",
            fg="white"
        )
        title.pack(pady=20)
        
        # Main container
        main = ttk.Frame(self.root, padding="20")
        main.pack(fill=tk.BOTH, expand=True)
        
        # Folder selection
        folder_frame = ttk.LabelFrame(main, text="📁 PDF-Ordner", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.folder_var = tk.StringVar(value="test_rechnungen")
        ttk.Entry(folder_frame, textvariable=self.folder_var, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(folder_frame, text="Durchsuchen...", command=self.browse_folder).pack(side=tk.LEFT)
        
        # Options
        options_frame = ttk.LabelFrame(main, text="⚙️ Optionen", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Parallel processing
        self.parallel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="⚡ Parallel Processing (4x schneller)",
            variable=self.parallel_var
        ).pack(anchor=tk.W)
        
        # Validation
        self.validation_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="✅ Validation aktivieren",
            variable=self.validation_var
        ).pack(anchor=tk.W)
        
        # Export formats
        export_frame = ttk.Frame(options_frame)
        export_frame.pack(anchor=tk.W, pady=(5, 0))
        
        ttk.Label(export_frame, text="💾 Export-Formate:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.xlsx_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(export_frame, text="XLSX", variable=self.xlsx_var).pack(side=tk.LEFT)
        
        self.csv_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(export_frame, text="CSV", variable=self.csv_var).pack(side=tk.LEFT)
        
        self.json_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(export_frame, text="JSON", variable=self.json_var).pack(side=tk.LEFT)
        
        # DATEV
        self.datev_var = tk.BooleanVar(value=self.config.get('features.datev_export', False))
        ttk.Checkbutton(
            options_frame,
            text="📤 DATEV-Export erstellen",
            variable=self.datev_var
        ).pack(anchor=tk.W)
        
        # Dashboard
        self.dashboard_var = tk.BooleanVar(value=self.config.get('features.dashboard', False))
        ttk.Checkbutton(
            options_frame,
            text="📊 Dashboard generieren",
            variable=self.dashboard_var
        ).pack(anchor=tk.W)
        
        # Progress
        progress_frame = ttk.LabelFrame(main, text="📊 Fortschritt", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            progress_frame,
            height=15,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#00d4ff"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Statistics
        stats_frame = ttk.LabelFrame(main, text="📈 Statistiken", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_label = ttk.Label(
            stats_frame,
            text="Noch keine Verarbeitung durchgeführt",
            font=("Arial", 10)
        )
        self.stats_label.pack()
        
        # Buttons
        button_frame = ttk.Frame(main)
        button_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(
            button_frame,
            text="🚀 Verarbeitung starten",
            command=self.start_processing,
            style="Accent.TButton"
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame,
            text="📂 Output-Ordner öffnen",
            command=lambda: subprocess.run(['open', 'output'])
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame,
            text="❌ Beenden",
            command=self.root.quit
        ).pack(side=tk.RIGHT)
        
        # Style
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 11, "bold"))
    
    def browse_folder(self):
        """Browse for PDF folder"""
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def start_processing(self):
        """Start processing in background thread"""
        if self.processing:
            messagebox.showwarning("Warnung", "Verarbeitung läuft bereits!")
            return
        
        # Start in thread
        thread = threading.Thread(target=self.process_invoices)
        thread.daemon = True
        thread.start()
    
    def process_invoices(self):
        """Process all PDFs"""
        self.processing = True
        self.start_btn.config(state='disabled')
        self.progress.start()
        self.log_text.delete(1.0, tk.END)
        self.results = []
        
        try:
            # Get PDFs
            folder = Path(self.folder_var.get())
            if not folder.exists():
                self.log(f"❌ Ordner nicht gefunden: {folder}")
                return
            
            pdfs = get_pdf_files(str(folder))
            if not pdfs:
                self.log(f"❌ Keine PDFs gefunden in: {folder}")
                return
            
            self.log(f"📄 Gefunden: {len(pdfs)} PDFs")
            self.log("")
            
            # Process
            if self.parallel_var.get():
                self.log("⚡ Parallel-Modus aktiviert (8 Threads)")
                from concurrent.futures import ThreadPoolExecutor
                
                with ThreadPoolExecutor(max_workers=8) as executor:
                    futures = {executor.submit(self.processor.process_invoice, pdf): pdf for pdf in pdfs}
                    
                    for future in futures:
                        pdf = futures[future]
                        try:
                            data = future.result()
                            if data:
                                self.results.append(data)
                                self.log(f"✅ {pdf.name}: {data.get('betrag_brutto', 0):.2f}€")
                            else:
                                self.log(f"❌ {pdf.name}: Fehler")
                        except Exception as e:
                            self.log(f"❌ {pdf.name}: {e}")
            else:
                self.log("📝 Sequentieller Modus")
                for pdf in pdfs:
                    try:
                        data = self.processor.process_invoice(pdf)
                        if data:
                            self.results.append(data)
                            self.log(f"✅ {pdf.name}: {data.get('betrag_brutto', 0):.2f}€")
                        else:
                            self.log(f"❌ {pdf.name}: Fehler")
                    except Exception as e:
                        self.log(f"❌ {pdf.name}: {e}")
            
            # Export
            if self.results:
                self.log("")
                self.log("💾 Exportiere Daten...")
                
                formats = []
                if self.xlsx_var.get():
                    formats.append('xlsx')
                if self.csv_var.get():
                    formats.append('csv')
                if self.json_var.get():
                    formats.append('json')
                
                manager = ExportManager()
                exported = manager.export_all(self.results, formats)
                
                for fmt, path in exported.items():
                    self.log(f"   ✅ {fmt.upper()}: {path}")
                
                # DATEV
                if self.datev_var.get():
                    self.log("")
                    self.log("📤 Erstelle DATEV-Export...")
                    try:
                        from datev_exporter import export_to_datev
                        datev_file = export_to_datev(self.results, self.config.get('datev', {}))
                        self.log(f"   ✅ DATEV: {datev_file}")
                    except Exception as e:
                        self.log(f"   ❌ DATEV-Fehler: {e}")
                
                # Dashboard
                if self.dashboard_var.get():
                    self.log("")
                    self.log("📊 Generiere Dashboard...")
                    try:
                        from dashboard import generate_dashboard
                        stats = calculate_statistics(self.results)
                        chart_file = generate_dashboard(self.results, stats)
                        self.log(f"   ✅ DASHBOARD: {chart_file}")
                        subprocess.run(['open', chart_file], check=False)
                    except Exception as e:
                        self.log(f"   ❌ Dashboard-Fehler: {e}")
                
                # Statistics
                stats = calculate_statistics(self.results)
                self.log("")
                self.log("📊 STATISTIKEN:")
                self.log(f"   Erfolgreich: {len(self.results)}/{len(pdfs)}")
                self.log(f"   Gesamt (Brutto): {stats['total_brutto']:.2f}€")
                self.log(f"   Gesamt (Netto): {stats['total_netto']:.2f}€")
                self.log(f"   MwSt. Total: {stats['total_mwst']:.2f}€")
                
                self.stats_label.config(
                    text=f"✅ {len(self.results)}/{len(pdfs)} PDFs | "
                         f"Gesamt: {stats['total_brutto']:.2f}€ | "
                         f"Durchschnitt: {stats['average_brutto']:.2f}€"
                )
                
                # Open Excel
                if 'xlsx' in exported:
                    subprocess.run(['open', exported['xlsx']], check=False)
                
                self.log("")
                self.log("✨ FERTIG!")
                
                messagebox.showinfo(
                    "Erfolg",
                    f"✅ {len(self.results)}/{len(pdfs)} Rechnungen verarbeitet!\n\n"
                    f"Gesamt: {stats['total_brutto']:.2f}€"
                )
            else:
                self.log("")
                self.log("❌ Keine Daten extrahiert")
                messagebox.showerror("Fehler", "Keine Rechnungen konnten verarbeitet werden!")
                
        except Exception as e:
            self.log(f"\n❌ FEHLER: {e}")
            messagebox.showerror("Fehler", str(e))
        
        finally:
            self.processing = False
            self.start_btn.config(state='normal')
            self.progress.stop()


def main():
    root = tk.Tk()
    app = InvoiceGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
