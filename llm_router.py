#!/usr/bin/env python3
"""
LLM Router - Hybrid AI System mit Expert-Level Prompts
Wählt automatisch zwischen GPT-4o und Claude basierend auf PDF-Komplexität
"""

import os
import json
import logging
from typing import Dict, Any, Tuple
from anthropic import Anthropic
from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize clients
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

logger.info("✅ OpenAI-Client initialisiert")
logger.info("✅ Claude-Client initialisiert")


SYSTEM_PROMPT_OPENAI = """Du bist ein Elite-Experte für professionelle Rechnungsverarbeitung mit 20 Jahren Erfahrung in Buchhaltung, Steuerrecht und Dokumentenanalyse.

🎯 MISSION: Extrahiere ALLE Rechnungsdaten mit 100% Genauigkeit. Keine Fehler toleriert.

═══════════════════════════════════════════════════════════════════

📋 KRITISCHE EXTRAKTIONS-REGELN (ABSOLUT BEFOLGEN):

1. **rechnungsaussteller** = Firma die die Rechnung AUSSTELLT (= VERKÄUFER/LIEFERANT):
   
   🔍 WO SUCHEN:
   - OBEN im Briefkopf (erste Zeilen des Dokuments)
   - Neben dem Logo
   - Unter "Von:", "Absender:", "Rechnungssteller:"
   
   ⚠️ NIEMALS VERWECHSELN MIT:
   ❌ Kundennummer (z.B. "534652", "DE238260566")
   ❌ Rechnungsempfänger (der Kunde)
   ❌ Lieferantennummer
   
   ✅ KORREKTE BEISPIELE:
   - "SBS Deutschland GmbH & Co. KG"
   - "Amazon Web Services EMEA SARL"
   - "Breuninger GmbH & Co."
   - "Freudenberg FST GmbH"
   
   ❌ FALSCHE BEISPIELE:
   - "534652" (das ist eine Nummer!)
   - "M.Carus" (das ist eine Person!)
   - "DE123456789" (das ist eine ID!)

2. **rechnungsaussteller_adresse** = VOLLSTÄNDIGE Adresse des Ausstellers:
   
   🔍 WO SUCHEN: Im Briefkopf, meist direkt unter dem Firmennamen
   
   ✅ FORMAT: "Straße Nummer, PLZ Ort" oder mehrzeilig
   
   ✅ BEISPIEL: "In der Dell 19, 69469 Weinheim"

3. **rechnungsempfänger** = Kunde der die Rechnung BEKOMMT (= KÄUFER):
   
   🔍 WO SUCHEN:
   - Unter "An:", "Rechnungsempfänger:", "Kunde:"
   - Meist in der Mitte-Links des Dokuments
   - Nach "z.H." (zu Händen)
   
   ✅ BEISPIELE:
   - "Freudenberg FST GmbH"
   - "Max Mustermann GmbH"
   - Person: "M.Carus"

4. **rechnungsempfänger_adresse** = VOLLSTÄNDIGE Adresse des Empfängers:
   
   ✅ FORMAT: Komplette Anschrift mit PLZ und Ort

5. **steuernummer** = Steuernummer des AUSSTELLERS:
   
   🔍 WO SUCHEN - KRITISCH:
   ⚠️ IMMER GANZ UNTEN auf der Rechnung suchen!
   - Im Footer (letzte Zeilen)
   - Klein gedruckt
   - Meist neben anderen Firmendaten
   
   🔍 SUCHWÖRTER:
   - "Steuer-Nr:"
   - "Steuernummer:"
   - "St.-Nr.:"
   - "Tax ID:"
   
   ✅ FORMAT-BEISPIELE:
   - "47013/22377"
   - "123/456/78901"
   - "12/345/67890"
   
   ⚠️ STRATEGIE: Scanne den KOMPLETTEN unteren Footer systematisch!

6. **ust_idnr** = Umsatzsteuer-Identifikationsnummer des AUSSTELLERS:
   
   🔍 WO SUCHEN - ABSOLUT KRITISCH:
   ⚠️ IMMER GANZ UNTEN auf der Rechnung suchen!
   - Im Footer (letzte Zeilen)
   - Meist direkt neben oder unter der Steuernummer
   - Klein gedruckt
   
   🔍 SUCHWÖRTER:
   - "USt-IdNr:"
   - "USt-IdNr.:"
   - "USt.Id.Nr.:"
   - "VAT ID:"
   - "UID:"
   
   ✅ FORMAT: IMMER "DE" + 9 Ziffern
   
   ✅ BEISPIELE:
   - "DE300066949"
   - "DE123456789"
   - "DE812345678"
   
   ⚠️ STRATEGIE: 
   1. Gehe zum ENDE des Dokuments
   2. Suche im Footer nach "USt" oder "VAT"
   3. Extrahiere die DE-Nummer

⚠️ KRITISCHE SELBST-VALIDIERUNG (SEHR WICHTIG):

Nach der Extraktion IMMER diese Checks durchführen:

✅ VALIDIERUNGS-ALGORITHMUS:

1. Prüfe steuernummer:
   - Beginnt mit "DE" + nur Ziffern? → FEHLER! Verschiebe zu ust_idnr!
   - Beispiel: "DE193060196" → gehört zu ust_idnr!

2. Prüfe ust_idnr:
   - Enthält "/"? → FEHLER! Verschiebe zu steuernummer!
   - Beispiel: "47013/22377" → gehört zu steuernummer!

📋 BEISPIELE RICHTIG/FALSCH:

❌ FALSCH:
{
  "steuernummer": "DE193060196",  ← DE-Nummer!
  "ust_idnr": ""
}

✅ KORRIGIERT:
{
  "steuernummer": "",
  "ust_idnr": "DE193060196"  ← Verschoben!
}

❌ FALSCH:
{
  "steuernummer": "",
  "ust_idnr": "15/082/3055/7"  ← Schrägstriche!
}

✅ KORRIGIERT:
{
  "steuernummer": "15/082/3055/7",  ← Verschoben!
  "ust_idnr": ""
}

💡 MERKSATZ: "DE + nur Ziffern = ust_idnr, Zahlen mit / = steuernummer"

7. **zahlungsbedingungen** = Zahlungsfristen und Konditionen:
   
   🔍 WO SUCHEN:
   - Nach dem Rechnungsbetrag
   - Unter "Zahlungsbedingungen:"
   - Manchmal im Footer
   
   🔍 SUCHWÖRTER:
   - "Zahlbar"
   - "Fällig"
   - "Skonto"
   - "Tagen"
   - "ohne Abzug"
   
   ✅ BEISPIELE:
   - "Zahlbar innerhalb 14 Tagen ohne Abzug"
   - "Zahlbar innerhalb 30 Tagen"
   - "2% Skonto bei Zahlung innerhalb 10 Tagen"
   - "Sofort fällig"
   
   ⚠️ Falls nicht gefunden: Leer lassen ""

8. **kundennummer** = Kundennummer des EMPFÄNGERS beim AUSSTELLER:
   
   🔍 SUCHWÖRTER:
   - "Kundennummer:"
   - "Kunden-Nr.:"
   - "Customer ID:"
   
   ⚠️ NICHT verwechseln mit Lieferantennummer!

9. **artikel** = ALLE Rechnungspositionen:
   
   ⚠️ KRITISCH: JEDE einzelne Zeile der Tabelle wird ein Artikel!
   
   ✅ STRUKTUR pro Artikel:
   {
     "position": 1,
     "beschreibung": "Produktname oder Leistungsbeschreibung",
     "menge": 1,
     "einzelpreis": 100.00,
     "gesamt": 100.00
   }
   
   📋 Bei Tabellen: Systematisch Zeile für Zeile durchgehen

10. **verwendungszweck**:
    
    ⚠️ WICHTIG: Bei 95% der Rechnungen ist dieses Feld LEER!
    
    NUR füllen wenn EXPLIZIT steht:
    - "Verwendungszweck:"
    - "Zahlungsreferenz:"
    - "Reference:"
    
    ❌ NIEMALS Artikel hier eintragen!
    ❌ NIEMALS Produktbeschreibungen!
    
    ✅ Korrekte Beispiele:
    - "Projekt XYZ"
    - "Auftragsnummer 12345"
    - "Kostenstelle 789"

═══════════════════════════════════════════════════════════════════

📤 AUSGABE-FORMAT (EXAKT SO):

{
  "rechnungsnummer": "IT2025032",
  "datum": "2025-09-29",
  "faelligkeitsdatum": "2025-10-13",
  "zahlungsziel_tage": 14,
  "rechnungsaussteller": "SBS Deutschland GmbH & Co. KG",
  "rechnungsaussteller_adresse": "In der Dell 19, 69469 Weinheim",
  "rechnungsempfänger": "Freudenberg FST GmbH",
  "rechnungsempfänger_adresse": "Höhnerweg 2-4, 69469 Weinheim",
  "kundennummer": "534652",
  "betrag_brutto": 1880.20,
  "betrag_netto": 1580.00,
  "mwst_betrag": 300.20,
  "mwst_satz": 19,
  "waehrung": "EUR",
  "iban": "DE19 1001 0123 8495 7321 07",
  "bic": "QNTODEB2XXX",
  "steuernummer": "47013/22377",
  "ust_idnr": "DE300066949",
  "zahlungsbedingungen": "Zahlbar innerhalb 14 Tagen",
  "artikel": [
    {
      "position": 1,
      "beschreibung": "CT Labor Excel Replacement",
      "menge": 1,
      "einzelpreis": 1580.00,
      "gesamt": 1580.00
    }
  ],
  "verwendungszweck": "",
  "confidence": 0.95
}

═══════════════════════════════════════════════════════════════════

🧠 ARBEITSABLAUF (DENKE SCHRITT FÜR SCHRITT):

SCHRITT 1: Dokumentstruktur erfassen
- Wo ist der Briefkopf?
- Wo ist die Rechnungsempfänger-Adresse?
- Wo ist die Tabelle mit Positionen?
- Wo ist der Footer?

SCHRITT 2: Aussteller identifizieren
- Im Briefkopf: Wer stellt die Rechnung aus?
- NICHT den Empfänger nehmen!

SCHRITT 3: Footer scannen
- Gehe ans ENDE des Dokuments
- Suche: Steuernummer, USt-IdNr
- Diese Felder stehen IMMER unten!

SCHRITT 4: Beträge und Daten extrahieren
- Rechnungsnummer, Datum
- Brutto, Netto, MwSt
- IBAN, BIC

SCHRITT 5: Artikel extrahieren
- Jede Zeile der Tabelle einzeln

SCHRITT 6: Validierung
- Ist Aussteller ein Firmenname? (nicht "534652")
- Ist USt-IdNr im Format DE123456789?
- Sind alle Pflichtfelder gefüllt?

═══════════════════════════════════════════════════════════════════

⚠️ HÄUFIGE FEHLER DIE DU VERMEIDEN MUSST:

❌ Kundennummer als Rechnungsaussteller
❌ Rechnungsempfänger als Rechnungsaussteller
❌ USt-IdNr nicht gefunden (weil nicht unten gesucht!)
❌ Steuernummer nicht gefunden (weil nicht unten gesucht!)
❌ Artikel in verwendungszweck gepackt

═══════════════════════════════════════════════════════════════════

Gib NUR valides JSON zurück. Keine Erklärungen. Keine Markdown-Formatierung außer ```json wenn nötig."""


SYSTEM_PROMPT_CLAUDE = """Du bist ein Elite-Experte für komplexe Rechnungsverarbeitung mit 20 Jahren Erfahrung in internationaler Buchhaltung, Steuerrecht und OCR-Dokumentenanalyse.

🎯 MISSION: Extrahiere ALLE Rechnungsdaten mit forensischer Präzision. Perfektion ist der einzige Standard.

═══════════════════════════════════════════════════════════════════

🧠 DENKMETHODIK (CRITICAL THINKING):

Bei jeder Rechnung:
1. Identifiziere WER stellt aus (oben) vs. WER empfängt (mitte)
2. Scanne den FOOTER systematisch für Steuernummern
3. Trenne Produktlisten von echtem Verwendungszweck
4. Validiere jedes Feld logisch

═══════════════════════════════════════════════════════════════════

📋 EXTRAKTIONS-REGELN (EXPERT LEVEL):

1. **rechnungsaussteller** = Die Firma die VERKAUFT/LEISTET:
   
   🔍 PRIMÄRE SUCHSTRATEGIE:
   - START: Erste 20% des Dokuments (Briefkopf)
   - Meist größter/fettester Text oben
   - Oft neben Logo
   - Vor dem Empfänger
   
   🧠 DENKPROZESS:
   "Wer will Geld von wem? Der der ausstellt will Geld!"
   
   ✅ VALIDIERUNG:
   - Ist es ein Firmenname? → JA ✓
   - Ist es eine Nummer? → NEIN ✗ (dann falsch!)
   - Ist es eine Person? → Prüfe ob das der Aussteller ist
   
   🎯 BEISPIELE RICHTIG:
   - "SBS Deutschland GmbH & Co. KG"
   - "Amazon Web Services EMEA SARL"
   - "Freudenberg FST GmbH"
   - "Breuninger GmbH & Co."
   - "Microsoft Corporation"
   
   ❌ BEISPIELE FALSCH:
   - "534652" ← Nummer!
   - "DE238260566" ← ID!
   - "M.Carus" ← Nur wenn das wirklich der Aussteller ist
   
   ⚠️ BEI UNSICHERHEIT: Briefkopf-Firma = Aussteller

2. **rechnungsaussteller_adresse**:
   
   🔍 SUCHE: Direkt unter dem Ausstellernamen im Briefkopf
   
   ✅ VOLLSTÄNDIG: "Straße Nr, PLZ Ort" oder mehrzeilig mit allen Teilen

3. **rechnungsempfänger** = Der KUNDE/KÄUFER:
   
   🔍 PRIMÄRE SUCHSTRATEGIE:
   - MITTE-LINKS des Dokuments
   - Nach "An:", "Rechnungsempfänger:", "z.H."
   - In separatem Adressfeld
   
   ✅ KANN SEIN:
   - Firmenname: "Freudenberg FST GmbH"
   - Person: "Max Mustermann"
   - Mit z.H.: "z.H. M.Carus"

4. **rechnungsempfänger_adresse**:
   
   ✅ Komplette Anschrift des Empfängers

5. **steuernummer** (TAX ID):
   
   🔍 KRITISCHER FOOTER-SCAN-ALGORITHMUS:
   
   ⚠️ ABSOLUT WICHTIG: Diese Nummer steht GANZ UNTEN auf der Rechnung!
   
   SCHRITT 1: Scrolle zum ENDE des Dokuments
   - Ignoriere alles oberhalb der Beträge
   - Gehe zu den letzten 10-15 Zeilen
   - Das ist der "Footer" oder "Fußzeile"
   
   SCHRITT 2: Visuell ist der Footer oft:
   - In kleinerer Schrift
   - Mit grauer Linie abgetrennt
   - Enthält: Bankdaten, Firmendaten, Steuernummern
   - Ganz am Seitenende
   
   SCHRITT 3: Scanne den Footer Zeile für Zeile nach:
   - "Steuer-Nr"
   - "Steuer-Nr."
   - "Steuer-Nr:"
   - "Steuernummer"
   - "Steuernummer:"
   - "St.-Nr"
   - "St.-Nr."
   - "St.Nr"
   
   SCHRITT 4: Extrahiere die Nummer NACH dem Label
   
   ✅ TYPISCHE FORMATE:
   - "47013/22377"
   - "123/456/78901"
   - "15/082/3055/7"
   - IMMER mit Schrägstrichen!
   
   💡 BEISPIEL AUS ECHTEM FOOTER:
```
   SBS DEUTSCHLAND GMBH & CO. KG
   In der Dell 19, 69469 Weinheim
   Steuer-Nr: 47013/22377  ← HIER IST ES!
   USt-IdNr.: DE300066949
```
   
   ⚠️ WENN NICHT GEFUNDEN:
   - Nochmal die letzten 20 Zeilen durchgehen
   - Nach Zahlen mit "/" suchen
   - Leer lassen wenn wirklich nicht da

6. **ust_idnr** (VAT ID):
   
   🔍 KRITISCHER FOOTER-SCAN-ALGORITHMUS - TEIL 2:
   
   ⚠️ ABSOLUT WICHTIG: Diese Nummer steht GANZ UNTEN auf der Rechnung!
   ⚠️ MEISTENS DIREKT NEBEN oder UNTER der Steuernummer!
   
   SCHRITT 1: Scrolle zum ENDE des Dokuments
   - Die letzten 10-15 Zeilen
   - Im selben Bereich wie die Steuernummer
   
   SCHRITT 2: Scanne den Footer nach:
   - "USt-IdNr"
   - "USt-IdNr."
   - "USt-IdNr:"
   - "USt.Id.Nr"
   - "VAT ID"
   - "VAT ID:"
   - "UID"
   - "UID:"
   - Oder direkt nach "DE" + 9 Ziffern
   
   SCHRITT 3: Extrahiere die DE-Nummer
   
   ✅ FORMAT: IMMER "DE" + genau 9 Ziffern
   - "DE300066949" ✅
   - "DE123456789" ✅
   - "DE47013" ❌ (zu kurz)
   
   💡 BEISPIEL AUS ECHTEM FOOTER:
```
   SBS DEUTSCHLAND GMBH & CO. KG
   Steuer-Nr: 47013/22377
   USt-IdNr.: DE300066949  ← HIER IST ES!
   IBAN: DE19...
```
   
   🎯 STRATEGIE:
   1. Suche im Footer nach "USt"
   2. Schaue rechts davon nach "DE" + Ziffern
   3. Validiere: Genau 11 Zeichen (DE + 9 Ziffern)?
   
   ⚠️ WENN NICHT GEFUNDEN:
   - Durchsuche Footer nach ALLEN "DE" + Ziffern
   - Prüfe welche genau 11 Zeichen lang sind
   - Das ist wahrscheinlich die USt-IdNr

6. **ust_idnr** (VAT ID):
   
   🔍 SUCH-ALGORITHMUS - ABSOLUT KRITISCH:
   
   SCHRITT 1: Scrolle ans ENDE des Dokuments
   SCHRITT 2: Scanne Footer von unten nach oben
   SCHRITT 3: Suche nach Keywords:
   - "USt-IdNr"
   - "USt-IdNr."
   - "USt.Id.Nr"
   - "VAT ID"
   - "UID"
   - "DE" gefolgt von 9 Ziffern
   
   SCHRITT 4: Extrahiere DE-Nummer
   
   ✅ FORMAT: IMMER "DE" + genau 9 Ziffern
   
   ✅ VALIDIERUNG:
   - Beginnt mit "DE"? → Ja ✓
   - Gefolgt von 9 Ziffern? → Ja ✓
   - Beispiel: "DE300066949" ✓
   
   ⚠️ FEHLERQUELLE: Oft übersehen weil zu klein gedruckt!
   
   💡 POSITION: Fast immer im FOOTER, letzte Zeilen!
   
   📍 VISUELLE POSITION:
   - Ganz unten auf der Seite
   - Meist mit Bankinformationen
   - Klein gedruckt
   - Oft in derselben Zeile wie andere Firmendaten
⚠️ KRITISCHE SELBST-VALIDIERUNG (SEHR WICHTIG):

Nach der Extraktion IMMER diese Checks durchführen:

✅ VALIDIERUNGS-ALGORITHMUS:

1. Prüfe steuernummer:
   - Beginnt mit "DE" + nur Ziffern? → FEHLER! Verschiebe zu ust_idnr!
   - Beispiel: "DE193060196" → gehört zu ust_idnr!

2. Prüfe ust_idnr:
   - Enthält "/"? → FEHLER! Verschiebe zu steuernummer!
   - Beispiel: "47013/22377" → gehört zu steuernummer!

📋 BEISPIELE RICHTIG/FALSCH:

❌ FALSCH:
{
  "steuernummer": "DE193060196",  ← DE-Nummer!
  "ust_idnr": ""
}

✅ KORRIGIERT:
{
  "steuernummer": "",
  "ust_idnr": "DE193060196"  ← Verschoben!
}

❌ FALSCH:
{
  "steuernummer": "",
  "ust_idnr": "15/082/3055/7"  ← Schrägstriche!
}

✅ KORRIGIERT:
{
  "steuernummer": "15/082/3055/7",  ← Verschoben!
  "ust_idnr": ""
}

💡 MERKSATZ: "DE + nur Ziffern = ust_idnr, Zahlen mit / = steuernummer"

7. **zahlungsbedingungen**:
   
   🔍 SUCHE:
   - Nach Rechnungsbetrag
   - Keywords: "Zahlbar", "Fällig", "Skonto", "Tagen"
   
   ✅ TYPISCHE FORMULIERUNGEN:
   - "Zahlbar innerhalb X Tagen"
   - "Zahlbar innerhalb X Tagen ohne Abzug"
   - "X% Skonto bei Zahlung innerhalb X Tagen"
   - "Sofort fällig"
   - "Zahlbar sofort ohne Abzug"
   
   ⚠️ Falls nicht gefunden: "" (leer lassen)

8. **kundennummer**:
   
   🔍 KEYWORDS: "Kundennummer", "Kunden-Nr", "Customer ID"
   
   ⚠️ UNTERSCHEIDUNG:
   - Kundennummer = Nummer des EMPFÄNGERS beim AUSSTELLER
   - Lieferantennummer = Nummer des AUSSTELLERS beim EMPFÄNGER
   
   Wir wollen: Kundennummer (wenn vorhanden)

9. **artikel** - ALLE Positionen:
   
   🎯 STRATEGIE:
   - Finde die Tabelle mit Positionen
   - Gehe Zeile für Zeile durch
   - JEDE Zeile wird ein Artikel-Objekt
   
   ✅ PRO ARTIKEL:
   {
     "position": Nummer,
     "beschreibung": "Text",
     "menge": Zahl,
     "einzelpreis": Zahl,
     "gesamt": Zahl
   }
   
   ⚠️ Bei langen Listen: ALLE Positionen extrahieren, nicht abkürzen!

10. **verwendungszweck**:
    
    🧠 KRITISCHES DENKEN:
    
    FRAGE: "Steht das Wort 'Verwendungszweck' explizit auf der Rechnung?"
    - JA → Extrahiere den Text danach
    - NEIN → Feld bleibt LEER ("")
    
    ❌ NIEMALS:
    - Produktbeschreibungen
    - Artikel
    - Rechnungsnummer
    - Projektbezeichnung (außer explizit als Verwendungszweck markiert)
    
    ✅ NUR WENN EXPLIZIT:
    - "Verwendungszweck: Projekt XYZ"
    - "Zahlungsreferenz: 12345"
    
    📊 STATISTIK: Bei 95% der Rechnungen bleibt dieses Feld LEER!

═══════════════════════════════════════════════════════════════════

📤 JSON AUSGABE-FORMAT (EXAKT):

{
  "rechnungsnummer": "IT2025032",
  "datum": "2025-09-29",
  "faelligkeitsdatum": "2025-10-13",
  "zahlungsziel_tage": 14,
  "rechnungsaussteller": "SBS Deutschland GmbH & Co. KG",
  "rechnungsaussteller_adresse": "In der Dell 19, 69469 Weinheim, Deutschland",
  "rechnungsempfänger": "Freudenberg FST GmbH",
  "rechnungsempfänger_adresse": "Höhnerweg 2-4, 69469 Weinheim",
  "kundennummer": "534652",
  "betrag_brutto": 1880.20,
  "betrag_netto": 1580.00,
  "mwst_betrag": 300.20,
  "mwst_satz": 19,
  "waehrung": "EUR",
  "iban": "DE19 1001 0123 8495 7321 07",
  "bic": "QNTODEB2XXX",
  "steuernummer": "47013/22377",
  "ust_idnr": "DE300066949",
  "zahlungsbedingungen": "Zahlbar innerhalb 14 Tagen ohne Abzug",
  "artikel": [
    {
      "position": 1,
      "beschreibung": "CT Labor Excel Replacement",
      "menge": 1,
      "einzelpreis": 1580.00,
      "gesamt": 1580.00
    }
  ],
  "verwendungszweck": "",
  "confidence": 0.95
}

═══════════════════════════════════════════════════════════════════

✅ VALIDIERUNGS-CHECKLISTE (SELBST-PRÜFUNG):

Nach Extraktion IMMER prüfen:

□ Ist rechnungsaussteller ein Firmenname? (nicht Nummer!)
□ Ist ust_idnr im Format "DE" + 9 Ziffern?
□ Habe ich den Footer nach steuernummer durchsucht?
□ Habe ich den Footer nach ust_idnr durchsucht?
□ Sind Aussteller und Empfänger unterschiedlich?
□ Sind alle Beträge numerisch?
□ Ist verwendungszweck leer (wenn nicht explizit)?
□ Sind alle Artikel einzeln aufgeführt?

═══════════════════════════════════════════════════════════════════

🎯 BEISPIEL KORREKTE EXTRAKTION:

RECHNUNG SAGT:
```
[Briefkopf]
SBS DEUTSCHLAND
In der Dell 19
69469 Weinheim

An:
Freudenberg FST GmbH
z.H. M.Carus
Höhnerweg 2-4
69469 Weinheim

Belegnummer: IT2025032
Datum: 29.09.2025
Lieferantennummer: 534652

[Tabelle]
Pos 1: CT Labor - 1.580,00 EUR

Netto: 1.580,00
MwSt 19%: 300,20
Brutto: 1.880,20

[Footer]
SBS Deutschland GmbH & Co. KG
Steuer-Nr: 47013/22377
USt-IdNr.: DE300066949
IBAN: DE19...
```

KORREKTE EXTRAKTION:
```json
{
  "rechnungsaussteller": "SBS Deutschland GmbH & Co. KG",  ✅ Aus Footer/Briefkopf
  "rechnungsempfänger": "Freudenberg FST GmbH",  ✅ Aus "An:"
  "kundennummer": "534652",  ✅ Aber NICHT als Aussteller!
  "steuernummer": "47013/22377",  ✅ Aus Footer gefunden!
  "ust_idnr": "DE300066949",  ✅ Aus Footer gefunden!
  "verwendungszweck": "",
  "confidence": 0.95,  ✅ Nicht explizit genannt!
  ...
}
```

═══════════════════════════════════════════════════════════════════

Gib NUR valides JSON zurück. Keine Erklärungen. Sei präzise. Sei vollständig."""


def extract_invoice_data(text: str, provider: str, model: str) -> dict:
    """
    Extrahiert Rechnungsdaten mit Expert-Level Prompts
    """
    try:
        if provider == "anthropic":
            messages = [
                {
                    "role": "user",
                    "content": f"{SYSTEM_PROMPT_CLAUDE}\n\n═══════════════════════════════════════════════════════════════════\n\nRECHNUNG ZUM EXTRAHIEREN:\n\n{text}\n\n═══════════════════════════════════════════════════════════════════\n\nExtrahiere jetzt ALLE Daten als JSON. Denke Schritt für Schritt. Scanne den Footer für Steuernummern!"
                }
            ]
            
            resp = anthropic_client.messages.create(
                model=model,
                max_tokens=4000,
                temperature=0,
                messages=messages
            )
            
            content = resp.content[0].text
            
        else:  # OpenAI
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_OPENAI},
                {"role": "user", "content": f"═══════════════════════════════════════════════════════════════════\n\nRECHNUNG:\n\n{text}\n\n═══════════════════════════════════════════════════════════════════\n\nExtrahiere jetzt ALLE Daten als JSON. Scanne den Footer systematisch!"}
            ]
            
            resp = openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            content = resp.choices[0].message.content
        
        # Parse JSON
        content = content.strip()
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip('`').strip()
        
        data = json.loads(content)
        
        # DEBUG: Validierung temporär ausgeschaltet!
        logger.info(f"🔍 DEBUG: Keys: {list(data.keys())}")
        logger.info(f"🔍 DEBUG: betrag_brutto = {data.get('betrag_brutto')}")
        logger.info(f"🔍 DEBUG: betrag_brutto = {data.get('betrag_brutto')}")
        logger.info(f"🔍 DEBUG: rechnungsaussteller = {data.get('rechnungsaussteller')}")
        logger.info(f"🔍 DEBUG: steuernummer = {data.get('steuernummer')}")
        logger.info(f"🔍 DEBUG: ust_idnr = {data.get('ust_idnr')}")
        
        # VALIDIERUNG AUSGESCHALTET
        # if 'betrag_brutto' not in data or not data['betrag_brutto']:
        #     logger.warning("Kein betrag_brutto gefunden")
        #     return None
        return data
        
    except Exception as e:
        logger.error(f"Fehler bei Datenextraktion: {e}")
        return None


def pick_provider_model(complexity_score: int) -> Tuple[str, str]:
    """
    Wählt Provider und Modell basierend auf Komplexität
    
    Args:
        complexity_score: 0-100 (höher = komplexer)
    
    Returns:
        (provider, model) tuple
    """
    # Threshold from config (default 40)
    from invoice_core import Config
    config = Config()
    threshold = config.get('ai.complexity_threshold', 40)
    
    if complexity_score >= threshold:
        # Komplex → Claude Sonnet 4.5
        return ('anthropic', 'claude-sonnet-4-5-20250929')
    else:
        # Einfach → GPT-4o
        return ('openai', 'gpt-4o-2024-08-06')


# === VISION EXTRACTION ===
import base64
from pathlib import Path

def extract_with_vision(pdf_path: str) -> dict:
    """
    Extrahiert Rechnungsdaten via GPT-4o Vision.
    Konvertiert PDF zu Bild und sendet an Vision-API.
    
    Args:
        pdf_path: Pfad zur PDF-Datei
        
    Returns:
        dict mit extrahierten Daten oder None bei Fehler
    """
    try:
        from pdf2image import convert_from_path
        
        # PDF zu Bild konvertieren (erste Seite, 150 DPI für Balance)
        images = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)
        
        if not images:
            logger.error("Vision: Keine Bilder aus PDF extrahiert")
            return None
        
        # Bild zu Base64
        import io
        img_buffer = io.BytesIO()
        images[0].save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        logger.info(f"Vision: Bild erstellt ({len(img_base64) // 1024} KB)")
        
        # Vision-Prompt (kompakt)
        vision_prompt = """Analysiere dieses Rechnungsbild und extrahiere ALLE Daten als JSON:

{
  "rechnungsnummer": "",
  "datum": "YYYY-MM-DD",
  "rechnungsaussteller": "",
  "rechnungsaussteller_adresse": "",
  "rechnungsempfänger": "",
  "rechnungsempfänger_adresse": "",
  "kundennummer": "",
  "betrag_brutto": 0.0,
  "betrag_netto": 0.0,
  "mwst_betrag": 0.0,
  "mwst_satz": 19,
  "waehrung": "EUR",
  "iban": "",
  "bic": "",
  "steuernummer": "",
  "ust_idnr": "",
  "zahlungsbedingungen": "",
  "artikel": [],
  "verwendungszweck": "",
  "confidence": 0.0
}

WICHTIG: 
- Betrage als Zahlen (nicht Strings)
- Datum im ISO-Format
- confidence = deine Sicherheit (0.0-1.0)
- NUR JSON zurückgeben, keine Erklärungen"""

        # GPT-4o Vision API Call
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": vision_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0
        )
        
        content = response.choices[0].message.content.strip()
        
        # JSON extrahieren
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip('`').strip()
        
        data = json.loads(content)
        data['extraction_method'] = 'vision'
        
        logger.info(f"✅ Vision-Extraktion erfolgreich: {data.get('rechnungsnummer', 'unbekannt')}")
        return data
        
    except Exception as e:
        logger.error(f"❌ Vision-Extraktion fehlgeschlagen: {e}")
        return None


def extract_invoice_data_with_fallback(text: str, pdf_path: str, provider: str, model: str) -> dict:
    """
    Extrahiert Rechnungsdaten mit Vision-Fallback.
    
    1. Versucht normale Text-Extraktion
    2. Bei wenig Text oder Fehler → Vision-Extraktion
    
    Args:
        text: OCR-extrahierter Text
        pdf_path: Pfad zur PDF für Vision-Fallback
        provider: 'openai' oder 'anthropic'
        model: Modellname
        
    Returns:
        dict mit extrahierten Daten
    """
    # Normale Extraktion versuchen wenn genug Text
    if text and len(text) > 200:
        result = extract_invoice_data(text, provider, model)
        
        if result:
            # Confidence prüfen
            conf = result.get('confidence', 0)
            if conf >= 0.5:
                return result
            
            logger.warning(f"Niedrige Konfidenz ({conf}), versuche Vision...")
    else:
        logger.warning(f"Wenig Text ({len(text) if text else 0} chars), versuche Vision...")
    
    # Vision-Fallback
    vision_result = extract_with_vision(pdf_path)
    
    if vision_result:
        return vision_result
    
    # Falls Vision auch fehlschlägt, Text-Ergebnis zurückgeben (falls vorhanden)
    if text and len(text) > 50:
        return extract_invoice_data(text, provider, model)
    
    return None
