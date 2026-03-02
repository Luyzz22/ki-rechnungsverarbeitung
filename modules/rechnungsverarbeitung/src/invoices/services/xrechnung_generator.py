"""XRechnung Generator – EN16931-compliant outgoing invoices.

Generates UBL 2.1 XML invoices conforming to:
- EN16931 (European e-invoicing standard)
- XRechnung 3.0.2 (German CIUS)
- Leitweg-ID routing for public sector

Output: Valid XML ready for KoSIT validation and Peppol transmission.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring, indent


# UBL 2.1 Namespaces
NS = {
    "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}

XRECHNUNG_CUSTOMIZATION = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
XRECHNUNG_PROFILE = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"


@dataclass
class Party:
    """Invoice party (seller or buyer)."""
    name: str
    street: str = ""
    city: str = ""
    postal_code: str = ""
    country_code: str = "DE"
    vat_id: str = ""
    tax_id: str = ""
    email: str = ""
    leitweg_id: str = ""


@dataclass
class LineItem:
    """Invoice line item."""
    description: str
    quantity: float = 1.0
    unit_code: str = "C62"  # piece
    unit_price: float = 0.0
    vat_percent: float = 19.0
    item_id: str = ""


@dataclass
class InvoiceData:
    """Complete invoice data for XRechnung generation."""
    invoice_number: str
    issue_date: date
    due_date: date
    seller: Party
    buyer: Party
    line_items: list[LineItem] = field(default_factory=list)
    currency: str = "EUR"
    note: str = ""
    payment_reference: str = ""
    iban: str = ""
    bic: str = ""
    bank_name: str = ""


class XRechnungGenerator:
    """Generates EN16931/XRechnung 3.0 compliant UBL 2.1 XML.

    Usage:
        gen = XRechnungGenerator(output_dir="./exports/xrechnung")
        path, xml_hash = gen.generate(invoice_data)
    """

    def __init__(self, output_dir: str = "./exports/xrechnung") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, data: InvoiceData) -> tuple[Path, str]:
        """Generate XRechnung XML file.

        Returns:
            Tuple of (file_path, sha256_hash).
        """
        root = self._build_xml(data)
        indent(root, space="  ")

        xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode").encode("utf-8")
        xml_hash = hashlib.sha256(xml_bytes).hexdigest()

        filename = f"XR-{data.invoice_number}-{data.issue_date.isoformat()}.xml"
        filepath = self.output_dir / filename
        filepath.write_bytes(xml_bytes)

        return filepath, xml_hash

    def _build_xml(self, data: InvoiceData) -> Element:
        """Build UBL 2.1 Invoice XML tree."""
        # Register namespaces
        for prefix, uri in NS.items():
            if prefix:
                Element(f"{{{uri}}}dummy")

        root = Element("Invoice")
        root.set("xmlns", NS[""])
        root.set("xmlns:cac", NS["cac"])
        root.set("xmlns:cbc", NS["cbc"])

        # BT-24: CustomizationID
        self._cbc(root, "CustomizationID", XRECHNUNG_CUSTOMIZATION)
        # BT-23: ProfileID
        self._cbc(root, "ProfileID", XRECHNUNG_PROFILE)
        # BT-1: Invoice number
        self._cbc(root, "ID", data.invoice_number)
        # BT-2: Issue date
        self._cbc(root, "IssueDate", data.issue_date.isoformat())
        # BT-9: Due date
        self._cbc(root, "DueDate", data.due_date.isoformat())
        # BT-3: Invoice type (380 = Commercial invoice)
        self._cbc(root, "InvoiceTypeCode", "380")
        # BT-22: Note
        if data.note:
            self._cbc(root, "Note", data.note)
        # BT-5: Currency
        self._cbc(root, "DocumentCurrencyCode", data.currency)
        # BT-10: Buyer reference / Leitweg-ID
        if data.buyer.leitweg_id:
            self._cbc(root, "BuyerReference", data.buyer.leitweg_id)

        # Seller (BG-4)
        self._add_party(root, "AccountingSupplierParty", data.seller)
        # Buyer (BG-7)
        self._add_party(root, "AccountingCustomerParty", data.buyer)

        # Payment means (BG-16)
        if data.iban:
            pm = SubElement(root, f"{{{NS['cac']}}}PaymentMeans")
            self._cbc(pm, "PaymentMeansCode", "58")  # SEPA
            if data.payment_reference:
                self._cbc(pm, "PaymentID", data.payment_reference)
            payee = SubElement(pm, f"{{{NS['cac']}}}PayeeFinancialAccount")
            self._cbc(payee, "ID", data.iban)
            if data.bic:
                branch = SubElement(payee, f"{{{NS['cac']}}}FinancialInstitutionBranch")
                self._cbc(branch, "ID", data.bic)

        # Tax totals and line items
        net_total = sum(item.quantity * item.unit_price for item in data.line_items)
        vat_total = sum(item.quantity * item.unit_price * item.vat_percent / 100 for item in data.line_items)
        gross_total = net_total + vat_total

        # Tax total (BG-22)
        tax_total = SubElement(root, f"{{{NS['cac']}}}TaxTotal")
        ta = self._cbc(tax_total, "TaxAmount", f"{vat_total:.2f}")
        ta.set("currencyID", data.currency)

        # Group by VAT rate
        vat_groups: dict[float, float] = {}
        for item in data.line_items:
            base = item.quantity * item.unit_price
            vat_groups[item.vat_percent] = vat_groups.get(item.vat_percent, 0) + base

        for rate, base in vat_groups.items():
            subtotal = SubElement(tax_total, f"{{{NS['cac']}}}TaxSubtotal")
            tb = self._cbc(subtotal, "TaxableAmount", f"{base:.2f}")
            tb.set("currencyID", data.currency)
            tv = self._cbc(subtotal, "TaxAmount", f"{base * rate / 100:.2f}")
            tv.set("currencyID", data.currency)
            cat = SubElement(subtotal, f"{{{NS['cac']}}}TaxCategory")
            self._cbc(cat, "ID", "S")
            self._cbc(cat, "Percent", f"{rate:.1f}")
            scheme = SubElement(cat, f"{{{NS['cac']}}}TaxScheme")
            self._cbc(scheme, "ID", "VAT")

        # Legal monetary totals (BG-22)
        totals = SubElement(root, f"{{{NS['cac']}}}LegalMonetaryTotal")
        le = self._cbc(totals, "LineExtensionAmount", f"{net_total:.2f}")
        le.set("currencyID", data.currency)
        te = self._cbc(totals, "TaxExclusiveAmount", f"{net_total:.2f}")
        te.set("currencyID", data.currency)
        ti = self._cbc(totals, "TaxInclusiveAmount", f"{gross_total:.2f}")
        ti.set("currencyID", data.currency)
        pa = self._cbc(totals, "PayableAmount", f"{gross_total:.2f}")
        pa.set("currencyID", data.currency)

        # Invoice lines (BG-25)
        for i, item in enumerate(data.line_items, 1):
            self._add_line(root, i, item, data.currency)

        return root

    def _add_party(self, parent: Element, tag: str, party: Party) -> None:
        """Add AccountingSupplierParty or AccountingCustomerParty."""
        wrapper = SubElement(parent, f"{{{NS['cac']}}}{tag}")
        p = SubElement(wrapper, f"{{{NS['cac']}}}Party")

        if party.email:
            contact = SubElement(p, f"{{{NS['cac']}}}EndpointID")
            contact.text = party.email
            contact.set("schemeID", "EM")

        name_el = SubElement(p, f"{{{NS['cac']}}}PartyName")
        self._cbc(name_el, "Name", party.name)

        if party.street or party.city:
            addr = SubElement(p, f"{{{NS['cac']}}}PostalAddress")
            if party.street:
                self._cbc(addr, "StreetName", party.street)
            if party.city:
                self._cbc(addr, "CityName", party.city)
            if party.postal_code:
                self._cbc(addr, "PostalZone", party.postal_code)
            country = SubElement(addr, f"{{{NS['cac']}}}Country")
            self._cbc(country, "IdentificationCode", party.country_code)

        if party.vat_id:
            tax_scheme = SubElement(p, f"{{{NS['cac']}}}PartyTaxScheme")
            self._cbc(tax_scheme, "CompanyID", party.vat_id)
            scheme = SubElement(tax_scheme, f"{{{NS['cac']}}}TaxScheme")
            self._cbc(scheme, "ID", "VAT")

        legal = SubElement(p, f"{{{NS['cac']}}}PartyLegalEntity")
        self._cbc(legal, "RegistrationName", party.name)

    def _add_line(self, root: Element, line_id: int, item: LineItem, currency: str) -> None:
        """Add InvoiceLine."""
        line = SubElement(root, f"{{{NS['cac']}}}InvoiceLine")
        self._cbc(line, "ID", str(line_id))

        qty = self._cbc(line, "InvoicedQuantity", f"{item.quantity:.2f}")
        qty.set("unitCode", item.unit_code)

        amount = item.quantity * item.unit_price
        la = self._cbc(line, "LineExtensionAmount", f"{amount:.2f}")
        la.set("currencyID", currency)

        # Item
        inv_item = SubElement(line, f"{{{NS['cac']}}}Item")
        self._cbc(inv_item, "Description", item.description)
        self._cbc(inv_item, "Name", item.description[:80])

        tax_cat = SubElement(inv_item, f"{{{NS['cac']}}}ClassifiedTaxCategory")
        self._cbc(tax_cat, "ID", "S")
        self._cbc(tax_cat, "Percent", f"{item.vat_percent:.1f}")
        scheme = SubElement(tax_cat, f"{{{NS['cac']}}}TaxScheme")
        self._cbc(scheme, "ID", "VAT")

        # Price
        price = SubElement(line, f"{{{NS['cac']}}}Price")
        pa = self._cbc(price, "PriceAmount", f"{item.unit_price:.2f}")
        pa.set("currencyID", currency)

    @staticmethod
    def _cbc(parent: Element, tag: str, text: str) -> Element:
        """Add a cbc: element."""
        el = SubElement(parent, f"{{{NS['cbc']}}}{tag}")
        el.text = text
        return el
