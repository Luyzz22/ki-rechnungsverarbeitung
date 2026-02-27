from __future__ import annotations

import json

from modules.rechnungsverarbeitung.src.invoices.services.erechnung_hub import (
    ERechnungHubService,
)


def test_detect_xrechnung_xml() -> None:
    service = ERechnungHubService()
    xml = b"<rsm:CrossIndustryInvoice><ram:GuidelineSpecifiedDocumentContextParameter><ram:ID>urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0</ram:ID></ram:GuidelineSpecifiedDocumentContextParameter></rsm:CrossIndustryInvoice>"
    assert service.detect_invoice_format(xml, "invoice.xml") == "xrechnung"


def test_detect_pdf_as_sonstige_rechnung() -> None:
    service = ERechnungHubService()
    assert service.detect_invoice_format(b"%PDF-1.7", "invoice.pdf") == "pdf_other"


def test_canonical_mapping_defaults() -> None:
    service = ERechnungHubService()
    canonical = service.build_canonical_invoice(
        {
            "rechnungsnummer": "RE-2026-001",
            "datum": "2026-02-01",
            "betrag_netto": 100.0,
            "betrag_brutto": 119.0,
            "rechnungsaussteller": "Lieferant GmbH",
            "positionen": "Service Fee",
        }
    )
    assert canonical.invoice_number == "RE-2026-001"
    assert canonical.total_vat == 19.0
    assert canonical.currency == "EUR"
    assert canonical.line_items[0]["description"] == "Service Fee"


def test_validation_report_written(tmp_path) -> None:
    service = ERechnungHubService(report_base_dir=tmp_path)
    json_path, txt_path, report = service.write_validation_report(
        document_id="doc-1",
        tenant_id="tenant-42",
        engine="kosit",
        status="failed",
        config_version="xrechnung-3.0.1",
        errors=["BR-DE-15 verletzt"],
        warnings=["Warnung"],
    )

    assert json_path.exists()
    assert txt_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["document_id"] == "doc-1"
    assert payload["status"] == "failed"
    assert payload["config_version"] == "xrechnung-3.0.1"
    assert report.report_hash


def test_validate_structured_invoice_uses_validator_result(tmp_path) -> None:
    service = ERechnungHubService(report_base_dir=tmp_path)

    class DummyValidator:
        config_version = "xrechnung-3.0.1"

        def validate_file(self, invoice_path, report_dir):
            assert invoice_path
            assert report_dir
            from modules.rechnungsverarbeitung.src.invoices.services.kosit_validator import (
                KositValidationResult,
            )

            return KositValidationResult(
                status="passed",
                errors=[],
                warnings=[],
                engine="kosit",
                config_version="xrechnung-3.0.1",
                raw_output="ok",
            )

    service.validator = DummyValidator()

    json_path, txt_path, report = service.validate_structured_invoice(
        document_id="doc-2",
        tenant_id="tenant-99",
        xml_content=b"<Invoice/>",
    )

    assert json_path.exists()
    assert txt_path.exists()
    assert report.status == "passed"
    assert report.config_version == "xrechnung-3.0.1"
