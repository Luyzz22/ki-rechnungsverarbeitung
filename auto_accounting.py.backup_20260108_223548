#!/usr/bin/env python3
"""
SBS Deutschland – Auto-Kontierung
KI-basierte Kontenvorschläge für SKR03/SKR04.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple
from database import get_connection

logger = logging.getLogger(__name__)

# SKR03 Kontenrahmen (häufigste Konten)
SKR03_ACCOUNTS = {
    # Aufwandskonten
    "4200": {"name": "Raumkosten", "keywords": ["miete", "nebenkosten", "strom", "gas", "heizung", "wasser", "reinigung"]},
    "4210": {"name": "Miete", "keywords": ["miete", "mietvertrag", "pacht", "büro", "gewerbe"]},
    "4240": {"name": "Gas, Strom, Wasser", "keywords": ["stadtwerke", "energie", "strom", "gas", "wasser", "eon", "vattenfall"]},
    "4250": {"name": "Reinigung", "keywords": ["reinigung", "putz", "gebäudereinigung", "cleaning"]},
    "4500": {"name": "Fahrzeugkosten", "keywords": ["tanken", "benzin", "diesel", "kfz", "auto", "werkstatt", "reifen", "tüv"]},
    "4510": {"name": "Kfz-Steuer", "keywords": ["kfz-steuer", "kraftfahrzeugsteuer"]},
    "4520": {"name": "Kfz-Versicherung", "keywords": ["kfz-versicherung", "autoversicherung", "haftpflicht"]},
    "4530": {"name": "Laufende Kfz-Kosten", "keywords": ["tanken", "shell", "aral", "esso", "total", "jet"]},
    "4540": {"name": "Kfz-Reparaturen", "keywords": ["werkstatt", "reparatur", "inspektion", "atu", "vergölst"]},
    "4600": {"name": "Werbekosten", "keywords": ["werbung", "marketing", "google ads", "facebook", "anzeige", "flyer"]},
    "4610": {"name": "Werbekosten", "keywords": ["werbung", "marketing", "kampagne", "social media"]},
    "4630": {"name": "Geschenke Kunden", "keywords": ["geschenk", "präsent", "kundengeschenk"]},
    "4650": {"name": "Bewirtung", "keywords": ["restaurant", "bewirtung", "essen", "gastronomie", "hotel"]},
    "4660": {"name": "Reisekosten AN", "keywords": ["reise", "flug", "bahn", "db", "lufthansa", "hotel", "übernachtung"]},
    "4663": {"name": "Reisekosten AN Verpflegung", "keywords": ["verpflegung", "spesen", "tagegeld"]},
    "4670": {"name": "Reisekosten Unternehmer", "keywords": ["geschäftsreise", "dienstreise"]},
    "4700": {"name": "Kosten Warenabgabe", "keywords": ["verpackung", "versand", "fracht", "dhl", "ups", "dpd", "hermes"]},
    "4730": {"name": "Ausgangsfrachten", "keywords": ["fracht", "spedition", "logistik", "transport"]},
    "4750": {"name": "Verpackungsmaterial", "keywords": ["karton", "verpackung", "folie", "palette"]},
    "4800": {"name": "Reparaturen", "keywords": ["reparatur", "wartung", "instandhaltung", "service"]},
    "4806": {"name": "Wartung EDV", "keywords": ["it-service", "edv", "computer", "server", "wartung"]},
    "4900": {"name": "Sonstige Aufwendungen", "keywords": ["sonstige", "diverses"]},
    "4910": {"name": "Porto", "keywords": ["porto", "brief", "post", "frankierung"]},
    "4920": {"name": "Telefon", "keywords": ["telefon", "telekom", "vodafone", "o2", "mobilfunk", "internet"]},
    "4930": {"name": "Bürobedarf", "keywords": ["büro", "schreibwaren", "papier", "drucker", "toner", "staples"]},
    "4940": {"name": "Zeitschriften, Bücher", "keywords": ["zeitung", "zeitschrift", "buch", "abo", "fachzeitschrift"]},
    "4950": {"name": "Rechts- und Beratungskosten", "keywords": ["anwalt", "rechtsanwalt", "notar", "beratung", "steuerberater"]},
    "4955": {"name": "Buchführungskosten", "keywords": ["buchhaltung", "buchführung", "datev", "steuerberater"]},
    "4957": {"name": "Abschluss- und Prüfungskosten", "keywords": ["jahresabschluss", "wirtschaftsprüfer", "prüfung"]},
    "4960": {"name": "Miete EDV", "keywords": ["software", "lizenz", "saas", "cloud", "microsoft", "adobe"]},
    "4964": {"name": "Leasing EDV", "keywords": ["leasing", "hardware", "computer"]},
    "4969": {"name": "Sonstige Aufwendungen EDV", "keywords": ["hosting", "domain", "server", "aws", "azure"]},
    "4970": {"name": "Nebenkosten Geldverkehr", "keywords": ["bank", "gebühren", "konto", "sparkasse", "volksbank"]},
    "4980": {"name": "Betriebsbedarf", "keywords": ["betriebsmittel", "werkzeug", "arbeitskleidung"]},
    
    # Wareneingang
    "3300": {"name": "Wareneingang 7%", "keywords": ["lebensmittel", "buch", "zeitschrift"]},
    "3400": {"name": "Wareneingang 19%", "keywords": ["ware", "einkauf", "material", "rohstoff"]},
    
    # Fremdleistungen
    "3100": {"name": "Fremdleistungen", "keywords": ["dienstleistung", "fremdleistung", "subunternehmer", "agentur"]},
}

# SKR04 Mapping (Kurzfassung - wichtigste Unterschiede)
SKR04_MAPPING = {
    "4200": "6310",  # Raumkosten -> Miete
    "4500": "6520",  # Fahrzeugkosten
    "4600": "6600",  # Werbekosten
    "4660": "6650",  # Reisekosten
    "4900": "6800",  # Sonstige
    "4920": "6805",  # Telefon
    "4930": "6815",  # Bürobedarf
    "4950": "6825",  # Rechtskosten
    "4970": "6855",  # Bankgebühren
}


def suggest_account(invoice_data: Dict, skr: str = "SKR03") -> Dict:
    """
    Schlägt Buchungskonto basierend auf Rechnungsdaten vor.
    
    Args:
        invoice_data: Rechnungsdaten
        skr: Kontenrahmen (SKR03 oder SKR04)
        
    Returns:
        Dict mit account, name, confidence, alternatives
    """
    # Relevante Felder extrahieren
    supplier = (invoice_data.get("rechnungsaussteller") or "").lower()
    description = (invoice_data.get("leistungsbeschreibung") or "").lower()
    positions = (invoice_data.get("positionen") or "").lower()
    
    # Kombinierter Suchtext
    search_text = f"{supplier} {description} {positions}"
    
    # Scoring für jedes Konto
    scores = []
    
    for account, info in SKR03_ACCOUNTS.items():
        score = 0
        matched_keywords = []
        
        for keyword in info["keywords"]:
            if keyword in search_text:
                # Längere Keywords = höherer Score
                score += len(keyword)
                matched_keywords.append(keyword)
        
        if score > 0:
            scores.append({
                "account": account,
                "name": info["name"],
                "score": score,
                "matched": matched_keywords
            })
    
    # Nach Score sortieren
    scores.sort(key=lambda x: x["score"], reverse=True)
    
    if not scores:
        # Fallback: Sonstige Aufwendungen
        best = {"account": "4900", "name": "Sonstige Aufwendungen", "confidence": 0.3}
        alternatives = []
    else:
        best_score = scores[0]
        max_possible = sum(len(k) for k in SKR03_ACCOUNTS[best_score["account"]]["keywords"])
        confidence = min(best_score["score"] / max(max_possible, 1), 1.0)
        
        best = {
            "account": best_score["account"],
            "name": best_score["name"],
            "confidence": round(confidence, 2),
            "matched_keywords": best_score["matched"]
        }
        
        alternatives = [
            {"account": s["account"], "name": s["name"]}
            for s in scores[1:4]
        ]
    
    # SKR04 Umrechnung wenn gewünscht
    if skr == "SKR04" and best["account"] in SKR04_MAPPING:
        best["account_skr04"] = SKR04_MAPPING[best["account"]]
    
    return {
        "suggested": best,
        "alternatives": alternatives,
        "skr": skr
    }


def suggest_account_with_llm(invoice_data: Dict, skr: str = "SKR03") -> Dict:
    """
    KI-basierte Kontenvorschlag mit GPT.
    Nutzt LLM für komplexere Fälle.
    """
    # Erst regelbasiert versuchen
    rule_based = suggest_account(invoice_data, skr)
    
    # Bei hoher Konfidenz: regelbasiertes Ergebnis
    if rule_based["suggested"]["confidence"] >= 0.6:
        rule_based["method"] = "rule_based"
        return rule_based
    
    # Bei niedriger Konfidenz: LLM fragen
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""Du bist ein deutscher Buchhalter. Schlage das passende SKR03-Konto vor.

Rechnungsdaten:
- Lieferant: {invoice_data.get('rechnungsaussteller', 'Unbekannt')}
- Beschreibung: {invoice_data.get('leistungsbeschreibung', '')}
- Betrag: {invoice_data.get('betrag_brutto', 0)} EUR

Antworte NUR im JSON-Format:
{{"account": "4XXX", "name": "Kontoname", "reason": "Kurze Begründung"}}
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # JSON parsen
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            llm_result = json.loads(json_match.group())
            
            return {
                "suggested": {
                    "account": llm_result.get("account", "4900"),
                    "name": llm_result.get("name", "Sonstige Aufwendungen"),
                    "confidence": 0.75,
                    "reason": llm_result.get("reason", "")
                },
                "alternatives": rule_based["alternatives"],
                "skr": skr,
                "method": "llm"
            }
    
    except Exception as e:
        logger.warning(f"LLM-Kontierung fehlgeschlagen: {e}")
    
    # Fallback zu regelbasiert
    rule_based["method"] = "rule_based_fallback"
    return rule_based


def learn_from_correction(user_id: int, invoice_data: Dict, selected_account: str):
    """
    Lernt aus User-Korrekturen für bessere Vorschläge.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    supplier = invoice_data.get("rechnungsaussteller", "")
    
    # Speichere Korrektur
    cursor.execute("""
        INSERT OR REPLACE INTO account_learning (user_id, supplier, account, count)
        VALUES (?, ?, ?, COALESCE(
            (SELECT count + 1 FROM account_learning WHERE user_id = ? AND supplier = ?), 
            1
        ))
    """, (user_id, supplier, selected_account, user_id, supplier))
    
    conn.commit()
    conn.close()
    
    logger.info(f"Kontierung gelernt: {supplier} -> {selected_account}")


def get_learned_account(user_id: int, supplier: str) -> Optional[str]:
    """
    Holt gelerntes Konto für einen Lieferanten.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT account FROM account_learning 
        WHERE user_id = ? AND supplier = ?
        ORDER BY count DESC
        LIMIT 1
    """, (user_id, supplier))
    
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else None


def batch_suggest_accounts(invoices: List[Dict], user_id: int = None, skr: str = "SKR03") -> List[Dict]:
    """
    Kontierung für mehrere Rechnungen.
    """
    results = []
    
    for inv in invoices:
        # Erst gelernte Konten prüfen
        if user_id:
            supplier = inv.get("rechnungsaussteller", "")
            learned = get_learned_account(user_id, supplier)
            if learned:
                results.append({
                    "invoice": inv.get("rechnungsnummer"),
                    "suggested": {
                        "account": learned,
                        "name": SKR03_ACCOUNTS.get(learned, {}).get("name", ""),
                        "confidence": 0.95
                    },
                    "method": "learned"
                })
                continue
        
        # Sonst KI-Vorschlag
        suggestion = suggest_account_with_llm(inv, skr)
        suggestion["invoice"] = inv.get("rechnungsnummer")
        results.append(suggestion)
    
    return results
