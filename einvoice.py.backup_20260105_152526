#!/usr/bin/env python3
"""
SBS Deutschland – E-Invoice Module
XRechnung und ZUGFeRD Export & Validierung
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# XML Namespaces für XRechnung (CII - Cross Industry Invoice)
NAMESPACES = {
    'rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100',
    'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
    'udt': 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100',
    'qdt': 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100',
}


class XRechnungGenerator:
    """Generiert XRechnung-konformes XML (EN16931 / CII Format)"""
    
    def __init__(self):
        # Register namespaces
        for prefix, uri in NAMESPACES.items():
            ET.register_namespace(prefix, uri)
    
    def generate(self, invoice_data: Dict[str, Any]) -> str:
        """
        Generiert XRechnung XML aus Invoice-Daten.
        
        Args:
            invoice_data: Extrahierte Rechnungsdaten
            
        Returns:
            XML-String im XRechnung-Format
        """
        # Root Element
        root = ET.Element('{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice')
        
        # Exchange Document Context
        context = ET.SubElement(root, '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}ExchangedDocumentContext')
        guideline = ET.SubElement(context, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}GuidelineSpecifiedDocumentContextParameter')
        guideline_id = ET.SubElement(guideline, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ID')
        guideline_id.text = 'urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_3.0'
        
        # Exchanged Document
        doc = ET.SubElement(root, '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}ExchangedDocument')
        
        # Invoice Number (BT-1)
        doc_id = ET.SubElement(doc, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ID')
        doc_id.text = str(invoice_data.get('rechnungsnummer', ''))
        
        # Type Code (BT-3) - 380 = Commercial Invoice
        type_code = ET.SubElement(doc, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TypeCode')
        type_code.text = '380'
        
        # Issue Date (BT-2)
        issue_date = ET.SubElement(doc, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}IssueDateTime')
        date_str = ET.SubElement(issue_date, '{urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100}DateTimeString')
        date_str.set('format', '102')  # YYYYMMDD
        date_str.text = self._format_date(invoice_data.get('datum', ''))
        
        # Supply Chain Trade Transaction
        transaction = ET.SubElement(root, '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}SupplyChainTradeTransaction')
        
        # Trade Agreement
        agreement = ET.SubElement(transaction, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableHeaderTradeAgreement')
        
        # Seller (BG-4)
        self._add_seller(agreement, invoice_data)
        
        # Buyer (BG-7)
        self._add_buyer(agreement, invoice_data)
        
        # Trade Delivery
        delivery = ET.SubElement(transaction, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableHeaderTradeDelivery')
        
        # Trade Settlement
        settlement = ET.SubElement(transaction, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableHeaderTradeSettlement')
        
        # Currency (BT-5)
        currency = ET.SubElement(settlement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}InvoiceCurrencyCode')
        currency.text = invoice_data.get('waehrung', 'EUR')
        
        # Payment Reference
        if invoice_data.get('verwendungszweck'):
            payment_ref = ET.SubElement(settlement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}PaymentReference')
            payment_ref.text = invoice_data.get('verwendungszweck')
        
        # Payment Means (BG-16)
        self._add_payment_means(settlement, invoice_data)
        
        # Tax (BG-23)
        self._add_tax(settlement, invoice_data)
        
        # Monetary Summation (BG-22)
        self._add_monetary_summation(settlement, invoice_data)
        
        # Line Items (BG-25)
        # Parse artikel if JSON string
        artikel = invoice_data.get('artikel', [])
        if isinstance(artikel, str):
            import json
            try:
                artikel = json.loads(artikel)
            except:
                artikel = []
        for item in artikel:
            self._add_line_item(transaction, item, invoice_data.get('waehrung', 'EUR'))
        
        # Generate XML string
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def _format_date(self, date_str: str) -> str:
        """Konvertiert Datum zu YYYYMMDD"""
        if not date_str:
            return datetime.now().strftime('%Y%m%d')
        
        # Versuche verschiedene Formate
        for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y%m%d')
            except ValueError:
                continue
        
        return datetime.now().strftime('%Y%m%d')
    
    def _add_seller(self, parent: ET.Element, data: Dict):
        """Fügt Verkäufer-Informationen hinzu (BG-4)"""
        seller = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SellerTradeParty')
        
        # Name (BT-27)
        name = ET.SubElement(seller, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}Name')
        name.text = data.get('rechnungsaussteller', '')
        
        # Tax Registration (BT-31 / BT-32)
        if data.get('ust_idnr'):
            tax_reg = ET.SubElement(seller, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTaxRegistration')
            tax_id = ET.SubElement(tax_reg, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ID')
            tax_id.set('schemeID', 'VA')  # VAT
            tax_id.text = data.get('ust_idnr')
        
        # Address (BG-5)
        if data.get('rechnungsaussteller_adresse'):
            self._add_address(seller, data.get('rechnungsaussteller_adresse'))
    
    def _add_buyer(self, parent: ET.Element, data: Dict):
        """Fügt Käufer-Informationen hinzu (BG-7)"""
        buyer = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BuyerTradeParty')
        
        # Name (BT-44)
        name = ET.SubElement(buyer, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}Name')
        name.text = data.get('rechnungsempfänger', data.get('rechnungsempfaenger', ''))
        
        # Address (BG-8)
        addr = data.get('rechnungsempfänger_adresse', data.get('rechnungsempfaenger_adresse', ''))
        if addr:
            self._add_address(buyer, addr)
    
    def _add_address(self, parent: ET.Element, address: str):
        """Fügt Adresse hinzu"""
        addr_elem = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}PostalTradeAddress')
        
        # Einfache Adress-Zeile
        line = ET.SubElement(addr_elem, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}LineOne')
        line.text = address
        
        # Country Code (default DE)
        country = ET.SubElement(addr_elem, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}CountryID')
        country.text = 'DE'
    
    def _add_payment_means(self, parent: ET.Element, data: Dict):
        """Fügt Zahlungsinformationen hinzu (BG-16)"""
        payment = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradeSettlementPaymentMeans')
        
        # Type Code (BT-81) - 58 = SEPA Credit Transfer
        type_code = ET.SubElement(payment, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TypeCode')
        type_code.text = '58'
        
        # IBAN (BT-84)
        if data.get('iban'):
            account = ET.SubElement(payment, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}PayeePartyCreditorFinancialAccount')
            iban = ET.SubElement(account, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}IBANID')
            iban.text = data.get('iban', '').replace(' ', '')
            
            # BIC (BT-86)
            if data.get('bic'):
                institution = ET.SubElement(payment, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}PayeeSpecifiedCreditorFinancialInstitution')
                bic = ET.SubElement(institution, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BICID')
                bic.text = data.get('bic')
    
    def _add_tax(self, parent: ET.Element, data: Dict):
        """Fügt Steuer-Informationen hinzu (BG-23)"""
        tax = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableTradeTax')
        
        # Tax Amount (BT-117)
        amount = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}CalculatedAmount')
        amount.text = str(data.get('mwst_betrag', 0))
        
        # Tax Type Code (BT-118)
        type_code = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TypeCode')
        type_code.text = 'VAT'
        
        # Taxable Amount (BT-116)
        basis = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BasisAmount')
        basis.text = str(data.get('betrag_netto', 0))
        
        # Tax Rate (BT-119)
        rate = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}RateApplicablePercent')
        rate.text = str(data.get('mwst_satz', 19))
    
    def _add_monetary_summation(self, parent: ET.Element, data: Dict):
        """Fügt Summen hinzu (BG-22)"""
        summation = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradeSettlementHeaderMonetarySummation')
        
        # Line Total (BT-106)
        line_total = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}LineTotalAmount')
        line_total.text = str(data.get('betrag_netto', 0))
        
        # Tax Basis (BT-109)
        tax_basis = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TaxBasisTotalAmount')
        tax_basis.text = str(data.get('betrag_netto', 0))
        
        # Tax Total (BT-110)
        tax_total = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TaxTotalAmount')
        tax_total.set('currencyID', data.get('waehrung', 'EUR'))
        tax_total.text = str(data.get('mwst_betrag', 0))
        
        # Grand Total (BT-112)
        grand_total = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}GrandTotalAmount')
        grand_total.text = str(data.get('betrag_brutto', 0))
        
        # Due Payable (BT-115)
        due = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}DuePayableAmount')
        due.text = str(data.get('betrag_brutto', 0))
    
    def _add_line_item(self, parent: ET.Element, item: Dict, currency: str):
        """Fügt Rechnungsposition hinzu (BG-25)"""
        line = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}IncludedSupplyChainTradeLineItem')
        
        # Line ID (BT-126)
        doc = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}AssociatedDocumentLineDocument')
        line_id = ET.SubElement(doc, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}LineID')
        line_id.text = str(item.get('position', 1))
        
        # Product (BG-31)
        product = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradeProduct')
        name = ET.SubElement(product, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}Name')
        name.text = item.get('beschreibung', '')
        
        # Agreement
        agreement = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedLineTradeAgreement')
        price = ET.SubElement(agreement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}NetPriceProductTradePrice')
        charge = ET.SubElement(price, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ChargeAmount')
        charge.text = str(item.get('einzelpreis', 0))
        
        # Delivery
        delivery = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedLineTradeDelivery')
        qty = ET.SubElement(delivery, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BilledQuantity')
        qty.set('unitCode', 'C62')  # Unit
        qty.text = str(item.get('menge', 1))
        
        # Settlement
        settlement = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedLineTradeSettlement')
        
        # Line Tax
        tax = ET.SubElement(settlement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableTradeTax')
        tax_type = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TypeCode')
        tax_type.text = 'VAT'
        tax_cat = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}CategoryCode')
        tax_cat.text = 'S'  # Standard rate
        tax_rate = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}RateApplicablePercent')
        tax_rate.text = '19'
        
        # Line Total
        summation = ET.SubElement(settlement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradeSettlementLineMonetarySummation')
        total = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}LineTotalAmount')
        total.text = str(item.get('gesamt', 0))


def generate_xrechnung(invoice_data: Dict[str, Any]) -> str:
    """
    Generiert XRechnung XML aus Invoice-Daten.
    
    Args:
        invoice_data: Extrahierte Rechnungsdaten
        
    Returns:
        XML-String im XRechnung-Format (EN16931 / CII)
    """
    generator = XRechnungGenerator()
    return generator.generate(invoice_data)


def validate_xrechnung(xml_string: str) -> Tuple[bool, str, str]:
    """
    Validiert XRechnung/ZUGFeRD XML.
    
    Args:
        xml_string: XML zu validieren
        
    Returns:
        Tuple[is_valid, message, detected_profile]
    """
    xml = (xml_string or "").strip()
    if not xml:
        return False, "Kein XML übergeben", ""
    
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        return False, f"XML Parse-Fehler: {e}", ""
    
    text_lower = xml.lower()
    profile = ""
    issues = []
    
    # Profile Detection
    if 'xrechnung' in text_lower or 'urn:cen.eu:en16931' in text_lower:
        profile = "XRechnung"
    elif 'zugferd' in text_lower or 'factur-x' in text_lower:
        profile = "ZUGFeRD/Factur-X"
    elif 'crossindustryinvoice' in root.tag.lower():
        profile = "CII (Cross Industry Invoice)"
    
    # Basic Structure Validation
    required_elements = [
        'ExchangedDocument',
        'SupplyChainTradeTransaction',
    ]
    
    for elem in required_elements:
        if elem.lower() not in xml.lower():
            issues.append(f"Fehlendes Element: {elem}")
    
    # Check for required business terms
    if 'ID' not in xml:
        issues.append("Rechnungsnummer (BT-1) fehlt")
    
    if issues:
        return False, f"Validierungsfehler: {', '.join(issues)}", profile
    
    return True, f"Valide {profile or 'E-Rechnung'}", profile


def export_xrechnung_file(invoice_data: Dict[str, Any], output_dir: str = "output") -> str:
    """
    Exportiert XRechnung als XML-Datei.
    
    Args:
        invoice_data: Rechnungsdaten
        output_dir: Ausgabeverzeichnis
        
    Returns:
        Pfad zur erstellten Datei
    """
    Path(output_dir).mkdir(exist_ok=True)
    
    xml_content = generate_xrechnung(invoice_data)
    
    # Filename
    invoice_nr = invoice_data.get('rechnungsnummer', 'unknown').replace('/', '-')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"xrechnung_{invoice_nr}_{timestamp}.xml"
    
    filepath = Path(output_dir) / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    logger.info(f"XRechnung exportiert: {filepath}")
    return str(filepath)
