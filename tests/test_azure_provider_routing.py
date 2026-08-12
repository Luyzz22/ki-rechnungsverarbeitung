import pytest

from shared.inference_policy import (
    DataClass,
    InferencePolicyDeniedError,
    InferenceProfile,
    InferenceProvider,
    assert_inference_allowed,
)
from shared.providers.provider_factory import select_provider_for_purpose


def test_standard_invoice_confidential_keeps_direct_router():
    provider = select_provider_for_purpose(
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.STANDARD,
        purpose="invoice_llm_extraction",
    )

    assert provider == InferenceProvider.OPENAI_DIRECT


def test_professional_secrecy_invoice_text_routes_to_azure_openai():
    provider = select_provider_for_purpose(
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        purpose="invoice_llm_extraction",
    )

    assert provider == InferenceProvider.AZURE_OPENAI_EU


def test_professional_secrecy_invoice_document_routes_to_docintel():
    provider = select_provider_for_purpose(
        data_class=DataClass.PROFESSIONAL_SECRET,
        inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        purpose="invoice_document_intelligence_extraction",
    )

    assert provider == InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU


def test_professional_secrecy_direct_providers_still_blocked():
    with pytest.raises(InferencePolicyDeniedError):
        assert_inference_allowed(
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
            provider=InferenceProvider.OPENAI_DIRECT,
            purpose="invoice_llm_extraction",
        )
    with pytest.raises(InferencePolicyDeniedError):
        assert_inference_allowed(
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
            provider=InferenceProvider.ANTHROPIC_DIRECT,
            purpose="invoice_llm_extraction",
        )
    with pytest.raises(InferencePolicyDeniedError):
        assert_inference_allowed(
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
            provider=InferenceProvider.GEMINI_DIRECT,
            purpose="invoice_llm_extraction",
        )


def test_sovereign_routes_to_local_and_blocks_azure():
    provider = select_provider_for_purpose(
        data_class=DataClass.SOVEREIGN_SECRET,
        inference_profile=InferenceProfile.SOVEREIGN,
        purpose="invoice_llm_extraction",
    )

    assert provider == InferenceProvider.LOCAL_OPENAI_COMPAT

    with pytest.raises(InferencePolicyDeniedError):
        assert_inference_allowed(
            data_class=DataClass.SOVEREIGN_SECRET,
            inference_profile=InferenceProfile.SOVEREIGN,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            purpose="invoice_llm_extraction",
        )
    with pytest.raises(InferencePolicyDeniedError):
        assert_inference_allowed(
            data_class=DataClass.SOVEREIGN_SECRET,
            inference_profile=InferenceProfile.SOVEREIGN,
            provider=InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU,
            purpose="invoice_document_intelligence_extraction",
        )
