#!/usr/bin/env python3
"""
KI-gestützte Auto-Kategorisierung von Rechnungen
"""
import logging
from typing import Dict, List, Optional, Tuple
from anthropic import Anthropic
import os
from database import get_all_categories, get_learned_category, save_category_learning
from invoice_extraction import get_anthropic_extraction_model
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

def predict_category(
    invoice_data: Dict,
    user_id: Optional[int] = None,
    data_class: str | None = None,
    inference_profile: str | None = None,
    organization_context: TrustedOrganizationContext | None = None,
) -> Tuple[int, float, str]:
    """
    Predict category for invoice using AI and learning history
    
    Returns:
        (category_id, confidence, reasoning)
    """
    
    supplier = invoice_data.get('rechnungsaussteller', '').strip()
    
    # Schritt 1: Prüfe ob wir bereits etwas gelernt haben
    learned = get_learned_category(supplier, user_id)
    if learned and learned['times_confirmed'] >= 2:
        # Hohe Confidence wenn mehrfach bestätigt
        confidence = min(0.95, 0.7 + (learned['times_confirmed'] * 0.05))
        safe_log(
            logger,
            logging.INFO,
            "category_prediction_learned",
            category_id=learned["category_id"],
            confidence=confidence,
        )
        return learned['category_id'], confidence, "Gelernt aus vorherigen Rechnungen"
    
    # Schritt 2: KI-basierte Kategorisierung
    model: str | None = None
    try:
        categories = get_all_categories(user_id)
        category_list = "\n".join([
            f"- ID {cat['id']}: {cat['name']} ({cat['description']}) - Konto {cat['account_number']}"
            for cat in categories
        ])
        
        # Erstelle Prompt für Claude
        prompt = f"""Analysiere diese Rechnung und ordne sie der passendsten Kategorie zu.

RECHNUNGSDATEN:
Aussteller: {invoice_data.get('rechnungsaussteller', 'Unbekannt')}
Betrag: {invoice_data.get('betrag_brutto', 0)}€
Artikel/Positionen: {', '.join(invoice_data.get('artikel', [])[:3]) if invoice_data.get('artikel') else 'Keine Angabe'}
Zahlungsdetails: {invoice_data.get('verwendungszweck', '')}

VERFÜGBARE KATEGORIEN:
{category_list}

AUFGABE:
1. Analysiere den Rechnungsaussteller und die Artikel
2. Wähle die passendste Kategorie
3. Gib einen Confidence-Score (0.0-1.0)

Antworte NUR mit diesem JSON-Format (kein Markdown, keine Backticks):
{{"category_id": 5, "confidence": 0.95, "reasoning": "EDEKA ist ein Lebensmittel-Einzelhändler"}}"""

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
            purpose="invoice_category_prediction",
        )

        model = get_anthropic_extraction_model()
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse Response
        import json
        response_text = response.content[0].text.strip()
        
        # Entferne Markdown wenn vorhanden
        if response_text.startswith('```'):
            response_text = response_text.split('\n', 1)[1].rsplit('\n', 1)[0]
        
        result = json.loads(response_text)
        
        category_id = result['category_id']
        confidence = float(result['confidence'])
        reasoning = result['reasoning']
        
        log_inference_event(
            logger,
            event="category_prediction_completed",
            provider=InferenceProvider.ANTHROPIC_DIRECT.value,
            model=model,
            data_class=decision.data_class,
            inference_profile=decision.inference_profile,
            policy_decision=decision.policy_decision,
            category_id=category_id,
            confidence=confidence,
        )

        return category_id, confidence, reasoning

    except (InferencePolicyDeniedError, OrganizationContextError) as e:
        log_inference_event(
            logger,
            event="category_prediction_policy_denied",
            provider=InferenceProvider.ANTHROPIC_DIRECT.value,
            model=model or "unresolved",
            policy_decision="denied",
            error_code=e.error_code,
            level=logging.WARNING,
        )
        raise
    except Exception as e:
        safe_log(logger, logging.ERROR, "category_prediction_failed", error_code=type(e).__name__)
        # Fallback: "Sonstiges" (ID 15)
        return 15, 0.3, "Automatische Kategorisierung fehlgeschlagen"

def categorize_invoice_batch(
    invoices: List[Dict],
    user_id: Optional[int] = None,
    organization_context: TrustedOrganizationContext | None = None,
) -> Dict[int, Dict]:
    """
    Categorize multiple invoices
    
    Returns:
        {invoice_id: {category_id, confidence, reasoning}}
    """
    results = {}
    
    for invoice in invoices:
        invoice_id = invoice.get('id')
        if not invoice_id:
            continue
            
        try:
            category_id, confidence, reasoning = predict_category(
                invoice,
                user_id,
                organization_context=organization_context,
            )
            results[invoice_id] = {
                'category_id': category_id,
                'confidence': confidence,
                'reasoning': reasoning
            }
        except (InferencePolicyDeniedError, OrganizationContextError):
            raise
        except Exception as e:
            safe_log(
                logger,
                logging.ERROR,
                "batch_category_prediction_failed",
                invoice_id=invoice_id,
                error_code=type(e).__name__,
            )
            results[invoice_id] = {
                'category_id': 15,  # Sonstiges
                'confidence': 0.3,
                'reasoning': "Automatische Kategorisierung fehlgeschlagen"
            }
    
    return results
