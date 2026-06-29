import pytest

from shared.inference_policy import DataClass, InferencePolicyDeniedError, InferenceProfile
from shared.providers.azure_openai_provider import AzureOpenAIProvider
from shared.providers.provider_factory import AzureProviderError


def _enabled_env(**overrides):
    env = {
        "FLOWCHECK_AZURE_ADAPTERS_ENABLED": "true",
        "FLOWCHECK_AZURE_AUTH_MODE": "entra",
        "FLOWCHECK_RUNTIME_ENV": "production",
        "FLOWCHECK_AZURE_IDENTITY_MODE": "managed_identity",
        "FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS": "false",
        "AZURE_OPENAI_ENDPOINT": "https://flowcheck-westeurope.openai.azure.com",
        "AZURE_OPENAI_DEPLOYMENT": "flowcheck-gpt",
        "AZURE_OPENAI_SCOPE": "https://ai.azure.com/.default",
        "FLOWCHECK_AZURE_ALLOWED_REGION": "westeurope",
        "FLOWCHECK_AZURE_ENDPOINT_HOST_ALLOWLIST": "flowcheck-westeurope.openai.azure.com",
    }
    env.update(overrides)
    return env


def test_professional_secrecy_azure_openai_disabled():
    provider = AzureOpenAIProvider(env={})

    with pytest.raises(AzureProviderError) as exc_info:
        provider.create_chat_completion(
            messages=[{"role": "user", "content": "redacted in tests"}],
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
            purpose="invoice_llm_extraction",
        )

    assert exc_info.value.error_code == "AZURE_ADAPTER_DISABLED"


def test_professional_secrecy_azure_openai_missing_endpoint():
    provider = AzureOpenAIProvider(env=_enabled_env(AZURE_OPENAI_ENDPOINT=""))

    with pytest.raises(AzureProviderError) as exc_info:
        provider.create_chat_completion(
            messages=[{"role": "user", "content": "redacted in tests"}],
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
            purpose="invoice_llm_extraction",
        )

    assert exc_info.value.error_code == "AZURE_CONFIGURATION_INVALID"
    assert exc_info.value.reason_code == "azure_openai_endpoint_or_deployment_missing"


def test_professional_secrecy_azure_openai_simulated_entra_request():
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

    def fake_client_factory(**kwargs):
        captured["client"] = kwargs
        return FakeClient()

    provider = AzureOpenAIProvider(
        env=_enabled_env(),
        credential_factory=lambda: object(),
        token_provider_factory=lambda credential, scope: (lambda: "token"),
        client_factory=fake_client_factory,
    )

    result = provider.complete_json(
        messages=[{"role": "user", "content": "redacted in tests"}],
        data_class=DataClass.PROFESSIONAL_SECRET,
        inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        purpose="invoice_llm_extraction",
    )

    assert result == {"ok": True}
    assert captured["client"]["azure_endpoint"] == "https://flowcheck-westeurope.openai.azure.com"
    assert captured["client"]["api_version"] == "2024-10-21"
    assert captured["request"]["model"] == "flowcheck-gpt"


def test_professional_secrecy_azure_openai_error_has_no_direct_fallback():
    calls = {"azure": 0, "direct": 0}

    class FailingCompletions:
        def create(self, **kwargs):
            calls["azure"] += 1
            raise RuntimeError("provider failed with IBAN DE89370400440532013000 and sk-secret123456789012345")

    class FakeChat:
        completions = FailingCompletions()

    class FailingClient:
        chat = FakeChat()

    provider = AzureOpenAIProvider(
        env=_enabled_env(),
        credential_factory=lambda: object(),
        token_provider_factory=lambda credential, scope: (lambda: "token"),
        client_factory=lambda **kwargs: FailingClient(),
    )

    with pytest.raises(AzureProviderError) as exc_info:
        provider.create_chat_completion(
            messages=[{"role": "user", "content": "prompt with max@example.com"}],
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
            purpose="invoice_llm_extraction",
        )

    assert calls == {"azure": 1, "direct": 0}
    assert exc_info.value.error_code == "AZURE_OPENAI_REQUEST_FAILED"
    assert exc_info.value.__cause__ is None
    assert "DE89370400440532013000" not in str(exc_info.value)
    assert "max@example.com" not in str(exc_info.value)
    assert "sk-secret" not in str(exc_info.value)


def test_sovereign_azure_openai_policy_denied_before_config():
    provider = AzureOpenAIProvider(env=_enabled_env())

    with pytest.raises(InferencePolicyDeniedError) as exc_info:
        provider.create_chat_completion(
            messages=[{"role": "user", "content": "redacted in tests"}],
            data_class=DataClass.SOVEREIGN_SECRET,
            inference_profile=InferenceProfile.SOVEREIGN,
            purpose="invoice_llm_extraction",
        )

    assert exc_info.value.error_code == "INFERENCE_POLICY_DENIED"
