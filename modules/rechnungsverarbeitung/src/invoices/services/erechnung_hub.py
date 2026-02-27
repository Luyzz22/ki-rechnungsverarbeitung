from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modules.rechnungsverarbeitung.src.invoices.services.kosit_validator import (
    KositValidator,
)


XRECHNUNG_URN_MARKERS: tuple[str, ...] = (
    "urn:cen.eu:en16931:2017",
    "urn:xeinkauf.de:kosit:xrechnung",
)

ZUGFERD_MARKERS: tuple[str, ...] = (
    "urn:factur-x.eu",
    "urn:zugferd",
    "CrossIndustryInvoice",
)


@dataclass
class CanonicalParty:
    name: str = ""
    tax_id: str = ""
    vat_id: str = ""


@dataclass
class CanonicalInvoice:
    """Canonical invoice snapshot for hub processing."""

    invoice_number: str
    invoice_date: str
    due_date: str
    currency: str
    total_net: float
    total_vat: float
    total_gross: float
    seller: CanonicalParty
    buyer: CanonicalParty
    line_items: list[dict[str, Any]]
    schema_version: str = "v1"


@dataclass
class ValidationReport:
    document_id: str
    tenant_id: str
    engine: str
    status: str
    errors: list[str]
    warnings: list[str]
    generated_at: str
    report_hash: str
    config_version: str


class ERechnungHubService:
    """Utilities for E-Rechnung format detection and canonicalization."""

    def __init__(self, report_base_dir: str | Path = "exports/validation_reports") -> None:
        self.report_base_dir = Path(report_base_dir)
        self.validator = KositValidator()

    def detect_invoice_format(self, content: bytes, filename: str = "") -> str:
        """Detect invoice type: xrechnung, zugferd, or pdf_other."""
        file_name = filename.lower()
        if file_name.endswith(".pdf"):
            return "pdf_other"

        text = content.decode("utf-8", errors="ignore")
        normalized = re.sub(r"\s+", " ", text.lower())

        if any(marker in normalized for marker in XRECHNUNG_URN_MARKERS):
            return "xrechnung"
        if any(marker.lower() in normalized for marker in ZUGFERD_MARKERS):
            return "zugferd"
        if file_name.endswith(".xml"):
            return "xml_other"
        return "unknown"

    def build_canonical_invoice(self, extracted: dict[str, Any]) -> CanonicalInvoice:
        """Map extracted invoice dict to canonical schema."""
        gross = float(extracted.get("betrag_brutto") or 0.0)
        net = float(extracted.get("betrag_netto") or 0.0)
        vat = float(extracted.get("mwst_betrag") or max(gross - net, 0.0))

        seller = CanonicalParty(
            name=str(extracted.get("rechnungsaussteller") or ""),
            tax_id=str(extracted.get("steuernummer") or ""),
            vat_id=str(extracted.get("ust_id") or extracted.get("ust_idnr") or ""),
        )
        buyer = CanonicalParty(
            name=str(extracted.get("rechnungsempfaenger") or ""),
            tax_id="",
            vat_id="",
        )

        line_items = extracted.get("positionen") or extracted.get("line_items") or []
        if isinstance(line_items, str):
            line_items = [{"description": line_items, "quantity": 1, "total": net or gross}]

        return CanonicalInvoice(
            invoice_number=str(extracted.get("rechnungsnummer") or ""),
            invoice_date=str(extracted.get("datum") or ""),
            due_date=str(extracted.get("faelligkeitsdatum") or ""),
            currency=str(extracted.get("waehrung") or "EUR"),
            total_net=net,
            total_vat=vat,
            total_gross=gross,
            seller=seller,
            buyer=buyer,
            line_items=list(line_items),
        )

    def write_validation_report(
        self,
        *,
        document_id: str,
        tenant_id: str,
        engine: str,
        status: str,
        config_version: str = "unknown",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> tuple[Path, Path, ValidationReport]:
        """Persist machine-readable and human-readable validation reports."""
        errors = errors or []
        warnings = warnings or []
        generated_at = datetime.now(timezone.utc).isoformat()

        payload = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "engine": engine,
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "generated_at": generated_at,
            "config_version": config_version,
        }
        report_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        report = ValidationReport(
            document_id=document_id,
            tenant_id=tenant_id,
            engine=engine,
            status=status,
            errors=errors,
            warnings=warnings,
            generated_at=generated_at,
            report_hash=report_hash,
            config_version=config_version,
        )

        tenant_dir = self.report_base_dir / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        json_path = tenant_dir / f"{document_id}.validation.json"
        txt_path = tenant_dir / f"{document_id}.validation.txt"

        json_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        txt_path.write_text(
            "\n".join(
                [
                    f"document_id: {document_id}",
                    f"tenant_id: {tenant_id}",
                    f"engine: {engine}",
                    f"status: {status}",
                    f"generated_at: {generated_at}",
                    f"report_hash: {report_hash}",
                    f"config_version: {config_version}",
                    f"errors: {len(errors)}",
                    *[f"  - {err}" for err in errors],
                    f"warnings: {len(warnings)}",
                    *[f"  - {warning}" for warning in warnings],
                ]
            ),
            encoding="utf-8",
        )

        return json_path, txt_path, report

    def validate_structured_invoice(
        self,
        *,
        document_id: str,
        tenant_id: str,
        xml_content: bytes,
    ) -> tuple[Path, Path, ValidationReport]:
        """Run KoSIT validation (with safe fallback) and persist final report."""
        tenant_dir = self.report_base_dir / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=True) as tmp:
            tmp.write(xml_content)
            tmp.flush()
            result = self.validator.validate_file(tmp.name, tenant_dir)

        return self.write_validation_report(
            document_id=document_id,
            tenant_id=tenant_id,
            engine=result.engine,
            status=result.status,
            config_version=result.config_version,
            errors=result.errors,
            warnings=result.warnings,
        )
