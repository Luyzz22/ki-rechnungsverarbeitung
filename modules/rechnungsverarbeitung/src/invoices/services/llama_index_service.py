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
load_dotenv("/var/www/invoice-app/.env")

logger = logging.getLogger(__name__)


class LlamaIndexService:
    """RAG service for intelligent invoice querying."""

    def __init__(self):
        self.api_key = os.getenv("LLAMAINDEX_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._index = None

    def build_invoice_index(self, tenant_id: str) -> int:
        """Build/rebuild the invoice index for a tenant."""
        try:
            from llama_index.core import VectorStoreIndex, Document, Settings
            from llama_index.llms.gemini import Gemini

            # Configure LLM
            if self.gemini_key:
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
                logger.info(f"No invoices for tenant {tenant_id}")
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
            logger.info(f"LlamaIndex: indexed {len(documents)} invoices for {tenant_id}")
            return len(documents)

        except Exception as e:
            logger.warning(f"LlamaIndex build failed: {e}")
            return 0

    def query(self, question: str, tenant_id: str) -> Optional[dict]:
        """Query the invoice index with natural language."""
        try:
            if not self._index:
                count = self.build_invoice_index(tenant_id)
                if count == 0:
                    return None

            query_engine = self._index.as_query_engine(
                similarity_top_k=5,
            )
            response = query_engine.query(question)

            return {
                "answer": str(response),
                "model": "llama-index-gemini-2.5",
                "sources": len(response.source_nodes) if hasattr(response, "source_nodes") else 0,
            }

        except Exception as e:
            logger.warning(f"LlamaIndex query failed: {e}")
            return None
