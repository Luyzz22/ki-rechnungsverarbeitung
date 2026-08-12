import pytest

from shared.inference_policy import InferenceProvider
from shared.providers.azure_identity import AzureProviderError, validate_azure_endpoint
from shared.providers.provider_factory import resolve_azure_openai_config


ALLOWED_HOST = "flowcheck-westeurope.openai.azure.com"


def _validate(endpoint: str, **kwargs):
    return validate_azure_endpoint(
        endpoint,
        allowed_hosts=kwargs.pop("allowed_hosts", ALLOWED_HOST),
        provider=InferenceProvider.AZURE_OPENAI_EU,
        **kwargs,
    )


def test_endpoint_https_required():
    with pytest.raises(AzureProviderError) as exc_info:
        _validate("http://flowcheck-westeurope.openai.azure.com")

    assert exc_info.value.error_code == "AZURE_CONFIGURATION_INVALID"
    assert exc_info.value.reason_code == "endpoint_must_be_https"


def test_endpoint_ip_address_blocked():
    with pytest.raises(AzureProviderError) as exc_info:
        _validate("https://10.0.0.5")

    assert exc_info.value.reason_code == "endpoint_ip_not_allowed"


def test_endpoint_query_or_fragment_blocked():
    with pytest.raises(AzureProviderError) as query_exc:
        _validate("https://flowcheck-westeurope.openai.azure.com?token=secret-token")
    with pytest.raises(AzureProviderError) as fragment_exc:
        _validate("https://flowcheck-westeurope.openai.azure.com#secret-token")

    assert query_exc.value.reason_code == "endpoint_query_or_fragment_not_allowed"
    assert fragment_exc.value.reason_code == "endpoint_query_or_fragment_not_allowed"
    assert "secret-token" not in str(query_exc.value)
    assert "secret-token" not in str(fragment_exc.value)


def test_endpoint_outside_allowlist_blocked():
    with pytest.raises(AzureProviderError) as exc_info:
        _validate("https://other-westeurope.openai.azure.com")

    assert exc_info.value.reason_code == "endpoint_host_not_allowed"


def test_empty_endpoint_allowlist_blocks_configuration():
    with pytest.raises(AzureProviderError) as exc_info:
        _validate("https://flowcheck-westeurope.openai.azure.com", allowed_hosts="")

    assert exc_info.value.reason_code == "endpoint_host_allowlist_required"


def test_endpoint_from_client_input_is_rejected():
    with pytest.raises(AzureProviderError) as exc_info:
        _validate("https://flowcheck-westeurope.openai.azure.com", source="client_input")

    assert exc_info.value.reason_code == "endpoint_source_not_allowed"


def test_endpoint_userinfo_is_rejected_without_leaking_value():
    with pytest.raises(AzureProviderError) as exc_info:
        _validate("https://tenant:secret-token@flowcheck-westeurope.openai.azure.com")

    rendered = str(exc_info.value) + repr(exc_info.value.to_safe_dict())
    assert exc_info.value.reason_code == "endpoint_userinfo_not_allowed"
    assert "tenant" not in rendered
    assert "secret-token" not in rendered


def test_server_config_endpoint_is_allowlisted():
    endpoint = _validate("https://flowcheck-westeurope.openai.azure.com/")

    assert endpoint == "https://flowcheck-westeurope.openai.azure.com"


def test_openai_config_resolver_uses_server_allowlist_not_client_input():
    config = resolve_azure_openai_config(
        env={
            "FLOWCHECK_AZURE_ADAPTERS_ENABLED": "true",
            "FLOWCHECK_AZURE_AUTH_MODE": "entra",
            "AZURE_OPENAI_ENDPOINT": "https://flowcheck-westeurope.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "flowcheck-gpt",
            "AZURE_OPENAI_SCOPE": "https://cognitiveservices.azure.com/.default",
            "FLOWCHECK_AZURE_ALLOWED_REGION": "westeurope",
            "FLOWCHECK_AZURE_ENDPOINT_HOST_ALLOWLIST": "flowcheck-westeurope.openai.azure.com",
        }
    )

    assert config.endpoint == "https://flowcheck-westeurope.openai.azure.com"


def test_openai_custom_subdomain_does_not_require_region_in_hostname():
    config = resolve_azure_openai_config(
        env={
            "FLOWCHECK_AZURE_ADAPTERS_ENABLED": "true",
            "FLOWCHECK_AZURE_AUTH_MODE": "entra",
            "AZURE_OPENAI_ENDPOINT": "https://flowcheck-nonprod-openai.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-5-5-eu-datazone-quality",
            "AZURE_OPENAI_SCOPE": "https://cognitiveservices.azure.com/.default",
            "FLOWCHECK_AZURE_ALLOWED_REGION": "germanywestcentral",
            "FLOWCHECK_AZURE_ENDPOINT_HOST_ALLOWLIST": "flowcheck-nonprod-openai.openai.azure.com",
        }
    )

    assert config.endpoint == "https://flowcheck-nonprod-openai.openai.azure.com"
