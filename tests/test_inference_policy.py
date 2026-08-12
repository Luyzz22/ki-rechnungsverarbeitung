import json
import logging
import importlib
import sys
import types

import pytest

from shared.inference_policy import (
    DataClass,
    InferencePolicyDeniedError,
    InferenceProfile,
    InferenceProvider,
    assert_inference_allowed,
    evaluate_inference_policy,
)
from shared.secure_logging import safe_log


def _import_llm_router_with_stubbed_sdks(monkeypatch):
    class FakeOpenAI:
        pass

    class FakeAnthropic:
        pass

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=FakeAnthropic))
    sys.modules.pop("llm_router", None)
    return importlib.import_module("llm_router")


def test_standard_invoice_confidential_openai_direct_allowed():
    decision = assert_inference_allowed(
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.STANDARD,
        provider=InferenceProvider.OPENAI_DIRECT,
        purpose="invoice_llm_extraction",
    )

    assert decision.allowed is True
    assert decision.policy_decision == "allowed"


def test_professional_secret_direct_openai_blocked():
    with pytest.raises(InferencePolicyDeniedError) as exc_info:
        assert_inference_allowed(
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
            provider=InferenceProvider.OPENAI_DIRECT,
            purpose="invoice_llm_extraction",
        )

    assert exc_info.value.error_code == "INFERENCE_POLICY_DENIED"
    assert exc_info.value.decision.reason_code == "professional_secrecy_provider_denied"


def test_professional_secret_azure_openai_allowed():
    decision = assert_inference_allowed(
        data_class=DataClass.PROFESSIONAL_SECRET,
        inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        provider=InferenceProvider.AZURE_OPENAI_EU,
        purpose="invoice_llm_extraction",
    )

    assert decision.allowed is True


def test_sovereign_secret_azure_openai_blocked():
    decision = evaluate_inference_policy(
        data_class=DataClass.SOVEREIGN_SECRET,
        inference_profile=InferenceProfile.SOVEREIGN,
        provider=InferenceProvider.AZURE_OPENAI_EU,
        purpose="invoice_llm_extraction",
    )

    assert decision.allowed is False
    assert decision.error_code == "INFERENCE_POLICY_DENIED"
    assert decision.blocked_rule == "sovereign_allowed_provider_set"


def test_sovereign_secret_local_llm_allowed():
    decision = assert_inference_allowed(
        data_class=DataClass.SOVEREIGN_SECRET,
        inference_profile=InferenceProfile.SOVEREIGN,
        provider=InferenceProvider.LOCAL_OPENAI_COMPAT,
        purpose="invoice_llm_extraction",
    )

    assert decision.allowed is True


def test_unknown_data_class_blocked():
    decision = evaluate_inference_policy(
        data_class="customer_text",
        inference_profile=InferenceProfile.STANDARD,
        provider=InferenceProvider.OPENAI_DIRECT,
        purpose="invoice_llm_extraction",
    )

    assert decision.allowed is False
    assert decision.error_code == "INFERENCE_POLICY_DENIED"
    assert decision.reason_code == "unknown_data_class"


def test_professional_secrecy_provider_outage_does_not_allow_direct_fallback():
    decision = evaluate_inference_policy(
        data_class=DataClass.PROFESSIONAL_SECRET,
        inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        provider=InferenceProvider.AZURE_OPENAI_EU,
        purpose="invoice_llm_extraction",
        provider_configured=False,
    )

    assert decision.allowed is False
    assert decision.error_code == "INFERENCE_POLICY_DENIED"
    assert InferenceProvider.OPENAI_DIRECT.value not in decision.allowed_providers
    assert InferenceProvider.ANTHROPIC_DIRECT.value not in decision.allowed_providers
    assert InferenceProvider.GEMINI_DIRECT.value not in decision.allowed_providers


def test_secure_logging_redacts_sensitive_values(caplog):
    logger = logging.getLogger("tests.secure_logging")
    caplog.set_level(logging.INFO, logger="tests.secure_logging")

    safe_log(
        logger,
        logging.INFO,
        "invoice_ai_event",
        invoice_text="Rechnung SECRET-INVOICE-TEXT Betrag 1234,56 EUR",
        prompt="Bitte extrahiere diese Rechnung",
        api_key="sk-test12345678901234567890",
        notes="Kontakt max@example.com IBAN DE89370400440532013000",
        supplier_name="Example Supplier GmbH",
    )

    output = caplog.text
    assert "SECRET-INVOICE-TEXT" not in output
    assert "Bitte extrahiere" not in output
    assert "sk-test" not in output
    assert "max@example.com" not in output
    assert "DE89370400440532013000" not in output
    assert "Example Supplier" not in output


def test_standard_llm_router_openai_flow_still_works(monkeypatch):
    llm_router = _import_llm_router_with_stubbed_sdks(monkeypatch)

    class FakeMessage:
        content = json.dumps(
            {
                "rechnungsaussteller": "Test GmbH",
                "betrag_brutto": 42.0,
                "confidence": 0.91,
            }
        )

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            self.kwargs = kwargs
            return type("FakeResponse", (), {"choices": [FakeChoice()]})()

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self):
            self.chat = FakeChat()

    monkeypatch.setattr(llm_router, "get_openai_client", lambda: FakeClient())

    result = llm_router.extract_invoice_data(
        "Dies ist ein ausreichend langer Rechnungstext. " * 8,
        provider="openai",
        model="gpt-test",
    )

    assert result["rechnungsaussteller"] == "Test GmbH"
    assert result["betrag_brutto"] == 42.0


def test_policy_denial_in_llm_router_does_not_fall_back_to_vision(monkeypatch):
    llm_router = _import_llm_router_with_stubbed_sdks(monkeypatch)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("vision fallback must not run after policy denial")

    monkeypatch.setattr(llm_router, "extract_with_vision", fail_if_called)

    with pytest.raises(InferencePolicyDeniedError):
        llm_router.extract_invoice_data_with_fallback(
            "Dies ist ein ausreichend langer Rechnungstext. " * 8,
            "/tmp/invoice.pdf",
            provider="openai",
            model="gpt-test",
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        )
