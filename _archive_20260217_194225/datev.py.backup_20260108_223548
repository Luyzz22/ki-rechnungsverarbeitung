#!/usr/bin/env python3
"""
SBS Deutschland – DATEV Enterprise Integration Module v1.0

Supports:
- DATEV XML-Schnittstelle online (für Unternehmen Online / Rechnungsdatenservice 1.0)
- DATEV CSV/EXTF Format (für Rechnungswesen / Buchungsdatenservice)
- SKR03 / SKR04 Kontenrahmen
- GoBD-konforme Belegverknüpfung
- Automatische Kontenzuordnung

Author: SBS Deutschland GmbH & Co. KG
"""

import csv
import io
import json
import logging
import os
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from xml.etree import ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger(__name__)

# =============================================================================
# KONSTANTEN & KONFIGURATION
# =============================================================================

class Kontenrahmen(str, Enum):
    SKR03 = "SKR03"
    SKR04 = "SKR04"

class BelegTyp(str, Enum):
    EINGANGSRECHNUNG = "ER"  # Accounts Payable
    AUSGANGSRECHNUNG = "AR"  # Accounts Receivable
    GUTSCHRIFT = "GS"
    KASSE = "KA"

# DATEV Steuerschlüssel
STEUERSCHLUESSEL = {
    0: {"code": "0", "beschreibung": "Keine Steuer", "satz": 0},
    7: {"code": "2", "beschreibung": "7% Vorsteuer", "satz": 7},
    19: {"code": "9", "beschreibung": "19% Vorsteuer", "satz": 19},
    # Umsatzsteuer (für Ausgangsrechnungen)
    107: {"code": "1", "beschreibung": "7% Umsatzsteuer", "satz": 7},
    119: {"code": "3", "beschreibung": "19% Umsatzsteuer", "satz": 19},
}

# Standard-Konten SKR03
KONTEN_SKR03 = {
    # Aufwandskonten (Soll)
    "wareneingang": 3400,
    "fremdleistungen": 3100,
    "miete": 4210,
    "telefon": 4920,
    "bürobedarf": 4930,
    "reisekosten": 4660,
    "werbung": 4600,
    "versicherung": 4360,
    "kfz": 4500,
    "sonstiger_aufwand": 4900,
    # Verbindlichkeiten (Haben)
    "verbindlichkeiten": 1600,
    "kreditoren_sammel": 70000,  # Kreditoren ab 70000
    # Bank/Kasse
    "bank": 1200,
    "kasse": 1000,
    # Vorsteuer
    "vorsteuer_19": 1576,
    "vorsteuer_7": 1571,
}

# Standard-Konten SKR04
KONTEN_SKR04 = {
    "wareneingang": 5400,
    "fremdleistungen": 5900,
    "miete": 6310,
    "telefon": 6805,
    "bürobedarf": 6815,
    "reisekosten": 6650,
    "werbung": 6600,
    "versicherung": 6400,
    "kfz": 6500,
    "sonstiger_aufwand": 6800,
    "verbindlichkeiten": 3300,
    "kreditoren_sammel": 70000,
    "bank": 1800,
    "kasse": 1600,
    "vorsteuer_19": 1406,
    "vorsteuer_7": 1401,
}


@dataclass
class DatevBuchung:
    """Einzelne Buchungszeile für DATEV"""
    umsatz: Decimal
    soll_haben: str  # "S" oder "H"
    konto: int
    gegenkonto: int
    belegdatum: date
    belegnummer: str
    buchungstext: str
    steuerschluessel: str = ""
    kostenstelle: str = ""
    kostentraeger: str = ""
    beleglink: str = ""
    waehrung: str = "EUR"
    
    # Zusätzliche DATEV-Felder
    rechnungsnummer: str = ""
    ust_idnr: str = ""
    skonto_betrag: Decimal = Decimal("0")
    skonto_datum: Optional[date] = None


@dataclass 
class DatevExportConfig:
    """Konfiguration für DATEV-Export"""
    berater_nummer: str
    mandanten_nummer: str
    wirtschaftsjahr_beginn: date
    kontenrahmen: Kontenrahmen = Kontenrahmen.SKR03
    sachkonten_laenge: int = 4
    kreditoren_laenge: int = 5
    bezeichnung: str = "SBS Invoice Export"
    
    # Optionale Einstellungen
    festschreibung: bool = False
    kost1_laenge: int = 0
    kost2_laenge: int = 0


# =============================================================================
# DATEV CSV/EXTF EXPORT (für Rechnungswesen)
# =============================================================================

class DatevCsvExporter:
    """
    Exportiert Buchungsdaten im DATEV EXTF-Format (CSV)
    für den Import in DATEV Rechnungswesen
    """
    
    # EXTF Header-Felder (Version 700)
    HEADER_FIELDS = [
        "EXTF", "700", "21", "Buchungsstapel", "7", 
        "", "", "", "", "",  # Berater, Mandant, WJ-Beginn, Sachkontenlänge, Datum von
        "", "", "", "", "",  # Datum bis, Bezeichnung, Diktatkürzel, Buchungstyp, Rechnungslegungszweck
        "", "", "", "", "",  # Festschreibung, WKZ, reserved, reserved, reserved
        "", "", "", "", "",  # reserved x5
        "", ""               # reserved x2
    ]
    
    # Buchungssatz-Felder (Spaltenköpfe)
    BOOKING_FIELDS = [
        "Umsatz (ohne Soll/Haben-Kz)", "Soll/Haben-Kennzeichen", "WKZ Umsatz",
        "Kurs", "Basis-Umsatz", "WKZ Basis-Umsatz", "Konto", "Gegenkonto (ohne BU-Schlüssel)",
        "BU-Schlüssel", "Belegdatum", "Belegfeld 1", "Belegfeld 2",
        "Skonto", "Buchungstext", "Postensperre", "Diverse Adressnummer",
        "Geschäftspartnerbank", "Sachverhalt", "Zinssperre", "Beleglink",
        "Beleginfo - Art 1", "Beleginfo - Inhalt 1", "Beleginfo - Art 2", "Beleginfo - Inhalt 2",
        "Beleginfo - Art 3", "Beleginfo - Inhalt 3", "Beleginfo - Art 4", "Beleginfo - Inhalt 4",
        "Beleginfo - Art 5", "Beleginfo - Inhalt 5", "Beleginfo - Art 6", "Beleginfo - Inhalt 6",
        "Beleginfo - Art 7", "Beleginfo - Inhalt 7", "Beleginfo - Art 8", "Beleginfo - Inhalt 8",
        "KOST1 - Kostenstelle", "KOST2 - Kostenstelle", "Kost-Menge",
        "EU-Land u. UStID", "EU-Steuersatz", "Abw. Versteuerungsart",
        "Sachverhalt L+L", "Funktionsergänzung L+L", "BU 49 Hauptfunktionstyp",
        "BU 49 Hauptfunktionsnummer", "BU 49 Funktionsergänzung",
        "Zusatzinformation - Art 1", "Zusatzinformation - Inhalt 1",
        "Zusatzinformation - Art 2", "Zusatzinformation - Inhalt 2",
        "Zusatzinformation - Art 3", "Zusatzinformation - Inhalt 3",
        "Zusatzinformation - Art 4", "Zusatzinformation - Inhalt 4",
        "Zusatzinformation - Art 5", "Zusatzinformation - Inhalt 5",
        "Zusatzinformation - Art 6", "Zusatzinformation - Inhalt 6",
        "Zusatzinformation - Art 7", "Zusatzinformation - Inhalt 7",
        "Zusatzinformation - Art 8", "Zusatzinformation - Inhalt 8",
        "Zusatzinformation - Art 9", "Zusatzinformation - Inhalt 9",
        "Zusatzinformation - Art 10", "Zusatzinformation - Inhalt 10",
        "Zusatzinformation - Art 11", "Zusatzinformation - Inhalt 11",
        "Zusatzinformation - Art 12", "Zusatzinformation - Inhalt 12",
        "Zusatzinformation - Art 13", "Zusatzinformation - Inhalt 13",
        "Zusatzinformation - Art 14", "Zusatzinformation - Inhalt 14",
        "Zusatzinformation - Art 15", "Zusatzinformation - Inhalt 15",
        "Zusatzinformation - Art 16", "Zusatzinformation - Inhalt 16",
        "Zusatzinformation - Art 17", "Zusatzinformation - Inhalt 17",
        "Zusatzinformation - Art 18", "Zusatzinformation - Inhalt 18",
        "Zusatzinformation - Art 19", "Zusatzinformation - Inhalt 19",
        "Zusatzinformation - Art 20", "Zusatzinformation - Inhalt 20",
        "Stück", "Gewicht", "Zahlweise", "Forderungsart", "Veranlagungsjahr",
        "Zugeordnete Fälligkeit", "Skontotyp", "Auftragsnummer",
        "Buchungstyp", "USt-Schlüssel (Anzahlungen)", "EU-Land (Anzahlungen)",
        "Sachverhalt L+L (Anzahlungen)", "EU-Steuersatz (Anzahlungen)",
        "Erlöskonto (Anzahlungen)", "Herkunft-Kz", "Buchungs GUID",
        "KOST-Datum", "SEPA-Mandatsreferenz", "Skontosperre",
        "Gesellschaftername", "Beteiligtennummer", "Identifikationsnummer",
        "Zeichnernummer", "Postensperre bis", "Bezeichnung SoBil-Sachverhalt",
        "Kennzeichen SoBil-Buchung", "Festschreibung", "Leistungsdatum",
        "Datum Zuord. Steuerperiode", "Fälligkeit", "Generalumkehr (GU)",
        "Steuersatz", "Land"
    ]
    
    def __init__(self, config: DatevExportConfig):
        self.config = config
    
    def _format_decimal(self, value: Decimal) -> str:
        """Formatiert Dezimalzahl für DATEV (Komma als Dezimaltrenner)"""
        return str(value.quantize(Decimal("0.01"), ROUND_HALF_UP)).replace(".", ",")
    
    def _format_date(self, d: date) -> str:
        """Formatiert Datum für DATEV (TTMM)"""
        return d.strftime("%d%m")
    
    def _format_date_full(self, d: date) -> str:
        """Formatiert Datum für DATEV Header (YYYYMMDD)"""
        return d.strftime("%Y%m%d")
    
    def _create_header(self, buchungen: List[DatevBuchung]) -> List[str]:
        """Erstellt den EXTF-Header"""
        if not buchungen:
            raise ValueError("Keine Buchungen vorhanden")
        
        # Ermittle Datums-Range
        dates = [b.belegdatum for b in buchungen]
        datum_von = min(dates)
        datum_bis = max(dates)
        
        now = datetime.now()
        
        header = [
            "EXTF",                                      # Kennzeichen
            "700",                                       # Versionsnummer
            "21",                                        # Formatkategorie
            "Buchungsstapel",                           # Formatname
            "7",                                         # Formatversion
            self._format_date_full(now.date()) + str(now.hour * 10000 + now.minute * 100 + now.second),  # Erzeugt am
            "",                                          # Importiert
            "SBS",                                       # Herkunft
            "",                                          # Exportiert von
            "",                                          # Importiert von
            self.config.berater_nummer,                  # Berater
            self.config.mandanten_nummer,                # Mandant
            self._format_date_full(self.config.wirtschaftsjahr_beginn),  # WJ-Beginn
            str(self.config.sachkonten_laenge),          # Sachkontenlänge
            self._format_date_full(datum_von),           # Datum von
            self._format_date_full(datum_bis),           # Datum bis
            self.config.bezeichnung,                     # Bezeichnung
            "SBS",                                       # Diktatkürzel
            "1",                                         # Buchungstyp (1=Fibu)
            "0",                                         # Rechnungslegungszweck
            "1" if self.config.festschreibung else "0",  # Festschreibung
            "EUR",                                       # WKZ
            "",                                          # reserved
            "",                                          # reserved
            "",                                          # reserved
            "",                                          # Derivatskennzeichen
            "",                                          # reserved
            "",                                          # reserved
            "",                                          # reserved
            "",                                          # Anwendungsinformation
        ]
        
        return header
    
    def _create_booking_row(self, buchung: DatevBuchung) -> List[str]:
        """Erstellt eine Buchungszeile"""
        row = [""] * len(self.BOOKING_FIELDS)
        
        row[0] = self._format_decimal(buchung.umsatz)      # Umsatz
        row[1] = buchung.soll_haben                         # S/H
        row[2] = buchung.waehrung                           # WKZ
        row[3] = ""                                         # Kurs
        row[4] = ""                                         # Basis-Umsatz
        row[5] = ""                                         # WKZ Basis-Umsatz
        row[6] = str(buchung.konto)                         # Konto
        row[7] = str(buchung.gegenkonto)                    # Gegenkonto
        row[8] = buchung.steuerschluessel                   # BU-Schlüssel
        row[9] = self._format_date(buchung.belegdatum)      # Belegdatum
        row[10] = buchung.belegnummer[:36]                  # Belegfeld 1 (max 36)
        row[11] = ""                                        # Belegfeld 2
        row[12] = ""                                        # Skonto
        row[13] = buchung.buchungstext[:60]                 # Buchungstext (max 60)
        row[14] = ""                                        # Postensperre
        row[15] = ""                                        # Diverse Adressnr
        row[16] = ""                                        # GP-Bank
        row[17] = ""                                        # Sachverhalt
        row[18] = ""                                        # Zinssperre
        row[19] = buchung.beleglink[:210] if buchung.beleglink else ""  # Beleglink
        
        # KOST1/KOST2
        row[36] = buchung.kostenstelle[:8] if buchung.kostenstelle else ""
        row[37] = buchung.kostentraeger[:8] if buchung.kostentraeger else ""
        
        # EU USt-ID
        if buchung.ust_idnr:
            row[39] = buchung.ust_idnr[:15]
        
        return row
    
    def export(self, buchungen: List[DatevBuchung]) -> str:
        """
        Exportiert Buchungen als DATEV CSV-String
        """
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quotechar='"', 
                           quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        
        # Header
        header = self._create_header(buchungen)
        writer.writerow(header)
        
        # Spaltenköpfe
        writer.writerow(self.BOOKING_FIELDS)
        
        # Buchungen
        for buchung in buchungen:
            row = self._create_booking_row(buchung)
            writer.writerow(row)
        
        return output.getvalue()
    
    def export_to_file(self, buchungen: List[DatevBuchung], filepath: str) -> str:
        """Exportiert in Datei und gibt Pfad zurück"""
        content = self.export(buchungen)
        
        # DATEV erwartet ANSI/Windows-1252 Encoding
        with open(filepath, 'w', encoding='cp1252', errors='replace') as f:
            f.write(content)
        
        logger.info(f"DATEV CSV Export: {len(buchungen)} Buchungen nach {filepath}")
        return filepath


# =============================================================================
# DATEV XML EXPORT (für Unternehmen Online / Rechnungsdatenservice)
# =============================================================================

class DatevXmlExporter:
    """
    Exportiert Rechnungsdaten im DATEV XML-Format
    für den Rechnungsdatenservice 1.0 / Unternehmen Online
    """
    
    NAMESPACE = "http://xml.datev.de/bedi/tps/invoice/v050"
    XSI = "http://www.w3.org/2001/XMLSchema-instance"
    
    def __init__(self, config: DatevExportConfig):
        self.config = config
    
    def _create_invoice_element(self, invoice_data: Dict) -> ET.Element:
        """Erstellt ein einzelnes Invoice-Element"""
        
        # Namespace-Registrierung
        ET.register_namespace('', self.NAMESPACE)
        ET.register_namespace('xsi', self.XSI)
        
        invoice = ET.Element("invoice")
        invoice.set("version", "5.0")
        invoice.set("generator_info", "SBS Deutschland Invoice Processing")
        invoice.set("generating_system", "SBS-KI-Rechnungsverarbeitung")
        
        # Consolidate Flags
        invoice.set("consolidate", "false")
        invoice.set("description", invoice_data.get('rechnungsaussteller', '')[:60])
        
        # Invoice Type
        invoice_type = "Eingangsrechnung"  # Default für AP
        if invoice_data.get('beleg_typ') == BelegTyp.AUSGANGSRECHNUNG:
            invoice_type = "Ausgangsrechnung"
        
        # Invoice Info
        invoice_info = ET.SubElement(invoice, "invoice_info")
        
        # Invoice ID
        inv_id = ET.SubElement(invoice_info, "invoice_id")
        inv_id.text = str(invoice_data.get('rechnungsnummer', ''))[:36]
        
        # Invoice Date
        inv_date = ET.SubElement(invoice_info, "invoice_date")
        datum = invoice_data.get('datum', '')
        if isinstance(datum, str):
            try:
                datum = datetime.strptime(datum, "%Y-%m-%d").date()
            except:
                datum = date.today()
        inv_date.text = datum.strftime("%Y-%m-%d")
        
        # Invoice Type
        inv_type = ET.SubElement(invoice_info, "invoice_type")
        inv_type.text = invoice_type
        
        # Currency
        currency = ET.SubElement(invoice_info, "currency_code")
        currency.text = invoice_data.get('waehrung', 'EUR')
        
        # Delivery Date (optional)
        if invoice_data.get('lieferdatum'):
            delivery = ET.SubElement(invoice_info, "delivery_date")
            delivery.text = invoice_data['lieferdatum']
        
        # Accounting Info (Buchungsinformationen)
        accounting_info = ET.SubElement(invoice, "accounting_info")
        
        # Booking Text
        booking_text = ET.SubElement(accounting_info, "booking_text")
        buchungstext = f"{invoice_data.get('rechnungsaussteller', 'Rechnung')[:30]} {invoice_data.get('rechnungsnummer', '')[:20]}"
        booking_text.text = buchungstext[:60]
        
        # Account (Aufwandskonto)
        konten = KONTEN_SKR03 if self.config.kontenrahmen == Kontenrahmen.SKR03 else KONTEN_SKR04
        konto = invoice_data.get('konto', konten['sonstiger_aufwand'])
        
        account = ET.SubElement(accounting_info, "account_no")
        account.text = str(konto)
        
        # Cost Center (optional)
        if invoice_data.get('kostenstelle'):
            cost1 = ET.SubElement(accounting_info, "cost_category_id")
            cost1.text = str(invoice_data['kostenstelle'])
        
        # Supplier Info (Lieferant)
        supplier = ET.SubElement(invoice, "supplier_party")
        
        supplier_name = ET.SubElement(supplier, "name")
        supplier_name.text = invoice_data.get('rechnungsaussteller', '')[:50]
        
        if invoice_data.get('rechnungsaussteller_adresse'):
            address = ET.SubElement(supplier, "address")
            addr_parts = invoice_data['rechnungsaussteller_adresse'].split(',')
            if addr_parts:
                street = ET.SubElement(address, "street")
                street.text = addr_parts[0].strip()[:35]
        
        if invoice_data.get('ust_idnr'):
            tax_id = ET.SubElement(supplier, "tax_id")
            tax_id.text = invoice_data['ust_idnr'][:15]
        
        if invoice_data.get('iban'):
            bank = ET.SubElement(supplier, "bank_account")
            iban_elem = ET.SubElement(bank, "iban")
            iban_elem.text = invoice_data['iban'].replace(" ", "")[:34]
            if invoice_data.get('bic'):
                bic_elem = ET.SubElement(bank, "bic")
                bic_elem.text = invoice_data['bic'][:11]
        
        # Amount Info (Beträge)
        total_amount = ET.SubElement(invoice, "total_amount")
        
        # Brutto
        gross = ET.SubElement(total_amount, "gross_amount")
        gross.text = f"{float(invoice_data.get('betrag_brutto', 0)):.2f}"
        
        # Netto
        net = ET.SubElement(total_amount, "net_amount")
        betrag_netto = invoice_data.get('betrag_netto')
        if not betrag_netto and invoice_data.get('betrag_brutto') and invoice_data.get('mwst_satz'):
            betrag_netto = float(invoice_data['betrag_brutto']) / (1 + float(invoice_data['mwst_satz']) / 100)
        net.text = f"{float(betrag_netto or 0):.2f}"
        
        # Tax
        tax = ET.SubElement(total_amount, "tax_amount")
        mwst = invoice_data.get('mwst_betrag')
        if not mwst and invoice_data.get('betrag_brutto') and betrag_netto:
            mwst = float(invoice_data['betrag_brutto']) - float(betrag_netto)
        tax.text = f"{float(mwst or 0):.2f}"
        
        # Tax Rate
        tax_rate = ET.SubElement(total_amount, "tax_rate")
        tax_rate.text = str(int(invoice_data.get('mwst_satz', 19)))
        
        # Payment Info
        if invoice_data.get('faelligkeitsdatum') or invoice_data.get('zahlungsziel_tage'):
            payment = ET.SubElement(invoice, "payment_info")
            
            if invoice_data.get('faelligkeitsdatum'):
                due = ET.SubElement(payment, "due_date")
                due.text = invoice_data['faelligkeitsdatum']
            
            if invoice_data.get('zahlungsziel_tage'):
                terms = ET.SubElement(payment, "payment_terms_days")
                terms.text = str(invoice_data['zahlungsziel_tage'])
        
        return invoice
    
    def export_single(self, invoice_data: Dict, pretty_print: bool = True) -> str:
        """Exportiert eine einzelne Rechnung als XML"""
        invoice = self._create_invoice_element(invoice_data)
        
        xml_str = ET.tostring(invoice, encoding='unicode', method='xml')
        
        if pretty_print:
            dom = minidom.parseString(xml_str)
            xml_str = dom.toprettyxml(indent="  ", encoding=None)
            # Entferne doppelte XML-Declaration
            if xml_str.startswith('<?xml'):
                xml_str = '\n'.join(xml_str.split('\n')[1:])
        
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'
    
    def export_batch(self, invoices: List[Dict], pretty_print: bool = True) -> str:
        """Exportiert mehrere Rechnungen als XML-Batch"""
        
        root = ET.Element("invoices")
        root.set("version", "5.0")
        root.set("generator", "SBS Deutschland Invoice Processing")
        root.set("generated", datetime.now().isoformat())
        root.set("consultant_number", self.config.berater_nummer)
        root.set("client_number", self.config.mandanten_nummer)
        
        for inv_data in invoices:
            invoice = self._create_invoice_element(inv_data)
            root.append(invoice)
        
        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        
        if pretty_print:
            dom = minidom.parseString(xml_str)
            xml_str = dom.toprettyxml(indent="  ", encoding=None)
            if xml_str.startswith('<?xml'):
                xml_str = '\n'.join(xml_str.split('\n')[1:])
        
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'
    
    def export_to_file(self, invoices: List[Dict], filepath: str) -> str:
        """Exportiert in XML-Datei"""
        if len(invoices) == 1:
            content = self.export_single(invoices[0])
        else:
            content = self.export_batch(invoices)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"DATEV XML Export: {len(invoices)} Rechnungen nach {filepath}")
        return filepath


# =============================================================================
# INVOICE TO BUCHUNG CONVERTER
# =============================================================================

class InvoiceToBuchungConverter:
    """Konvertiert Rechnungsdaten in DATEV-Buchungssätze"""
    
    def __init__(self, kontenrahmen: Kontenrahmen = Kontenrahmen.SKR03):
        self.kontenrahmen = kontenrahmen
        self.konten = KONTEN_SKR03 if kontenrahmen == Kontenrahmen.SKR03 else KONTEN_SKR04
    
    def detect_account(self, invoice_data: Dict) -> int:
        """
        Erkennt automatisch das passende Aufwandskonto
        basierend auf Lieferant oder Beschreibung
        """
        supplier = (invoice_data.get('rechnungsaussteller', '') or '').lower()
        beschreibung = (invoice_data.get('verwendungszweck', '') or '').lower()
        
        # Artikel-Text hinzufügen
        artikel = invoice_data.get('artikel', [])
        if isinstance(artikel, str):
            try:
                artikel = json.loads(artikel)
            except:
                artikel = []
        
        artikel_text = ' '.join([str(a.get('beschreibung', '')) for a in artikel if isinstance(a, dict)]).lower()
        combined = f"{supplier} {beschreibung} {artikel_text}"
        
        # Regel-basierte Erkennung
        if any(kw in combined for kw in ['telefon', 'vodafone', 'telekom', 'o2', 'mobile']):
            return self.konten['telefon']
        elif any(kw in combined for kw in ['miete', 'rent', 'büro', 'office space']):
            return self.konten['miete']
        elif any(kw in combined for kw in ['werbung', 'marketing', 'advertising', 'google ads', 'facebook']):
            return self.konten['werbung']
        elif any(kw in combined for kw in ['versicherung', 'insurance', 'allianz', 'axa']):
            return self.konten['versicherung']
        elif any(kw in combined for kw in ['reise', 'hotel', 'flug', 'bahn', 'travel']):
            return self.konten['reisekosten']
        elif any(kw in combined for kw in ['kfz', 'auto', 'benzin', 'tanken', 'shell', 'aral']):
            return self.konten['kfz']
        elif any(kw in combined for kw in ['büromaterial', 'office supplies', 'papier', 'drucker']):
            return self.konten['bürobedarf']
        elif any(kw in combined for kw in ['beratung', 'consulting', 'dienstleistung', 'freelance']):
            return self.konten['fremdleistungen']
        elif any(kw in combined for kw in ['ware', 'produkt', 'material', 'einkauf']):
            return self.konten['wareneingang']
        
        return self.konten['sonstiger_aufwand']
    
    def get_steuerschluessel(self, mwst_satz: float, is_vorsteuer: bool = True) -> str:
        """Ermittelt den DATEV-Steuerschlüssel"""
        satz = int(round(mwst_satz))
        
        if is_vorsteuer:
            if satz == 19:
                return "9"
            elif satz == 7:
                return "2"
        else:  # Umsatzsteuer
            if satz == 19:
                return "3"
            elif satz == 7:
                return "1"
        
        return ""  # Keine Steuer
    
    def convert(self, invoice_data: Dict, kreditor_nummer: Optional[int] = None) -> List[DatevBuchung]:
        """
        Konvertiert eine Rechnung in DATEV-Buchungssätze
        
        Standard-Buchung Eingangsrechnung:
        Aufwand (Soll) an Verbindlichkeiten (Haben)
        """
        buchungen = []
        
        # Parse Beträge
        brutto = Decimal(str(invoice_data.get('betrag_brutto', 0)))
        mwst_satz = float(invoice_data.get('mwst_satz', 19))
        
        netto = invoice_data.get('betrag_netto')
        if netto:
            netto = Decimal(str(netto))
        else:
            netto = brutto / (1 + Decimal(str(mwst_satz)) / 100)
            netto = netto.quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        mwst = brutto - netto
        
        # Parse Datum
        datum_str = invoice_data.get('datum', '')
        if isinstance(datum_str, str):
            try:
                belegdatum = datetime.strptime(datum_str, "%Y-%m-%d").date()
            except:
                belegdatum = date.today()
        else:
            belegdatum = datum_str or date.today()
        
        # Ermittle Konten
        aufwandskonto = invoice_data.get('konto') or self.detect_account(invoice_data)
        gegenkonto = kreditor_nummer or self.konten['verbindlichkeiten']
        
        # Steuerschlüssel
        bu_schluessel = self.get_steuerschluessel(mwst_satz, is_vorsteuer=True)
        
        # Buchungstext
        supplier = (invoice_data.get('rechnungsaussteller', '') or 'Rechnung')[:30]
        inv_nr = (invoice_data.get('rechnungsnummer', '') or '')[:20]
        buchungstext = f"{supplier} {inv_nr}".strip()[:60]
        
        # Hauptbuchung: Brutto-Betrag
        hauptbuchung = DatevBuchung(
            umsatz=brutto,
            soll_haben="S",  # Soll (Aufwand)
            konto=aufwandskonto,
            gegenkonto=gegenkonto,
            belegdatum=belegdatum,
            belegnummer=str(invoice_data.get('rechnungsnummer', ''))[:36],
            buchungstext=buchungstext,
            steuerschluessel=bu_schluessel,
            kostenstelle=str(invoice_data.get('kostenstelle', ''))[:8],
            beleglink=invoice_data.get('pdf_link', ''),
            waehrung=invoice_data.get('waehrung', 'EUR'),
            rechnungsnummer=str(invoice_data.get('rechnungsnummer', '')),
            ust_idnr=invoice_data.get('ust_idnr', ''),
        )
        
        buchungen.append(hauptbuchung)
        
        return buchungen


# =============================================================================
# DATEV ZIP EXPORT (für Rechnungsdatenservice)
# =============================================================================

class DatevZipExporter:
    """
    Erstellt ein DATEV-konformes ZIP-Paket mit:
    - XML-Daten (document.xml)
    - PDF-Belege
    - Manifest
    """
    
    def __init__(self, config: DatevExportConfig):
        self.config = config
        self.xml_exporter = DatevXmlExporter(config)
    
    def create_package(self, invoices: List[Dict], pdf_files: List[str] = None,
                       output_path: str = None) -> str:
        """
        Erstellt ein ZIP-Paket für DATEV Unternehmen Online
        """
        if output_path is None:
            output_path = f"datev_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # XML-Daten
            xml_content = self.xml_exporter.export_batch(invoices)
            zf.writestr("document.xml", xml_content.encode('utf-8'))
            
            # PDF-Belege (falls vorhanden)
            if pdf_files:
                for i, pdf_path in enumerate(pdf_files):
                    if os.path.exists(pdf_path):
                        filename = os.path.basename(pdf_path)
                        zf.write(pdf_path, f"attachments/{filename}")
            
            # Manifest
            manifest = self._create_manifest(invoices, pdf_files)
            zf.writestr("manifest.xml", manifest.encode('utf-8'))
        
        logger.info(f"DATEV ZIP Package erstellt: {output_path}")
        return output_path
    
    def _create_manifest(self, invoices: List[Dict], pdf_files: List[str] = None) -> str:
        """Erstellt das Manifest für das ZIP-Paket"""
        root = ET.Element("manifest")
        root.set("version", "1.0")
        root.set("created", datetime.now().isoformat())
        
        meta = ET.SubElement(root, "metadata")
        ET.SubElement(meta, "consultant_number").text = self.config.berater_nummer
        ET.SubElement(meta, "client_number").text = self.config.mandanten_nummer
        ET.SubElement(meta, "document_count").text = str(len(invoices))
        ET.SubElement(meta, "generator").text = "SBS Deutschland Invoice Processing"
        
        files = ET.SubElement(root, "files")
        
        # XML
        xml_file = ET.SubElement(files, "file")
        xml_file.set("type", "data")
        xml_file.set("name", "document.xml")
        
        # PDFs
        if pdf_files:
            for pdf_path in pdf_files:
                pdf_file = ET.SubElement(files, "file")
                pdf_file.set("type", "attachment")
                pdf_file.set("name", f"attachments/{os.path.basename(pdf_path)}")
        
        return ET.tostring(root, encoding='unicode', method='xml')


# =============================================================================
# HIGH-LEVEL EXPORT FUNCTIONS
# =============================================================================

def export_invoices_to_datev_csv(invoices: List[Dict], config: DatevExportConfig,
                                  filepath: str = None) -> str:
    """
    Exportiert Rechnungen als DATEV CSV (EXTF-Format)
    für Import in DATEV Rechnungswesen
    """
    converter = InvoiceToBuchungConverter(config.kontenrahmen)
    exporter = DatevCsvExporter(config)
    
    buchungen = []
    for inv in invoices:
        buchungen.extend(converter.convert(inv))
    
    if filepath is None:
        filepath = f"EXTF_Buchungen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return exporter.export_to_file(buchungen, filepath)


def export_invoices_to_datev_xml(invoices: List[Dict], config: DatevExportConfig,
                                  filepath: str = None) -> str:
    """
    Exportiert Rechnungen als DATEV XML
    für Rechnungsdatenservice 1.0 / Unternehmen Online
    """
    exporter = DatevXmlExporter(config)
    
    if filepath is None:
        filepath = f"DATEV_Rechnungen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    
    return exporter.export_to_file(invoices, filepath)


def export_invoices_to_datev_zip(invoices: List[Dict], config: DatevExportConfig,
                                  pdf_files: List[str] = None,
                                  output_path: str = None) -> str:
    """
    Erstellt ein vollständiges DATEV ZIP-Paket
    für Rechnungsdatenservice 1.0
    """
    exporter = DatevZipExporter(config)
    return exporter.create_package(invoices, pdf_files, output_path)


# =============================================================================
# DEMO / TEST
# =============================================================================

if __name__ == "__main__":
    # Test-Konfiguration
    config = DatevExportConfig(
        berater_nummer="12345",
        mandanten_nummer="00001",
        wirtschaftsjahr_beginn=date(2025, 1, 1),
        kontenrahmen=Kontenrahmen.SKR03,
        bezeichnung="SBS Test Export"
    )
    
    # Test-Rechnung
    test_invoice = {
        'id': 1,
        'rechnungsnummer': 'RE-2025-001',
        'datum': '2025-01-06',
        'rechnungsaussteller': 'Test GmbH',
        'rechnungsaussteller_adresse': 'Teststraße 1, 12345 Berlin',
        'betrag_brutto': 119.00,
        'betrag_netto': 100.00,
        'mwst_satz': 19,
        'mwst_betrag': 19.00,
        'waehrung': 'EUR',
        'ust_idnr': 'DE123456789',
        'iban': 'DE89370400440532013000',
        'bic': 'COBADEFFXXX',
        'faelligkeitsdatum': '2025-01-20',
        'verwendungszweck': 'Beratungsleistung'
    }
    
    print("DATEV Export Test")
    print("=" * 50)
    
    # CSV Export
    csv_path = export_invoices_to_datev_csv([test_invoice], config, "/tmp/test_datev.csv")
    print(f"✅ CSV Export: {csv_path}")
    
    # XML Export
    xml_path = export_invoices_to_datev_xml([test_invoice], config, "/tmp/test_datev.xml")
    print(f"✅ XML Export: {xml_path}")
    
    # ZIP Export
    zip_path = export_invoices_to_datev_zip([test_invoice], config, output_path="/tmp/test_datev.zip")
    print(f"✅ ZIP Export: {zip_path}")
    
    # Zeige CSV-Inhalt
    print("\nCSV Inhalt (erste 5 Zeilen):")
    with open(csv_path, 'r', encoding='cp1252') as f:
        for i, line in enumerate(f):
            if i < 5:
                print(f"  {line.strip()[:100]}...")
    
    print("\n✅ Alle Tests erfolgreich!")
