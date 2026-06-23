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
import os
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
        service_url: str | None = None,
        service_connect_timeout: float = 5.0,
    ) -> None:
        self.binary = binary
        self.timeout_seconds = timeout_seconds
        self.config_version = config_version
        # Echtes KoSIT-Prüftool im Daemon-Modus (validationtool -D) per HTTP.
        # Default aus Umgebung (docker-compose/Server setzt KOSIT_VALIDATOR_URL).
        self.service_url = service_url if service_url is not None else os.environ.get("KOSIT_VALIDATOR_URL")
        # Strikter Connect-Timeout → bei Nichterreichbarkeit schneller, sauberer Fallback.
        try:
            self.service_connect_timeout = float(
                os.environ.get("KOSIT_VALIDATOR_CONNECT_TIMEOUT", service_connect_timeout)
            )
        except (TypeError, ValueError):
            self.service_connect_timeout = service_connect_timeout

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

        # 1) Bevorzugt: echtes KoSIT-Prüftool über HTTP-Daemon (KOSIT_VALIDATOR_URL).
        #    Bei Nichterreichbarkeit/Timeout -> None -> sauberer Fallback unten.
        if self.service_url:
            try:
                xml_bytes = invoice_path.read_bytes()
            except OSError as exc:
                logger.warning("kosit: could not read invoice for service call: %s", exc)
                xml_bytes = None
            if xml_bytes is not None:
                svc = self._validate_via_service(xml_bytes, self.service_url)
                if svc is not None:
                    return svc

        # 2) Fallback: lokales KoSIT-Binary, falls installiert.
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

    def _validate_via_service(self, xml_bytes: bytes, base_url: str) -> KositValidationResult | None:
        """POST the document to the KoSIT validationtool daemon (``-D``) and parse
        the VARL report it returns.

        Returns a :class:`KositValidationResult` (``engine='kosit'``) on a usable
        HTTP response, or ``None`` when the service is unreachable / errors out, so
        the caller can fall back cleanly to the binary or Python path.
        """
        try:
            import requests
        except Exception:  # pragma: no cover - requests is a declared dependency
            logger.warning("kosit: requests not available, skipping HTTP service")
            return None

        url = base_url.rstrip("/") + "/"
        try:
            resp = requests.post(
                url,
                data=xml_bytes,
                headers={"Content-Type": "application/xml"},
                # (connect, read): strikt -> Nichterreichbarkeit scheitert schnell.
                timeout=(self.service_connect_timeout, float(self.timeout_seconds)),
            )
        except requests.RequestException as exc:
            logger.warning("kosit service unreachable (%s) – falling back", type(exc).__name__)
            return None

        if resp.status_code != 200 or not resp.content:
            logger.warning("kosit service returned HTTP %s – falling back", resp.status_code)
            return None

        return self._parse_varl_report(resp.content)

    def _parse_varl_report(self, report_bytes: bytes) -> KositValidationResult:
        """Parse a KoSIT VARL report (XXE-safe). ``accept`` -> passed, ``reject`` -> failed."""
        parser = etree.XMLParser(
            resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
        )
        raw = report_bytes[:4000].decode("utf-8", errors="ignore")
        try:
            root = etree.fromstring(report_bytes, parser)
        except etree.XMLSyntaxError:
            return KositValidationResult(
                status="failed",
                errors=["KoSIT-Service lieferte einen ungültigen Report."],
                warnings=[],
                engine="kosit",
                config_version=self.config_version,
                raw_output=raw,
            )

        accepted = bool(root.xpath("//*[local-name()='accept']"))
        rejected = bool(root.xpath("//*[local-name()='reject']"))

        errors: list[str] = []
        warnings: list[str] = []
        for msg in root.xpath("//*[local-name()='message']"):
            level = (msg.get("level") or "").lower()
            text = " ".join((msg.text or "").split())
            code = msg.get("code")
            if code and code not in text:
                text = f"{code}: {text}" if text else code
            if not text:
                continue
            if level in ("error", "fatal"):
                errors.append(text)
            elif level == "warning":
                warnings.append(text)

        if rejected:
            status = "failed"
            if not errors:
                errors.append("KoSIT: Dokument wurde abgelehnt (reject).")
        elif accepted:
            status = "passed"
        else:
            status = "failed" if errors else "passed"

        return KositValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            engine="kosit",
            config_version=self.config_version,
            raw_output=raw,
        )

# Backward compatibility alias
KositValidator = KoSITValidator
