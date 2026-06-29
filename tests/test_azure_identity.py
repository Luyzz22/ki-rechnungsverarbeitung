import pytest

from shared.inference_policy import InferenceProvider
from shared.providers.azure_identity import AzureProviderError, resolve_azure_credential


def _env(**overrides):
    env = {
        "FLOWCHECK_RUNTIME_ENV": "production",
        "FLOWCHECK_AZURE_IDENTITY_MODE": "managed_identity",
        "FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS": "false",
    }
    env.update(overrides)
    return env


def test_production_default_azure_credential_not_allowed():
    calls = {"default": 0}

    class FakeDefaultCredential:
        def __init__(self):
            calls["default"] += 1

    with pytest.raises(AzureProviderError) as exc_info:
        resolve_azure_credential(
            provider=InferenceProvider.AZURE_OPENAI_EU,
            env=_env(
                FLOWCHECK_AZURE_IDENTITY_MODE="developer_credentials",
                FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS="true",
            ),
            default_credential_cls=FakeDefaultCredential,
        )

    assert calls["default"] == 0
    assert exc_info.value.error_code == "AZURE_CONFIGURATION_INVALID"
    assert exc_info.value.reason_code == "developer_credentials_not_allowed_in_production"


def test_production_managed_identity_credential_is_used():
    calls = []

    class FakeManagedIdentityCredential:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    credential = resolve_azure_credential(
        provider=InferenceProvider.AZURE_OPENAI_EU,
        env=_env(FLOWCHECK_AZURE_MANAGED_IDENTITY_CLIENT_ID="client-id-for-test"),
        managed_identity_credential_cls=FakeManagedIdentityCredential,
    )

    assert isinstance(credential, FakeManagedIdentityCredential)
    assert calls == [{"client_id": "client-id-for-test"}]


def test_development_developer_credentials_disabled():
    with pytest.raises(AzureProviderError) as exc_info:
        resolve_azure_credential(
            provider=InferenceProvider.AZURE_OPENAI_EU,
            env=_env(
                FLOWCHECK_RUNTIME_ENV="development",
                FLOWCHECK_AZURE_IDENTITY_MODE="developer_credentials",
                FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS="false",
            ),
        )

    assert exc_info.value.error_code == "AZURE_CONFIGURATION_INVALID"
    assert exc_info.value.reason_code == "developer_credentials_not_allowed"


def test_development_explicit_developer_credentials_allowed():
    calls = {"default": 0}

    class FakeDefaultCredential:
        def __init__(self):
            calls["default"] += 1

    credential = resolve_azure_credential(
        provider=InferenceProvider.AZURE_OPENAI_EU,
        env=_env(
            FLOWCHECK_RUNTIME_ENV="development",
            FLOWCHECK_AZURE_IDENTITY_MODE="developer_credentials",
            FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS="true",
        ),
        default_credential_cls=FakeDefaultCredential,
    )

    assert isinstance(credential, FakeDefaultCredential)
    assert calls == {"default": 1}


def test_managed_identity_unavailable_is_pii_free():
    class FailingManagedIdentityCredential:
        def __init__(self, **kwargs):
            raise RuntimeError(
                "tenant 00000000-0000-0000-0000-000000000000 "
                "client client-id-for-test token secret-token invoice INV-42"
            )

    with pytest.raises(AzureProviderError) as exc_info:
        resolve_azure_credential(
            provider=InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU,
            env=_env(FLOWCHECK_AZURE_MANAGED_IDENTITY_CLIENT_ID="client-id-for-test"),
            managed_identity_credential_cls=FailingManagedIdentityCredential,
        )

    rendered = str(exc_info.value) + repr(exc_info.value.to_safe_dict())
    assert exc_info.value.error_code == "AZURE_AUTH_UNAVAILABLE"
    assert exc_info.value.__cause__ is None
    assert "00000000-0000-0000-0000-000000000000" not in rendered
    assert "client-id-for-test" not in rendered
    assert "secret-token" not in rendered
    assert "INV-42" not in rendered


def test_production_non_managed_identity_mode_fails_closed():
    with pytest.raises(AzureProviderError) as exc_info:
        resolve_azure_credential(
            provider=InferenceProvider.AZURE_OPENAI_EU,
            env=_env(FLOWCHECK_AZURE_IDENTITY_MODE="developer_credentials"),
        )

    assert exc_info.value.error_code == "AZURE_CONFIGURATION_INVALID"
    assert exc_info.value.reason_code == "production_requires_managed_identity"
