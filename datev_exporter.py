#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung - DATEV Export Module v3.1
Export invoices to DATEV ASCII format
"""

import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import csv

logger = logging.getLogger(__name__)


class DATEVExporter:
    """
    Export invoices to DATEV ASCII format
    
    Supports:
    - DATEV-Format KNE (Kontennachweis)
    - Version 7.0
    """
    
    # DATEV Format specifications
    DATEV_VERSION = "7.00"
    FORMAT_NAME = "Buchungsstapel"
    FORMAT_VERSION = 8
    
    def __init__(self, config: Dict = None):
        """
        Initialize DATEV Exporter
        
        Args:
            config: DATEV configuration (client number, consultant number, etc.)
        """
        self.config = config or {}
        
        # Required configuration
        self.client_number = self.config.get('client_number', '0')
        self.consultant_number = self.config.get('consultant_number', '0')
        self.fiscal_year_start = self.config.get('fiscal_year_start', '0101')
        self.account_length = self.config.get('account_length', 4)
        
        # Account mapping (customizable)
        self.account_mapping = self.config.get('account_mapping', {
            'default_revenue': '8400',      # Erlöse 19% USt
            'default_expense': '4400',      # Wareneingang 19% Vorsteuer
            'default_bank': '1200',         # Bank
            'default_debitor': '10000',     # Debitorenkonto
            'default_kreditor': '70000'     # Kreditorenkonto
        })
    
    def export_to_datev(self, results: List[Dict], output_path: str = None) -> str:
        """
        Export invoice data to DATEV ASCII format
        
        Args:
            results: List of processed invoice data
            output_path: Output file path (optional)
            
        Returns:
            Path to created DATEV file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/DATEV_Export_{timestamp}.csv"
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_file, 'w', encoding='iso-8859-1', newline='') as f:
                writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
                
                # Write header
                self._write_header(writer)
                
                # Write invoice records
                for result in results:
                    self._write_invoice_record(writer, result)
            
            logger.info(f"DATEV export created: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"DATEV export failed: {e}")
            raise
    
    def _write_header(self, writer):
        """Write DATEV file header"""
        
        # Header Line 1: Format description
        header1 = [
            "EXTF",                          # Format name
            self.DATEV_VERSION,              # DATEV version
            self.FORMAT_VERSION,             # Format category
            "Buchungsstapel",                # Format name
            "2",                             # Format type (2 = Buchungsstapel)
            "",                              # Reserved
            "",                              # Date from (empty = all)
            "",                              # Date to (empty = all)
            "",                              # Designation
            "",                              # Dictation abbreviation
            self.consultant_number,          # Consultant number
            self.client_number,              # Client number
            self.fiscal_year_start,          # Fiscal year start (MMDD)
            str(self.account_length),        # Account length
            "",                              # Reserved
            "",                              # Reserved
            "",                              # Reserved
            "",                              # Reserved
            "",                              # Reserved
            "",                              # Reserved
            "",                              # Reserved
        ]
        writer.writerow(header1)
        
        # Header Line 2: Column names
        header2 = [
            "Umsatz (ohne Soll/Haben-Kz)",   # Amount
            "Soll/Haben-Kennzeichen",        # Debit/Credit indicator
            "WKZ Umsatz",                    # Currency
            "Kurs",                          # Exchange rate
            "Basis-Umsatz",                  # Base amount
            "WKZ Basis-Umsatz",              # Base currency
            "Konto",                         # Account
            "Gegenkonto (ohne BU-Schlüssel)", # Contra account
            "BU-Schlüssel",                  # Posting key
            "Belegdatum",                    # Document date
            "Belegfeld 1",                   # Document field 1
            "Belegfeld 2",                   # Document field 2
            "Skonto",                        # Discount
            "Buchungstext",                  # Posting text
            "Postensperre",                  # Item lock
            "Diverse Adressnummer",          # Address number
            "Geschäftspartnerbank",          # Business partner bank
            "Sachverhalt",                   # Matter
            "Zinssperre",                    # Interest lock
            "Beleglink",                     # Document link
            "Beleginfo - Art 1",             # Document info type 1
            "Beleginfo - Inhalt 1",          # Document info content 1
            "Festschreibung",                # Posting lock
            "Leistungsdatum",                # Service date
            "Datum Zuord. Steuerperiode",    # Tax period date
        ]
        writer.writerow(header2)
    
    def _write_invoice_record(self, writer, invoice_data: Dict):
        """Write single invoice record"""
        
        # Extract data
        betrag_brutto = invoice_data.get('betrag_brutto', 0)
        betrag_netto = invoice_data.get('betrag_netto', 0)
        mwst = invoice_data.get('mwst_betrag', 0)
        datum = invoice_data.get('datum', datetime.now().strftime('%Y-%m-%d'))
        rechnungsnr = invoice_data.get('rechnungsnummer', '')
        lieferant = invoice_data.get('lieferant', '')
        
        # Format date (DDMM)
        try:
            date_obj = datetime.strptime(datum, '%Y-%m-%d')
            datev_date = date_obj.strftime('%d%m')
        except:
            datev_date = datetime.now().strftime('%d%m')
        
        # Determine accounts (simplified - should be customized per business)
        # This is for expense invoices (Eingangsrechnungen)
        gegenkonto = self.account_mapping['default_expense']  # Expense account
        konto = self.account_mapping['default_kreditor']       # Creditor account
        
        # Posting key
        # 31 = Eingangsrechnung (incoming invoice)
        bu_schluessel = "31"
        
        # Clean invoice number for DATEV (max 36 chars)
        beleg1 = str(rechnungsnr)[:36] if rechnungsnr else ""
        
        # Posting text (max 60 chars)
        buchungstext = f"ER {lieferant[:50]}"[:60]
        
        # Record
        record = [
            f"{betrag_brutto:.2f}".replace('.', ','),  # Amount (comma as decimal)
            "S",                                        # S = Soll (Debit)
            "EUR",                                      # Currency
            "",                                         # Exchange rate (empty for EUR)
            "",                                         # Base amount
            "",                                         # Base currency
            konto,                                      # Account (Kreditor)
            gegenkonto,                                 # Contra account (Expense)
            bu_schluessel,                              # Posting key
            datev_date,                                 # Document date (DDMM)
            beleg1,                                     # Document field 1 (Invoice number)
            "",                                         # Document field 2
            "",                                         # Discount
            buchungstext,                               # Posting text
            "",                                         # Item lock
            "",                                         # Address number
            "",                                         # Business partner bank
            "",                                         # Matter
            "",                                         # Interest lock
            "",                                         # Document link
            "",                                         # Document info type 1
            "",                                         # Document info content 1
            "",                                         # Posting lock
            datev_date,                                 # Service date
            "",                                         # Tax period date
        ]
        
        writer.writerow(record)
    
    def validate_config(self) -> List[str]:
        """Validate DATEV configuration"""
        errors = []
        
        if not self.client_number or self.client_number == '0':
            errors.append("Client number (Mandantennummer) fehlt")
        
        if not self.consultant_number or self.consultant_number == '0':
            errors.append("Consultant number (Beraternummer) fehlt")
        
        if len(self.fiscal_year_start) != 4:
            errors.append("Fiscal year start muss Format MMDD haben")
        
        return errors


class DATEVAccountMapper:
    """Helper class for account mapping"""
    
    # Common SKR03 accounts (Standardkontenrahmen)
    SKR03_ACCOUNTS = {
        # Revenue accounts
        'revenue_19': '8400',           # Erlöse 19% USt
        'revenue_7': '8300',            # Erlöse 7% USt
        'revenue_0': '8100',            # Erlöse 0% USt (steuerfrei)
        
        # Expense accounts
        'expense_19': '4400',           # Wareneingang 19% Vorsteuer
        'expense_7': '4300',            # Wareneingang 7% Vorsteuer
        'expense_0': '4200',            # Wareneingang steuerfrei
        
        # Asset accounts
        'bank': '1200',                 # Bank
        'cash': '1000',                 # Kasse
        'debitor': '10000',             # Debitorenkonto (Standard)
        'kreditor': '70000',            # Kreditorenkonto (Standard)
        
        # Tax accounts
        'vat_19': '1776',               # Umsatzsteuer 19%
        'vat_7': '1771',                # Umsatzsteuer 7%
        'input_vat_19': '1576',         # Vorsteuer 19%
        'input_vat_7': '1571',          # Vorsteuer 7%
    }
    
    # SKR04 accounts (alternative)
    SKR04_ACCOUNTS = {
        'revenue_19': '4400',
        'revenue_7': '4300',
        'expense_19': '5400',
        'expense_7': '5300',
        'bank': '1800',
        'debitor': '10000',
        'kreditor': '70000',
    }
    
    @staticmethod
    def get_account_by_tax_rate(amount: float, tax_rate: int, is_revenue: bool = False, 
                                 account_plan: str = 'SKR03') -> str:
        """
        Get appropriate account based on tax rate
        
        Args:
            amount: Transaction amount
            tax_rate: Tax rate (0, 7, 19)
            is_revenue: True for revenue, False for expenses
            account_plan: 'SKR03' or 'SKR04'
            
        Returns:
            Account number
        """
        accounts = DATEVAccountMapper.SKR03_ACCOUNTS if account_plan == 'SKR03' else DATEVAccountMapper.SKR04_ACCOUNTS
        
        category = 'revenue' if is_revenue else 'expense'
        
        if tax_rate == 19:
            return accounts[f'{category}_19']
        elif tax_rate == 7:
            return accounts[f'{category}_7']
        else:
            return accounts[f'{category}_0']


def export_to_datev(results: List[Dict], config: Dict = None, output_path: str = None) -> str:
    """
    Convenience function to export to DATEV
    
    Usage:
        from datev_exporter import export_to_datev
        
        config = {
            'client_number': '12345',
            'consultant_number': '1001',
            'fiscal_year_start': '0101'
        }
        
        file_path = export_to_datev(results, config)
    
    Args:
        results: List of processed invoices
        config: DATEV configuration
        output_path: Output file path (optional)
        
    Returns:
        Path to DATEV file
    """
    exporter = DATEVExporter(config)
    
    # Validate configuration
    errors = exporter.validate_config()
    if errors:
        logger.warning(f"DATEV config warnings: {errors}")
    
    return exporter.export_to_datev(results, output_path)


# Configuration template
DATEV_CONFIG_TEMPLATE = """
═══════════════════════════════════════════════════════════════
  DATEV-EXPORT KONFIGURATION
═══════════════════════════════════════════════════════════════

In config.yaml hinzufügen:
───────────────────────────

datev:
  enabled: true
  client_number: "12345"           # Mandantennummer
  consultant_number: "1001"        # Beraternummer
  fiscal_year_start: "0101"        # Wirtschaftsjahr-Beginn (MMDD)
  account_length: 4                # Kontenlänge (4 oder 5)
  
  # Kontenplan (SKR03 oder SKR04)
  account_plan: "SKR03"
  
  # Konten-Zuordnung (optional - kann angepasst werden)
  account_mapping:
    default_revenue: "8400"        # Erlöse 19% USt
    default_expense: "4400"        # Wareneingang 19% Vorsteuer
    default_bank: "1200"           # Bank
    default_debitor: "10000"       # Debitorenkonto
    default_kreditor: "70000"      # Kreditorenkonto

═══════════════════════════════════════════════════════════════
  WICHTIGE HINWEISE
═══════════════════════════════════════════════════════════════

⚠️  DATEV-Format ist komplex!
    Dieses Modul erstellt einen EINFACHEN Export.
    Für produktiven Einsatz sollte die Konto-Zuordnung
    mit Ihrem Steuerberater abgestimmt werden!

✅  Was funktioniert:
    • Basis-Export von Eingangsrechnungen
    • Standard-Kontenrahmen (SKR03/SKR04)
    • DATEV ASCII Format 7.0

⚠️  Was NICHT automatisch funktioniert:
    • Komplexe Buchungslogik
    • Automatische Splittbuchungen
    • Anlagenbuchhaltung
    • Lohnbuchhaltung
    
📚  Empfehlung:
    Export von Steuerberater prüfen lassen bevor er
    in DATEV importiert wird!

═══════════════════════════════════════════════════════════════
  NUTZUNG
═══════════════════════════════════════════════════════════════

Automatisch aktivieren:
─────────────────────────
features:
  datev_export: true

Oder manuell:
─────────────────────────
from datev_exporter import export_to_datev

config = {
    'client_number': '12345',
    'consultant_number': '1001'
}

datev_file = export_to_datev(results, config)

═══════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(DATEV_CONFIG_TEMPLATE)
