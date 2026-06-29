"""Azure Document Intelligence adapter for guarded invoice analysis."""
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from shared.inference_policy import (
    DataClass,
    InferenceProfile,
    InferenceProvider,
    assert_inference_allowed,
)
from shared.providers.provider_factory import AzureProviderError, resolve_azure_document_intelligence_config
from shared.providers.azure_identity import resolve_azure_credential
from shared.secure_logging import log_inference_event


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AzureDocumentIntelligenceResult:
    invoice_data: dict[str, Any]
    provider: str
    model: str
    policy_decision: str


def _document_intelligence_client_factory(*, endpoint: str, credential: Any) -> Any:
    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
    except Exception as exc:  # pragma: no cover
        raise AzureProviderError(
            "AZURE_DOCINTEL_UNAVAILABLE",
            "document_intelligence_client_not_available",
            provider=InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU,
        ) from None
    return DocumentIntelligenceClient(endpoint=endpoint, credential=credential)


class AzureDocumentIntelligenceProvider:
    """Invoice extraction through Azure Document Intelligence prebuilt-invoice."""

    provider = InferenceProvider.AZURE_DOCUMENT_INTELLIGENCE_EU

    def __init__(
        self,
        *,
        settings: Any | None = None,
        env: Mapping[str, str] | None = None,
        credential_factory: Callable[[], Any] | None = None,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.settings = settings
        self.env = env
        self.credential_factory = credential_factory
        self.client_factory = client_factory or _document_intelligence_client_factory

    def analyze_invoice(
        self,
        *,
        file_bytes: bytes | bytearray | memoryview,
        mime_type: str,
        data_class: DataClass | str,
        inference_profile: InferenceProfile | str,
        purpose: str = "invoice_document_intelligence_extraction",
        url_source: str | None = None,
    ) -> AzureDocumentIntelligenceResult:
        if url_source:
            raise AzureProviderError(
                "AZURE_DOCINTEL_REQUEST_FAILED",
                "url_source_not_allowed",
                provider=self.provider,
            )
        if not isinstance(file_bytes, (bytes, bytearray, memoryview)):
            raise AzureProviderError(
                "AZURE_DOCINTEL_REQUEST_FAILED",
                "byte_input_required",
                provider=self.provider,
            )

        decision = assert_inference_allowed(
            data_class=data_class,
            inference_profile=inference_profile,
            provider=self.provider,
            purpose=purpose,
        )
        config = resolve_azure_document_intelligence_config(settings=self.settings, env=self.env)
        client = self._build_client(config)

        try:
            poller = client.begin_analyze_document(
                config.model,
                body=bytes(file_bytes),
                content_type=mime_type,
            )
            response = poller.result()
        except AzureProviderError:
            raise
        except Exception as exc:
            raise AzureProviderError(
                self._request_error_code(exc),
                self._request_reason_code(exc),
                provider=self.provider,
                retryable=True,
            ) from None

        invoice_data = self._normalize_response(response)
        log_inference_event(
            logger,
            event="azure_docintel_invoice_analyzed",
            provider=self.provider.value,
            model=config.model,
            data_class=decision.data_class,
            inference_profile=decision.inference_profile,
            policy_decision=decision.policy_decision,
            fields_present=sorted(key for key, value in invoice_data.items() if value not in (None, "", [], {})),
        )
        return AzureDocumentIntelligenceResult(
            invoice_data=invoice_data,
            provider=self.provider.value,
            model=config.model,
            policy_decision=decision.policy_decision,
        )

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
            return self.client_factory(endpoint=config.endpoint, credential=credential)
        except AzureProviderError:
            raise
        except Exception as exc:
            raise AzureProviderError(
                "AZURE_AUTH_UNAVAILABLE",
                "entra_credential_unavailable",
                provider=self.provider,
            ) from None

    def _normalize_response(self, response: Any) -> dict[str, Any]:
        documents = getattr(response, "documents", None) or []
        if not documents:
            raise AzureProviderError(
                "AZURE_DOCINTEL_RESPONSE_INVALID",
                "no_invoice_documents_returned",
                provider=self.provider,
            )
        fields = getattr(documents[0], "fields", None) or {}
        if not isinstance(fields, Mapping):
            raise AzureProviderError(
                "AZURE_DOCINTEL_RESPONSE_INVALID",
                "invoice_fields_missing",
                provider=self.provider,
            )

        invoice_total = self._currency_field(fields.get("InvoiceTotal"))
        sub_total = self._currency_field(fields.get("SubTotal"))
        total_tax = self._currency_field(fields.get("TotalTax"))
        normalized = {
            "rechnungsaussteller": self._field_value(fields.get("VendorName")),
            "rechnungsnummer": self._field_value(fields.get("InvoiceId")),
            "datum": self._date_value(fields.get("InvoiceDate")),
            "faelligkeitsdatum": self._date_value(fields.get("DueDate")),
            "betrag_brutto": invoice_total.get("amount"),
            "betrag_netto": sub_total.get("amount"),
            "mwst_betrag": total_tax.get("amount"),
            "waehrung": invoice_total.get("currency") or sub_total.get("currency") or total_tax.get("currency") or "EUR",
            "extraction_method": "azure_document_intelligence",
            "confidence": self._average_confidence(fields),
        }
        return normalized

    def _field_value(self, field: Any) -> Any:
        if field is None:
            return None
        for attr in ("value_string", "value_number", "value_integer", "value_date", "content"):
            value = getattr(field, attr, None)
            if value not in (None, ""):
                return self._serialize_value(value)
        return None

    def _date_value(self, field: Any) -> str | None:
        value = self._field_value(field)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value) if value else None

    def _currency_field(self, field: Any) -> dict[str, Any]:
        currency = getattr(field, "value_currency", None) if field is not None else None
        if currency is None:
            value = self._field_value(field)
            return {"amount": value if isinstance(value, (int, float)) else None, "currency": None}
        amount = getattr(currency, "amount", None)
        currency_code = getattr(currency, "currency_code", None) or getattr(currency, "code", None)
        return {"amount": amount, "currency": currency_code}

    def _average_confidence(self, fields: Mapping[str, Any]) -> float:
        confidences = [
            float(confidence)
            for field in fields.values()
            if (confidence := getattr(field, "confidence", None)) is not None
        ]
        if not confidences:
            return 0.0
        return round(sum(confidences) / len(confidences), 4)

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

    @staticmethod
    def _request_error_code(exc: Exception) -> str:
        error_type = type(exc).__name__.lower()
        if "model" in error_type or "notfound" in error_type:
            return "AZURE_DOCINTEL_MODEL_UNAVAILABLE"
        if "credential" in error_type or "auth" in error_type:
            return "AZURE_AUTH_UNAVAILABLE"
        return "AZURE_DOCINTEL_REQUEST_FAILED"

    @staticmethod
    def _request_reason_code(exc: Exception) -> str:
        error_type = type(exc).__name__.lower()
        if "model" in error_type or "notfound" in error_type:
            return "prebuilt_invoice_model_unavailable"
        if "credential" in error_type or "auth" in error_type:
            return "entra_auth_failed"
        return "azure_docintel_request_failed"
