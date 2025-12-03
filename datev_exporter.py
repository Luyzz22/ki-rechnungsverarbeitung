#!/usr/bin/env python3
"""
DATEV ASCII Export Module
Exports invoice data to DATEV format
"""

from pathlib import Path
from typing import List, Dict
from datetime import datetime
from auto_accounting import suggest_account


def export_to_datev(results: List[Dict], config: Dict) -> str:
    """
    Export invoice data to DATEV ASCII format
    
    Args:
        results: List of processed invoice data
        config: DATEV configuration from config.yaml
    
    Returns:
        Path to exported DATEV file
    """
    if not results:
        raise ValueError("No results to export")
    
    # Output directory
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"datev_export_{timestamp}.csv"
    
    # DATEV configuration with defaults
    datev_config = {
        'sachkonto': config.get('sachkonto', '4900'),
        'gegenkonto': config.get('gegenkonto', '1200'),
        'kostenstelle_1': config.get('kostenstelle_1', ''),
        'kostenstelle_2': config.get('kostenstelle_2', ''),
        'waehrung': config.get('waehrung', 'EUR'),
    }
    
    # Write DATEV format
    with open(output_file, 'w', encoding='cp1252') as f:
        # Write header
        header = _generate_header(datev_config)
        f.write(header)
        
        # Write data rows
        for result in results:
            row = _format_datev_row(result, datev_config)
            f.write(row)
    
    return str(output_file)


def _generate_header(config: Dict) -> str:
    """Generate DATEV file header"""
    
    # DATEV ASCII Format header
    header_lines = [
        "EXTF",
        "300",
        "21",
        "Buchungsstapel",
        "5",
        "",
        "",
        "",
        "",
        "",
        "",
        "EUR",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        ""
    ]
    
    header = ";".join(header_lines) + "\n"
    
    # Column headers
    columns = [
        "Umsatz (ohne Soll/Haben-Kz)",
        "Soll/Haben-Kennzeichen",
        "WKZ Umsatz",
        "Kurs",
        "Basis-Umsatz",
        "WKZ Basis-Umsatz",
        "Konto",
        "Gegenkonto (ohne BU-Schlüssel)",
        "BU-Schlüssel",
        "Belegdatum",
        "Belegfeld 1",
        "Belegfeld 2",
        "Skonto",
        "Buchungstext",
        "Postensperre",
        "Diverse Adressnummer",
        "Geschäftspartnerbank",
        "Sachverhalt",
        "Zinssperre",
        "Beleglink",
        "Beleginfo - Art 1",
        "Beleginfo - Inhalt 1",
        "Beleginfo - Art 2",
        "Beleginfo - Inhalt 2",
        "Beleginfo - Art 3",
        "Beleginfo - Inhalt 3",
        "Beleginfo - Art 4",
        "Beleginfo - Inhalt 4",
        "Beleginfo - Art 5",
        "Beleginfo - Inhalt 5",
        "Beleginfo - Art 6",
        "Beleginfo - Inhalt 6",
        "Beleginfo - Art 7",
        "Beleginfo - Inhalt 7",
        "Beleginfo - Art 8",
        "Beleginfo - Inhalt 8",
        "KOST1 - Kostenstelle",
        "KOST2 - Kostenstelle",
        "KOST-Menge",
        "EU-Land u. UStID",
        "EU-Steuersatz",
        "Abw. Versteuerungsart",
        "Sachverhalt L+L",
        "Funktionsergänzung L+L",
        "BU 49 Hauptfunktionstyp",
        "BU 49 Hauptfunktionsnummer",
        "BU 49 Funktionsergänzung",
        "Zusatzinformation - Art 1",
        "Zusatzinformation - Inhalt 1"
    ]
    
    header += ";".join(columns) + "\n"
    
    return header


def _format_datev_row(result: Dict, config: Dict) -> str:
    """Format a single invoice as DATEV row"""
    
    def safe_get(key, default=''):
        """Safely get value from result, return default if None or empty"""
        value = result.get(key)
        if value is None or value == '':
            return default
        return str(value)
    
    def safe_float(key, default=0.0):
        """Safely get float value, return default if None"""
        value = result.get(key)
        if value is None or value == '':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_date(key, default=''):
        """Safely format date, return default if None"""
        value = result.get(key)
        if value is None or value == '':
            return default
        try:
            if isinstance(value, str) and len(value) >= 10:
                parts = value.split('-')
                if len(parts) == 3:
                    return f"{parts[2]}{parts[1]}"
            return default
        except:
            return default
    
    betrag_brutto = safe_float('betrag_brutto', 0.0)
    datum = safe_date('datum', datetime.now().strftime('%d%m'))
    rechnungsnummer = safe_get('rechnungsnummer', 'KEINE')
    lieferant = safe_get('lieferant', 'Unbekannt')
    verwendungszweck = safe_get('verwendungszweck', '')
    
    # Auto-Kontierung: KI schlägt Konto vor
    suggestion = suggest_account(result)
    sachkonto = suggestion['suggested']['account']
    
    row_data = [
        f"{betrag_brutto:.2f}".replace('.', ','),
        "S",
        config.get('waehrung', 'EUR'),
        "",
        "",
        "",
        sachkonto,  # Auto-Kontierung
        config.get('gegenkonto', '1200'),
        "",
        datum,
        rechnungsnummer[:36] if rechnungsnummer else "",
        "",
        "",
        (lieferant[:60] if lieferant else "")[:60],
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        config.get('kostenstelle_1', ''),
        config.get('kostenstelle_2', ''),
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        (verwendungszweck[:210] if verwendungszweck else "")[:210]
    ]
    
    return ";".join(row_data) + "\n"


if __name__ == "__main__":
    test_data = [{
        'rechnungsnummer': 'RE-001',
        'datum': '2025-10-20',
        'lieferant': 'Test Lieferant GmbH',
        'betrag_brutto': 119.00,
        'betrag_netto': 100.00,
        'mwst_betrag': 19.00,
        'verwendungszweck': 'Test Rechnung'
    }]
    
    test_config = {
        'sachkonto': '4900',
        'gegenkonto': '1200',
        'waehrung': 'EUR'
    }
    
    try:
        output_file = export_to_datev(test_data, test_config)
        print(f"✅ DATEV Export erfolgreich: {output_file}")
    except Exception as e:
        print(f"❌ Fehler: {e}")
