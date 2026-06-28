"""Data-class and profile resolution helpers for FlowCheck+ inference calls."""
from __future__ import annotations

import os
from collections.abc import Mapping

from shared.inference_policy import DataClass, InferenceProfile, InferenceProvider


DEFAULT_DATA_CLASS = DataClass.INVOICE_CONFIDENTIAL
DEFAULT_INFERENCE_PROFILE = InferenceProfile.STANDARD


def coerce_data_class(value: DataClass | str | None) -> DataClass | str:
    """Return a known ``DataClass`` or the raw value so policy can fail closed."""
    if value is None or value == "":
        return DEFAULT_DATA_CLASS
    if isinstance(value, DataClass):
        return value
    try:
        return DataClass(str(value))
    except ValueError:
        return str(value)


def coerce_inference_profile(value: InferenceProfile | str | None) -> InferenceProfile | str:
    """Return a known ``InferenceProfile`` or the raw value for fail-closed policy."""
    if value is None or value == "":
        value = os.getenv("FLOWCHECK_DEFAULT_INFERENCE_PROFILE", DEFAULT_INFERENCE_PROFILE.value)
    if isinstance(value, InferenceProfile):
        return value
    try:
        return InferenceProfile(str(value))
    except ValueError:
        return str(value)


def classify_invoice_data(
    *,
    explicit_data_class: DataClass | str | None = None,
    demo: bool = False,
) -> DataClass | str:
    """Resolve the data class for invoice/OCR/DATEV/MBR-related inference.

    Existing records default to ``invoice_confidential`` for backward
    compatibility. Explicit values are preserved so the policy can block
    unknown or secret classes instead of silently downgrading them.
    """
    if explicit_data_class is not None:
        return coerce_data_class(explicit_data_class)
    if demo:
        return DataClass.DEMO
    return DEFAULT_DATA_CLASS


def resolve_inference_profile(
    explicit_profile: InferenceProfile | str | None = None,
) -> InferenceProfile | str:
    """Resolve the active inference profile from an explicit value or env."""
    return coerce_inference_profile(explicit_profile)


def resolve_provider_configured(
    provider: InferenceProvider | str,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Best-effort provider configuration check for adapters.

    Direct providers require their API key. Azure/local providers require the
    phase-1 placeholder configuration. This helper does not read or expose
    secret values.
    """
    source = env if env is not None else os.environ
    try:
        provider_enum = provider if isinstance(provider, InferenceProvider) else InferenceProvider(str(provider))
    except ValueError:
        return False

    if provider_enum == InferenceProvider.OPENAI_DIRECT:
        return bool(source.get("OPENAI_API_KEY"))
    if provider_enum == InferenceProvider.ANTHROPIC_DIRECT:
        return bool(source.get("ANTHROPIC_API_KEY"))
    if provider_enum == InferenceProvider.GEMINI_DIRECT:
        return bool(source.get("GEMINI_API_KEY") or source.get("GOOGLE_API_KEY"))
    if provider_enum == InferenceProvider.AZURE_OPENAI_EU:
        return bool(source.get("AZURE_OPENAI_ENDPOINT") and source.get("AZURE_OPENAI_DEPLOYMENT"))
    if provider_enum == InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU:
        return bool(
            source.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            or source.get("AZURE_FORM_RECOGNIZER_ENDPOINT")
        )
    if provider_enum == InferenceProvider.LOCAL_OPENAI_COMPAT:
        return bool(source.get("LOCAL_LLM_BASE_URL") and source.get("LOCAL_LLM_MODEL"))
    if provider_enum == InferenceProvider.LOCAL_OCR:
        return str(source.get("LOCAL_OCR_ENABLED", "")).strip().lower() in {"1", "true", "yes", "on"}
    return False
