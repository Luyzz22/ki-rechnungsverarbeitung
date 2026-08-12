"""LlamaIndex Integration for BelegFlow AI.

Provides RAG (Retrieval Augmented Generation) over invoice data
for the Finance Copilot. Uses LlamaIndex to index all invoice
metadata and extracted data for intelligent querying.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from dotenv import load_dotenv
from shared.data_classification import classify_invoice_data, resolve_inference_profile
from shared.inference_policy import (
    InferencePolicyDeniedError,
    InferenceProvider,
    assert_inference_allowed,
)
from shared.organization_context import (
    OrganizationContextError,
    TrustedOrganizationContext,
    assert_organization_inference_allowed,
)
from shared.secure_logging import log_inference_event, safe_log
load_dotenv("/var/www/invoice-app/.env")

logger = logging.getLogger(__name__)


class LlamaIndexService:
    """RAG service for intelligent invoice querying."""

    def __init__(self):
        self.api_key = os.getenv("LLAMAINDEX_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._index = None

    def build_invoice_index(
        self,
        tenant_id: str,
        data_class: str | None = None,
        inference_profile: str | None = None,
        organization_context: TrustedOrganizationContext | None = None,
    ) -> int:
        """Build/rebuild the invoice index for a tenant."""
        try:
            from llama_index.core import VectorStoreIndex, Document, Settings
            from llama_index.llms.gemini import Gemini

            # Configure LLM
            if self.gemini_key:
                resolved_data_class = classify_invoice_data(explicit_data_class=data_class)
                requested_profile = resolve_inference_profile(inference_profile)
                resolved_profile = assert_organization_inference_allowed(
                    organization_context=organization_context,
                    data_class=resolved_data_class,
                    requested_inference_profile=requested_profile,
                    provider=InferenceProvider.GEMINI_DIRECT,
                )
                decision = assert_inference_allowed(
                    data_class=resolved_data_class,
                    inference_profile=resolved_profile,
                    provider=InferenceProvider.GEMINI_DIRECT,
                    purpose="invoice_rag_index",
                )
                Settings.llm = Gemini(model="models/gemini-2.5-flash", api_key=self.gemini_key)

            # Load invoice data from DB
            from shared.db.session import get_session
            from sqlalchemy import text

            with get_session() as s:
                rows = s.execute(text("""
                    SELECT document_id, file_name, status, supplier, total_amount,
                           currency, invoice_number, invoice_date, due_date, extracted_data
                    FROM invoices WHERE tenant_id = :t
                """), {"t": tenant_id}).fetchall()

            if not rows:
                safe_log(logger, logging.INFO, "invoice_rag_no_invoices", tenant_id=tenant_id)
                return 0

            # Create documents for indexing
            documents = []
            for r in rows:
                doc_text = f"""Rechnung {r[3] or r[1] or r[0]}:
Lieferant: {r[3] or 'Unbekannt'}
Rechnungsnummer: {r[6] or 'Unbekannt'}
Betrag: {r[4] or 0} {r[5] or 'EUR'}
Rechnungsdatum: {r[7] or 'Unbekannt'}
Fälligkeitsdatum: {r[8] or 'Unbekannt'}
Status: {r[2]}
Dateiname: {r[1] or 'Unbekannt'}
"""
                if r[9]:  # extracted_data JSON
                    try:
                        extra = json.loads(r[9]) if isinstance(r[9], str) else r[9]
                        if extra.get("line_items"):
                            doc_text += "Positionen:\n"
                            for item in extra["line_items"]:
                                doc_text += f"  - {item.get('description','')}: {item.get('total',0)} EUR\n"
                    except Exception:
                        pass

                documents.append(Document(
                    text=doc_text,
                    metadata={
                        "document_id": r[0],
                        "supplier": r[3] or "",
                        "amount": float(r[4]) if r[4] else 0,
                        "status": r[2],
                    }
                ))

            # Build index
            self._index = VectorStoreIndex.from_documents(documents)
            if self.gemini_key:
                log_inference_event(
                    logger,
                    event="invoice_rag_index_built",
                    provider=InferenceProvider.GEMINI_DIRECT.value,
                    model="models/gemini-2.5-flash",
                    data_class=decision.data_class,
                    inference_profile=decision.inference_profile,
                    policy_decision=decision.policy_decision,
                    tenant_id=tenant_id,
                    document_count=len(documents),
                )
            else:
                safe_log(logger, logging.INFO, "invoice_rag_index_built", tenant_id=tenant_id, document_count=len(documents))
            return len(documents)

        except (InferencePolicyDeniedError, OrganizationContextError):
            raise
        except Exception as e:
            safe_log(logger, logging.WARNING, "llama_index_build_failed", error_code=type(e).__name__)
            return 0

    def query(
        self,
        question: str,
        tenant_id: str,
        data_class: str | None = None,
        inference_profile: str | None = None,
        organization_context: TrustedOrganizationContext | None = None,
    ) -> Optional[dict]:
        """Query the invoice index with natural language."""
        try:
            if not self._index:
                count = self.build_invoice_index(
                    tenant_id,
                    data_class=data_class,
                    inference_profile=inference_profile,
                    organization_context=organization_context,
                )
                if count == 0:
                    return None

            if self.gemini_key:
                resolved_data_class = classify_invoice_data(explicit_data_class=data_class)
                requested_profile = resolve_inference_profile(inference_profile)
                resolved_profile = assert_organization_inference_allowed(
                    organization_context=organization_context,
                    data_class=resolved_data_class,
                    requested_inference_profile=requested_profile,
                    provider=InferenceProvider.GEMINI_DIRECT,
                )
                decision = assert_inference_allowed(
                    data_class=resolved_data_class,
                    inference_profile=resolved_profile,
                    provider=InferenceProvider.GEMINI_DIRECT,
                    purpose="invoice_rag_query",
                )

            query_engine = self._index.as_query_engine(
                similarity_top_k=5,
            )
            response = query_engine.query(question)
            if self.gemini_key:
                log_inference_event(
                    logger,
                    event="invoice_rag_query_completed",
                    provider=InferenceProvider.GEMINI_DIRECT.value,
                    model="models/gemini-2.5-flash",
                    data_class=decision.data_class,
                    inference_profile=decision.inference_profile,
                    policy_decision=decision.policy_decision,
                    tenant_id=tenant_id,
                )

            return {
                "answer": str(response),
                "model": "llama-index-gemini-2.5",
                "sources": len(response.source_nodes) if hasattr(response, "source_nodes") else 0,
            }

        except (InferencePolicyDeniedError, OrganizationContextError):
            raise
        except Exception as e:
            safe_log(logger, logging.WARNING, "llama_index_query_failed", error_code=type(e).__name__)
            return None
