#!/usr/bin/env python3
"""
SBS Deutschland – Intelligenter Kontierungsservice
Verbindet auto_accounting mit DATEV-Export und lernt aus Korrekturen.
"""

import sqlite3
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import date, datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# =============================================================================
# KONFIGURATION
# =============================================================================

SKR03_ACCOUNTS = {
    # Aufwandskonten
    "3300": {"name": "Wareneingang 7%", "kategorie": "Wareneingang"},
    "3400": {"name": "Wareneingang 19%", "kategorie": "Wareneingang"},
    "3100": {"name": "Fremdleistungen", "kategorie": "Dienstleistungen"},
    "4200": {"name": "Raumkosten", "kategorie": "Miete"},
    "4210": {"name": "Miete", "kategorie": "Miete"},
    "4240": {"name": "Gas, Strom, Wasser", "kategorie": "Energie"},
    "4360": {"name": "Versicherungen", "kategorie": "Versicherung"},
    "4500": {"name": "Fahrzeugkosten", "kategorie": "KFZ"},
    "4530": {"name": "Laufende Kfz-Kosten", "kategorie": "KFZ"},
    "4600": {"name": "Werbekosten", "kategorie": "Marketing"},
    "4650": {"name": "Bewirtung", "kategorie": "Bewirtung"},
    "4660": {"name": "Reisekosten AN", "kategorie": "Reise"},
    "4700": {"name": "Kosten Warenabgabe", "kategorie": "Versand"},
    "4900": {"name": "Sonstige Aufwendungen", "kategorie": "Sonstige"},
    "4910": {"name": "Porto", "kategorie": "Porto"},
    "4920": {"name": "Telefon/Internet", "kategorie": "Kommunikation"},
    "4930": {"name": "Bürobedarf", "kategorie": "Büro"},
    "4950": {"name": "Rechts- und Beratungskosten", "kategorie": "Beratung"},
    "4955": {"name": "Buchführungskosten", "kategorie": "Buchhaltung"},
    "4960": {"name": "Miete für EDV", "kategorie": "Software"},
    "4969": {"name": "Sonstige EDV-Kosten", "kategorie": "IT"},
    "4970": {"name": "Nebenkosten Geldverkehr", "kategorie": "Bank"},
}

SKR04_MAPPING = {
    "3300": "5300", "3400": "5400", "3100": "5900",
    "4200": "6310", "4210": "6310", "4240": "6325",
    "4360": "6400", "4500": "6520", "4530": "6530",
    "4600": "6600", "4650": "6640", "4660": "6650",
    "4700": "6740", "4900": "6800", "4910": "6800",
    "4920": "6805", "4930": "6815", "4950": "6825",
    "4955": "6827", "4960": "6835", "4969": "6850",
    "4970": "6855",
}

# Keyword-Regeln für Konten
KONTIERUNG_RULES = {
    "4920": ["telekom", "vodafone", "o2", "telefon", "mobilfunk", "internet", "1&1", "unitymedia"],
    "4210": ["miete", "rent", "büro", "gewerbe", "pacht", "mietvertrag"],
    "4240": ["strom", "gas", "energie", "stadtwerke", "eon", "vattenfall", "heizung", "wasser"],
    "4600": ["werbung", "marketing", "google ads", "facebook", "anzeige", "kampagne", "social media"],
    "4360": ["versicherung", "allianz", "axa", "haftpflicht", "police"],
    "4660": ["reise", "hotel", "flug", "bahn", "db ", "lufthansa", "booking"],
    "4650": ["restaurant", "bewirtung", "gastronomie", "essen", "catering"],
    "4500": ["kfz", "auto", "werkstatt", "reparatur", "tüv", "inspektion"],
    "4530": ["tanken", "shell", "aral", "esso", "total", "jet ", "benzin", "diesel"],
    "4930": ["büro", "papier", "drucker", "toner", "schreibwaren", "staples"],
    "4950": ["anwalt", "rechtsanwalt", "notar", "beratung", "kanzlei"],
    "4955": ["steuerberater", "buchhaltung", "datev", "steuerbüro", "wirtschaftsprüfer"],
    "4960": ["software", "lizenz", "saas", "cloud", "microsoft", "adobe", "subscription"],
    "4969": ["hosting", "server", "domain", "aws", "azure", "hetzner", "it-service"],
    "4970": ["bank", "gebühr", "konto", "sparkasse", "volksbank", "commerzbank"],
    "4700": ["versand", "dhl", "ups", "dpd", "hermes", "fracht", "paket"],
    "4910": ["porto", "brief", "post", "frankierung"],
    "3100": ["dienstleistung", "freelance", "agentur", "beratung", "consulting", "honorar"],
    "3400": ["ware", "material", "einkauf", "produkt", "artikel", "lieferung"],
}


@dataclass
class Buchungssatz:
    """Einzelner Buchungssatz"""
    invoice_id: int
    betrag_brutto: Decimal
    betrag_netto: Decimal
    mwst_betrag: Decimal
    mwst_satz: float
    soll_konto: str
    soll_konto_name: str
    haben_konto: str
    haben_konto_name: str
    steuerschluessel: str
    buchungstext: str
    belegdatum: date
    belegnummer: str
    lieferant: str
    kostenstelle: str = ""
    confidence: float = 0.0
    alternatives: List[Dict] = None
    

class KontierungsService:
    """Intelligenter Service für Buchungskontierung"""
    
    def __init__(self, db_path: str = "invoices.db", skr: str = "SKR03"):
        self.db_path = db_path
        self.skr = skr
        self.accounts = SKR03_ACCOUNTS
        
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _normalize_text(self, text: str) -> str:
        """Normalisiert Text für Keyword-Matching"""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return ' '.join(text.split())
    
    def _get_steuerschluessel(self, mwst_satz: float) -> str:
        """Ermittelt DATEV-Steuerschlüssel"""
        satz = int(round(mwst_satz))
        if satz == 19:
            return "9"  # Vorsteuer 19%
        elif satz == 7:
            return "2"  # Vorsteuer 7%
        return ""
    
    def _check_learned_kontierung(self, lieferant: str) -> Optional[Dict]:
        """Prüft ob für diesen Lieferanten bereits eine Kontierung gelernt wurde"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Normalisierter Lieferantenname
        pattern = self._normalize_text(lieferant)[:50]
        
        cursor.execute("""
            SELECT final_account, account_name, kostenstelle, COUNT(*) as count
            FROM kontierung_historie
            WHERE lieferant_pattern = ? 
              AND was_corrected = 0
            GROUP BY final_account
            ORDER BY count DESC
            LIMIT 1
        """, (pattern,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row['count'] >= 2:
            return {
                "account": row['final_account'],
                "name": row['account_name'],
                "kostenstelle": row['kostenstelle'] or "",
                "confidence": min(0.9, 0.6 + row['count'] * 0.1),
                "source": "learned"
            }
        return None
    
    def suggest_konto(self, invoice_data: Dict) -> Dict:
        """
        Schlägt Buchungskonto vor basierend auf:
        1. Gelernten Kontierungen (höchste Priorität)
        2. Regelbasiertem Matching
        3. Fallback auf Sonstige Aufwendungen
        """
        lieferant = invoice_data.get('rechnungsaussteller', '') or ''
        beschreibung = invoice_data.get('verwendungszweck', '') or ''
        positionen = invoice_data.get('artikel', '')
        
        if isinstance(positionen, list):
            positionen = ' '.join([str(p.get('beschreibung', '')) for p in positionen])
        
        # 1. Prüfe gelernte Kontierungen
        learned = self._check_learned_kontierung(lieferant)
        if learned:
            return {
                "suggested": learned,
                "alternatives": self._get_alternatives(lieferant, beschreibung, exclude=learned['account']),
                "method": "learned"
            }
        
        # 2. Regelbasiertes Matching
        combined_text = self._normalize_text(f"{lieferant} {beschreibung} {positionen}")
        
        scores = []
        for konto, keywords in KONTIERUNG_RULES.items():
            score = 0
            matched = []
            for kw in keywords:
                if kw in combined_text:
                    score += len(kw) * 2  # Längere Keywords = höherer Score
                    matched.append(kw)
            
            if score > 0:
                scores.append({
                    "account": konto,
                    "name": SKR03_ACCOUNTS.get(konto, {}).get("name", "Unbekannt"),
                    "score": score,
                    "matched": matched
                })
        
        scores.sort(key=lambda x: x['score'], reverse=True)
        
        if scores:
            best = scores[0]
            confidence = min(0.85, best['score'] / 20)
            
            # SKR04 Konvertierung
            account = best['account']
            if self.skr == "SKR04" and account in SKR04_MAPPING:
                account = SKR04_MAPPING[account]
            
            return {
                "suggested": {
                    "account": account,
                    "name": best['name'],
                    "confidence": round(confidence, 2),
                    "matched_keywords": best['matched'],
                    "source": "rules"
                },
                "alternatives": [
                    {"account": s['account'], "name": s['name']} 
                    for s in scores[1:4]
                ],
                "method": "rules"
            }
        
        # 3. Fallback
        fallback_account = "4900" if self.skr == "SKR03" else "6800"
        return {
            "suggested": {
                "account": fallback_account,
                "name": "Sonstige Aufwendungen",
                "confidence": 0.3,
                "source": "fallback"
            },
            "alternatives": [
                {"account": "3100", "name": "Fremdleistungen"},
                {"account": "3400", "name": "Wareneingang 19%"},
            ],
            "method": "fallback"
        }
    
    def _get_alternatives(self, lieferant: str, beschreibung: str, exclude: str = None) -> List[Dict]:
        """Holt alternative Kontovorschläge"""
        combined = self._normalize_text(f"{lieferant} {beschreibung}")
        alternatives = []
        
        for konto, keywords in KONTIERUNG_RULES.items():
            if konto == exclude:
                continue
            for kw in keywords:
                if kw in combined:
                    alternatives.append({
                        "account": konto,
                        "name": SKR03_ACCOUNTS.get(konto, {}).get("name", "")
                    })
                    break
        
        return alternatives[:3]
    
    def create_buchungssatz(self, invoice_data: Dict, konto_override: str = None) -> Buchungssatz:
        """
        Erstellt einen vollständigen Buchungssatz für eine Rechnung
        """
        # Kontierung ermitteln
        if konto_override:
            soll_konto = konto_override
            konto_name = SKR03_ACCOUNTS.get(soll_konto, {}).get("name", "Benutzerdefiniert")
            confidence = 1.0
            alternatives = []
        else:
            suggestion = self.suggest_konto(invoice_data)
            soll_konto = suggestion['suggested']['account']
            konto_name = suggestion['suggested']['name']
            confidence = suggestion['suggested']['confidence']
            alternatives = suggestion.get('alternatives', [])
        
        # Beträge
        brutto = Decimal(str(invoice_data.get('betrag_brutto', 0)))
        mwst_satz = float(invoice_data.get('mwst_satz', 19))
        
        # Netto berechnen falls nicht vorhanden
        if invoice_data.get('betrag_netto'):
            netto = Decimal(str(invoice_data['betrag_netto']))
            mwst = brutto - netto
        else:
            faktor = Decimal(str(1 + mwst_satz / 100))
            netto = (brutto / faktor).quantize(Decimal('0.01'))
            mwst = brutto - netto
        
        # Gegenkonto (Verbindlichkeiten)
        haben_konto = "1600" if self.skr == "SKR03" else "3300"
        
        # Belegdatum
        datum_str = invoice_data.get('datum') or invoice_data.get('rechnungsdatum')
        if datum_str:
            if isinstance(datum_str, str):
                try:
                    belegdatum = datetime.strptime(datum_str[:10], '%Y-%m-%d').date()
                except:
                    belegdatum = date.today()
            else:
                belegdatum = datum_str
        else:
            belegdatum = date.today()
        
        # Buchungstext
        lieferant = invoice_data.get('rechnungsaussteller', 'Unbekannt')
        rechnungsnr = invoice_data.get('rechnungsnummer', '')
        buchungstext = f"{lieferant[:30]} RE {rechnungsnr}"[:60]
        
        return Buchungssatz(
            invoice_id=invoice_data.get('id', 0),
            betrag_brutto=brutto,
            betrag_netto=netto,
            mwst_betrag=mwst,
            mwst_satz=mwst_satz,
            soll_konto=soll_konto,
            soll_konto_name=konto_name,
            haben_konto=haben_konto,
            haben_konto_name="Verbindlichkeiten aLuL",
            steuerschluessel=self._get_steuerschluessel(mwst_satz),
            buchungstext=buchungstext,
            belegdatum=belegdatum,
            belegnummer=rechnungsnr,
            lieferant=lieferant,
            confidence=confidence,
            alternatives=alternatives
        )
    
    def save_kontierung(self, lieferant: str, suggested: str, final: str, 
                        account_name: str, kostenstelle: str = "", user_id: int = None):
        """Speichert eine Kontierung für Lernzwecke"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        pattern = self._normalize_text(lieferant)[:50]
        was_corrected = 1 if suggested != final else 0
        
        cursor.execute("""
            INSERT INTO kontierung_historie 
            (lieferant_name, lieferant_pattern, suggested_account, final_account, 
             account_name, kostenstelle, user_id, was_corrected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (lieferant[:100], pattern, suggested, final, account_name, 
              kostenstelle, user_id, was_corrected))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Kontierung gespeichert: {lieferant} → {final} (korrigiert: {was_corrected})")
    
    def get_buchungsvorschau(self, invoice_ids: List[int]) -> List[Dict]:
        """
        Erstellt Buchungsvorschau für mehrere Rechnungen
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join(['?' for _ in invoice_ids])
        cursor.execute(f"""
            SELECT * FROM invoices WHERE id IN ({placeholders})
        """, invoice_ids)
        
        invoices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        vorschau = []
        for inv in invoices:
            buchung = self.create_buchungssatz(inv)
            vorschau.append({
                "invoice_id": buchung.invoice_id,
                "lieferant": buchung.lieferant,
                "belegnummer": buchung.belegnummer,
                "belegdatum": buchung.belegdatum.isoformat() if buchung.belegdatum else None,
                "betrag_brutto": float(buchung.betrag_brutto),
                "betrag_netto": float(buchung.betrag_netto),
                "mwst_betrag": float(buchung.mwst_betrag),
                "mwst_satz": buchung.mwst_satz,
                "soll_konto": buchung.soll_konto,
                "soll_konto_name": buchung.soll_konto_name,
                "haben_konto": buchung.haben_konto,
                "haben_konto_name": buchung.haben_konto_name,
                "steuerschluessel": buchung.steuerschluessel,
                "buchungstext": buchung.buchungstext,
                "confidence": buchung.confidence,
                "alternatives": buchung.alternatives or [],
            })
        
        return vorschau


# Singleton Instance
_service = None

def get_kontierung_service(skr: str = "SKR03") -> KontierungsService:
    global _service
    if _service is None or _service.skr != skr:
        _service = KontierungsService(skr=skr)
    return _service
