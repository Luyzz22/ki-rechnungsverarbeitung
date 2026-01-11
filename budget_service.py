"""
Budget-Service für SBS Invoice Processing System
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"

@dataclass
class BudgetKategorie:
    id: Optional[int]
    name: str
    beschreibung: str
    konten_mapping: List[str]
    aktiv: bool = True
    erstellt_am: Optional[str] = None

class BudgetService:
    def __init__(self, db_path: str = "invoices.db"):
        self.db_path = db_path
        self._init_database()
        self._init_default_kategorien()
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_kategorien (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                beschreibung TEXT,
                konten_mapping TEXT,
                aktiv INTEGER DEFAULT 1,
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monats_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kategorie_id INTEGER NOT NULL,
                jahr INTEGER NOT NULL,
                monat INTEGER NOT NULL,
                budget_betrag REAL NOT NULL,
                notiz TEXT,
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (kategorie_id) REFERENCES budget_kategorien(id),
                UNIQUE(kategorie_id, jahr, monat)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_ist_werte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kategorie_id INTEGER NOT NULL,
                jahr INTEGER NOT NULL,
                monat INTEGER NOT NULL,
                ist_betrag REAL DEFAULT 0,
                anzahl_buchungen INTEGER DEFAULT 0,
                letzte_aktualisierung TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (kategorie_id) REFERENCES budget_kategorien(id),
                UNIQUE(kategorie_id, jahr, monat)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kategorie_id INTEGER NOT NULL,
                jahr INTEGER NOT NULL,
                monat INTEGER NOT NULL,
                alert_typ TEXT NOT NULL,
                severity TEXT NOT NULL,
                nachricht TEXT NOT NULL,
                ist_gelesen INTEGER DEFAULT 0,
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (kategorie_id) REFERENCES budget_kategorien(id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Budget-Datenbank initialisiert")
    
    def _init_default_kategorien(self):
        default_kategorien = [
            {"name": "Personal", "beschreibung": "Löhne, Gehälter, Sozialabgaben", "konten_mapping": ["4100", "4110", "4120", "4130", "4140"]},
            {"name": "Miete & Nebenkosten", "beschreibung": "Büroräume, Betriebskosten", "konten_mapping": ["4210", "4220", "4230"]},
            {"name": "Marketing & Werbung", "beschreibung": "Werbekosten, PR, Events", "konten_mapping": ["4600", "4610", "4620"]},
            {"name": "IT & Software", "beschreibung": "Hardware, Software-Lizenzen, Cloud-Services", "konten_mapping": ["4964", "4970", "4980"]},
            {"name": "Büromaterial", "beschreibung": "Verbrauchsmaterial, Bürobedarf", "konten_mapping": ["4930", "4940"]},
            {"name": "Reisekosten", "beschreibung": "Geschäftsreisen, Übernachtungen, Bewirtung", "konten_mapping": ["4660", "4670", "4680"]},
            {"name": "Versicherungen", "beschreibung": "Betriebliche Versicherungen", "konten_mapping": ["4360", "4370"]},
            {"name": "Beratung & Dienstleistungen", "beschreibung": "Externe Berater, Rechtsanwälte, Steuerberater", "konten_mapping": ["4950", "4955", "4957"]},
            {"name": "Telekommunikation", "beschreibung": "Telefon, Internet, Mobilfunk", "konten_mapping": ["4920", "4925"]},
            {"name": "Sonstige Kosten", "beschreibung": "Nicht kategorisierte Ausgaben", "konten_mapping": ["4900", "4999"]}
        ]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for kategorie in default_kategorien:
            try:
                cursor.execute("""INSERT OR IGNORE INTO budget_kategorien (name, beschreibung, konten_mapping) VALUES (?, ?, ?)""",
                    (kategorie["name"], kategorie["beschreibung"], json.dumps(kategorie["konten_mapping"])))
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()
    
    def get_kategorien(self, nur_aktive: bool = True) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if nur_aktive:
            cursor.execute("SELECT * FROM budget_kategorien WHERE aktiv = 1 ORDER BY name")
        else:
            cursor.execute("SELECT * FROM budget_kategorien ORDER BY name")
        
        kategorien = []
        for row in cursor.fetchall():
            kat = dict(row)
            kat["konten_mapping"] = json.loads(kat["konten_mapping"] or "[]")
            kategorien.append(kat)
        
        conn.close()
        return kategorien
    
    def set_monatsbudget(self, kategorie_id: int, jahr: int, monat: int, betrag: float, notiz: str = None) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO monats_budgets (kategorie_id, jahr, monat, budget_betrag, notiz)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(kategorie_id, jahr, monat) 
            DO UPDATE SET budget_betrag = excluded.budget_betrag, notiz = excluded.notiz, aktualisiert_am = CURRENT_TIMESTAMP
        """, (kategorie_id, jahr, monat, betrag, notiz))
        
        budget_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return budget_id
    
    def copy_budgets_to_month(self, von_jahr: int, von_monat: int, nach_jahr: int, nach_monat: int, prozent_aenderung: float = 0) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT kategorie_id, budget_betrag FROM monats_budgets WHERE jahr = ? AND monat = ?", (von_jahr, von_monat))
        quell_budgets = cursor.fetchall()
        kopiert = 0
        
        for budget in quell_budgets:
            neuer_betrag = budget["budget_betrag"] * (1 + prozent_aenderung / 100)
            cursor.execute("""INSERT INTO monats_budgets (kategorie_id, jahr, monat, budget_betrag) VALUES (?, ?, ?, ?) ON CONFLICT(kategorie_id, jahr, monat) DO NOTHING""",
                (budget["kategorie_id"], nach_jahr, nach_monat, neuer_betrag))
            if cursor.rowcount > 0:
                kopiert += 1
        
        conn.commit()
        conn.close()
        return kopiert
    
    def get_jahresbudget(self, jahr: int) -> Dict:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT bk.id as kategorie_id, bk.name as kategorie_name, mb.monat, mb.budget_betrag, COALESCE(bi.ist_betrag, 0) as ist_betrag
            FROM budget_kategorien bk
            LEFT JOIN monats_budgets mb ON bk.id = mb.kategorie_id AND mb.jahr = ?
            LEFT JOIN budget_ist_werte bi ON bk.id = bi.kategorie_id AND bi.jahr = ? AND bi.monat = mb.monat
            WHERE bk.aktiv = 1 ORDER BY bk.name, mb.monat
        """, (jahr, jahr))
        
        rows = cursor.fetchall()
        conn.close()
        
        jahresbudget = {"jahr": jahr, "kategorien": {}, "gesamt_soll": 0, "gesamt_ist": 0}
        
        for row in rows:
            kat_id = row["kategorie_id"]
            kat_name = row["kategorie_name"]
            
            if kat_id not in jahresbudget["kategorien"]:
                jahresbudget["kategorien"][kat_id] = {"name": kat_name, "monate": {}, "jahres_soll": 0, "jahres_ist": 0}
            
            if row["monat"]:
                monat = row["monat"]
                soll = row["budget_betrag"] or 0
                ist = row["ist_betrag"] or 0
                
                jahresbudget["kategorien"][kat_id]["monate"][monat] = {"soll": soll, "ist": ist, "differenz": soll - ist, "auslastung": (ist / soll * 100) if soll > 0 else 0}
                jahresbudget["kategorien"][kat_id]["jahres_soll"] += soll
                jahresbudget["kategorien"][kat_id]["jahres_ist"] += ist
                jahresbudget["gesamt_soll"] += soll
                jahresbudget["gesamt_ist"] += ist
        
        return jahresbudget
    
    def update_ist_werte_from_invoices(self, jahr: int = None, monat: int = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        if not cursor.fetchone():
            self._create_demo_ist_werte(conn, jahr or datetime.now().year)
            conn.close()
            return
        
        kategorien = self.get_kategorien()
        
        for kategorie in kategorien:
            konten = kategorie.get("konten_mapping", [])
            if not konten:
                continue
            
            konten_filter = " OR ".join([f"gegenkonto LIKE '{k}%'" for k in konten])
            query = f"""SELECT strftime('%Y', rechnungsdatum) as jahr, strftime('%m', rechnungsdatum) as monat, SUM(bruttobetrag) as summe, COUNT(*) as anzahl FROM invoices WHERE ({konten_filter})"""
            params = []
            if jahr:
                query += " AND strftime('%Y', rechnungsdatum) = ?"
                params.append(str(jahr))
            if monat:
                query += " AND strftime('%m', rechnungsdatum) = ?"
                params.append(str(monat).zfill(2))
            query += " GROUP BY jahr, monat"
            
            try:
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    if row["jahr"] and row["monat"]:
                        cursor.execute("""INSERT INTO budget_ist_werte (kategorie_id, jahr, monat, ist_betrag, anzahl_buchungen) VALUES (?, ?, ?, ?, ?) ON CONFLICT(kategorie_id, jahr, monat) DO UPDATE SET ist_betrag = excluded.ist_betrag, anzahl_buchungen = excluded.anzahl_buchungen, letzte_aktualisierung = CURRENT_TIMESTAMP""",
                            (kategorie["id"], int(row["jahr"]), int(row["monat"]), row["summe"] or 0, row["anzahl"] or 0))
            except sqlite3.OperationalError as e:
                logger.error(f"Fehler bei Ist-Wert Aktualisierung: {e}")
        
        conn.commit()
        conn.close()
    
    def _create_demo_ist_werte(self, conn: sqlite3.Connection, jahr: int):
        import random
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM budget_kategorien WHERE aktiv = 1")
        kategorien = cursor.fetchall()
        aktueller_monat = datetime.now().month
        
        for kat in kategorien:
            for monat in range(1, aktueller_monat + 1):
                basis = random.uniform(1000, 15000)
                cursor.execute("""INSERT OR REPLACE INTO budget_ist_werte (kategorie_id, jahr, monat, ist_betrag, anzahl_buchungen) VALUES (?, ?, ?, ?, ?)""",
                    (kat["id"], jahr, monat, round(basis, 2), random.randint(5, 30)))
        conn.commit()
    
    def get_monatsauswertung(self, jahr: int, monat: int) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT bk.id as kategorie_id, bk.name as kategorie_name, COALESCE(mb.budget_betrag, 0) as budget_soll, COALESCE(bi.ist_betrag, 0) as ist_ausgaben, COALESCE(bi.anzahl_buchungen, 0) as anzahl_buchungen
            FROM budget_kategorien bk
            LEFT JOIN monats_budgets mb ON bk.id = mb.kategorie_id AND mb.jahr = ? AND mb.monat = ?
            LEFT JOIN budget_ist_werte bi ON bk.id = bi.kategorie_id AND bi.jahr = ? AND bi.monat = ?
            WHERE bk.aktiv = 1 ORDER BY bk.name
        """, (jahr, monat, jahr, monat))
        
        auswertungen = []
        
        for row in cursor.fetchall():
            soll = row["budget_soll"]
            ist = row["ist_ausgaben"]
            differenz = soll - ist
            auslastung = (ist / soll) * 100 if soll > 0 else (100 if ist > 0 else 0)
            
            if auslastung < 80:
                severity = AlertSeverity.INFO
            elif auslastung < 100:
                severity = AlertSeverity.WARNING
            elif auslastung < 120:
                severity = AlertSeverity.DANGER
            else:
                severity = AlertSeverity.CRITICAL
            
            trend = self._calculate_trend(row["kategorie_id"], jahr, monat)
            
            auswertungen.append({
                "kategorie_id": row["kategorie_id"], "kategorie_name": row["kategorie_name"],
                "budget_soll": round(soll, 2), "ist_ausgaben": round(ist, 2),
                "differenz": round(differenz, 2), "auslastung_prozent": round(auslastung, 1),
                "alert_severity": severity.value, "verbleibend": round(max(0, differenz), 2),
                "trend": trend, "anzahl_buchungen": row["anzahl_buchungen"]
            })
        
        conn.close()
        return auswertungen
    
    def _calculate_trend(self, kategorie_id: int, jahr: int, monat: int) -> str:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        monate_zurueck = []
        for i in range(3):
            m = monat - i
            j = jahr
            if m <= 0:
                m += 12
                j -= 1
            monate_zurueck.append((j, m))
        
        auslastungen = []
        for j, m in monate_zurueck:
            cursor.execute("""SELECT COALESCE(mb.budget_betrag, 0) as soll, COALESCE(bi.ist_betrag, 0) as ist FROM budget_kategorien bk LEFT JOIN monats_budgets mb ON bk.id = mb.kategorie_id AND mb.jahr = ? AND mb.monat = ? LEFT JOIN budget_ist_werte bi ON bk.id = bi.kategorie_id AND bi.jahr = ? AND bi.monat = ? WHERE bk.id = ?""", (j, m, j, m, kategorie_id))
            row = cursor.fetchone()
            if row and row["soll"] > 0:
                auslastungen.append(row["ist"] / row["soll"] * 100)
        
        conn.close()
        
        if len(auslastungen) < 2:
            return "stabil"
        
        aktuell = auslastungen[0] if auslastungen else 0
        vorher = sum(auslastungen[1:]) / len(auslastungen[1:]) if len(auslastungen) > 1 else 0
        
        if aktuell > vorher + 10:
            return "steigend"
        elif aktuell < vorher - 10:
            return "fallend"
        return "stabil"
    
    def get_dashboard_summary(self, jahr: int, monat: int) -> Dict:
        auswertungen = self.get_monatsauswertung(jahr, monat)
        
        gesamt_soll = sum(a["budget_soll"] for a in auswertungen)
        gesamt_ist = sum(a["ist_ausgaben"] for a in auswertungen)
        
        kritisch = [a for a in auswertungen if a["alert_severity"] == "critical"]
        warnung = [a for a in auswertungen if a["alert_severity"] == "danger"]
        achtung = [a for a in auswertungen if a["alert_severity"] == "warning"]
        ok = [a for a in auswertungen if a["alert_severity"] == "info"]
        
        ueberschreitungen = sorted([a for a in auswertungen if a["ist_ausgaben"] > a["budget_soll"]], key=lambda x: x["ist_ausgaben"] - x["budget_soll"], reverse=True)[:5]
        alerts = self.get_unread_alerts()
        
        return {
            "jahr": jahr, "monat": monat, "monat_name": self._monat_name(monat),
            "gesamt_budget": round(gesamt_soll, 2), "gesamt_ausgaben": round(gesamt_ist, 2),
            "gesamt_auslastung": round((gesamt_ist / gesamt_soll * 100) if gesamt_soll > 0 else 0, 1),
            "gesamt_verbleibend": round(gesamt_soll - gesamt_ist, 2),
            "anzahl_kategorien": len(auswertungen),
            "status_kritisch": len(kritisch), "status_warnung": len(warnung),
            "status_achtung": len(achtung), "status_ok": len(ok),
            "top_ueberschreitungen": ueberschreitungen, "kategorien": auswertungen,
            "ungelesene_alerts": len(alerts), "alerts": alerts[:5]
        }
    
    def _monat_name(self, monat: int) -> str:
        namen = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        return namen[monat] if 1 <= monat <= 12 else ""
    
    def get_alerts(self, nur_ungelesen: bool = False, limit: int = 50) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """SELECT ba.*, bk.name as kategorie_name FROM budget_alerts ba JOIN budget_kategorien bk ON ba.kategorie_id = bk.id"""
        if nur_ungelesen:
            query += " WHERE ba.ist_gelesen = 0"
        query += " ORDER BY ba.erstellt_am DESC LIMIT ?"
        
        cursor.execute(query, (limit,))
        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return alerts
    
    def get_unread_alerts(self) -> List[Dict]:
        return self.get_alerts(nur_ungelesen=True)
    
    def mark_alert_read(self, alert_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE budget_alerts SET ist_gelesen = 1 WHERE id = ?", (alert_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def mark_all_alerts_read(self) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE budget_alerts SET ist_gelesen = 1 WHERE ist_gelesen = 0")
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count
    
    def get_trend_data(self, kategorie_id: int = None, monate_zurueck: int = 12) -> Dict:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if kategorie_id:
            cursor.execute("""SELECT mb.jahr, mb.monat, mb.budget_betrag as soll, COALESCE(bi.ist_betrag, 0) as ist FROM monats_budgets mb LEFT JOIN budget_ist_werte bi ON mb.kategorie_id = bi.kategorie_id AND mb.jahr = bi.jahr AND mb.monat = bi.monat WHERE mb.kategorie_id = ? ORDER BY mb.jahr, mb.monat""", (kategorie_id,))
        else:
            cursor.execute("""SELECT mb.jahr, mb.monat, SUM(mb.budget_betrag) as soll, SUM(COALESCE(bi.ist_betrag, 0)) as ist FROM monats_budgets mb LEFT JOIN budget_ist_werte bi ON mb.kategorie_id = bi.kategorie_id AND mb.jahr = bi.jahr AND mb.monat = bi.monat GROUP BY mb.jahr, mb.monat ORDER BY mb.jahr, mb.monat""")
        
        rows = cursor.fetchall()
        conn.close()
        
        labels, soll_werte, ist_werte, auslastung_werte = [], [], [], []
        
        for row in rows:
            labels.append(f"{self._monat_name(row['monat'])[:3]} {row['jahr']}")
            soll_werte.append(round(row["soll"], 2))
            ist_werte.append(round(row["ist"], 2))
            auslastung_werte.append(round(row["ist"] / row["soll"] * 100, 1) if row["soll"] > 0 else 0)
        
        return {"labels": labels, "soll": soll_werte, "ist": ist_werte, "auslastung": auslastung_werte}
    
    def get_kategorie_verteilung(self, jahr: int, monat: int) -> Dict:
        auswertungen = self.get_monatsauswertung(jahr, monat)
        mit_ausgaben = sorted([a for a in auswertungen if a["ist_ausgaben"] > 0], key=lambda x: x["ist_ausgaben"], reverse=True)
        
        return {
            "labels": [a["kategorie_name"] for a in mit_ausgaben],
            "werte": [a["ist_ausgaben"] for a in mit_ausgaben],
            "farben": ["#003856", "#FFB900", "#28a745", "#dc3545", "#6c757d", "#17a2b8", "#fd7e14", "#6f42c1", "#20c997", "#e83e8c"][:len(mit_ausgaben)]
        }

def create_demo_budgets():
    service = BudgetService()
    kategorien = service.get_kategorien()
    jahr = datetime.now().year
    
    demo_budgets = {"Personal": 25000, "Miete & Nebenkosten": 8000, "Marketing & Werbung": 5000, "IT & Software": 3500, "Büromaterial": 500, "Reisekosten": 2000, "Versicherungen": 1500, "Beratung & Dienstleistungen": 4000, "Telekommunikation": 800, "Sonstige Kosten": 1000}
    
    for kat in kategorien:
        budget = demo_budgets.get(kat["name"], 2000)
        for monat in range(1, 13):
            variation = 1 + (monat - 6) * 0.02
            service.set_monatsbudget(kat["id"], jahr, monat, round(budget * variation, 2))
    
    service.update_ist_werte_from_invoices(jahr)
    print(f"Demo-Budgets für {jahr} erstellt")
    return service
