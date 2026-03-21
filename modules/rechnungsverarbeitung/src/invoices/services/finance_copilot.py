"""Finance Copilot – AI-powered chat for invoice intelligence.

Uses Gemini/Claude to answer questions about invoices, spend patterns,
anomalies, and DATEV compliance based on real database data.

Architecture:
    1. User asks question in natural language
    2. System queries DB for relevant context (invoices, events, stats)
    3. AI generates answer grounded in actual data
    4. Response includes sources and suggested follow-ups
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text

from shared.db.session import get_session

load_dotenv()
logger = logging.getLogger(__name__)

# Optional LlamaIndex RAG enhancement
try:
    from modules.rechnungsverarbeitung.src.invoices.services.llama_index_service import LlamaIndexService
    _llama_service = LlamaIndexService()
except Exception:
    _llama_service = None



class FinanceCopilotService:
    """AI-powered finance assistant with DB-grounded answers."""

    def __init__(self) -> None:
        self.gemini_key = os.getenv("GOOGLE_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    # ------------------------------------------------------------------
    # DB Context Builders
    # ------------------------------------------------------------------
    def _get_invoice_summary(self, tenant_id: str) -> dict[str, Any]:
        """Aggregate invoice statistics for tenant."""
        with get_session() as s:
            total = s.execute(
                text("SELECT COUNT(*) FROM invoices WHERE tenant_id = :t"),
                {"t": tenant_id},
            ).scalar() or 0

            by_status = s.execute(
                text("""
                    SELECT status, COUNT(*) as cnt
                    FROM invoices WHERE tenant_id = :t
                    GROUP BY status ORDER BY cnt DESC
                """),
                {"t": tenant_id},
            ).fetchall()

            recent = s.execute(
                text("""
                    SELECT document_id, file_name, status, uploaded_at, uploaded_by
                    FROM invoices WHERE tenant_id = :t
                    ORDER BY uploaded_at DESC LIMIT 10
                """),
                {"t": tenant_id},
            ).fetchall()

            events_recent = s.execute(
                text("""
                    SELECT e.document_id, e.event_type, e.status_from, e.status_to,
                           e.actor, e.created_at, e.details
                    FROM invoice_events e
                    WHERE e.tenant_id = :t
                    ORDER BY e.created_at DESC LIMIT 20
                """),
                {"t": tenant_id},
            ).fetchall()

        return {
            "total_invoices": total,
            "by_status": [{"status": r[0], "count": r[1]} for r in by_status],
            "recent_invoices": [
                {
                    "document_id": r[0][:12],
                    "file_name": r[1],
                    "status": r[2],
                    "uploaded_at": r[3].isoformat() if r[3] else None,
                    "uploaded_by": r[4],
                }
                for r in recent
            ],
            "recent_events": [
                {
                    "document_id": r[0][:12],
                    "event_type": r[1],
                    "from": r[2],
                    "to": r[3],
                    "actor": r[4],
                    "timestamp": r[5].isoformat() if r[5] else None,
                    "details": r[6] if isinstance(r[6], dict) else {},
                }
                for r in events_recent
            ],
        }

    def _get_kontierung_stats(self, tenant_id: str) -> dict[str, Any]:
        """Get AI kontierung statistics."""
        with get_session() as s:
            kontierung_events = s.execute(
                text("""
                    SELECT e.details
                    FROM invoice_events e
                    WHERE e.tenant_id = :t
                      AND e.event_type = 'kontierung_suggested'
                    ORDER BY e.created_at DESC LIMIT 20
                """),
                {"t": tenant_id},
            ).fetchall()

        models = {}
        confidences = []
        konten = {}
        for row in kontierung_events:
            details = row[0] if isinstance(row[0], dict) else {}
            model = details.get("model", "unknown")
            models[model] = models.get(model, 0) + 1
            conf = details.get("confidence", 0)
            if conf:
                confidences.append(conf)
            konto = details.get("konto", "")
            if konto:
                konten[konto] = konten.get(konto, 0) + 1

        return {
            "total_kontierungen": len(kontierung_events),
            "models_used": models,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "top_konten": dict(sorted(konten.items(), key=lambda x: -x[1])[:5]),
        }

    def _build_system_prompt(self) -> str:
        return """Du bist der SBS Nexus Finance Copilot – ein KI-Finanzassistent für deutsche Unternehmen.

ROLLE:
- Du beantwortest Fragen zu Eingangsrechnungen, Kontierungen, DATEV-Exporten und Spend-Analysen.
- Du basierst ALLE Antworten auf den bereitgestellten Echtzeitdaten aus der Datenbank.
- Du sprichst professionelles Deutsch, wie ein erfahrener Buchhalter/Controller.

REGELN:
- Antworte präzise und datengestützt. Nenne konkrete Zahlen.
- Wenn Daten fehlen, sage das ehrlich.
- Gib am Ende 2-3 Folgefragen als Vorschläge.
- Formatiere mit Markdown: **fett** für KPIs, `code` für IDs/Konten.
- Halte Antworten auf 150-250 Wörter.
- Erwähne relevante SKR03-Konten wenn passend.
- Bei Anomalien oder Auffälligkeiten weise proaktiv darauf hin.

KONTEXT: Du arbeitest mit dem SBS Nexus E-Rechnungs-System das XRechnung/ZUGFeRD verarbeitet,
KI-Kontierung (Gemini/Claude) durchführt, und DATEV-Exporte im SKR03-Format erstellt.
Das System hat einen 9-Status Workflow: uploaded → classified → validated → suggested → approved → exported → archived."""

    # ------------------------------------------------------------------
    # AI Chat
    # ------------------------------------------------------------------
    def chat(
        self,
        question: str,
        tenant_id: str,
        conversation_history: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Process a chat question and return AI-generated answer.

        Returns:
            dict with keys: answer, sources, suggested_questions, model, context_used
        """
        # 1. Gather DB context
        summary = self._get_invoice_summary(tenant_id)
        kontierung = self._get_kontierung_stats(tenant_id)

        context = f"""
AKTUELLE DATENBANK-STATISTIKEN (Tenant: {tenant_id}):

RECHNUNGEN:
- Gesamt: {summary['total_invoices']}
- Nach Status: {json.dumps(summary['by_status'], ensure_ascii=False)}

LETZTE RECHNUNGEN:
{json.dumps(summary['recent_invoices'], ensure_ascii=False, indent=2)}

KI-KONTIERUNG:
- Durchgeführt: {kontierung['total_kontierungen']}
- Modelle: {json.dumps(kontierung['models_used'])}
- Ø Confidence: {kontierung['avg_confidence']:.0%}
- Häufigste Konten: {json.dumps(kontierung['top_konten'])}

LETZTE EVENTS:
{json.dumps(summary['recent_events'][:10], ensure_ascii=False, indent=2)}
"""

        # 2. Build messages
        messages = []
        if conversation_history:
            for msg in conversation_history[-6:]:  # Keep last 3 exchanges
                messages.append(msg)
        messages.append({"role": "user", "content": f"{context}\n\nFRAGE: {question}"})

        # 3. Try Gemini first, then Claude
        answer, model = self._call_gemini(messages)
        if not answer:
            answer, model = self._call_claude(messages)
        if not answer:
            answer = self._fallback_answer(question, summary, kontierung)
            model = "rules-v1"

        # 4. Generate suggested questions
        suggested = self._generate_suggestions(question, summary)

        return {
            "answer": answer,
            "model": model,
            "sources": {
                "invoices_analyzed": summary["total_invoices"],
                "events_analyzed": len(summary["recent_events"]),
                "kontierungen_analyzed": kontierung["total_kontierungen"],
            },
            "suggested_questions": suggested,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _call_gemini(self, messages: list[dict]) -> tuple[str, str]:
        """Call Gemini 2.0 Flash."""
        if not self.gemini_key:
            return "", ""
        try:
            from google import genai

            client = genai.Client(api_key=self.gemini_key)
            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=self._build_system_prompt(),
            )

            # Convert messages to Gemini format
            history = []
            for msg in messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                history.append({"role": role, "parts": [msg["content"]]})

            chat = model.start_chat(history=history)
            response = chat.send_message(messages[-1]["content"])
            return response.text, "gemini-2.5-flash"
        except Exception as e:
            logger.warning(f"gemini_copilot_error: {e}")
            return "", ""

    def _call_claude(self, messages: list[dict]) -> tuple[str, str]:
        """Call Claude Sonnet as fallback."""
        if not self.anthropic_key:
            return "", ""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.anthropic_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system=self._build_system_prompt(),
                messages=messages,
            )
            return response.content[0].text, "claude-sonnet-4"
        except Exception as e:
            logger.warning(f"claude_copilot_error: {e}")
            return "", ""

    def _fallback_answer(
        self, question: str, summary: dict, kontierung: dict
    ) -> str:
        """Rule-based fallback when AI unavailable."""
        total = summary["total_invoices"]
        statuses = {s["status"]: s["count"] for s in summary["by_status"]}

        return (
            f"**Übersicht Ihres Rechnungseingangs:**\n\n"
            f"Aktuell befinden sich **{total} Rechnungen** im System.\n"
            f"Davon: {', '.join(f'{v}x {k}' for k, v in statuses.items())}.\n\n"
            f"Die KI-Kontierung hat **{kontierung['total_kontierungen']}** Vorschläge "
            f"mit einer Ø-Confidence von **{kontierung['avg_confidence']:.0%}** generiert.\n\n"
            f"_Hinweis: Diese Antwort wurde regelbasiert erstellt. "
            f"Für detailliertere Analysen wird eine AI-Verbindung benötigt._"
        )

    def _generate_suggestions(self, question: str, summary: dict) -> list[str]:
        """Generate contextual follow-up questions."""
        q = question.lower()
        suggestions = []

        statuses = {s["status"]: s["count"] for s in summary["by_status"]}

        if statuses.get("suggested", 0) > 0:
            suggestions.append(
                f"Es gibt {statuses['suggested']} Rechnungen mit KI-Vorschlag. Soll ich die Details zeigen?"
            )
        if statuses.get("approved", 0) > 0:
            suggestions.append(
                f"{statuses['approved']} freigegebene Rechnungen warten auf DATEV-Export. Batch starten?"
            )
        if "kontierung" not in q and "konto" not in q:
            suggestions.append("Wie verteilen sich die Konten bei der KI-Kontierung?")
        if "trend" not in q:
            suggestions.append("Zeige mir den Rechnungstrend der letzten Wochen.")
        if "audit" not in q:
            suggestions.append("Gibt es Auffälligkeiten in der Audit-Chain?")

        return suggestions[:3]
