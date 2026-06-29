from datetime import date

import pytest

from shared.inference_policy import DataClass, InferenceProfile
from shared.providers.azure_document_intelligence_provider import AzureDocumentIntelligenceProvider
from shared.providers.provider_factory import AzureProviderError


def _enabled_env(**overrides):
    env = {
        "FLOWCHECK_AZURE_ADAPTERS_ENABLED": "true",
        "FLOWCHECK_AZURE_AUTH_MODE": "entra",
        "FLOWCHECK_RUNTIME_ENV": "production",
        "FLOWCHECK_AZURE_IDENTITY_MODE": "managed_identity",
        "FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS": "false",
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": "https://flowcheck-westeurope.cognitiveservices.azure.com",
        "AZURE_DOCUMENT_INTELLIGENCE_MODEL": "prebuilt-invoice",
        "FLOWCHECK_AZURE_ALLOWED_REGION": "westeurope",
        "FLOWCHECK_AZURE_ENDPOINT_HOST_ALLOWLIST": "flowcheck-westeurope.cognitiveservices.azure.com",
    }
    env.update(overrides)
    return env


class Field:
    def __init__(self, *, value_string=None, value_date=None, value_currency=None, confidence=0.9):
        self.value_string = value_string
        self.value_date = value_date
        self.value_currency = value_currency
        self.confidence = confidence


class Currency:
    def __init__(self, amount, currency_code="EUR"):
        self.amount = amount
        self.currency_code = currency_code


def _successful_client(captured):
    class FakePoller:
        def result(self):
            document = type(
                "Document",
                (),
                {
                    "fields": {
                        "VendorName": Field(value_string="Supplier GmbH"),
                        "InvoiceId": Field(value_string="INV-001"),
                        "InvoiceDate": Field(value_date=date(2026, 6, 29)),
                        "InvoiceTotal": Field(value_currency=Currency(119.0)),
                        "SubTotal": Field(value_currency=Currency(100.0)),
                        "TotalTax": Field(value_currency=Currency(19.0)),
                    }
                },
            )()
            return type("AnalyzeResult", (), {"documents": [document]})()

    class FakeClient:
        def begin_analyze_document(self, model, *, body, content_type):
            captured["model"] = model
            captured["body_type"] = type(body)
            captured["content_type"] = content_type
            return FakePoller()

    return FakeClient()


def test_professional_secrecy_docintel_policy_allowed_and_normalized():
    captured = {}
    provider = AzureDocumentIntelligenceProvider(
        env=_enabled_env(),
        credential_factory=lambda: object(),
        client_factory=lambda **kwargs: _successful_client(captured),
    )

    result = provider.analyze_invoice(
        file_bytes=b"%PDF-1.7",
        mime_type="application/pdf",
        data_class=DataClass.PROFESSIONAL_SECRET,
        inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
    )

    assert result.provider == "azure_document_intelligence_eu"
    assert result.model == "prebuilt-invoice"
    assert result.invoice_data["rechnungsaussteller"] == "Supplier GmbH"
    assert result.invoice_data["rechnungsnummer"] == "INV-001"
    assert result.invoice_data["datum"] == "2026-06-29"
    assert result.invoice_data["betrag_brutto"] == 119.0
    assert captured == {
        "model": "prebuilt-invoice",
        "body_type": bytes,
        "content_type": "application/pdf",
    }


def test_docintel_rejects_non_byte_input():
    provider = AzureDocumentIntelligenceProvider(env=_enabled_env())

    with pytest.raises(AzureProviderError) as exc_info:
        provider.analyze_invoice(
            file_bytes="https://example.invalid/invoice.pdf",
            mime_type="application/pdf",
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        )

    assert exc_info.value.error_code == "AZURE_DOCINTEL_REQUEST_FAILED"
    assert exc_info.value.reason_code == "byte_input_required"


def test_docintel_rejects_url_source():
    provider = AzureDocumentIntelligenceProvider(env=_enabled_env())

    with pytest.raises(AzureProviderError) as exc_info:
        provider.analyze_invoice(
            file_bytes=b"%PDF-1.7",
            mime_type="application/pdf",
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
            url_source="https://example.invalid/invoice.pdf",
        )

    assert exc_info.value.error_code == "AZURE_DOCINTEL_REQUEST_FAILED"
    assert exc_info.value.reason_code == "url_source_not_allowed"


def test_docintel_error_has_no_sensitive_payload():
    class FailingClient:
        def begin_analyze_document(self, *args, **kwargs):
            raise RuntimeError(
                "failed for invoice INV-999, IBAN DE89370400440532013000, "
                "mail max@example.com, token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            )

    provider = AzureDocumentIntelligenceProvider(
        env=_enabled_env(),
        credential_factory=lambda: object(),
        client_factory=lambda **kwargs: FailingClient(),
    )

    with pytest.raises(AzureProviderError) as exc_info:
        provider.analyze_invoice(
            file_bytes=b"VGhpcyBpcyBiYXNlNjQgZW5vdWdoIHRvIGJlIHJlZGFjdGVk",
            mime_type="application/pdf",
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        )

    rendered = str(exc_info.value) + repr(exc_info.value.to_safe_dict())
    assert exc_info.value.error_code == "AZURE_DOCINTEL_REQUEST_FAILED"
    assert exc_info.value.__cause__ is None
    assert "INV-999" not in rendered
    assert "DE89370400440532013000" not in rendered
    assert "max@example.com" not in rendered
    assert "VGhpcy" not in rendered
    assert "eyJhbGci" not in rendered


def test_docintel_model_override_is_rejected():
    provider = AzureDocumentIntelligenceProvider(env=_enabled_env(AZURE_DOCUMENT_INTELLIGENCE_MODEL="custom-model"))

    with pytest.raises(AzureProviderError) as exc_info:
        provider.analyze_invoice(
            file_bytes=b"%PDF-1.7",
            mime_type="application/pdf",
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        )

    assert exc_info.value.error_code == "AZURE_DOCINTEL_MODEL_UNAVAILABLE"
