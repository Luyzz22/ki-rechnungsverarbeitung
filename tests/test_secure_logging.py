import json
import logging

from shared.secure_logging import hash_identifier, safe_log, sanitize_for_log


def test_safe_log_redacts_realistic_sensitive_values(caplog):
    logger = logging.getLogger("tests.secure_logging.strict")
    caplog.set_level(logging.INFO, logger="tests.secure_logging.strict")

    sensitive_values = {
        "iban": "DE89370400440532013000",
        "email": "buchhaltung@example.com",
        "invoice_number": "RE-2026-00042",
        "api_key": "sk-test123456789012345678901234",
        "base64": "U29tZUJhc2U2NERhdGFGb3JSZWNobnVuZw==",
        "prompt": "Bitte extrahiere alle Positionen aus dieser Rechnung.",
        "supplier_name": "Sensitive Supplier GmbH",
        "file_name": "RE-2026-00042-Sensitive Supplier GmbH.pdf",
    }

    safe_log(
        logger,
        logging.INFO,
        "inference_request_metadata",
        **sensitive_values,
        message=(
            "Kontakt buchhaltung@example.com IBAN DE89370400440532013000 "
            "Rechnung RE-2026-00042 payload U29tZUJhc2U2NERhdGFGb3JSZWNobnVuZw=="
        ),
    )

    output = caplog.text
    for value in sensitive_values.values():
        assert value not in output
    assert "buchhaltung@example.com" not in output
    assert "DE89370400440532013000" not in output
    assert "RE-2026-00042" not in output
    assert "U29tZUJhc2U2NERhdGFGb3JSZWNobnVuZw==" not in output


def test_long_strings_are_hashed_without_preview():
    secret = ("Rechnung OCR Inhalt mit vertraulichen Positionen, Beträgen und Details. " * 12).strip()
    sanitized = sanitize_for_log({"notes": secret})

    serialized = json.dumps(sanitized, sort_keys=True)
    assert "Rechnung OCR Inhalt" not in serialized
    assert "AAAA" not in serialized
    assert sanitized["notes"]["truncated"] is True
    assert sanitized["notes"]["length"] > 120
    assert "sha256" in sanitized["notes"]


def test_allowed_invoice_id_metadata_is_hashed(caplog):
    logger = logging.getLogger("tests.secure_logging.invoice_id")
    caplog.set_level(logging.INFO, logger="tests.secure_logging.invoice_id")

    safe_log(logger, logging.INFO, "policy_decision", invoice_id="invoice-12345", status="denied")

    output = caplog.text
    assert "invoice-12345" not in output
    assert hash_identifier("invoice-12345") in output
    assert '"status": "denied"' in output
