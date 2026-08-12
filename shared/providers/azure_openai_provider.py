"""Azure OpenAI adapter for guarded FlowCheck+ inference calls."""
from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from shared.inference_policy import (
    DataClass,
    InferenceProfile,
    InferenceProvider,
    assert_inference_allowed,
)
from shared.providers.provider_factory import (
    AzureProviderError,
    resolve_azure_openai_config,
)
from shared.providers.azure_identity import resolve_azure_credential
from shared.provider_governance import assert_provider_governance_allowed
from shared.secure_logging import log_inference_event


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AzureOpenAIResult:
    content: str
    model: str
    provider: str
    policy_decision: str


def _token_provider_factory(credential: Any, scope: str) -> Callable[[], str]:
    try:
        from azure.identity import get_bearer_token_provider
    except Exception as exc:  # pragma: no cover
        raise AzureProviderError(
            "AZURE_AUTH_UNAVAILABLE",
            "azure_token_provider_not_available",
            provider=InferenceProvider.AZURE_OPENAI_EU,
        ) from None
    return get_bearer_token_provider(credential, scope)


def _azure_openai_client_factory(*, azure_endpoint: str, azure_ad_token_provider: Callable[[], str], api_version: str) -> Any:
    try:
        from openai import AzureOpenAI
    except Exception as exc:  # pragma: no cover
        raise AzureProviderError(
            "AZURE_OPENAI_UNAVAILABLE",
            "azure_openai_client_not_available",
            provider=InferenceProvider.AZURE_OPENAI_EU,
        ) from None
    return AzureOpenAI(
        azure_endpoint=azure_endpoint,
        azure_ad_token_provider=azure_ad_token_provider,
        api_version=api_version,
    )


class AzureOpenAIProvider:
    """Azure OpenAI provider using Entra ID only."""

    provider = InferenceProvider.AZURE_OPENAI_EU

    def __init__(
        self,
        *,
        settings: Any | None = None,
        env: Mapping[str, str] | None = None,
        credential_factory: Callable[[], Any] | None = None,
        token_provider_factory: Callable[[Any, str], Callable[[], str]] | None = None,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.settings = settings
        self.env = env
        self.credential_factory = credential_factory
        self.token_provider_factory = token_provider_factory or _token_provider_factory
        self.client_factory = client_factory or _azure_openai_client_factory

    def create_chat_completion(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        data_class: DataClass | str,
        inference_profile: InferenceProfile | str,
        purpose: str,
        temperature: float = 0,
        response_format: Mapping[str, str] | None = None,
        max_tokens: int | None = None,
    ) -> AzureOpenAIResult:
        decision = assert_inference_allowed(
            data_class=data_class,
            inference_profile=inference_profile,
            provider=self.provider,
            purpose=purpose,
        )

        config = resolve_azure_openai_config(settings=self.settings, env=self.env)
        assert_provider_governance_allowed(
            data_class=data_class,
            inference_profile=inference_profile,
            provider=self.provider,
            purpose=purpose,
            endpoint_host=urlparse(config.endpoint).hostname or "",
            model_deployment_id=config.deployment,
            settings=self.settings,
            env=self.env,
        )
        client = self._build_client(config)
        request_kwargs: dict[str, Any] = {
            "model": config.deployment,
            "messages": list(messages),
            "temperature": temperature,
        }
        if response_format is not None:
            request_kwargs["response_format"] = dict(response_format)
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens

        try:
            response = client.chat.completions.create(**request_kwargs)
        except AzureProviderError:
            raise
        except Exception as exc:
            raise AzureProviderError(
                self._request_error_code(exc),
                self._request_reason_code(exc),
                provider=self.provider,
                retryable=True,
            ) from None

        content = self._extract_content(response)
        log_inference_event(
            logger,
            event="azure_openai_request_succeeded",
            provider=self.provider.value,
            model=config.deployment,
            data_class=decision.data_class,
            inference_profile=decision.inference_profile,
            policy_decision=decision.policy_decision,
        )
        return AzureOpenAIResult(
            content=content,
            model=config.deployment,
            provider=self.provider.value,
            policy_decision=decision.policy_decision,
        )

    def complete_json(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        data_class: DataClass | str,
        inference_profile: InferenceProfile | str,
        purpose: str,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        result = self.create_chat_completion(
            messages=messages,
            data_class=data_class,
            inference_profile=inference_profile,
            purpose=purpose,
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
        )
        try:
            return json.loads(result.content)
        except json.JSONDecodeError as exc:
            raise AzureProviderError(
                "AZURE_OPENAI_RESPONSE_INVALID",
                "response_was_not_valid_json",
                provider=self.provider,
            ) from None

    def _build_client(self, config: Any) -> Any:
        try:
            credential = (
                self.credential_factory()
                if self.credential_factory is not None
                else resolve_azure_credential(
                    provider=self.provider,
                    settings=self.settings,
                    env=self.env,
                )
            )
            token_provider = self.token_provider_factory(credential, config.scope)
            return self.client_factory(
                azure_endpoint=config.endpoint,
                azure_ad_token_provider=token_provider,
                api_version=config.api_version,
            )
        except AzureProviderError:
            raise
        except Exception as exc:
            raise AzureProviderError(
                "AZURE_AUTH_UNAVAILABLE",
                "entra_credential_unavailable",
                provider=self.provider,
            ) from None

    def _extract_content(self, response: Any) -> str:
        try:
            content = response.choices[0].message.content
        except Exception as exc:
            raise AzureProviderError(
                "AZURE_OPENAI_RESPONSE_INVALID",
                "missing_choice_message_content",
                provider=self.provider,
            ) from None
        if not isinstance(content, str) or not content.strip():
            raise AzureProviderError(
                "AZURE_OPENAI_RESPONSE_INVALID",
                "empty_response_content",
                provider=self.provider,
            )
        return content

    @staticmethod
    def _request_error_code(exc: Exception) -> str:
        error_type = type(exc).__name__.lower()
        if "credential" in error_type or "auth" in error_type:
            return "AZURE_AUTH_UNAVAILABLE"
        return "AZURE_OPENAI_REQUEST_FAILED"

    @staticmethod
    def _request_reason_code(exc: Exception) -> str:
        error_type = type(exc).__name__.lower()
        if "credential" in error_type or "auth" in error_type:
            return "entra_auth_failed"
        return "azure_openai_request_failed"
