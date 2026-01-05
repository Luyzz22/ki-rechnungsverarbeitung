#!/usr/bin/env python3
"""
SBS Deutschland – E-Invoice Module v2.0
Enterprise-Grade XRechnung und ZUGFeRD Export

Features:
- XRechnung 3.0 / EN16931 compliant
- Intelligente Adress-Parsing (PLZ, Stadt, Straße, Land)
- Automatische Länder-Erkennung
- Korrekte Netto/Brutto Berechnung auf Line-Item Ebene
- Validierung vor Export
- Umfangreiche Fehlerbehandlung
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import logging
import re
import json

logger = logging.getLogger(__name__)

# XML Namespaces für XRechnung (CII - Cross Industry Invoice)
NAMESPACES = {
    'rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100',
    'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
    'udt': 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100',
    'qdt': 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100',
}

# Länder-Erkennung Patterns
COUNTRY_PATTERNS = {
    'DE': [
        r'\bGermany\b', r'\bDeutschland\b', r'\b\d{5}\s+\w+\b',  # 5-stellige PLZ
        r'\bDE\d{9}\b',  # DE USt-IdNr
    ],
    'AT': [
        r'\bAustria\b', r'\bÖsterreich\b', r'\b\d{4}\s+\w+\b',  # 4-stellige PLZ
        r'\bATU\d{8}\b',  # AT USt-IdNr
    ],
    'CH': [
        r'\bSwitzerland\b', r'\bSchweiz\b', r'\bSuisse\b',
        r'\bCH-\d{4}\b', r'\bCHE-\d{3}\.\d{3}\.\d{3}\b',
    ],
    'US': [
        r'\bUnited States\b', r'\bUSA\b', r'\bU\.S\.A\.\b',
        r'\b[A-Z]{2}\s+\d{5}(-\d{4})?\b',  # US ZIP Code
        r'\bCalifornia\b', r'\bNew York\b', r'\bTexas\b',
    ],
    'GB': [
        r'\bUnited Kingdom\b', r'\bUK\b', r'\bEngland\b',
        r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b',  # UK Postcode
    ],
    'FR': [
        r'\bFrance\b', r'\bFrankreich\b',
        r'\bFR\d{2}\s?\d{9}\b',  # FR USt-IdNr
    ],
    'NL': [
        r'\bNetherlands\b', r'\bNiederlande\b', r'\bHolland\b',
        r'\bNL\d{9}B\d{2}\b',  # NL USt-IdNr
    ],
}

# Deutsche PLZ-Patterns
DE_PLZ_PATTERN = re.compile(r'\b(\d{5})\s+([A-Za-zäöüÄÖÜß\-\s]+)\b')
# Straßen-Pattern
STREET_PATTERN = re.compile(r'^(.+?(?:straße|str\.|weg|allee|platz|ring|gasse|damm|ufer|chaussee|avenue|street|road|lane))\s*(\d+[a-zA-Z]?)?\s*,?\s*', re.IGNORECASE)


class AddressParser:
    """Intelligentes Adress-Parsing für XRechnung"""
    
    @staticmethod
    def parse(address: str) -> Dict[str, str]:
        """
        Parst eine Adress-Zeile in strukturierte Komponenten.
        
        Returns:
            Dict mit: street, postcode, city, country_code, country_name
        """
        if not address:
            return {
                'street': '',
                'postcode': '',
                'city': '',
                'country_code': 'DE',
                'country_name': '',
            }
        
        result = {
            'street': '',
            'postcode': '',
            'city': '',
            'country_code': 'DE',
            'country_name': '',
            'raw': address,
        }
        
        # Detect country
        result['country_code'] = AddressParser.detect_country(address)
        
        # Clean address
        addr = address.strip()
        
        # Remove country name from end
        country_names = ['Germany', 'Deutschland', 'Austria', 'Österreich', 
                        'Switzerland', 'Schweiz', 'United States', 'USA',
                        'United Kingdom', 'UK', 'France', 'Frankreich',
                        'Netherlands', 'Niederlande']
        for cn in country_names:
            if addr.lower().endswith(cn.lower()):
                result['country_name'] = cn
                addr = addr[:-len(cn)].strip().rstrip(',').strip()
                break
        
        # Try to extract German-style address (PLZ Stadt)
        plz_match = DE_PLZ_PATTERN.search(addr)
        if plz_match:
            result['postcode'] = plz_match.group(1)
            city_raw = plz_match.group(2).strip()
            # Remove trailing country or comma
            city_raw = re.sub(r',?\s*(Germany|Deutschland|DE)?\s*$', '', city_raw, flags=re.IGNORECASE)
            result['city'] = city_raw.strip()
            
            # Street is everything before PLZ
            street_part = addr[:plz_match.start()].strip().rstrip(',').strip()
            result['street'] = street_part
        else:
            # Fallback: Split by comma
            parts = [p.strip() for p in addr.split(',')]
            if len(parts) >= 3:
                result['street'] = parts[0]
                # Try to find PLZ in middle parts
                for i, part in enumerate(parts[1:-1], 1):
                    plz_only = re.search(r'\b(\d{4,5})\b', part)
                    if plz_only:
                        result['postcode'] = plz_only.group(1)
                        result['city'] = re.sub(r'\b\d{4,5}\b', '', part).strip()
                        break
                    else:
                        result['city'] = part
            elif len(parts) == 2:
                result['street'] = parts[0]
                # Second part might be "PLZ City" or just "City"
                plz_only = re.search(r'\b(\d{4,5})\s+(.+)', parts[1])
                if plz_only:
                    result['postcode'] = plz_only.group(1)
                    result['city'] = plz_only.group(2).strip()
                else:
                    result['city'] = parts[1]
            else:
                result['street'] = addr
        
        return result
    
    @staticmethod
    def detect_country(text: str) -> str:
        """Erkennt das Land aus Adresse oder USt-IdNr"""
        if not text:
            return 'DE'
        
        text_upper = text.upper()
        
        # Check USt-IdNr prefix first (most reliable)
        ust_match = re.search(r'\b([A-Z]{2})\d{8,12}\b', text_upper)
        if ust_match:
            country = ust_match.group(1)
            if country in ['DE', 'AT', 'CH', 'FR', 'NL', 'GB', 'IT', 'ES', 'BE', 'PL']:
                return country
        
        # Check patterns
        for country_code, patterns in COUNTRY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return country_code
        
        # Default
        return 'DE'


class XRechnungGenerator:
    """Generiert XRechnung-konformes XML (EN16931 / CII Format) - Enterprise Edition"""
    
    def __init__(self, pretty_print: bool = False):
        """
        Args:
            pretty_print: XML mit Einrückung formatieren
        """
        self.pretty_print = pretty_print
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
        # Validate and clean data first
        data = self._prepare_data(invoice_data)
        
        # Root Element
        root = ET.Element('{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice')
        
        # Exchange Document Context
        self._add_context(root)
        
        # Exchanged Document
        self._add_document(root, data)
        
        # Supply Chain Trade Transaction
        self._add_transaction(root, data)
        
        # Generate XML string
        xml_str = ET.tostring(root, encoding='unicode', xml_declaration=True)
        
        if self.pretty_print:
            xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
            # Remove extra blank lines
            xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
        
        return xml_str
    
    def _prepare_data(self, data: Dict) -> Dict:
        """Bereitet und validiert Daten vor"""
        result = dict(data)
        
        # Ensure numeric values
        for field in ['betrag_brutto', 'betrag_netto', 'mwst_betrag', 'mwst_satz']:
            if field in result:
                try:
                    result[field] = float(result[field] or 0)
                except (ValueError, TypeError):
                    result[field] = 0.0
        
        # Calculate missing values
        if result.get('betrag_brutto') and not result.get('betrag_netto'):
            mwst_satz = result.get('mwst_satz', 19)
            result['betrag_netto'] = round(result['betrag_brutto'] / (1 + mwst_satz / 100), 2)
            result['mwst_betrag'] = round(result['betrag_brutto'] - result['betrag_netto'], 2)
        elif result.get('betrag_netto') and not result.get('betrag_brutto'):
            mwst_satz = result.get('mwst_satz', 19)
            result['mwst_betrag'] = round(result['betrag_netto'] * mwst_satz / 100, 2)
            result['betrag_brutto'] = round(result['betrag_netto'] + result['mwst_betrag'], 2)
        
        # Parse addresses
        result['_seller_addr'] = AddressParser.parse(result.get('rechnungsaussteller_adresse', ''))
        result['_buyer_addr'] = AddressParser.parse(
            result.get('rechnungsempfänger_adresse', result.get('rechnungsempfaenger_adresse', ''))
        )
        
        # Detect seller country from USt-IdNr or address
        ust_id = result.get('ust_idnr', '')
        if ust_id:
            result['_seller_addr']['country_code'] = AddressParser.detect_country(ust_id)
        
        # Parse artikel
        artikel = result.get('artikel', [])
        if isinstance(artikel, str):
            try:
                artikel = json.loads(artikel)
            except:
                artikel = []
        result['_artikel'] = artikel if isinstance(artikel, list) else []
        
        # If no line items, create one from total
        if not result['_artikel']:
            result['_artikel'] = [{
                'position': 1,
                'beschreibung': result.get('verwendungszweck', 'Rechnungsposition'),
                'menge': 1,
                'einzelpreis': result.get('betrag_brutto', 0),
                'einzelpreis_netto': result.get('betrag_netto', 0),
                'gesamt': result.get('betrag_brutto', 0),
                'gesamt_netto': result.get('betrag_netto', 0),
            }]
        
        # Calculate netto for each line item if missing
        mwst_satz = result.get('mwst_satz', 19)
        for item in result['_artikel']:
            if 'einzelpreis_netto' not in item:
                einzelpreis = float(item.get('einzelpreis', 0))
                item['einzelpreis_netto'] = round(einzelpreis / (1 + mwst_satz / 100), 2)
            if 'gesamt_netto' not in item:
                gesamt = float(item.get('gesamt', item.get('einzelpreis', 0)))
                item['gesamt_netto'] = round(gesamt / (1 + mwst_satz / 100), 2)
        
        return result
    
    def _add_context(self, root: ET.Element):
        """Fügt Document Context hinzu"""
        context = ET.SubElement(root, '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}ExchangedDocumentContext')
        guideline = ET.SubElement(context, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}GuidelineSpecifiedDocumentContextParameter')
        guideline_id = ET.SubElement(guideline, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ID')
        guideline_id.text = 'urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_3.0'
    
    def _add_document(self, root: ET.Element, data: Dict):
        """Fügt Exchanged Document hinzu"""
        doc = ET.SubElement(root, '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}ExchangedDocument')
        
        # Invoice Number (BT-1) - Required
        doc_id = ET.SubElement(doc, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ID')
        doc_id.text = str(data.get('rechnungsnummer', 'UNKNOWN'))
        
        # Type Code (BT-3) - 380 = Commercial Invoice
        type_code = ET.SubElement(doc, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TypeCode')
        type_code.text = '380'
        
        # Issue Date (BT-2) - Required
        issue_date = ET.SubElement(doc, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}IssueDateTime')
        date_str = ET.SubElement(issue_date, '{urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100}DateTimeString')
        date_str.set('format', '102')
        date_str.text = self._format_date(data.get('datum', ''))
        
        # Notes (BT-22) - Optional
        if data.get('zahlungsbedingungen'):
            note = ET.SubElement(doc, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}IncludedNote')
            content = ET.SubElement(note, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}Content')
            content.text = data.get('zahlungsbedingungen')
    
    def _add_transaction(self, root: ET.Element, data: Dict):
        """Fügt Supply Chain Trade Transaction hinzu"""
        transaction = ET.SubElement(root, '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}SupplyChainTradeTransaction')
        
        # Trade Agreement
        agreement = ET.SubElement(transaction, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableHeaderTradeAgreement')
        
        # Buyer Reference (BT-10) - Required for XRechnung to public sector
        if data.get('leitweg_id'):
            buyer_ref = ET.SubElement(agreement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BuyerReference')
            buyer_ref.text = data.get('leitweg_id')
        
        # Seller (BG-4)
        self._add_seller(agreement, data)
        
        # Buyer (BG-7)
        self._add_buyer(agreement, data)
        
        # Trade Delivery (BG-13)
        delivery = ET.SubElement(transaction, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableHeaderTradeDelivery')
        
        # Delivery Date if available
        if data.get('lieferdatum'):
            actual_delivery = ET.SubElement(delivery, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ActualDeliverySupplyChainEvent')
            occurrence = ET.SubElement(actual_delivery, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}OccurrenceDateTime')
            date_str = ET.SubElement(occurrence, '{urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100}DateTimeString')
            date_str.set('format', '102')
            date_str.text = self._format_date(data.get('lieferdatum'))
        
        # Trade Settlement (BG-19)
        settlement = ET.SubElement(transaction, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableHeaderTradeSettlement')
        
        # Currency (BT-5) - Required
        currency = ET.SubElement(settlement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}InvoiceCurrencyCode')
        currency.text = data.get('waehrung', 'EUR')
        
        # Payment Reference (BT-83)
        verwendungszweck = data.get('verwendungszweck', data.get('rechnungsnummer', ''))
        if verwendungszweck:
            payment_ref = ET.SubElement(settlement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}PaymentReference')
            payment_ref.text = str(verwendungszweck)
        
        # Payment Means (BG-16)
        self._add_payment_means(settlement, data)
        
        # Payment Terms (BT-9 / BT-20)
        self._add_payment_terms(settlement, data)
        
        # Tax (BG-23)
        self._add_tax(settlement, data)
        
        # Monetary Summation (BG-22)
        self._add_monetary_summation(settlement, data)
        
        # Line Items (BG-25)
        for idx, item in enumerate(data['_artikel'], 1):
            item['position'] = item.get('position', idx)
            self._add_line_item(transaction, item, data)
    
    def _add_seller(self, parent: ET.Element, data: Dict):
        """Fügt Verkäufer-Informationen hinzu (BG-4)"""
        seller = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SellerTradeParty')
        
        # Name (BT-27) - Required
        name = ET.SubElement(seller, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}Name')
        name.text = data.get('rechnungsaussteller', 'Unbekannter Aussteller')
        
        # Tax Registration - Steuernummer (BT-32)
        if data.get('steuernummer'):
            tax_reg = ET.SubElement(seller, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTaxRegistration')
            tax_id = ET.SubElement(tax_reg, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ID')
            tax_id.set('schemeID', 'FC')  # Fiscal Code / Steuernummer
            tax_id.text = data.get('steuernummer')
        
        # Tax Registration - USt-IdNr (BT-31)
        if data.get('ust_idnr'):
            tax_reg = ET.SubElement(seller, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTaxRegistration')
            tax_id = ET.SubElement(tax_reg, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ID')
            tax_id.set('schemeID', 'VA')  # VAT Registration
            tax_id.text = data.get('ust_idnr')
        
        # Address (BG-5) - Required
        addr = data.get('_seller_addr', {})
        self._add_structured_address(seller, addr)
    
    def _add_buyer(self, parent: ET.Element, data: Dict):
        """Fügt Käufer-Informationen hinzu (BG-7)"""
        buyer = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BuyerTradeParty')
        
        # Name (BT-44) - Required
        name = ET.SubElement(buyer, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}Name')
        buyer_name = data.get('rechnungsempfänger', data.get('rechnungsempfaenger', 'Unbekannter Empfänger'))
        name.text = buyer_name
        
        # Address (BG-8)
        addr = data.get('_buyer_addr', {})
        self._add_structured_address(buyer, addr)
    
    def _add_structured_address(self, parent: ET.Element, addr: Dict):
        """Fügt strukturierte Adresse hinzu (BG-5 / BG-8)"""
        addr_elem = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}PostalTradeAddress')
        
        # Postcode (BT-38 / BT-53)
        if addr.get('postcode'):
            postcode = ET.SubElement(addr_elem, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}PostcodeCode')
            postcode.text = addr['postcode']
        
        # Street (BT-35 / BT-50)
        if addr.get('street'):
            line = ET.SubElement(addr_elem, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}LineOne')
            line.text = addr['street']
        elif addr.get('raw'):
            # Fallback: use raw address
            line = ET.SubElement(addr_elem, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}LineOne')
            line.text = addr['raw']
        
        # City (BT-37 / BT-52)
        if addr.get('city'):
            city = ET.SubElement(addr_elem, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}CityName')
            city.text = addr['city']
        
        # Country Code (BT-40 / BT-55) - Required
        country = ET.SubElement(addr_elem, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}CountryID')
        country.text = addr.get('country_code', 'DE')
    
    def _add_payment_means(self, parent: ET.Element, data: Dict):
        """Fügt Zahlungsinformationen hinzu (BG-16)"""
        payment = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradeSettlementPaymentMeans')
        
        # Type Code (BT-81)
        type_code = ET.SubElement(payment, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TypeCode')
        
        # Determine payment type
        if data.get('iban'):
            type_code.text = '58'  # SEPA Credit Transfer
        else:
            type_code.text = '1'  # Instrument not defined
        
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
    
    def _add_payment_terms(self, parent: ET.Element, data: Dict):
        """Fügt Zahlungsbedingungen hinzu (BT-9 / BT-20)"""
        # Due Date (BT-9)
        if data.get('faelligkeitsdatum'):
            terms = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradePaymentTerms')
            due_date = ET.SubElement(terms, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}DueDateDateTime')
            date_str = ET.SubElement(due_date, '{urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100}DateTimeString')
            date_str.set('format', '102')
            date_str.text = self._format_date(data.get('faelligkeitsdatum'))
        elif data.get('zahlungsziel_tage'):
            # Calculate due date from invoice date
            terms = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradePaymentTerms')
            desc = ET.SubElement(terms, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}Description')
            desc.text = f"Zahlbar innerhalb von {data.get('zahlungsziel_tage')} Tagen"
    
    def _add_tax(self, parent: ET.Element, data: Dict):
        """Fügt Steuer-Informationen hinzu (BG-23)"""
        tax = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableTradeTax')
        
        mwst_betrag = data.get('mwst_betrag', 0)
        betrag_netto = data.get('betrag_netto', 0)
        mwst_satz = data.get('mwst_satz', 19)
        
        # Tax Amount (BT-117)
        amount = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}CalculatedAmount')
        amount.text = f"{mwst_betrag:.2f}"
        
        # Tax Type Code (BT-118)
        type_code = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TypeCode')
        type_code.text = 'VAT'
        
        # Tax Category Code (BT-118-0)
        cat_code = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}CategoryCode')
        if mwst_satz == 0:
            cat_code.text = 'Z'  # Zero rated
        elif mwst_satz == 7:
            cat_code.text = 'S'  # Standard (reduced)
        else:
            cat_code.text = 'S'  # Standard
        
        # Taxable Amount (BT-116)
        basis = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BasisAmount')
        basis.text = f"{betrag_netto:.2f}"
        
        # Tax Rate (BT-119)
        rate = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}RateApplicablePercent')
        rate.text = f"{mwst_satz:.1f}"
    
    def _add_monetary_summation(self, parent: ET.Element, data: Dict):
        """Fügt Summen hinzu (BG-22)"""
        summation = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradeSettlementHeaderMonetarySummation')
        
        betrag_netto = data.get('betrag_netto', 0)
        mwst_betrag = data.get('mwst_betrag', 0)
        betrag_brutto = data.get('betrag_brutto', 0)
        currency = data.get('waehrung', 'EUR')
        
        # Line Total (BT-106)
        line_total = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}LineTotalAmount')
        line_total.text = f"{betrag_netto:.2f}"
        
        # Tax Basis (BT-109)
        tax_basis = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TaxBasisTotalAmount')
        tax_basis.text = f"{betrag_netto:.2f}"
        
        # Tax Total (BT-110)
        tax_total = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TaxTotalAmount')
        tax_total.set('currencyID', currency)
        tax_total.text = f"{mwst_betrag:.2f}"
        
        # Grand Total (BT-112)
        grand_total = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}GrandTotalAmount')
        grand_total.text = f"{betrag_brutto:.2f}"
        
        # Due Payable (BT-115)
        due = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}DuePayableAmount')
        due.text = f"{betrag_brutto:.2f}"
    
    def _add_line_item(self, parent: ET.Element, item: Dict, data: Dict):
        """Fügt Rechnungsposition hinzu (BG-25)"""
        line = ET.SubElement(parent, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}IncludedSupplyChainTradeLineItem')
        
        # Line ID (BT-126) - Required
        doc = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}AssociatedDocumentLineDocument')
        line_id = ET.SubElement(doc, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}LineID')
        line_id.text = str(item.get('position', 1))
        
        # Product (BG-31)
        product = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradeProduct')
        name = ET.SubElement(product, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}Name')
        name.text = item.get('beschreibung', 'Artikel/Dienstleistung')
        
        # Agreement - Net Price (BT-146)
        agreement = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedLineTradeAgreement')
        price = ET.SubElement(agreement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}NetPriceProductTradePrice')
        charge = ET.SubElement(price, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ChargeAmount')
        # IMPORTANT: Net price must be NETTO, not Brutto!
        netto_preis = item.get('einzelpreis_netto', item.get('einzelpreis', 0))
        charge.text = f"{float(netto_preis):.2f}"
        
        # Delivery - Quantity (BT-129)
        delivery = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedLineTradeDelivery')
        qty = ET.SubElement(delivery, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}BilledQuantity')
        qty.set('unitCode', item.get('einheit', 'C62'))  # C62 = Unit/Stück
        qty.text = str(item.get('menge', 1))
        
        # Settlement
        settlement = ET.SubElement(line, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedLineTradeSettlement')
        
        # Line Tax (BG-30)
        mwst_satz = data.get('mwst_satz', 19)
        tax = ET.SubElement(settlement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}ApplicableTradeTax')
        tax_type = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}TypeCode')
        tax_type.text = 'VAT'
        tax_cat = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}CategoryCode')
        tax_cat.text = 'S' if mwst_satz > 0 else 'Z'
        tax_rate = ET.SubElement(tax, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}RateApplicablePercent')
        tax_rate.text = f"{mwst_satz:.0f}"
        
        # Line Total (BT-131) - Must be NETTO!
        summation = ET.SubElement(settlement, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}SpecifiedTradeSettlementLineMonetarySummation')
        total = ET.SubElement(summation, '{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}LineTotalAmount')
        netto_gesamt = item.get('gesamt_netto', item.get('gesamt', 0))
        total.text = f"{float(netto_gesamt):.2f}"
    
    def _format_date(self, date_str: str) -> str:
        """Konvertiert Datum zu YYYYMMDD"""
        if not date_str:
            return datetime.now().strftime('%Y%m%d')
        
        # Versuche verschiedene Formate
        for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y%m%d']:
            try:
                dt = datetime.strptime(str(date_str).strip(), fmt)
                return dt.strftime('%Y%m%d')
            except ValueError:
                continue
        
        return datetime.now().strftime('%Y%m%d')


def generate_xrechnung(invoice_data: Dict[str, Any], pretty_print: bool = False) -> str:
    """
    Generiert XRechnung XML aus Invoice-Daten.
    
    Args:
        invoice_data: Extrahierte Rechnungsdaten
        pretty_print: XML formatiert ausgeben
        
    Returns:
        XML-String im XRechnung-Format (EN16931 / CII)
    """
    generator = XRechnungGenerator(pretty_print=pretty_print)
    return generator.generate(invoice_data)


def validate_xrechnung(xml_string: str) -> Tuple[bool, List[str], str]:
    """
    Validiert XRechnung/ZUGFeRD XML.
    
    Args:
        xml_string: XML zu validieren
        
    Returns:
        Tuple[is_valid, list_of_issues, detected_profile]
    """
    xml = (xml_string or "").strip()
    if not xml:
        return False, ["Kein XML übergeben"], ""
    
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        return False, [f"XML Parse-Fehler: {e}"], ""
    
    text_lower = xml.lower()
    profile = ""
    issues = []
    warnings = []
    
    # Profile Detection
    if 'xrechnung' in text_lower or 'urn:cen.eu:en16931' in text_lower:
        profile = "XRechnung 3.0"
    elif 'zugferd' in text_lower or 'factur-x' in text_lower:
        profile = "ZUGFeRD/Factur-X"
    elif 'crossindustryinvoice' in root.tag.lower():
        profile = "CII (Cross Industry Invoice)"
    
    # Required Elements Check
    required_checks = [
        ('ExchangedDocument', 'Rechnungskopf (ExchangedDocument)'),
        ('SupplyChainTradeTransaction', 'Transaktionsdaten (SupplyChainTradeTransaction)'),
        ('SellerTradeParty', 'Verkäufer (BG-4)'),
        ('BuyerTradeParty', 'Käufer (BG-7)'),
        ('InvoiceCurrencyCode', 'Währung (BT-5)'),
        ('GrandTotalAmount', 'Gesamtbetrag (BT-112)'),
    ]
    
    for elem, desc in required_checks:
        if elem.lower() not in xml.lower():
            issues.append(f"Fehlendes Pflichtfeld: {desc}")
    
    # Business Rule Checks
    # BT-1: Invoice Number
    if '<ram:ID>' not in xml:
        issues.append("Rechnungsnummer (BT-1) fehlt")
    
    # BT-2: Issue Date
    if '<udt:DateTimeString' not in xml:
        issues.append("Rechnungsdatum (BT-2) fehlt")
    
    # Check for proper seller identification
    if 'SpecifiedTaxRegistration' not in xml:
        warnings.append("Warnung: Keine Steuer-ID des Verkäufers (BT-31/BT-32)")
    
    # Check for line items
    if 'IncludedSupplyChainTradeLineItem' not in xml:
        issues.append("Mindestens eine Rechnungsposition (BG-25) erforderlich")
    
    all_issues = issues + warnings
    is_valid = len(issues) == 0
    
    return is_valid, all_issues, profile


def export_xrechnung_file(invoice_data: Dict[str, Any], output_dir: str = "output", pretty_print: bool = True) -> str:
    """
    Exportiert XRechnung als XML-Datei.
    
    Args:
        invoice_data: Rechnungsdaten
        output_dir: Ausgabeverzeichnis
        pretty_print: XML formatiert
        
    Returns:
        Pfad zur erstellten Datei
    """
    Path(output_dir).mkdir(exist_ok=True)
    
    xml_content = generate_xrechnung(invoice_data, pretty_print=pretty_print)
    
    # Validate before saving
    is_valid, issues, profile = validate_xrechnung(xml_content)
    if not is_valid:
        logger.warning(f"XRechnung Validierung: {issues}")
    
    # Filename
    invoice_nr = str(invoice_data.get('rechnungsnummer', 'unknown')).replace('/', '-').replace('\\', '-')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"xrechnung_{invoice_nr}_{timestamp}.xml"
    
    filepath = Path(output_dir) / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    logger.info(f"XRechnung exportiert: {filepath} ({profile})")
    return str(filepath)


# Convenience alias
XRechnung = XRechnungGenerator
