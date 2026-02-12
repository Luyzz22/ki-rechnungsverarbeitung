"""
SBS Smart Maintenance Alert - MVP
Enterprise Feature: Techniker fotografiert Teil → Komplette Handlungsempfehlung

Workflow:
1. Bild-Upload → Gemini Vision erkennt Teilenummer/Beschreibung
2. Invoice-Lookup → Letzte Bestellungen des Teils
3. Contract-Lookup → Garantie/Wartungsvertrag Status
4. Recommendation → Handlungsempfehlung generieren
5. Notification → Slack/Email an Einkauf + Controlling
"""

import sqlite3
import json
import os
import base64
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def configure_gemini():
    """Configure Gemini API"""
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        return True
    return False

# ============================================================================
# PART 1: Visual Part Recognition (Gemini Vision)
# ============================================================================

async def recognize_part_from_image(image_base64: str, context: str = "") -> Dict[str, Any]:
    """
    Verwendet Gemini 1.5 Pro Vision um ein Teil aus einem Foto zu erkennen.
    
    Returns:
        {
            "part_number": "HZ-500-A",
            "part_name": "Hydraulikzylinder",
            "manufacturer": "Bosch Rexroth",
            "category": "Hydraulik",
            "confidence": 0.85,
            "description": "Doppeltwirkender Hydraulikzylinder, 50mm Kolben",
            "raw_response": "..."
        }
    """
    if not configure_gemini():
        return {"error": "Gemini API not configured", "part_number": None}
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""Du bist ein Experte für industrielle Ersatzteile im deutschen Maschinenbau.
Analysiere dieses Bild eines Ersatzteils oder einer Komponente.

Kontext vom Techniker: {context if context else 'Kein Kontext angegeben'}

Extrahiere folgende Informationen (falls erkennbar):
1. Teilenummer/Artikelnummer (oft auf Typenschild oder graviert)
2. Bezeichnung des Teils
3. Hersteller (Logo, Schriftzug)
4. Kategorie (Hydraulik, Pneumatik, Elektrik, Mechanik, Dichtung, Lager, etc.)
5. Technische Details (Maße, Anschlüsse, Material)
6. Zustand (neu, verschlissen, defekt, korrodiert)

Antworte AUSSCHLIESSLICH als JSON:
{{
    "part_number": "erkannte Nummer oder null",
    "part_name": "Bezeichnung",
    "manufacturer": "Hersteller oder null",
    "category": "Kategorie",
    "confidence": 0.0-1.0,
    "description": "Kurze technische Beschreibung",
    "condition": "Zustand des Teils",
    "search_terms": ["Begriff1", "Begriff2"]
}}"""
        
        # Decode base64 image
        image_data = base64.b64decode(image_base64)
        
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_data}
        ])
        
        # Parse JSON response
        response_text = response.text
        # Clean up markdown if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        result = json.loads(response_text.strip())
        result["raw_response"] = response.text
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "part_number": None,
            "part_name": "Unbekannt",
            "confidence": 0
        }


# ============================================================================
# PART 2: Invoice/Supplier Lookup
# ============================================================================

def search_invoices_by_part(search_terms: List[str], user_id: int = None) -> List[Dict]:
    """
    Sucht in Rechnungen nach Teilen basierend auf Suchbegriffen.
    Gibt Lieferanten, Preise und letzte Bestelldaten zurück.
    """
    conn = sqlite3.connect('/var/www/invoice-app/invoices.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    results = []
    
    for term in search_terms:
        # Suche in Artikel-Beschreibung und Verwendungszweck
        query = """
            SELECT 
                id,
                rechnungsnummer,
                datum,
                rechnungsaussteller as supplier,
                rechnungsaussteller_adresse as supplier_address,
                betrag_brutto as amount,
                betrag_netto as amount_net,
                artikel as items,
                verwendungszweck as purpose,
                iban,
                user_id
            FROM invoices 
            WHERE (artikel LIKE ? OR verwendungszweck LIKE ? OR rechnungsaussteller LIKE ?)
        """
        params = [f'%{term}%', f'%{term}%', f'%{term}%']
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY datum DESC LIMIT 10"
        
        cursor.execute(query, params)
        
        for row in cursor.fetchall():
            results.append({
                "invoice_id": row["id"],
                "invoice_number": row["rechnungsnummer"],
                "date": row["datum"],
                "supplier": row["supplier"],
                "supplier_address": row["supplier_address"],
                "amount": row["amount"],
                "amount_net": row["amount_net"],
                "items": row["items"],
                "purpose": row["purpose"],
                "iban": row["iban"],
                "matched_term": term
            })
    
    conn.close()
    
    # Deduplizieren nach invoice_id
    seen = set()
    unique_results = []
    for r in results:
        if r["invoice_id"] not in seen:
            seen.add(r["invoice_id"])
            unique_results.append(r)
    
    return unique_results


def get_supplier_statistics(supplier_name: str, user_id: int = None) -> Dict:
    """
    Statistiken zu einem Lieferanten: Bestellvolumen, Häufigkeit, Durchschnittspreise
    """
    conn = sqlite3.connect('/var/www/invoice-app/invoices.db')
    cursor = conn.cursor()
    
    query = """
        SELECT 
            COUNT(*) as order_count,
            SUM(betrag_brutto) as total_volume,
            AVG(betrag_brutto) as avg_order,
            MIN(datum) as first_order,
            MAX(datum) as last_order
        FROM invoices 
        WHERE rechnungsaussteller LIKE ?
    """
    params = [f'%{supplier_name}%']
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    cursor.execute(query, params)
    row = cursor.fetchone()
    
    conn.close()
    
    return {
        "supplier": supplier_name,
        "order_count": row[0] or 0,
        "total_volume": round(row[1] or 0, 2),
        "avg_order_value": round(row[2] or 0, 2),
        "first_order": row[3],
        "last_order": row[4],
        "relationship_status": "Stammlieferant" if (row[0] or 0) >= 5 else "Gelegentlich"
    }


# ============================================================================
# PART 3: Contract/Warranty Lookup
# ============================================================================

def search_contracts_by_part(search_terms: List[str], user_id: int = None) -> List[Dict]:
    """
    Sucht in Verträgen nach Wartungsverträgen, Garantien, Rahmenverträgen
    die zum Teil passen könnten.
    """
    conn = sqlite3.connect('/var/www/contract-app/data/contracts.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    results = []
    
    for term in search_terms:
        # Suche in contracts und analysis_results
        query = """
            SELECT 
                c.contract_id,
                c.filename,
                c.contract_type,
                c.created_at,
                c.status,
                c.risk_level,
                c.risk_score,
                a.analysis_json
            FROM contracts c
            LEFT JOIN analysis_results a ON c.contract_id = a.contract_id
            WHERE c.filename LIKE ? 
               OR c.contract_type LIKE ?
               OR a.analysis_json LIKE ?
        """
        params = [f'%{term}%', f'%{term}%', f'%{term}%']
        
        if user_id:
            query += " AND c.user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY c.created_at DESC LIMIT 10"
        
        cursor.execute(query, params)
        
        for row in cursor.fetchall():
            analysis = {}
            if row["analysis_json"]:
                try:
                    analysis = json.loads(row["analysis_json"])
                except:
                    pass
            
            # Extrahiere relevante Vertragsinfos
            results.append({
                "contract_id": row["contract_id"],
                "filename": row["filename"],
                "contract_type": row["contract_type"],
                "created_at": row["created_at"],
                "status": row["status"],
                "risk_level": row["risk_level"],
                "risk_score": row["risk_score"],
                "parties": analysis.get("parties", []),
                "key_dates": analysis.get("key_dates", {}),
                "obligations": analysis.get("obligations", []),
                "matched_term": term
            })
    
    conn.close()
    
    # Deduplizieren
    seen = set()
    unique_results = []
    for r in results:
        if r["contract_id"] not in seen:
            seen.add(r["contract_id"])
            unique_results.append(r)
    
    return unique_results


def check_warranty_status(contracts: List[Dict]) -> Dict:
    """
    Prüft Garantie/Wartungsstatus basierend auf gefundenen Verträgen
    """
    warranty_contracts = [c for c in contracts if c["contract_type"] in 
                         ["warranty", "wartung", "service", "maintenance", "garantie", "Wartungsvertrag", "Rahmenvertrag"]]
    
    if not warranty_contracts:
        return {
            "has_warranty": False,
            "warranty_status": "Keine Garantie/Wartungsvertrag gefunden",
            "recommendation": "Prüfen Sie ob ein Wartungsvertrag besteht oder ob Garantie noch gilt"
        }
    
    # Analyse des neuesten relevanten Vertrags
    latest = warranty_contracts[0]
    key_dates = latest.get("key_dates", {})
    
    # Prüfe Ablaufdatum wenn vorhanden
    end_date = key_dates.get("end_date") or key_dates.get("expiry") or key_dates.get("ablauf")
    
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if end > datetime.now():
                return {
                    "has_warranty": True,
                    "warranty_status": f"Aktiv bis {end_date}",
                    "contract_id": latest["contract_id"],
                    "contract_type": latest["contract_type"],
                    "recommendation": "Teil über Wartungsvertrag/Garantie abwickeln"
                }
            else:
                return {
                    "has_warranty": False,
                    "warranty_status": f"Abgelaufen am {end_date}",
                    "contract_id": latest["contract_id"],
                    "recommendation": "Vertrag verlängern oder Neubestellung"
                }
        except:
            pass
    
    return {
        "has_warranty": True,
        "warranty_status": "Vertrag vorhanden (Datum prüfen)",
        "contract_id": latest["contract_id"],
        "contract_type": latest["contract_type"],
        "recommendation": "Vertragsbedingungen manuell prüfen"
    }


# ============================================================================
# PART 4: Smart Recommendation Engine
# ============================================================================

def generate_recommendation(
    part_info: Dict,
    invoice_history: List[Dict],
    contract_info: Dict,
    warranty_status: Dict
) -> Dict:
    """
    Generiert intelligente Handlungsempfehlung basierend auf allen Daten
    """
    recommendation = {
        "timestamp": datetime.now().isoformat(),
        "part": part_info,
        "action": "unknown",
        "priority": "normal",
        "steps": [],
        "cost_estimate": None,
        "supplier_recommendation": None,
        "summary": ""
    }
    
    # Bestimme beste Aktion
    if warranty_status.get("has_warranty"):
        recommendation["action"] = "warranty_claim"
        recommendation["priority"] = "normal"
        recommendation["steps"] = [
            f"1. Garantie/Wartungsvertrag prüfen: {warranty_status.get('contract_id')}",
            "2. Schadensfall beim Vertragspartner melden",
            "3. Austausch/Reparatur über Vertrag abwickeln",
            "4. Dokumentation für Controlling"
        ]
        recommendation["summary"] = f"✅ GARANTIE AKTIV - Über Wartungsvertrag abwickeln ({warranty_status.get('warranty_status')})"
    
    elif invoice_history:
        # Finde besten Lieferanten
        suppliers = {}
        for inv in invoice_history:
            sup = inv.get("supplier", "Unbekannt")
            if sup not in suppliers:
                suppliers[sup] = {"count": 0, "total": 0, "last_date": None, "iban": None}
            suppliers[sup]["count"] += 1
            suppliers[sup]["total"] += inv.get("amount", 0) or 0
            suppliers[sup]["last_date"] = inv.get("date")
            suppliers[sup]["iban"] = inv.get("iban")
        
        # Sortiere nach Häufigkeit
        best_supplier = max(suppliers.items(), key=lambda x: x[1]["count"])
        
        recommendation["action"] = "reorder"
        recommendation["priority"] = "normal"
        recommendation["supplier_recommendation"] = {
            "name": best_supplier[0],
            "order_count": best_supplier[1]["count"],
            "avg_price": round(best_supplier[1]["total"] / best_supplier[1]["count"], 2) if best_supplier[1]["count"] > 0 else 0,
            "last_order": best_supplier[1]["last_date"],
            "iban": best_supplier[1]["iban"]
        }
        recommendation["cost_estimate"] = recommendation["supplier_recommendation"]["avg_price"]
        recommendation["steps"] = [
            f"1. Bestellung bei {best_supplier[0]} (Stammlieferant, {best_supplier[1]['count']} Bestellungen)",
            f"2. Geschätzter Preis: {recommendation['cost_estimate']:.2f}€",
            "3. Lieferzeit beim Lieferanten erfragen",
            "4. Bestellung auslösen und dokumentieren"
        ]
        recommendation["summary"] = f"📦 NEUBESTELLUNG - Empfohlen bei {best_supplier[0]} (ca. {recommendation['cost_estimate']:.2f}€)"
    
    else:
        recommendation["action"] = "new_supplier"
        recommendation["priority"] = "high"
        recommendation["steps"] = [
            "1. Kein bisheriger Lieferant gefunden",
            "2. Angebot bei Herstellern einholen",
            f"3. Suchbegriffe: {', '.join(part_info.get('search_terms', []))}",
            "4. Alternativ: Technischen Einkauf kontaktieren"
        ]
        recommendation["summary"] = "⚠️ NEUER LIEFERANT BENÖTIGT - Kein historischer Bezug gefunden"
    
    return recommendation


# ============================================================================
# PART 5: Main API Function
# ============================================================================

async def process_maintenance_request(
    image_base64: str,
    technician_notes: str = "",
    user_id: int = None,
    location: str = "",
    urgency: str = "normal"
) -> Dict:
    """
    Hauptfunktion: Verarbeitet komplette Wartungsanfrage
    
    Args:
        image_base64: Base64-kodiertes Bild des Teils
        technician_notes: Notizen vom Techniker
        user_id: User-ID für Datenzugriff
        location: Standort/Maschine
        urgency: Dringlichkeit (low, normal, high, critical)
    
    Returns:
        Komplettes Maintenance-Alert Objekt mit Empfehlung
    """
    result = {
        "request_id": f"MA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "location": location,
        "urgency": urgency,
        "technician_notes": technician_notes,
        "part_recognition": None,
        "invoice_history": [],
        "contracts_found": [],
        "warranty_status": None,
        "recommendation": None,
        "notification_targets": [],
        "status": "processing"
    }
    
    try:
        # Step 1: Teil erkennen
        part_info = await recognize_part_from_image(image_base64, technician_notes)
        result["part_recognition"] = part_info
        
        if part_info.get("error"):
            result["status"] = "partial"
            result["part_recognition"]["search_terms"] = technician_notes.split() if technician_notes else []
        
        # Search terms zusammenstellen
        search_terms = part_info.get("search_terms", [])
        if part_info.get("part_number"):
            search_terms.insert(0, part_info["part_number"])
        if part_info.get("manufacturer"):
            search_terms.append(part_info["manufacturer"])
        if part_info.get("part_name"):
            search_terms.append(part_info["part_name"])
        
        # Fallback auf Techniker-Notizen
        if not search_terms and technician_notes:
            search_terms = [w for w in technician_notes.split() if len(w) > 3]
        
        # Step 2: Invoice History
        if search_terms:
            result["invoice_history"] = search_invoices_by_part(search_terms, user_id)
        
        # Step 3: Contracts
        if search_terms:
            result["contracts_found"] = search_contracts_by_part(search_terms, user_id)
        
        # Step 4: Warranty Check
        result["warranty_status"] = check_warranty_status(result["contracts_found"])
        
        # Step 5: Generate Recommendation
        result["recommendation"] = generate_recommendation(
            part_info,
            result["invoice_history"],
            result["contracts_found"],
            result["warranty_status"]
        )
        
        # Adjust priority based on urgency
        if urgency in ["high", "critical"]:
            result["recommendation"]["priority"] = urgency
        
        # Define notification targets
        result["notification_targets"] = [
            {"role": "purchasing", "action": result["recommendation"]["action"]},
            {"role": "controlling", "action": "cost_tracking"},
        ]
        if urgency == "critical":
            result["notification_targets"].append({"role": "management", "action": "escalation"})
        
        result["status"] = "completed"
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


# ============================================================================
# PART 6: Database for Maintenance Requests
# ============================================================================

def init_maintenance_db():
    """Initialisiert Maintenance-Requests Tabelle"""
    conn = sqlite3.connect('/var/www/invoice-app/invoices.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            timestamp TEXT NOT NULL,
            location TEXT,
            urgency TEXT DEFAULT 'normal',
            technician_notes TEXT,
            part_info_json TEXT,
            recommendation_json TEXT,
            status TEXT DEFAULT 'pending',
            notification_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_maintenance_user ON maintenance_requests(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_maintenance_status ON maintenance_requests(status)
    """)
    
    conn.commit()
    conn.close()
    print("✅ Maintenance requests table initialized")


def save_maintenance_request(result: Dict, user_id: int = None) -> int:
    """Speichert Maintenance Request in DB"""
    conn = sqlite3.connect('/var/www/invoice-app/invoices.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO maintenance_requests 
        (request_id, user_id, timestamp, location, urgency, technician_notes, 
         part_info_json, recommendation_json, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result.get("request_id"),
        user_id,
        result.get("timestamp"),
        result.get("location"),
        result.get("urgency"),
        result.get("technician_notes"),
        json.dumps(result.get("part_recognition")),
        json.dumps(result.get("recommendation")),
        result.get("status")
    ))
    
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return request_id


# Init DB on import
init_maintenance_db()


# ============================================================================
# PART 7: HydraulikDoc Integration
# ============================================================================

# Import HydraulikDoc's Gemini Analyzer
import sys
sys.path.insert(0, '/var/www/hydraulikdoc')

def get_hydraulikdoc_analyzer():
    """Lädt den GeminiVideoAnalyzer von HydraulikDoc"""
    try:
        from gemini_video_analyzer import GeminiVideoAnalyzer
        
        # Lade Credentials aus ENV
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        project_id = os.getenv("GOOGLE_PROJECT_ID", "verdant-wave-440815-v6")
        
        analyzer = GeminiVideoAnalyzer(
            api_key=api_key,
            project_id=project_id,
            location="europe-west3"  # Frankfurt für DSGVO
        )
        return analyzer
    except Exception as e:
        print(f"HydraulikDoc Analyzer nicht verfügbar: {e}")
        return None


async def analyze_part_with_hydraulikdoc(image_base64: str, context: str = "") -> Dict[str, Any]:
    """
    Analysiert Teil-Bild mit HydraulikDoc's Gemini 2.5 Pro
    
    Kombiniert:
    - Visuelle Teilerkennung
    - Technische Dokumentations-Suche
    - Hydraulik-spezifisches Wissen
    """
    analyzer = get_hydraulikdoc_analyzer()
    
    if not analyzer:
        # Fallback auf standard recognize_part_from_image
        return await recognize_part_from_image(image_base64, context)
    
    try:
        # HydraulikDoc-spezifischer Prompt
        prompt = f"""Du bist ein Experte für industrielle Hydraulik- und Maschinenkomponenten.
        
Analysiere dieses Bild eines Ersatzteils/einer Komponente aus dem Bereich:
- Hydraulik (Zylinder, Ventile, Pumpen, Schläuche, Dichtungen)
- Pneumatik
- Antriebstechnik
- Maschinenbau allgemein

Kontext vom Techniker: {context if context else 'Kein Kontext'}

AUFGABE:
1. Identifiziere das Teil so präzise wie möglich
2. Erkenne Teilenummern auf Typenschildern
3. Identifiziere den Hersteller (Bosch Rexroth, Parker, Festo, SMC, etc.)
4. Beschreibe technische Spezifikationen
5. Bewerte den Zustand

Antworte NUR als JSON:
{{
    "part_number": "erkannte Nummer oder null",
    "part_name": "Bezeichnung auf Deutsch",
    "manufacturer": "Hersteller",
    "category": "Hydraulik|Pneumatik|Mechanik|Elektrik|Dichtung|Sonstiges",
    "subcategory": "spezifische Kategorie",
    "confidence": 0.0-1.0,
    "description": "Technische Beschreibung",
    "specifications": {{
        "dimensions": "falls erkennbar",
        "pressure_rating": "falls erkennbar",
        "connection_type": "falls erkennbar"
    }},
    "condition": "neu|gebraucht|verschlissen|defekt|korrodiert",
    "condition_details": "Details zum Zustand",
    "search_terms": ["Suchbegriff1", "Suchbegriff2", "..."],
    "alternative_parts": ["mögliche kompatible Teile"],
    "hydraulikdoc_analysis": true
}}"""

        # Nutze Gemini direkt (da GeminiVideoAnalyzer für Videos ist)
        import google.generativeai as genai
        
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Decode image
        image_data = base64.b64decode(image_base64)
        
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_data}
        ])
        
        # Parse response
        response_text = response.text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        result = json.loads(response_text.strip())
        result["hydraulikdoc_analysis"] = True
        result["model_used"] = "gemini-2.0-flash"
        
        return result
        
    except Exception as e:
        print(f"HydraulikDoc Analysis Error: {e}")
        # Fallback
        return await recognize_part_from_image(image_base64, context)


# ============================================================================
# PART 8: Enhanced Process with HydraulikDoc
# ============================================================================

async def process_maintenance_request_v2(
    image_base64: str,
    technician_notes: str = "",
    user_id: int = None,
    location: str = "",
    urgency: str = "normal",
    machine_id: str = None,
    use_hydraulikdoc: bool = True
) -> Dict:
    """
    Enhanced Maintenance Request Processing v2
    
    Nutzt HydraulikDoc für bessere Teilerkennung bei Hydraulik-Komponenten
    """
    result = {
        "request_id": f"MA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "location": location,
        "machine_id": machine_id,
        "urgency": urgency,
        "technician_notes": technician_notes,
        "part_recognition": None,
        "invoice_history": [],
        "contracts_found": [],
        "warranty_status": None,
        "recommendation": None,
        "notification_targets": [],
        "processing_time_ms": 0,
        "status": "processing"
    }
    
    start_time = datetime.now()
    
    try:
        # Step 1: Teil erkennen (HydraulikDoc oder Standard)
        if use_hydraulikdoc:
            part_info = await analyze_part_with_hydraulikdoc(image_base64, technician_notes)
        else:
            part_info = await recognize_part_from_image(image_base64, technician_notes)
        
        result["part_recognition"] = part_info
        
        # Search terms zusammenstellen
        search_terms = part_info.get("search_terms", [])
        if part_info.get("part_number"):
            search_terms.insert(0, part_info["part_number"])
        if part_info.get("manufacturer"):
            search_terms.append(part_info["manufacturer"])
        if part_info.get("part_name"):
            search_terms.append(part_info["part_name"])
        if part_info.get("subcategory"):
            search_terms.append(part_info["subcategory"])
        
        # Fallback auf Techniker-Notizen
        if not search_terms and technician_notes:
            search_terms = [w for w in technician_notes.split() if len(w) > 3]
        
        # Step 2: Invoice History
        if search_terms:
            result["invoice_history"] = search_invoices_by_part(search_terms, user_id)
        
        # Step 3: Contracts
        if search_terms:
            result["contracts_found"] = search_contracts_by_part(search_terms, user_id)
        
        # Step 4: Warranty Check
        result["warranty_status"] = check_warranty_status(result["contracts_found"])
        
        # Step 5: Generate Recommendation
        result["recommendation"] = generate_recommendation(
            part_info,
            result["invoice_history"],
            result["contracts_found"],
            result["warranty_status"]
        )
        
        # Add HydraulikDoc specific info to recommendation
        if part_info.get("hydraulikdoc_analysis"):
            result["recommendation"]["hydraulik_specific"] = True
            if part_info.get("alternative_parts"):
                result["recommendation"]["alternatives"] = part_info["alternative_parts"]
        
        # Adjust priority based on urgency and condition
        if urgency in ["high", "critical"]:
            result["recommendation"]["priority"] = urgency
        if part_info.get("condition") in ["defekt", "korrodiert"]:
            result["recommendation"]["priority"] = "high"
        
        # Define notification targets
        result["notification_targets"] = [
            {"role": "purchasing", "action": result["recommendation"]["action"], "email": "einkauf@sbsdeutschland.de"},
            {"role": "controlling", "action": "cost_tracking", "email": "controlling@sbsdeutschland.de"},
        ]
        if urgency == "critical":
            result["notification_targets"].append({"role": "management", "action": "escalation"})
        if part_info.get("category") == "Hydraulik":
            result["notification_targets"].append({"role": "hydraulik_expert", "action": "technical_review"})
        
        result["status"] = "completed"
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    # Calculate processing time
    result["processing_time_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return result
