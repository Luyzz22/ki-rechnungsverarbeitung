"""XRechnung / ZUGFeRD Generator for BelegFlow AI.

Generates EN 16931-compliant e-invoices in XRechnung (UBL 2.1) format
from extracted invoice data. Required for the E-Rechnungspflicht 2027.

Output: Valid XML conforming to XRechnung 3.0 / EN 16931.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, date
from typing import Any, Optional
from xml.etree.ElementTree import Element, SubElement, tostring

logger = logging.getLogger(__name__)

# XRechnung UBL 2.1 Namespaces
NS = {
    "ubl": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


class XRechnungGenerator:
    """Generates XRechnung-compliant UBL 2.1 invoices."""

    def generate(self, invoice_data: dict[str, Any], seller: dict | None = None, buyer: dict | None = None) -> str:
        """Generate XRechnung XML from invoice data.

        Args:
            invoice_data: Extracted invoice fields (supplier, amounts, dates, line_items)
            seller: Seller info override {name, street, city, zip, country, vat_id, iban}
            buyer: Buyer info override {name, street, city, zip, country, vat_id}

        Returns:
            XML string conforming to XRechnung 3.0
        """
        # Build seller from invoice data if not provided
        if not seller:
            seller = {
                "name": invoice_data.get("supplier", "Unbekannter Lieferant"),
                "street": "",
                "city": "",
                "zip": "",
                "country": "DE",
                "vat_id": "",
                "iban": invoice_data.get("iban", ""),
            }

        if not buyer:
            buyer = {
                "name": "SBS Deutschland GmbH & Co. KG",
                "street": "",
                "city": "Heidelberg",
                "zip": "69115",
                "country": "DE",
                "vat_id": "",
            }

        inv_number = invoice_data.get("invoice_number", f"BF-{uuid.uuid4().hex[:8].upper()}")
        inv_date = invoice_data.get("invoice_date", date.today().isoformat())
        due_date = invoice_data.get("due_date")
        currency = invoice_data.get("currency", "EUR")
        total_net = invoice_data.get("total_amount_net", 0) or 0
        tax_amount = invoice_data.get("tax_amount", 0) or 0
        total_gross = invoice_data.get("total_amount_gross") or invoice_data.get("total_amount", 0) or 0
        tax_rate = invoice_data.get("tax_rate", 19) or 19
        line_items = invoice_data.get("line_items", []) or []

        # If no net amount, calculate from gross
        if not total_net and total_gross:
            total_net = round(total_gross / (1 + tax_rate / 100), 2)
            tax_amount = round(total_gross - total_net, 2)

        root = Element("{%s}Invoice" % NS["ubl"])
        root.set("xmlns", NS["ubl"])
        root.set("xmlns:cac", NS["cac"])
        root.set("xmlns:cbc", NS["cbc"])

        # Customization + Profile
        SubElement(root, "{%s}CustomizationID" % NS["cbc"]).text = (
            "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
        )
        SubElement(root, "{%s}ProfileID" % NS["cbc"]).text = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

        # Invoice Number + Dates
        SubElement(root, "{%s}ID" % NS["cbc"]).text = inv_number
        SubElement(root, "{%s}IssueDate" % NS["cbc"]).text = str(inv_date)[:10]
        if due_date:
            SubElement(root, "{%s}DueDate" % NS["cbc"]).text = str(due_date)[:10]
        SubElement(root, "{%s}InvoiceTypeCode" % NS["cbc"]).text = "380"
        SubElement(root, "{%s}DocumentCurrencyCode" % NS["cbc"]).text = currency

        # Buyer Reference (Leitweg-ID for public sector, otherwise generic)
        SubElement(root, "{%s}BuyerReference" % NS["cbc"]).text = "BF-BUYER-REF"

        # Seller (AccountingSupplierParty)
        self._add_party(root, "AccountingSupplierParty", seller)

        # Buyer (AccountingCustomerParty)
        self._add_party(root, "AccountingCustomerParty", buyer)

        # Payment Means
        if seller.get("iban"):
            pm = SubElement(root, "{%s}PaymentMeans" % NS["cac"])
            SubElement(pm, "{%s}PaymentMeansCode" % NS["cbc"]).text = "58"
            payee = SubElement(pm, "{%s}PayeeFinancialAccount" % NS["cac"])
            SubElement(payee, "{%s}ID" % NS["cbc"]).text = seller["iban"]

        # Tax Total
        tt = SubElement(root, "{%s}TaxTotal" % NS["cac"])
        ta = SubElement(tt, "{%s}TaxAmount" % NS["cbc"])
        ta.text = f"{tax_amount:.2f}"
        ta.set("currencyID", currency)

        ts = SubElement(tt, "{%s}TaxSubtotal" % NS["cac"])
        tb = SubElement(ts, "{%s}TaxableAmount" % NS["cbc"])
        tb.text = f"{total_net:.2f}"
        tb.set("currencyID", currency)
        ta2 = SubElement(ts, "{%s}TaxAmount" % NS["cbc"])
        ta2.text = f"{tax_amount:.2f}"
        ta2.set("currencyID", currency)
        tc = SubElement(ts, "{%s}TaxCategory" % NS["cac"])
        SubElement(tc, "{%s}ID" % NS["cbc"]).text = "S"
        SubElement(tc, "{%s}Percent" % NS["cbc"]).text = str(int(tax_rate))
        SubElement(tc, "{%s}TaxScheme" % NS["cac"]).append(
            self._text_elem("{%s}ID" % NS["cbc"], "VAT")
        )

        # Legal Monetary Total
        lmt = SubElement(root, "{%s}LegalMonetaryTotal" % NS["cac"])
        for tag, val in [
            ("LineExtensionAmount", total_net),
            ("TaxExclusiveAmount", total_net),
            ("TaxInclusiveAmount", total_gross),
            ("PayableAmount", total_gross),
        ]:
            el = SubElement(lmt, "{%s}%s" % (NS["cbc"], tag))
            el.text = f"{val:.2f}"
            el.set("currencyID", currency)

        # Invoice Lines
        if line_items:
            for idx, item in enumerate(line_items, 1):
                self._add_line(root, idx, item, currency, tax_rate)
        else:
            # Single line from total
            self._add_line(root, 1, {
                "description": invoice_data.get("supplier", "Lieferung/Leistung"),
                "quantity": 1,
                "unit_price": total_net,
                "total": total_net,
            }, currency, tax_rate)

        xml_str = tostring(root, encoding="unicode", xml_declaration=False)
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

        logger.info(f"xrechnung_generated: {inv_number} | {total_gross} {currency}")
        return xml_str

    def _add_party(self, root: Element, party_type: str, info: dict) -> None:
        party_wrapper = SubElement(root, "{%s}%s" % (NS["cac"], party_type))
        party = SubElement(party_wrapper, "{%s}Party" % NS["cac"])

        if info.get("name"):
            pn = SubElement(party, "{%s}PartyName" % NS["cac"])
            SubElement(pn, "{%s}Name" % NS["cbc"]).text = info["name"]

        addr = SubElement(party, "{%s}PostalAddress" % NS["cac"])
        if info.get("street"):
            SubElement(addr, "{%s}StreetName" % NS["cbc"]).text = info["street"]
        if info.get("city"):
            SubElement(addr, "{%s}CityName" % NS["cbc"]).text = info["city"]
        if info.get("zip"):
            SubElement(addr, "{%s}PostalZone" % NS["cbc"]).text = info["zip"]
        country = SubElement(addr, "{%s}Country" % NS["cac"])
        SubElement(country, "{%s}IdentificationCode" % NS["cbc"]).text = info.get("country", "DE")

        if info.get("vat_id"):
            pts = SubElement(party, "{%s}PartyTaxScheme" % NS["cac"])
            SubElement(pts, "{%s}CompanyID" % NS["cbc"]).text = info["vat_id"]
            SubElement(pts, "{%s}TaxScheme" % NS["cac"]).append(
                self._text_elem("{%s}ID" % NS["cbc"], "VAT")
            )

        ple = SubElement(party, "{%s}PartyLegalEntity" % NS["cac"])
        SubElement(ple, "{%s}RegistrationName" % NS["cbc"]).text = info.get("name", "")

    def _add_line(self, root: Element, idx: int, item: dict, currency: str, tax_rate: float) -> None:
        line = SubElement(root, "{%s}InvoiceLine" % NS["cac"])
        SubElement(line, "{%s}ID" % NS["cbc"]).text = str(idx)

        qty = SubElement(line, "{%s}InvoicedQuantity" % NS["cbc"])
        qty.text = str(item.get("quantity", 1))
        qty.set("unitCode", "C62")

        lea = SubElement(line, "{%s}LineExtensionAmount" % NS["cbc"])
        lea.text = f"{item.get('total', 0):.2f}"
        lea.set("currencyID", currency)

        i = SubElement(line, "{%s}Item" % NS["cac"])
        SubElement(i, "{%s}Name" % NS["cbc"]).text = item.get("description", "Position")[:100]

        ctc = SubElement(i, "{%s}ClassifiedTaxCategory" % NS["cac"])
        SubElement(ctc, "{%s}ID" % NS["cbc"]).text = "S"
        SubElement(ctc, "{%s}Percent" % NS["cbc"]).text = str(int(tax_rate))
        SubElement(ctc, "{%s}TaxScheme" % NS["cac"]).append(
            self._text_elem("{%s}ID" % NS["cbc"], "VAT")
        )

        price = SubElement(line, "{%s}Price" % NS["cac"])
        pa = SubElement(price, "{%s}PriceAmount" % NS["cbc"])
        pa.text = f"{item.get('unit_price', item.get('total', 0)):.2f}"
        pa.set("currencyID", currency)

    @staticmethod
    def _text_elem(tag: str, text: str) -> Element:
        el = Element(tag)
        el.text = text
        return el
