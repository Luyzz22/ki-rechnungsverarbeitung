"""Central inference policy guard for FlowCheck+.

This module is intentionally framework-free so it can be reused by legacy
routes, modular services, background jobs, and unit tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


POLICY_VERSION = "flowcheck-inference-policy-v1"


class DataClass(str, Enum):
    DEMO = "demo"
    INTERNAL = "internal"
    PERSONAL_DATA = "personal_data"
    INVOICE_CONFIDENTIAL = "invoice_confidential"
    PROFESSIONAL_SECRET = "professional_secret"
    SOVEREIGN_SECRET = "sovereign_secret"


class InferenceProfile(str, Enum):
    STANDARD = "standard"
    PROFESSIONAL_SECRECY = "professional_secrecy"
    SOVEREIGN = "sovereign"


class InferenceProvider(str, Enum):
    OPENAI_DIRECT = "openai_direct"
    ANTHROPIC_DIRECT = "anthropic_direct"
    GEMINI_DIRECT = "gemini_direct"
    AZURE_OPENAI_EU = "azure_openai_eu"
    LOCAL_OPENAI_COMPAT = "local_openai_compat"
    LOCAL_OCR = "local_ocr"
    AZURE_DOCUMENT_INTELLIGENCE_EU = "azure_document_intelligence_eu"


DIRECT_PROVIDERS = frozenset(
    {
        InferenceProvider.OPENAI_DIRECT,
        InferenceProvider.ANTHROPIC_DIRECT,
        InferenceProvider.GEMINI_DIRECT,
    }
)

SECRET_DATA_CLASSES = frozenset(
    {
        DataClass.PROFESSIONAL_SECRET,
        DataClass.SOVEREIGN_SECRET,
    }
)

LOCAL_ONLY_PROVIDERS = frozenset(
    {
        InferenceProvider.LOCAL_OPENAI_COMPAT,
        InferenceProvider.LOCAL_OCR,
    }
)

PROFESSIONAL_SECRECY_PROVIDERS = frozenset(
    {
        InferenceProvider.AZURE_OPENAI_EU,
        InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU,
        InferenceProvider.LOCAL_OPENAI_COMPAT,
        InferenceProvider.LOCAL_OCR,
    }
)

ALLOWED_PROVIDERS_BY_PROFILE: dict[InferenceProfile, frozenset[InferenceProvider]] = {
    InferenceProfile.STANDARD: frozenset(InferenceProvider),
    InferenceProfile.PROFESSIONAL_SECRECY: PROFESSIONAL_SECRECY_PROVIDERS,
    InferenceProfile.SOVEREIGN: LOCAL_ONLY_PROVIDERS,
}


@dataclass(frozen=True)
class InferencePolicyDecision:
    """PII-free policy evaluation result."""

    allowed: bool
    data_class: str
    inference_profile: str
    provider: str
    purpose: str
    policy_version: str = POLICY_VERSION
    policy_decision: str = "denied"
    error_code: str | None = None
    reason_code: str | None = None
    blocked_rule: str | None = None
    allowed_providers: tuple[str, ...] = ()

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a structured, PII-free representation for API errors/logs."""
        return {
            "allowed": self.allowed,
            "data_class": self.data_class,
            "inference_profile": self.inference_profile,
            "provider": self.provider,
            "purpose": self.purpose,
            "policy_version": self.policy_version,
            "policy_decision": self.policy_decision,
            "error_code": self.error_code,
            "reason_code": self.reason_code,
            "blocked_rule": self.blocked_rule,
            "allowed_providers": list(self.allowed_providers),
        }


class InferencePolicyDeniedError(RuntimeError):
    """Raised when an inference call is blocked by policy."""

    def __init__(self, decision: InferencePolicyDecision):
        self.decision = decision
        super().__init__(f"{decision.error_code}: {decision.reason_code}")

    @property
    def error_code(self) -> str | None:
        return self.decision.error_code

    def to_safe_dict(self) -> dict[str, Any]:
        return self.decision.to_safe_dict()


def _coerce_enum(value: str | Enum, enum_type: type[Enum]) -> Enum | None:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except (TypeError, ValueError):
        return None


def _allowed_provider_values(profile: InferenceProfile | None) -> tuple[str, ...]:
    if profile is None:
        return ()
    return tuple(sorted(provider.value for provider in ALLOWED_PROVIDERS_BY_PROFILE[profile]))


def _deny(
    *,
    data_class: str,
    inference_profile: str,
    provider: str,
    purpose: str,
    error_code: str,
    reason_code: str,
    blocked_rule: str,
    allowed_providers: tuple[str, ...] = (),
) -> InferencePolicyDecision:
    return InferencePolicyDecision(
        allowed=False,
        data_class=data_class,
        inference_profile=inference_profile,
        provider=provider,
        purpose=purpose,
        policy_decision="denied",
        error_code=error_code,
        reason_code=reason_code,
        blocked_rule=blocked_rule,
        allowed_providers=allowed_providers,
    )


def evaluate_inference_policy(
    *,
    data_class: DataClass | str,
    inference_profile: InferenceProfile | str,
    provider: InferenceProvider | str,
    purpose: str,
    provider_configured: bool | None = None,
) -> InferencePolicyDecision:
    """Evaluate whether an inference provider may process a data class.

    Unknown enum values fail closed. ``provider_configured=False`` can be used
    by provider adapters to make Azure/local unavailability explicit without
    falling back to Direct APIs.
    """
    data_class_value = getattr(data_class, "value", str(data_class))
    profile_value = getattr(inference_profile, "value", str(inference_profile))
    provider_value = getattr(provider, "value", str(provider))
    safe_purpose = str(purpose or "unspecified")[:120]

    data_class_enum = _coerce_enum(data_class, DataClass)
    profile_enum = _coerce_enum(inference_profile, InferenceProfile)
    provider_enum = _coerce_enum(provider, InferenceProvider)

    if data_class_enum is None:
        return _deny(
            data_class=data_class_value,
            inference_profile=profile_value,
            provider=provider_value,
            purpose=safe_purpose,
            error_code="INFERENCE_POLICY_DENIED",
            reason_code="unknown_data_class",
            blocked_rule="unknown_data_class_fail_closed",
        )

    if profile_enum is None:
        return _deny(
            data_class=data_class_enum.value,
            inference_profile=profile_value,
            provider=provider_value,
            purpose=safe_purpose,
            error_code="INFERENCE_POLICY_DENIED",
            reason_code="unknown_inference_profile",
            blocked_rule="unknown_profile_fail_closed",
        )

    if provider_enum is None:
        return _deny(
            data_class=data_class_enum.value,
            inference_profile=profile_enum.value,
            provider=provider_value,
            purpose=safe_purpose,
            error_code="INFERENCE_POLICY_DENIED",
            reason_code="unknown_provider",
            blocked_rule="unknown_provider_fail_closed",
            allowed_providers=_allowed_provider_values(profile_enum),
        )

    allowed_providers = _allowed_provider_values(profile_enum)

    if profile_enum == InferenceProfile.STANDARD:
        if data_class_enum in SECRET_DATA_CLASSES and provider_enum in DIRECT_PROVIDERS:
            return _deny(
                data_class=data_class_enum.value,
                inference_profile=profile_enum.value,
                provider=provider_enum.value,
                purpose=safe_purpose,
                error_code="INFERENCE_POLICY_DENIED",
                reason_code="standard_secret_direct_provider_denied",
                blocked_rule="explicit_secret_data_requires_guarded_provider",
                allowed_providers=allowed_providers,
            )
    elif provider_enum not in ALLOWED_PROVIDERS_BY_PROFILE[profile_enum]:
        return _deny(
            data_class=data_class_enum.value,
            inference_profile=profile_enum.value,
            provider=provider_enum.value,
            purpose=safe_purpose,
            error_code="INFERENCE_POLICY_DENIED",
            reason_code=f"{profile_enum.value}_provider_denied",
            blocked_rule=f"{profile_enum.value}_allowed_provider_set",
            allowed_providers=allowed_providers,
        )

    if provider_configured is False:
        if profile_enum == InferenceProfile.SOVEREIGN:
            return _deny(
                data_class=data_class_enum.value,
                inference_profile=profile_enum.value,
                provider=provider_enum.value,
                purpose=safe_purpose,
                error_code="SOVEREIGN_INFERENCE_UNAVAILABLE",
                reason_code="local_provider_not_configured",
                blocked_rule="sovereign_requires_configured_local_provider",
                allowed_providers=allowed_providers,
            )
        return _deny(
            data_class=data_class_enum.value,
            inference_profile=profile_enum.value,
            provider=provider_enum.value,
            purpose=safe_purpose,
            error_code="INFERENCE_POLICY_DENIED",
            reason_code="provider_not_configured",
            blocked_rule="configured_provider_required",
            allowed_providers=allowed_providers,
        )

    return InferencePolicyDecision(
        allowed=True,
        data_class=data_class_enum.value,
        inference_profile=profile_enum.value,
        provider=provider_enum.value,
        purpose=safe_purpose,
        policy_decision="allowed",
        reason_code=f"{profile_enum.value}_provider_allowed",
        allowed_providers=allowed_providers,
    )


def assert_inference_allowed(
    *,
    data_class: DataClass | str,
    inference_profile: InferenceProfile | str,
    provider: InferenceProvider | str,
    purpose: str,
    provider_configured: bool | None = None,
) -> InferencePolicyDecision:
    """Raise ``InferencePolicyDeniedError`` unless the policy allows the call."""
    decision = evaluate_inference_policy(
        data_class=data_class,
        inference_profile=inference_profile,
        provider=provider,
        purpose=purpose,
        provider_configured=provider_configured,
    )
    if not decision.allowed:
        raise InferencePolicyDeniedError(decision)
    return decision
