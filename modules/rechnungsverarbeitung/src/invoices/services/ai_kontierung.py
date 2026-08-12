"""AI-powered account assignment (Kontierung) service.

Uses Google Gemini 2.0 Flash (primary) or Anthropic Claude (fallback)
to suggest SKR03/SKR04 account assignments from invoice data.

Output:
- Konto (expense account)
- Gegenkonto (offsetting account)
- Steuerschluessel (tax code)
- Kostenstelle (cost center, optional)
- Confidence score
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
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

logger = logging.getLogger(__name__)

KONTIERUNG_PROMPT = """Du bist ein deutscher Buchhalter-Assistent. Analysiere die folgende Rechnung und schlage die korrekte DATEV-Kontierung nach SKR03 vor.

Rechnungsdaten:
{invoice_data}

Antworte ausschließlich als JSON-Objekt mit diesen Feldern:
{{
  "konto": "Sachkonto (z.B. 4400 für Bürobedarf, 4200 für Raumkosten, 3400 für Wareneingang)",
  "gegenkonto": "Gegenkonto (z.B. 1200 Forderungen, 1600 Verbindlichkeiten, 1800 Bank)",
  "steuerschluessel": "DATEV Steuerschlüssel (z.B. 9 für 19% VSt, 8 für 7% VSt, 0 für steuerfrei)",
  "buchungstext": "Kurzer Buchungstext max 60 Zeichen",
  "kostenstelle": "Kostenstelle falls erkennbar, sonst leer",
  "confidence": 0.85,
  "reasoning": "Kurze Begründung der Kontenwahl"
}}

Regeln:
- Verwende NUR gültige SKR03-Konten
- Bei Unklarheit confidence < 0.7 setzen
- Hydraulik/Maschinenbau-Rechnungen: meist 3400 (Wareneingang) oder 4980 (Reparaturen)
- Dienstleistungen: 4900 (sonstige betriebliche Aufwendungen)
"""


@dataclass
class KontierungResult:
    """AI-generated account assignment suggestion."""

    konto: str
    gegenkonto: str
    steuerschluessel: str
    buchungstext: str
    kostenstelle: str
    confidence: float
    reasoning: str
    model: str
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "konto": self.konto,
            "gegenkonto": self.gegenkonto,
            "steuerschluessel": self.steuerschluessel,
            "buchungstext": self.buchungstext,
            "kostenstelle": self.kostenstelle,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "model": self.model,
        }


class AIKontierungService:
    """Suggests DATEV account assignments using AI.

    Tries Gemini first, falls back to Claude, then to rule-based defaults.
    """

    def __init__(self) -> None:
        self.gemini_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    def suggest(
        self,
        invoice_data: dict[str, Any],
        skr: str = "SKR03",
        data_class: str | None = None,
        inference_profile: str | None = None,
        organization_context: TrustedOrganizationContext | None = None,
    ) -> KontierungResult:
        """Generate account assignment suggestion.

        Args:
            invoice_data: Extracted invoice fields (rechnungsnummer, betrag, etc.)
            skr: Chart of accounts (SKR03 or SKR04)

        Returns:
            KontierungResult with suggested accounts and confidence.
        """
        resolved_data_class = classify_invoice_data(explicit_data_class=data_class)
        requested_profile = resolve_inference_profile(inference_profile)

        # Try Gemini first
        if self.gemini_key:
            try:
                resolved_profile = assert_organization_inference_allowed(
                    organization_context=organization_context,
                    data_class=resolved_data_class,
                    requested_inference_profile=requested_profile,
                    provider=InferenceProvider.GEMINI_DIRECT,
                )
                return self._suggest_gemini(
                    invoice_data,
                    skr,
                    data_class=resolved_data_class,
                    inference_profile=resolved_profile,
                    organization_context=organization_context,
                )
            except (InferencePolicyDeniedError, OrganizationContextError):
                raise
            except Exception as e:
                safe_log(logger, logging.WARNING, "gemini_kontierung_failed", error_code=type(e).__name__)

        # Fallback to Claude
        if self.anthropic_key:
            try:
                resolved_profile = assert_organization_inference_allowed(
                    organization_context=organization_context,
                    data_class=resolved_data_class,
                    requested_inference_profile=requested_profile,
                    provider=InferenceProvider.ANTHROPIC_DIRECT,
                )
                return self._suggest_claude(
                    invoice_data,
                    skr,
                    data_class=resolved_data_class,
                    inference_profile=resolved_profile,
                    organization_context=organization_context,
                )
            except (InferencePolicyDeniedError, OrganizationContextError):
                raise
            except Exception as e:
                safe_log(logger, logging.WARNING, "claude_kontierung_failed", error_code=type(e).__name__)

        # Rule-based fallback
        return self._suggest_rules(invoice_data, skr)

    def _suggest_gemini(
        self,
        invoice_data: dict[str, Any],
        skr: str,
        data_class: str | None = None,
        inference_profile: str | None = None,
        organization_context: TrustedOrganizationContext | None = None,
    ) -> KontierungResult:
        """Use Google Gemini 2.0 Flash for kontierung."""
        from google import genai

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
            purpose="invoice_kontierung",
        )

        client = genai.Client(api_key=self.gemini_key)
        

        prompt = KONTIERUNG_PROMPT.format(invoice_data=json.dumps(invoice_data, indent=2, ensure_ascii=False))
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip()

        parsed = self._parse_json_response(raw)
        log_inference_event(
            logger,
            event="kontierung_completed",
            provider=InferenceProvider.GEMINI_DIRECT.value,
            model="gemini-2.5-flash",
            data_class=decision.data_class,
            inference_profile=decision.inference_profile,
            policy_decision=decision.policy_decision,
            fields_present=sorted(parsed.keys()),
        )
        return KontierungResult(
            konto=parsed.get("konto", "4900"),
            gegenkonto=parsed.get("gegenkonto", "1600"),
            steuerschluessel=parsed.get("steuerschluessel", "9"),
            buchungstext=parsed.get("buchungstext", "")[:60],
            kostenstelle=parsed.get("kostenstelle", ""),
            confidence=float(parsed.get("confidence", 0.5)),
            reasoning=parsed.get("reasoning", ""),
            model="gemini-2.5-flash",
            raw_response=raw,
        )

    def _suggest_claude(
        self,
        invoice_data: dict[str, Any],
        skr: str,
        data_class: str | None = None,
        inference_profile: str | None = None,
        organization_context: TrustedOrganizationContext | None = None,
    ) -> KontierungResult:
        """Use Anthropic Claude as fallback."""
        import anthropic

        resolved_data_class = classify_invoice_data(explicit_data_class=data_class)
        requested_profile = resolve_inference_profile(inference_profile)
        resolved_profile = assert_organization_inference_allowed(
            organization_context=organization_context,
            data_class=resolved_data_class,
            requested_inference_profile=requested_profile,
            provider=InferenceProvider.ANTHROPIC_DIRECT,
        )
        decision = assert_inference_allowed(
            data_class=resolved_data_class,
            inference_profile=resolved_profile,
            provider=InferenceProvider.ANTHROPIC_DIRECT,
            purpose="invoice_kontierung",
        )

        client = anthropic.Anthropic(api_key=self.anthropic_key)
        prompt = KONTIERUNG_PROMPT.format(invoice_data=json.dumps(invoice_data, indent=2, ensure_ascii=False))

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        parsed = self._parse_json_response(raw)
        log_inference_event(
            logger,
            event="kontierung_completed",
            provider=InferenceProvider.ANTHROPIC_DIRECT.value,
            model="claude-sonnet-4-20250514",
            data_class=decision.data_class,
            inference_profile=decision.inference_profile,
            policy_decision=decision.policy_decision,
            fields_present=sorted(parsed.keys()),
        )
        return KontierungResult(
            konto=parsed.get("konto", "4900"),
            gegenkonto=parsed.get("gegenkonto", "1600"),
            steuerschluessel=parsed.get("steuerschluessel", "9"),
            buchungstext=parsed.get("buchungstext", "")[:60],
            kostenstelle=parsed.get("kostenstelle", ""),
            confidence=float(parsed.get("confidence", 0.5)),
            reasoning=parsed.get("reasoning", ""),
            model="claude-sonnet-4",
            raw_response=raw,
        )

    def _suggest_rules(self, invoice_data: dict[str, Any], skr: str) -> KontierungResult:
        """Rule-based fallback when no AI is available."""
        text = json.dumps(invoice_data).lower()

        # Simple keyword matching for common invoice types
        if any(kw in text for kw in ("reparatur", "wartung", "instandhaltung", "service")):
            konto, reason = "4980", "Reparaturen und Instandhaltung"
        elif any(kw in text for kw in ("hydraulik", "pumpe", "zylinder", "ventil", "schlauch")):
            konto, reason = "3400", "Wareneingang Hydraulik-Teile"
        elif any(kw in text for kw in ("miete", "raum", "buero", "büro")):
            konto, reason = "4200", "Raumkosten"
        elif any(kw in text for kw in ("software", "lizenz", "cloud", "saas")):
            konto, reason = "4964", "EDV-Kosten / Software"
        elif any(kw in text for kw in ("beratung", "consulting", "dienstleistung")):
            konto, reason = "4900", "Sonstige betriebliche Aufwendungen"
        else:
            konto, reason = "4900", "Fallback: Sonstige betriebliche Aufwendungen"

        betrag = float(invoice_data.get("betrag_brutto", invoice_data.get("total_gross", 0)))
        buchungstext = str(invoice_data.get("rechnungsaussteller", invoice_data.get("file_name", "Rechnung")))

        return KontierungResult(
            konto=konto,
            gegenkonto="1600",
            steuerschluessel="9",
            buchungstext=buchungstext[:60],
            kostenstelle="",
            confidence=0.4,
            reasoning=f"Rule-based: {reason}",
            model="rules-v1",
        )

    @staticmethod
    def _parse_json_response(raw: str) -> dict[str, Any]:
        """Extract JSON from AI response, handling markdown fences."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:])
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{[^{}]+\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {}
