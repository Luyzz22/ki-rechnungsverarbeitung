#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung - Export Module v3.0
Multi-format export (Excel, CSV, JSON)
"""

import os
import json
import logging
import subprocess
import platform
from pathlib import Path
from typing import List, Dict
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


class ExportManager:
    """Manages data export in multiple formats"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = Path(self.config.get('output_dir', 'output'))
        self.output_dir.mkdir(exist_ok=True)
        
    def export_all(self, results: List[Dict], formats: List[str] = None) -> Dict[str, str]:
        """
        Export results in multiple formats
        Returns: dict with format -> filepath mapping
        """
        if not results:
            logger.warning("No results to export")
            return {}
        
        formats = formats or self.config.get('formats', ['xlsx'])
        exported_files = {}
        
        # Create DataFrame
        df = self._prepare_dataframe(results)
        
        # Export each format
        for fmt in formats:
            try:
                if fmt == 'xlsx':
                    filepath = self.export_excel(df)
                elif fmt == 'csv':
                    filepath = self.export_csv(df)
                elif fmt == 'json':
                    filepath = self.export_json(results)
                else:
                    logger.warning(f"Unknown format: {fmt}")
                    continue
                
                exported_files[fmt] = filepath
                logger.info(f"Exported {fmt.upper()}: {filepath}")
                
            except Exception as e:
                logger.error(f"Export failed for {fmt}: {e}")
        
        return exported_files
    
    def _prepare_dataframe(self, results: List[Dict]) -> pd.DataFrame:
        """Prepare DataFrame with proper column order"""
        df = pd.DataFrame(results)
        
        # Define preferred column order
        preferred_order = [
            'dateiname',
            'rechnungsnummer',
            'datum',
            'faelligkeitsdatum',
            'lieferant',
            'lieferant_adresse',
            'kundennummer',
            'betrag_brutto',
            'betrag_netto',
            'mwst_betrag',
            'mwst_satz',
            'waehrung',
            'iban',
            'bic',
            'steuernummer',
            'ust_idnr',
            'zahlungsbedingungen',
            'verarbeitet_am',
            'text_laenge',
            'model'
        ]
        
        # Reorder columns (only those that exist)
        existing_cols = [col for col in preferred_order if col in df.columns]
        remaining_cols = [col for col in df.columns if col not in existing_cols]
        
        df = df[existing_cols + remaining_cols]
        
        return df
    
    def export_excel(self, df: pd.DataFrame) -> str:
        """Export to Excel with formatting"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = self.config.get('filename_prefix', 'rechnungen')
        filename = f"{prefix}_export_{timestamp}.xlsx"
        filepath = self.output_dir / filename
        
        # Create Excel writer with styling
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Rechnungen', index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Rechnungen']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Freeze header row
            worksheet.freeze_panes = 'A2'
        
        logger.info(f"Excel export successful: {filepath}")
        return str(filepath)
    
    def export_csv(self, df: pd.DataFrame) -> str:
        """Export to CSV"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = self.config.get('filename_prefix', 'rechnungen')
        filename = f"{prefix}_export_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig', sep=';')
        
        logger.info(f"CSV export successful: {filepath}")
        return str(filepath)
    
    def export_json(self, results: List[Dict]) -> str:
        """Export to JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = self.config.get('filename_prefix', 'rechnungen')
        filename = f"{prefix}_export_{timestamp}.json"
        filepath = self.output_dir / filename
        
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_invoices': len(results),
                'version': '3.0'
            },
            'invoices': results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON export successful: {filepath}")
        return str(filepath)
    
    def open_file(self, filepath: str):
        """Open file with default application"""
        try:
            system = platform.system()
            
            if system == 'Darwin':  # macOS
                subprocess.run(['open', filepath], check=False)
            elif system == 'Windows':
                os.startfile(filepath)
            elif system == 'Linux':
                subprocess.run(['xdg-open', filepath], check=False)
            
            logger.info(f"Opened file: {filepath}")
            
        except Exception as e:
            logger.error(f"Could not open file {filepath}: {e}")


class ReportGenerator:
    """Generates summary reports"""
    
    @staticmethod
    def generate_summary_report(results: List[Dict], stats: Dict) -> str:
        """Generate text summary report"""
        
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("  RECHNUNGSVERARBEITUNG - ZUSAMMENFASSUNG")
        report_lines.append("=" * 70)
        report_lines.append("")
        
        # Statistics
        report_lines.append("📊 STATISTIKEN:")
        report_lines.append(f"  • Verarbeitete Rechnungen: {stats.get('total_invoices', 0)}")
        report_lines.append(f"  • Gesamtbetrag (Brutto): {stats.get('total_brutto', 0):.2f} {stats.get('currency', 'EUR')}")
        report_lines.append(f"  • Gesamtbetrag (Netto): {stats.get('total_netto', 0):.2f} {stats.get('currency', 'EUR')}")
        report_lines.append(f"  • MwSt. Gesamt: {stats.get('total_mwst', 0):.2f} {stats.get('currency', 'EUR')}")
        report_lines.append(f"  • Durchschnitt (Brutto): {stats.get('average_brutto', 0):.2f} {stats.get('currency', 'EUR')}")
        report_lines.append("")
        
        # Top invoices
        if results:
            sorted_results = sorted(
                [r for r in results if r.get('betrag_brutto')],
                key=lambda x: x.get('betrag_brutto', 0),
                reverse=True
            )
            
            report_lines.append("💰 TOP 5 HÖCHSTE RECHNUNGEN:")
            for i, invoice in enumerate(sorted_results[:5], 1):
                lieferant = invoice.get('lieferant', 'N/A')
                betrag = invoice.get('betrag_brutto', 0)
                datum = invoice.get('datum', 'N/A')
                report_lines.append(f"  {i}. {lieferant:<30} {betrag:>10.2f}€  ({datum})")
            report_lines.append("")
        
        # Validation summary
        validation_failed = [r for r in results if not r.get('validation', {}).get('valid', True)]
        if validation_failed:
            report_lines.append(f"⚠️  VALIDIERUNGSWARNUNGEN: {len(validation_failed)}")
            for invoice in validation_failed[:5]:
                filename = invoice.get('dateiname', 'unknown')
                errors = invoice.get('validation', {}).get('errors', [])
                report_lines.append(f"  • {filename}: {errors[0] if errors else 'Unknown error'}")
            report_lines.append("")
        
        # Footer
        report_lines.append("=" * 70)
        report_lines.append(f"Erstellt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 70)
        
        return "\n".join(report_lines)
    
    @staticmethod
    def save_report(report: str, output_dir: Path = Path('output')):
        """Save report to text file"""
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{timestamp}.txt"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Report saved: {filepath}")
        return str(filepath)


def export_results(results: List[Dict], config: Dict = None) -> Dict[str, str]:
    """
    Convenience function to export results
    Returns: dict with format -> filepath mapping
    """
    manager = ExportManager(config)
    formats = config.get('formats', ['xlsx']) if config else ['xlsx']
    return manager.export_all(results, formats)
