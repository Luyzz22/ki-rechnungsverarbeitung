#!/usr/bin/env python3
"""
SBS Deutschland – Zahlungsvorschläge & Skonto-Optimierung
Automatische Erkennung von Zahlungsbedingungen und Optimierungsvorschläge.
"""

import sqlite3
import re
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# =============================================================================
# KONFIGURATION
# =============================================================================

class ZahlungsEmpfehlung(str, Enum):
    SKONTO_NUTZEN = "skonto_nutzen"
    NORMAL_ZAHLEN = "normal_zahlen"
    SOFORT_ZAHLEN = "sofort_zahlen"
    VERHANDELN = "verhandeln"
    UEBERFAELLIG = "ueberfaellig"

# Skonto-Erkennungsmuster
SKONTO_PATTERNS = [
    # "2% Skonto bei Zahlung innerhalb von 10 Tagen"
    r'(\d+(?:,\d+)?)\s*%?\s*skonto.*?(?:innerhalb|binnen|bei zahlung).*?(\d+)\s*tag',
    # "Bei Zahlung innerhalb 14 Tagen 3% Skonto"
    r'(?:innerhalb|binnen).*?(\d+)\s*tag.*?(\d+(?:,\d+)?)\s*%?\s*skonto',
    # "2% 10 Tage, netto 30 Tage"
    r'(\d+(?:,\d+)?)\s*%\s*(\d+)\s*tag.*?netto\s*(\d+)\s*tag',
    # "Skonto: 2% / 10 Tage"
    r'skonto:?\s*(\d+(?:,\d+)?)\s*%?\s*[/\-]\s*(\d+)\s*tag',
    # "2% bei Zahlung bis 10.01.2025"
    r'(\d+(?:,\d+)?)\s*%.*?(?:zahlung|bezahlung).*?bis\s*(\d{1,2}\.\d{1,2}\.\d{2,4})',
    # "10 Tage 2% Skonto"
    r'(\d+)\s*tag.*?(\d+(?:,\d+)?)\s*%\s*skonto',
]

# Zahlungsziel-Erkennungsmuster
ZAHLUNGSZIEL_PATTERNS = [
    # "Zahlungsziel: 30 Tage"
    r'zahlungsziel:?\s*(\d+)\s*tag',
    # "netto 30 Tage"
    r'netto\s*(\d+)\s*tag',
    # "Zahlbar innerhalb von 30 Tagen"
    r'zahlbar.*?(?:innerhalb|binnen).*?(\d+)\s*tag',
    # "Fällig am 15.02.2025" - wird separat behandelt
    r'f[äa]llig.*?(\d{1,2}\.\d{1,2}\.\d{2,4})',
    # "Zahlung bis 15.02.2025"
    r'zahlung\s*bis\s*(\d{1,2}\.\d{1,2}\.\d{2,4})',
    # "30 Tage netto"
    r'(\d+)\s*tag.*?netto',
    # "sofort zahlbar"
    r'sofort\s*(?:zahlbar|fällig)',
]


@dataclass
class Zahlungsbedingung:
    """Extrahierte Zahlungsbedingungen einer Rechnung"""
    invoice_id: int
    rechnungsdatum: date
    betrag_brutto: Decimal
    faelligkeit: date
    skonto_prozent: float = 0.0
    skonto_tage: int = 0
    skonto_datum: Optional[date] = None
    skonto_betrag: Decimal = Decimal("0")
    zahlungsziel_tage: int = 30
    lieferant: str = ""
    rechnungsnummer: str = ""


@dataclass
class Zahlungsvorschlag:
    """Optimierter Zahlungsvorschlag"""
    invoice_id: int
    lieferant: str
    rechnungsnummer: str
    betrag_brutto: Decimal
    faelligkeit: date
    tage_bis_faelligkeit: int
    
    # Skonto-Infos
    skonto_verfuegbar: bool = False
    skonto_prozent: float = 0.0
    skonto_datum: Optional[date] = None
    skonto_ersparnis: Decimal = Decimal("0")
    tage_bis_skonto: int = 0
    
    # Empfehlung
    empfehlung: ZahlungsEmpfehlung = ZahlungsEmpfehlung.NORMAL_ZAHLEN
    empfehlung_text: str = ""
    optimaler_zahltag: date = None
    
    # ROI-Berechnung
    skonto_jahresrendite: float = 0.0  # Annualisierte Rendite bei Skonto-Nutzung


class ZahlungsService:
    """Service für Zahlungsoptimierung und Skonto-Management"""
    
    def __init__(self, db_path: str = "invoices.db"):
        self.db_path = db_path
    
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _parse_german_date(self, date_str: str) -> Optional[date]:
        """Parst deutsches Datum (DD.MM.YYYY)"""
        if not date_str:
            return None
        try:
            # Versuche verschiedene Formate
            for fmt in ['%d.%m.%Y', '%d.%m.%y', '%Y-%m-%d']:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
        except:
            pass
        return None
    
    def _extract_skonto(self, text: str) -> Tuple[float, int]:
        """
        Extrahiert Skonto-Prozent und Skonto-Tage aus Text.
        Returns: (skonto_prozent, skonto_tage)
        """
        if not text:
            return 0.0, 0
        
        text_lower = text.lower()
        
        for pattern in SKONTO_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    # Je nach Pattern-Struktur
                    if len(groups) >= 2:
                        # Versuche Prozent und Tage zu extrahieren
                        val1 = groups[0].replace(',', '.')
                        val2 = groups[1].replace(',', '.') if len(groups) > 1 else '0'
                        
                        # Heuristik: Kleinerer Wert ist meist Prozent, größerer Wert ist Tage
                        num1 = float(val1)
                        num2 = float(val2) if val2 else 0
                        
                        if num1 <= 10 and num2 > num1:
                            # num1 ist Prozent, num2 ist Tage
                            return num1, int(num2)
                        elif num2 <= 10 and num1 > num2:
                            # num2 ist Prozent, num1 ist Tage
                            return num2, int(num1)
                        elif num1 <= 10:
                            return num1, int(num2) if num2 else 14
                        else:
                            return num2, int(num1)
                except (ValueError, IndexError):
                    continue
        
        return 0.0, 0
    
    def _extract_zahlungsziel(self, text: str, rechnungsdatum: date) -> Tuple[int, Optional[date]]:
        """
        Extrahiert Zahlungsziel aus Text.
        Returns: (zahlungsziel_tage, faelligkeitsdatum)
        """
        if not text:
            return 30, rechnungsdatum + timedelta(days=30)
        
        text_lower = text.lower()
        
        # Prüfe auf "sofort zahlbar"
        if re.search(r'sofort\s*(?:zahlbar|fällig)', text_lower):
            return 0, rechnungsdatum
        
        for pattern in ZAHLUNGSZIEL_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                val = match.group(1)
                
                # Prüfe ob es ein Datum ist
                if '.' in val:
                    parsed_date = self._parse_german_date(val)
                    if parsed_date:
                        delta = (parsed_date - rechnungsdatum).days
                        return max(delta, 0), parsed_date
                else:
                    # Es ist eine Anzahl Tage
                    try:
                        tage = int(val)
                        return tage, rechnungsdatum + timedelta(days=tage)
                    except ValueError:
                        continue
        
        # Default: 30 Tage
        return 30, rechnungsdatum + timedelta(days=30)
    
    def extract_zahlungsbedingungen(self, invoice_data: Dict) -> Zahlungsbedingung:
        """
        Extrahiert Zahlungsbedingungen aus Rechnungsdaten.
        Analysiert Freitext-Felder nach Skonto und Zahlungszielen.
        """
        # Rechnungsdatum
        datum_str = invoice_data.get('datum') or invoice_data.get('rechnungsdatum')
        if isinstance(datum_str, str):
            rechnungsdatum = self._parse_german_date(datum_str) or date.today()
        elif isinstance(datum_str, date):
            rechnungsdatum = datum_str
        else:
            rechnungsdatum = date.today()
        
        # Betrag
        betrag = Decimal(str(invoice_data.get('betrag_brutto', 0) or 0))
        
        # Kombiniere alle Textfelder für Analyse
        text_fields = [
            invoice_data.get('zahlungsbedingungen', ''),
            invoice_data.get('verwendungszweck', ''),
            invoice_data.get('notizen', ''),
            invoice_data.get('freitext', ''),
            str(invoice_data.get('artikel', '')),
        ]
        combined_text = ' '.join(filter(None, text_fields))
        
        # Extrahiere Skonto
        skonto_prozent, skonto_tage = self._extract_skonto(combined_text)
        
        # Extrahiere Zahlungsziel
        zahlungsziel_tage, faelligkeit = self._extract_zahlungsziel(combined_text, rechnungsdatum)
        
        # Berechne Skonto-Datum und -Betrag
        skonto_datum = None
        skonto_betrag = Decimal("0")
        if skonto_prozent > 0 and skonto_tage > 0:
            skonto_datum = rechnungsdatum + timedelta(days=skonto_tage)
            skonto_betrag = (betrag * Decimal(str(skonto_prozent)) / Decimal("100")).quantize(Decimal("0.01"))
        
        return Zahlungsbedingung(
            invoice_id=invoice_data.get('id', 0),
            rechnungsdatum=rechnungsdatum,
            betrag_brutto=betrag,
            faelligkeit=faelligkeit,
            skonto_prozent=skonto_prozent,
            skonto_tage=skonto_tage,
            skonto_datum=skonto_datum,
            skonto_betrag=skonto_betrag,
            zahlungsziel_tage=zahlungsziel_tage,
            lieferant=invoice_data.get('rechnungsaussteller', '') or '',
            rechnungsnummer=invoice_data.get('rechnungsnummer', '') or ''
        )
    
    def _calculate_skonto_rendite(self, skonto_prozent: float, skonto_tage: int, zahlungsziel_tage: int) -> float:
        """
        Berechnet die annualisierte Rendite der Skonto-Nutzung.
        
        Formel: Rendite = (Skonto% / (100 - Skonto%)) * (365 / (Zahlungsziel - Skonto-Tage))
        
        Beispiel: 2% Skonto bei 10 Tagen, Zahlungsziel 30 Tage
        = (2 / 98) * (365 / 20) = 0.0204 * 18.25 = 37.2% p.a.
        """
        if skonto_prozent <= 0 or zahlungsziel_tage <= skonto_tage:
            return 0.0
        
        differenz_tage = zahlungsziel_tage - skonto_tage
        if differenz_tage <= 0:
            return 0.0
        
        rendite = (skonto_prozent / (100 - skonto_prozent)) * (365 / differenz_tage) * 100
        return round(rendite, 1)
    
    def create_zahlungsvorschlag(self, zahlungsbedingung: Zahlungsbedingung) -> Zahlungsvorschlag:
        """
        Erstellt einen optimierten Zahlungsvorschlag basierend auf den Bedingungen.
        """
        heute = date.today()
        tage_bis_faelligkeit = (zahlungsbedingung.faelligkeit - heute).days
        
        # Skonto-Infos
        skonto_verfuegbar = zahlungsbedingung.skonto_prozent > 0 and zahlungsbedingung.skonto_datum
        tage_bis_skonto = 0
        if skonto_verfuegbar and zahlungsbedingung.skonto_datum:
            tage_bis_skonto = (zahlungsbedingung.skonto_datum - heute).days
        
        # Berechne Skonto-Rendite
        skonto_rendite = 0.0
        if skonto_verfuegbar:
            skonto_rendite = self._calculate_skonto_rendite(
                zahlungsbedingung.skonto_prozent,
                zahlungsbedingung.skonto_tage,
                zahlungsbedingung.zahlungsziel_tage
            )
        
        # Bestimme Empfehlung
        empfehlung = ZahlungsEmpfehlung.NORMAL_ZAHLEN
        empfehlung_text = ""
        optimaler_zahltag = zahlungsbedingung.faelligkeit
        
        if tage_bis_faelligkeit < 0:
            # Überfällig
            empfehlung = ZahlungsEmpfehlung.UEBERFAELLIG
            empfehlung_text = f"⚠️ Rechnung ist {abs(tage_bis_faelligkeit)} Tage überfällig! Sofort bezahlen."
            optimaler_zahltag = heute
            
        elif skonto_verfuegbar and tage_bis_skonto >= 0:
            # Skonto noch möglich
            if skonto_rendite >= 20:  # Ab 20% Jahresrendite lohnt sich Skonto fast immer
                empfehlung = ZahlungsEmpfehlung.SKONTO_NUTZEN
                empfehlung_text = (
                    f"💰 Skonto nutzen! {zahlungsbedingung.skonto_prozent}% Ersparnis "
                    f"({zahlungsbedingung.skonto_betrag:.2f} €) bei Zahlung bis "
                    f"{zahlungsbedingung.skonto_datum.strftime('%d.%m.%Y')}. "
                    f"Entspricht {skonto_rendite:.1f}% p.a. Rendite!"
                )
                optimaler_zahltag = zahlungsbedingung.skonto_datum
            else:
                empfehlung = ZahlungsEmpfehlung.NORMAL_ZAHLEN
                empfehlung_text = (
                    f"Skonto verfügbar ({zahlungsbedingung.skonto_prozent}%), "
                    f"aber Rendite nur {skonto_rendite:.1f}% p.a. Normal zahlen."
                )
                
        elif skonto_verfuegbar and tage_bis_skonto < 0:
            # Skonto verpasst
            empfehlung = ZahlungsEmpfehlung.NORMAL_ZAHLEN
            empfehlung_text = (
                f"Skonto-Frist abgelaufen (war {zahlungsbedingung.skonto_prozent}%). "
                f"Bis Fälligkeit {zahlungsbedingung.faelligkeit.strftime('%d.%m.%Y')} zahlen."
            )
            
        elif tage_bis_faelligkeit <= 3:
            # Bald fällig
            empfehlung = ZahlungsEmpfehlung.SOFORT_ZAHLEN
            empfehlung_text = f"📅 Fälligkeit in {tage_bis_faelligkeit} Tagen. Zeitnah überweisen."
            optimaler_zahltag = heute
            
        else:
            # Normale Zahlung
            empfehlung = ZahlungsEmpfehlung.NORMAL_ZAHLEN
            empfehlung_text = f"Zahlung bis {zahlungsbedingung.faelligkeit.strftime('%d.%m.%Y')} ({tage_bis_faelligkeit} Tage)."
        
        return Zahlungsvorschlag(
            invoice_id=zahlungsbedingung.invoice_id,
            lieferant=zahlungsbedingung.lieferant,
            rechnungsnummer=zahlungsbedingung.rechnungsnummer,
            betrag_brutto=zahlungsbedingung.betrag_brutto,
            faelligkeit=zahlungsbedingung.faelligkeit,
            tage_bis_faelligkeit=tage_bis_faelligkeit,
            skonto_verfuegbar=skonto_verfuegbar,
            skonto_prozent=zahlungsbedingung.skonto_prozent,
            skonto_datum=zahlungsbedingung.skonto_datum,
            skonto_ersparnis=zahlungsbedingung.skonto_betrag,
            tage_bis_skonto=tage_bis_skonto,
            empfehlung=empfehlung,
            empfehlung_text=empfehlung_text,
            optimaler_zahltag=optimaler_zahltag,
            skonto_jahresrendite=skonto_rendite
        )
    
    def save_zahlungsbedingungen(self, zb: Zahlungsbedingung, vorschlag: Zahlungsvorschlag):
        """Speichert Zahlungsbedingungen in der Datenbank"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO zahlungsbedingungen 
            (invoice_id, faelligkeit, skonto_prozent, skonto_tage, skonto_datum, 
             skonto_betrag, zahlungsziel_tage, zahlungsstatus, geplantes_zahldatum,
             empfehlung, empfehlung_grund, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'offen', ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            zb.invoice_id,
            zb.faelligkeit.isoformat() if zb.faelligkeit else None,
            zb.skonto_prozent,
            zb.skonto_tage,
            zb.skonto_datum.isoformat() if zb.skonto_datum else None,
            float(zb.skonto_betrag),
            zb.zahlungsziel_tage,
            vorschlag.optimaler_zahltag.isoformat() if vorschlag.optimaler_zahltag else None,
            vorschlag.empfehlung.value,
            vorschlag.empfehlung_text
        ))
        
        conn.commit()
        conn.close()
    
    def get_offene_zahlungen(self, user_id: int = None, limit: int = 100) -> List[Dict]:
        """Holt alle offenen Zahlungen mit Vorschlägen"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Hole Rechnungen mit Status 'approved' die noch nicht bezahlt sind
        if user_id:
            cursor.execute("""
                SELECT i.*, z.faelligkeit as z_faelligkeit, z.skonto_prozent, z.skonto_tage,
                       z.skonto_datum, z.skonto_betrag, z.zahlungsziel_tage, z.empfehlung,
                       z.empfehlung_grund, z.geplantes_zahldatum, z.zahlungsstatus
                FROM invoices i
                JOIN jobs j ON i.job_id = j.job_id
                LEFT JOIN zahlungsbedingungen z ON i.id = z.invoice_id
                WHERE i.status = 'approved'
                  AND j.user_id = ?
                  AND (z.zahlungsstatus IS NULL OR z.zahlungsstatus = 'offen')
                ORDER BY COALESCE(z.faelligkeit, date(i.datum, '+30 days')) ASC
                LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT i.*, z.faelligkeit as z_faelligkeit, z.skonto_prozent, z.skonto_tage,
                       z.skonto_datum, z.skonto_betrag, z.zahlungsziel_tage, z.empfehlung,
                       z.empfehlung_grund, z.geplantes_zahldatum, z.zahlungsstatus
                FROM invoices i
                LEFT JOIN zahlungsbedingungen z ON i.id = z.invoice_id
                WHERE i.status = 'approved'
                  AND (z.zahlungsstatus IS NULL OR z.zahlungsstatus = 'offen')
                ORDER BY COALESCE(z.faelligkeit, date(i.datum, '+30 days')) ASC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        ergebnisse = []
        for row in rows:
            invoice = dict(row)
            
            # Erstelle/aktualisiere Zahlungsvorschlag
            zb = self.extract_zahlungsbedingungen(invoice)
            vorschlag = self.create_zahlungsvorschlag(zb)
            
            # Speichere falls noch nicht vorhanden
            if not invoice.get('z_faelligkeit'):
                self.save_zahlungsbedingungen(zb, vorschlag)
            
            ergebnisse.append({
                "invoice_id": invoice['id'],
                "lieferant": vorschlag.lieferant,
                "rechnungsnummer": vorschlag.rechnungsnummer,
                "betrag_brutto": float(vorschlag.betrag_brutto),
                "faelligkeit": vorschlag.faelligkeit.isoformat() if vorschlag.faelligkeit else None,
                "tage_bis_faelligkeit": vorschlag.tage_bis_faelligkeit,
                "skonto_verfuegbar": vorschlag.skonto_verfuegbar,
                "skonto_prozent": vorschlag.skonto_prozent,
                "skonto_datum": vorschlag.skonto_datum.isoformat() if vorschlag.skonto_datum else None,
                "skonto_ersparnis": float(vorschlag.skonto_ersparnis),
                "tage_bis_skonto": vorschlag.tage_bis_skonto,
                "empfehlung": vorschlag.empfehlung.value,
                "empfehlung_text": vorschlag.empfehlung_text,
                "optimaler_zahltag": vorschlag.optimaler_zahltag.isoformat() if vorschlag.optimaler_zahltag else None,
                "skonto_jahresrendite": vorschlag.skonto_jahresrendite,
            })
        
        return ergebnisse
    
    def get_zahlungs_dashboard(self) -> Dict:
        """Erstellt Dashboard-Daten für Zahlungsübersicht"""
        zahlungen = self.get_offene_zahlungen(limit=500)
        heute = date.today()
        
        # Statistiken berechnen
        total_offen = sum(z['betrag_brutto'] for z in zahlungen)
        total_skonto_potenzial = sum(z['skonto_ersparnis'] for z in zahlungen if z['tage_bis_skonto'] >= 0)
        
        ueberfaellig = [z for z in zahlungen if z['tage_bis_faelligkeit'] < 0]
        diese_woche = [z for z in zahlungen if 0 <= z['tage_bis_faelligkeit'] <= 7]
        naechste_woche = [z for z in zahlungen if 7 < z['tage_bis_faelligkeit'] <= 14]
        spaeter = [z for z in zahlungen if z['tage_bis_faelligkeit'] > 14]
        
        skonto_nutzbar = [z for z in zahlungen if z['skonto_verfuegbar'] and z['tage_bis_skonto'] >= 0]
        
        return {
            "uebersicht": {
                "total_offen": round(total_offen, 2),
                "anzahl_rechnungen": len(zahlungen),
                "skonto_potenzial": round(total_skonto_potenzial, 2),
                "anzahl_skonto_nutzbar": len(skonto_nutzbar),
            },
            "kategorien": {
                "ueberfaellig": {
                    "anzahl": len(ueberfaellig),
                    "summe": round(sum(z['betrag_brutto'] for z in ueberfaellig), 2),
                    "rechnungen": ueberfaellig[:5]
                },
                "diese_woche": {
                    "anzahl": len(diese_woche),
                    "summe": round(sum(z['betrag_brutto'] for z in diese_woche), 2),
                    "rechnungen": diese_woche[:5]
                },
                "naechste_woche": {
                    "anzahl": len(naechste_woche),
                    "summe": round(sum(z['betrag_brutto'] for z in naechste_woche), 2),
                    "rechnungen": naechste_woche[:5]
                },
                "spaeter": {
                    "anzahl": len(spaeter),
                    "summe": round(sum(z['betrag_brutto'] for z in spaeter), 2),
                    "rechnungen": spaeter[:5]
                },
            },
            "skonto_chancen": skonto_nutzbar[:10],
            "alle_zahlungen": zahlungen
        }
    
    def mark_as_paid(self, invoice_id: int, bezahlt_betrag: float = None):
        """Markiert eine Rechnung als bezahlt"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE zahlungsbedingungen 
            SET zahlungsstatus = 'bezahlt', 
                bezahlt_am = date('now'),
                bezahlt_betrag = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE invoice_id = ?
        """, (bezahlt_betrag, invoice_id))
        
        conn.commit()
        conn.close()


    def get_skonto_chancen(self, user_id: int = None, limit: int = 20) -> List[Dict]:
        """Holt Rechnungen mit nutzbarem Skonto"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT i.id, i.rechnungsnummer, i.rechnungsaussteller, i.betrag_brutto,
                       z.skonto_prozent, z.skonto_tage, z.skonto_datum, z.skonto_betrag,
                       z.faelligkeit
                FROM invoices i
                JOIN jobs j ON i.job_id = j.job_id
                JOIN zahlungsbedingungen z ON i.id = z.invoice_id
                WHERE i.status = 'approved'
                  AND j.user_id = ?
                  AND z.skonto_datum >= date('now')
                  AND z.zahlungsstatus = 'offen'
                ORDER BY z.skonto_datum ASC
                LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT i.id, i.rechnungsnummer, i.rechnungsaussteller, i.betrag_brutto,
                       z.skonto_prozent, z.skonto_tage, z.skonto_datum, z.skonto_betrag,
                       z.faelligkeit
                FROM invoices i
                JOIN zahlungsbedingungen z ON i.id = z.invoice_id
                WHERE i.status = 'approved'
                  AND z.skonto_datum >= date('now')
                  AND z.zahlungsstatus = 'offen'
                ORDER BY z.skonto_datum ASC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


# Singleton
_service = None

def get_zahlungs_service() -> ZahlungsService:
    global _service
    if _service is None:
        _service = ZahlungsService()
    return _service
