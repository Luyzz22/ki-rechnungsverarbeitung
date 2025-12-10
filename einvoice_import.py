#!/usr/bin/env python3
"""
SBS Deutschland – E-Invoice Import Parser
Liest ZUGFeRD PDFs und XRechnung XMLs und extrahiert strukturierte Rechnungsdaten
"""

import xml.etree.ElementTree as ET
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Namespaces für CII (Cross Industry Invoice) - ZUGFeRD/Factur-X/XRechnung
CII_NAMESPACES = {
    'rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100',
    'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
    'udt': 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100',
    'qdt': 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100',
}

# Namespaces für UBL (Universal Business Language) - XRechnung UBL
UBL_NAMESPACES = {
    'ubl': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
}


class EInvoiceImporter:
    """Importiert und parsed E-Rechnungen (ZUGFeRD, XRechnung, Factur-X)"""
    
    def __init__(self):
        self.format = None  # 'CII' oder 'UBL'
        self.profile = None  # 'ZUGFeRD', 'XRechnung', 'Factur-X'
    
    def parse_xml(self, xml_content: str) -> Dict[str, Any]:
        """
        Parsed XML-Inhalt und extrahiert Rechnungsdaten.
        
        Args:
            xml_content: XML-String
            
        Returns:
            Dict mit extrahierten Rechnungsdaten
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Detect format
            root_tag = root.tag.lower()
            
            if 'crossindustryinvoice' in root_tag:
                self.format = 'CII'
                return self._parse_cii(root)
            elif 'invoice' in root_tag and 'ubl' in root_tag:
                self.format = 'UBL'
                return self._parse_ubl(root)
            else:
                # Try CII first, then UBL
                try:
                    return self._parse_cii(root)
                except:
                    return self._parse_ubl(root)
                    
        except ET.ParseError as e:
            logger.error(f"XML Parse Error: {e}")
            return {"error": f"XML Parse Error: {e}", "source": "einvoice_import"}
    
    def _parse_cii(self, root: ET.Element) -> Dict[str, Any]:
        """Parse CII Format (ZUGFeRD, Factur-X, XRechnung CII)"""
        
        data = {
            "source": "einvoice_import",
            "format": "CII",
            "profile": None,
            "confidence": 0.99,  # Strukturierte Daten = hohe Confidence
        }
        
        # Helper für Namespace-Suche
        def find(element, path):
            """Findet Element mit Namespace-Prefix"""
            for prefix, uri in CII_NAMESPACES.items():
                full_path = path.replace('ram:', f'{{{uri}}}').replace('rsm:', f'{{{CII_NAMESPACES["rsm"]}}}').replace('udt:', f'{{{CII_NAMESPACES["udt"]}}}')
                result = element.find(full_path)
                if result is not None:
                    return result
            # Fallback: ohne Namespace
            return element.find(path.replace('ram:', '').replace('rsm:', '').replace('udt:', ''))
        
        def find_text(element, path, default=''):
            """Findet Element-Text"""
            el = find(element, path)
            return el.text if el is not None and el.text else default
        
        # Profile erkennen
        context = find(root, './/rsm:ExchangedDocumentContext')
        if context is not None:
            guideline = find_text(context, './/ram:ID')
            if 'xrechnung' in guideline.lower():
                data['profile'] = 'XRechnung'
            elif 'zugferd' in guideline.lower() or 'factur-x' in guideline.lower():
                data['profile'] = 'ZUGFeRD/Factur-X'
            else:
                data['profile'] = 'EN16931'
        
        # Exchanged Document
        doc = find(root, './/rsm:ExchangedDocument')
        if doc is not None:
            data['rechnungsnummer'] = find_text(doc, './/ram:ID')
            
            # Datum
            date_str = find_text(doc, './/udt:DateTimeString')
            if date_str:
                data['datum'] = self._parse_date(date_str)
        
        # Supply Chain Trade Transaction
        transaction = find(root, './/rsm:SupplyChainTradeTransaction')
        if transaction is not None:
            # Trade Agreement (Seller/Buyer)
            agreement = find(transaction, './/ram:ApplicableHeaderTradeAgreement')
            if agreement is not None:
                # Seller
                seller = find(agreement, './/ram:SellerTradeParty')
                if seller is not None:
                    data['rechnungsaussteller'] = find_text(seller, './/ram:Name')
                    
                    # Adresse
                    addr = find(seller, './/ram:PostalTradeAddress')
                    if addr is not None:
                        street = find_text(addr, './/ram:LineOne')
                        city = find_text(addr, './/ram:CityName')
                        postal = find_text(addr, './/ram:PostcodeCode')
                        country = find_text(addr, './/ram:CountryID')
                        data['aussteller_adresse'] = f"{street}, {postal} {city}, {country}".strip(', ')
                    
                    # Steuernummer/USt-ID
                    tax_reg = find(seller, './/ram:SpecifiedTaxRegistration')
                    if tax_reg is not None:
                        tax_id = find_text(tax_reg, './/ram:ID')
                        scheme = find(tax_reg, './/ram:ID')
                        if scheme is not None and scheme.get('schemeID') == 'VA':
                            data['ust_id'] = tax_id
                        else:
                            data['steuernummer'] = tax_id
                
                # Buyer
                buyer = find(agreement, './/ram:BuyerTradeParty')
                if buyer is not None:
                    data['rechnungsempfaenger'] = find_text(buyer, './/ram:Name')
            
            # Trade Settlement (Amounts)
            settlement = find(transaction, './/ram:ApplicableHeaderTradeSettlement')
            if settlement is not None:
                data['waehrung'] = find_text(settlement, './/ram:InvoiceCurrencyCode', 'EUR')
                data['verwendungszweck'] = find_text(settlement, './/ram:PaymentReference')
                
                # Payment Means (Bank)
                payment = find(settlement, './/ram:SpecifiedTradeSettlementPaymentMeans')
                if payment is not None:
                    account = find(payment, './/ram:PayeePartyCreditorFinancialAccount')
                    if account is not None:
                        data['iban'] = find_text(account, './/ram:IBANID')
                    
                    institution = find(payment, './/ram:PayeeSpecifiedCreditorFinancialInstitution')
                    if institution is not None:
                        data['bic'] = find_text(institution, './/ram:BICID')
                
                # Tax
                tax = find(settlement, './/ram:ApplicableTradeTax')
                if tax is not None:
                    data['mwst_satz'] = self._parse_float(find_text(tax, './/ram:RateApplicablePercent'))
                    data['mwst_betrag'] = self._parse_float(find_text(tax, './/ram:CalculatedAmount'))
                    data['betrag_netto'] = self._parse_float(find_text(tax, './/ram:BasisAmount'))
                
                # Monetary Summation
                summation = find(settlement, './/ram:SpecifiedTradeSettlementHeaderMonetarySummation')
                if summation is not None:
                    data['betrag_netto'] = self._parse_float(find_text(summation, './/ram:LineTotalAmount')) or data.get('betrag_netto')
                    data['mwst_betrag'] = self._parse_float(find_text(summation, './/ram:TaxTotalAmount')) or data.get('mwst_betrag')
                    data['betrag_brutto'] = self._parse_float(find_text(summation, './/ram:GrandTotalAmount'))
                    data['bereits_bezahlt'] = self._parse_float(find_text(summation, './/ram:TotalPrepaidAmount'))
                    data['zahlbetrag'] = self._parse_float(find_text(summation, './/ram:DuePayableAmount'))
                
                # Payment Terms
                terms = find(settlement, './/ram:SpecifiedTradePaymentTerms')
                if terms is not None:
                    due_date = find_text(terms, './/udt:DateTimeString')
                    if due_date:
                        data['faelligkeitsdatum'] = self._parse_date(due_date)
                    
                    # Skonto
                    description = find_text(terms, './/ram:Description')
                    if description and 'skonto' in description.lower():
                        data['skonto_text'] = description
        
        # Line Items
        items = []
        for item in root.findall('.//{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}IncludedSupplyChainTradeLineItem'):
            line_item = {}
            
            product = find(item, './/ram:SpecifiedTradeProduct')
            if product is not None:
                line_item['bezeichnung'] = find_text(product, './/ram:Name')
                line_item['artikelnummer'] = find_text(product, './/ram:SellerAssignedID')
            
            line_agreement = find(item, './/ram:SpecifiedLineTradeAgreement')
            if line_agreement is not None:
                price = find(line_agreement, './/ram:NetPriceProductTradePrice')
                if price is not None:
                    line_item['einzelpreis'] = self._parse_float(find_text(price, './/ram:ChargeAmount'))
            
            line_delivery = find(item, './/ram:SpecifiedLineTradeDelivery')
            if line_delivery is not None:
                line_item['menge'] = self._parse_float(find_text(line_delivery, './/ram:BilledQuantity'))
            
            line_settlement = find(item, './/ram:SpecifiedLineTradeSettlement')
            if line_settlement is not None:
                line_item['gesamtpreis'] = self._parse_float(find_text(line_settlement, './/ram:LineTotalAmount'))
            
            if line_item:
                items.append(line_item)
        
        if items:
            data['positionen'] = items
        
        return data
    
    def _parse_ubl(self, root: ET.Element) -> Dict[str, Any]:
        """Parse UBL Format (XRechnung UBL)"""
        
        data = {
            "source": "einvoice_import",
            "format": "UBL",
            "profile": "XRechnung-UBL",
            "confidence": 0.99,
        }
        
        # Helper
        def find_text(path, default=''):
            for prefix, uri in UBL_NAMESPACES.items():
                full_path = path
                for p, u in UBL_NAMESPACES.items():
                    full_path = full_path.replace(f'{p}:', f'{{{u}}}')
                el = root.find(full_path)
                if el is not None and el.text:
                    return el.text
            return default
        
        # Basic fields
        data['rechnungsnummer'] = find_text('.//cbc:ID')
        data['datum'] = find_text('.//cbc:IssueDate')
        data['faelligkeitsdatum'] = find_text('.//cbc:DueDate')
        data['waehrung'] = find_text('.//cbc:DocumentCurrencyCode', 'EUR')
        
        # Seller
        data['rechnungsaussteller'] = find_text('.//cac:AccountingSupplierParty//cbc:RegistrationName') or \
                                       find_text('.//cac:AccountingSupplierParty//cbc:Name')
        
        # Buyer
        data['rechnungsempfaenger'] = find_text('.//cac:AccountingCustomerParty//cbc:RegistrationName') or \
                                       find_text('.//cac:AccountingCustomerParty//cbc:Name')
        
        # Amounts
        data['betrag_netto'] = self._parse_float(find_text('.//cac:LegalMonetaryTotal//cbc:TaxExclusiveAmount'))
        data['betrag_brutto'] = self._parse_float(find_text('.//cac:LegalMonetaryTotal//cbc:TaxInclusiveAmount'))
        data['zahlbetrag'] = self._parse_float(find_text('.//cac:LegalMonetaryTotal//cbc:PayableAmount'))
        
        # Tax
        data['mwst_betrag'] = self._parse_float(find_text('.//cac:TaxTotal//cbc:TaxAmount'))
        data['mwst_satz'] = self._parse_float(find_text('.//cac:TaxSubtotal//cbc:Percent'))
        
        # Bank
        data['iban'] = find_text('.//cac:PaymentMeans//cac:PayeeFinancialAccount//cbc:ID')
        data['bic'] = find_text('.//cac:PaymentMeans//cac:PayeeFinancialAccount//cac:FinancialInstitutionBranch//cbc:ID')
        
        return data
    
    def _parse_date(self, date_str: str) -> str:
        """Konvertiert verschiedene Datumsformate zu YYYY-MM-DD"""
        if not date_str:
            return ''
        
        # Format 102: YYYYMMDD
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # ISO Format
        if 'T' in date_str:
            return date_str.split('T')[0]
        
        return date_str
    
    def _parse_float(self, value: str) -> Optional[float]:
        """Konvertiert String zu Float"""
        if not value:
            return None
        try:
            # Handle German format (1.234,56)
            value = value.replace(' ', '').replace('\xa0', '')
            if ',' in value and '.' in value:
                value = value.replace('.', '').replace(',', '.')
            elif ',' in value:
                value = value.replace(',', '.')
            return float(value)
        except:
            return None


def extract_xml_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extrahiert eingebettetes XML aus ZUGFeRD/Factur-X PDF.
    
    Args:
        pdf_path: Pfad zur PDF
        
    Returns:
        XML-String oder None
    """
    try:
        import pikepdf
    except ImportError:
        logger.warning("pikepdf nicht verfügbar")
        return None
    
    try:
        pdf = pikepdf.open(pdf_path)
        
        # Suche nach eingebetteten Dateien
        if "/Names" in pdf.Root and "/EmbeddedFiles" in pdf.Root["/Names"]:
            ef = pdf.Root["/Names"]["/EmbeddedFiles"]
            if "/Names" in ef:
                names = list(ef["/Names"])
                for i in range(0, len(names), 2):
                    filename = str(names[i])
                    if filename.lower().endswith('.xml') or 'factur' in filename.lower() or 'zugferd' in filename.lower():
                        filespec = names[i + 1]
                        if "/EF" in filespec and "/F" in filespec["/EF"]:
                            stream = filespec["/EF"]["/F"]
                            xml_bytes = bytes(stream.read_bytes())
                            pdf.close()
                            return xml_bytes.decode('utf-8')
        
        pdf.close()
        return None
        
    except Exception as e:
        logger.error(f"Fehler beim XML-Extrahieren: {e}")
        return None


def parse_einvoice(file_path: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Hauptfunktion: Parsed E-Rechnung (PDF oder XML).
    
    Args:
        file_path: Pfad zur Datei
        
    Returns:
        Tuple (is_einvoice, extracted_data)
    """
    path = Path(file_path)
    importer = EInvoiceImporter()
    
    # XML-Datei direkt
    if path.suffix.lower() == '.xml':
        try:
            with open(path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            data = importer.parse_xml(xml_content)
            if 'error' not in data:
                logger.info(f"✅ E-Rechnung erkannt: {data.get('profile', 'Unknown')} ({data.get('format', 'Unknown')})")
                return True, data
        except Exception as e:
            logger.error(f"XML-Parsing fehlgeschlagen: {e}")
    
    # PDF mit eingebettetem XML
    elif path.suffix.lower() == '.pdf':
        xml_content = extract_xml_from_pdf(str(path))
        if xml_content:
            data = importer.parse_xml(xml_content)
            if 'error' not in data:
                logger.info(f"✅ ZUGFeRD/Factur-X erkannt: {data.get('profile', 'Unknown')}")
                return True, data
    
    return False, {}


def is_einvoice(file_path: str) -> bool:
    """Quick-Check ob Datei eine E-Rechnung ist"""
    is_invoice, _ = parse_einvoice(file_path)
    return is_invoice


# CLI Test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        is_inv, data = parse_einvoice(sys.argv[1])
        if is_inv:
            print(f"✅ E-Rechnung erkannt!")
            print(f"   Format: {data.get('format')}")
            print(f"   Profil: {data.get('profile')}")
            print(f"   Rechnungsnr: {data.get('rechnungsnummer')}")
            print(f"   Aussteller: {data.get('rechnungsaussteller')}")
            print(f"   Brutto: {data.get('betrag_brutto')} {data.get('waehrung', 'EUR')}")
        else:
            print("❌ Keine E-Rechnung erkannt")
    else:
        print("Usage: python einvoice_import.py <file.pdf|file.xml>")
