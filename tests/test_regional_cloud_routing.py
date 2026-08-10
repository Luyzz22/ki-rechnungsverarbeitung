import json

import pytest

from shared.inference_policy import (
    DataClass,
    InferencePolicyDeniedError,
    InferenceProfile,
    InferenceProvider,
    assert_inference_allowed,
)
from shared.providers.azure_openai_provider import AzureOpenAIProvider
from shared.providers.provider_factory import select_provider_for_purpose
from shared.provider_governance import ProviderGovernanceError, assert_provider_governance_allowed


HOST = "flowcheck-westeurope.openai.azure.com"
DEPLOYMENT_ID = "flowcheck-gpt-4o-prod-2026-06"


def _deployment_config():
    return json.dumps(
        {
            "provider": InferenceProvider.AZURE_OPENAI_EU.value,
            "endpoint_host": HOST,
            "processing_region": "EU",
            "model_deployment_id": DEPLOYMENT_ID,
            "model_version": "gpt-4o-2024-08-06",
            "purpose_allowlist": ["invoice_llm_extraction"],
            "data_class_allowlist": [DataClass.INVOICE_CONFIDENTIAL.value],
            "retention_evidence_ref": "RETENTION-EVIDENCE-001",
            "no_training_evidence_ref": "NO-TRAINING-EVIDENCE-001",
            "provider_governance_approved": True,
        }
    )


def _env(**overrides):
    env = {
        "FLOWCHECK_RUNTIME_ENV": "production",
        "FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION": "true",
        "FLOWCHECK_CLOUD_PROCESSING_REGION": "EU",
        "FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST": HOST,
        "FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG": _deployment_config(),
        "FLOWCHECK_AZURE_ADAPTERS_ENABLED": "true",
        "FLOWCHECK_AZURE_AUTH_MODE": "entra",
        "FLOWCHECK_AZURE_IDENTITY_MODE": "managed_identity",
        "FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS": "false",
        "AZURE_OPENAI_ENDPOINT": f"https://{HOST}",
        "AZURE_OPENAI_DEPLOYMENT": DEPLOYMENT_ID,
        "AZURE_OPENAI_SCOPE": "https://cognitiveservices.azure.com/.default",
        "FLOWCHECK_AZURE_ALLOWED_REGION": "westeurope",
        "FLOWCHECK_AZURE_ENDPOINT_HOST_ALLOWLIST": HOST,
    }
    env.update(overrides)
    return env


def test_eu_regional_cloud_invoice_confidential_routes_to_azure_openai():
    provider = select_provider_for_purpose(
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
        purpose="invoice_llm_extraction",
    )

    assert provider == InferenceProvider.AZURE_OPENAI_EU


def test_eu_regional_cloud_document_purpose_routes_to_docintel():
    provider = select_provider_for_purpose(
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
        purpose="invoice_document_intelligence_extraction",
    )

    assert provider == InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU


def test_eu_regional_cloud_blocks_direct_provider_fallbacks():
    for provider in (
        InferenceProvider.OPENAI_DIRECT,
        InferenceProvider.ANTHROPIC_DIRECT,
        InferenceProvider.GEMINI_DIRECT,
    ):
        with pytest.raises(InferencePolicyDeniedError):
            assert_inference_allowed(
                data_class=DataClass.INVOICE_CONFIDENTIAL,
                inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
                provider=provider,
                purpose="invoice_llm_extraction",
            )


def test_eu_regional_cloud_requires_governed_deployment_before_adapter_client():
    captured = {}

    class FakeMessage:
        content = '{"ok": true}'

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            captured["request"] = kwargs
            return type("FakeResponse", (), {"choices": [FakeChoice()]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    provider = AzureOpenAIProvider(
        env=_env(),
        credential_factory=lambda: object(),
        token_provider_factory=lambda credential, scope: (lambda: "token"),
        client_factory=lambda **kwargs: FakeClient(),
    )

    result = provider.complete_json(
        messages=[{"role": "user", "content": "redacted"}],
        data_class=DataClass.INVOICE_CONFIDENTIAL,
        inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
        purpose="invoice_llm_extraction",
    )

    assert result == {"ok": True}
    assert captured["request"]["model"] == DEPLOYMENT_ID


def test_eu_regional_cloud_missing_governance_blocks_before_client():
    class FailIfInstantiated:
        def __init__(self, **kwargs):
            raise AssertionError("client must not be instantiated without governance")

    provider = AzureOpenAIProvider(
        env=_env(FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG=""),
        credential_factory=lambda: object(),
        token_provider_factory=lambda credential, scope: (lambda: "token"),
        client_factory=FailIfInstantiated,
    )

    with pytest.raises(ProviderGovernanceError) as exc_info:
        provider.create_chat_completion(
            messages=[{"role": "user", "content": "redacted"}],
            data_class=DataClass.INVOICE_CONFIDENTIAL,
            inference_profile=InferenceProfile.EU_REGIONAL_CLOUD,
            purpose="invoice_llm_extraction",
        )

    assert exc_info.value.reason_code == "deployment_policy_not_found"


def test_professional_secrecy_and_sovereign_rules_remain_unchanged():
    professional_decision = assert_provider_governance_allowed(
        data_class=DataClass.PROFESSIONAL_SECRET,
        inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        provider=InferenceProvider.AZURE_OPENAI_EU,
        purpose="invoice_llm_extraction",
        env=_env(),
    )
    assert professional_decision.allowed is True

    with pytest.raises(InferencePolicyDeniedError):
        assert_provider_governance_allowed(
            data_class=DataClass.SOVEREIGN_SECRET,
            inference_profile=InferenceProfile.SOVEREIGN,
            provider=InferenceProvider.AZURE_OPENAI_EU,
            purpose="invoice_llm_extraction",
            env=_env(),
        )
