"""KoSIT XRechnung Validator.

Validates generated XRechnung XML against:
1. XML well-formedness
2. EN 16931 structural requirements
3. XRechnung business rules (BR-DE)

Uses lxml for XML parsing and custom validation rules.
For production: integrate with KoSIT Prüftool (Java) or use
the PEPPOL validation service.
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from lxml import etree

logger = logging.getLogger(__name__)

NS = {
    "ubl": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }


@dataclass
class KositValidationResult:
    status: str
    errors: list[str]
    warnings: list[str]
    engine: str
    config_version: str
    raw_output: str


class KoSITValidator:
    """Validates XRechnung XML documents."""

    def __init__(
        self,
        binary: str = "kosit-validator",
        timeout_seconds: int = 10,
        config_version: str = "xrechnung-3.0.1",
    ) -> None:
        self.binary = binary
        self.timeout_seconds = timeout_seconds
        self.config_version = config_version

    def validate(self, xml_content: str | bytes) -> ValidationResult:
        result = ValidationResult()

        # 1. XML Well-formedness
        try:
            if isinstance(xml_content, str):
                xml_content = xml_content.encode("utf-8")
            tree = etree.fromstring(xml_content)
        except etree.XMLSyntaxError as e:
            result.valid = False
            result.errors.append(f"XML Syntax Error: {e}")
            return result

        result.info["root_tag"] = tree.tag

        # 2. Namespace check
        if "Invoice" not in tree.tag:
            result.valid = False
            result.errors.append(f"Root element must be Invoice, got: {tree.tag}")
            return result

        # 3. Required fields (EN 16931 / XRechnung)
        required_checks = [
            ("BT-1", ".//cbc:ID", "Invoice Number"),
            ("BT-2", ".//cbc:IssueDate", "Issue Date"),
            ("BT-3", ".//cbc:InvoiceTypeCode", "Invoice Type Code"),
            ("BT-5", ".//cbc:DocumentCurrencyCode", "Currency Code"),
            ("BT-10", ".//cbc:BuyerReference", "Buyer Reference (Leitweg-ID)"),
            ("BT-27", ".//cac:AccountingSupplierParty//cbc:Name", "Seller Name"),
            ("BT-44", ".//cac:AccountingCustomerParty//cbc:Name", "Buyer Name"),
            ("BT-112", ".//cac:LegalMonetaryTotal/cbc:PayableAmount", "Payable Amount"),
        ]

        # Register namespaces for XPath
        nsmap = {"cbc": NS["cbc"], "cac": NS["cac"]}

        for bt_id, xpath, label in required_checks:
            elements = tree.xpath(xpath, namespaces=nsmap)
            if not elements:
                result.valid = False
                result.errors.append(f"{bt_id}: Missing required field '{label}'")
            else:
                text = elements[0].text or ""
                if not text.strip():
                    result.warnings.append(f"{bt_id}: Field '{label}' is empty")
                else:
                    result.info[bt_id] = text.strip()

        # 4. XRechnung-specific (BR-DE rules)
        # BR-DE-1: CustomizationID must contain xrechnung
        cust = tree.xpath(".//cbc:CustomizationID", namespaces=nsmap)
        if cust and "xrechnung" in (cust[0].text or "").lower():
            result.info["xrechnung_version"] = cust[0].text
        else:
            result.warnings.append("BR-DE-1: CustomizationID should reference XRechnung")

        # BR-DE-15: BuyerReference is mandatory
        buyer_ref = tree.xpath(".//cbc:BuyerReference", namespaces=nsmap)
        if not buyer_ref or not (buyer_ref[0].text or "").strip():
            result.errors.append("BR-DE-15: BuyerReference (Leitweg-ID) is mandatory for XRechnung")
            result.valid = False

        # 5. Invoice Lines check
        lines = tree.xpath(".//cac:InvoiceLine", namespaces=nsmap)
        if not lines:
            result.valid = False
            result.errors.append("BG-25: At least one InvoiceLine is required")
        else:
            result.info["line_count"] = len(lines)

        # 6. Tax validation
        tax_total = tree.xpath(".//cac:TaxTotal/cbc:TaxAmount", namespaces=nsmap)
        if tax_total:
            result.info["tax_amount"] = tax_total[0].text

        # 7. Date format validation
        issue_date = tree.xpath(".//cbc:IssueDate", namespaces=nsmap)
        if issue_date:
            date_text = issue_date[0].text or ""
            if not re.match(r"\d{4}-\d{2}-\d{2}", date_text):
                result.errors.append(f"BT-2: IssueDate format must be YYYY-MM-DD, got: {date_text}")
                result.valid = False

        logger.info(f"kosit_validation: valid={result.valid} errors={len(result.errors)} warnings={len(result.warnings)}")
        return result

    def validate_file(self, invoice_path: str | Path, report_dir: str | Path) -> KositValidationResult:
        """
        Validate XML file via KoSIT binary when available.
        Falls back to warning-mode when validator binary is not installed.
        """
        invoice_path = Path(invoice_path)
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        if shutil.which(self.binary) is None:
            return KositValidationResult(
                status="warning",
                errors=[],
                warnings=[f"KoSIT validator binary '{self.binary}' not found; fallback mode active."],
                engine="kosit-fallback",
                config_version=self.config_version,
                raw_output="",
            )

        cmd = [
            self.binary,
            "--input",
            str(invoice_path),
            "--output",
            str(report_dir),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return KositValidationResult(
                status="failed",
                errors=[f"KoSIT validation timed out after {self.timeout_seconds}s"],
                warnings=[],
                engine="kosit",
                config_version=self.config_version,
                raw_output="",
            )

        raw_output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        if proc.returncode == 0:
            return KositValidationResult(
                status="passed",
                errors=[],
                warnings=[],
                engine="kosit",
                config_version=self.config_version,
                raw_output=raw_output.strip(),
            )

        errors = [line.strip() for line in (proc.stderr or "").splitlines() if line.strip()] or ["KoSIT validation failed"]
        return KositValidationResult(
            status="failed",
            errors=errors,
            warnings=[],
            engine="kosit",
            config_version=self.config_version,
            raw_output=raw_output.strip(),
        )

# Backward compatibility alias
KositValidator = KoSITValidator
