#!/usr/bin/env python3
"""
SBS Deutschland – Predictive Spend Alerts & Analytics
Phase 2: Enterprise Spend Intelligence
Version: 2.0.0
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import math

DB_PATH = "/var/www/invoice-app/invoices.db"


@dataclass
class SpendAlert:
    alert_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    data: Dict[str, Any]
    created_at: str
    acknowledged: bool = False


@dataclass
class SpendForecast:
    period: str
    predicted_amount: float
    confidence: float
    trend: str
    basis: str


def init_spend_analytics_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spend_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            budget_type TEXT NOT NULL,
            reference_key TEXT,
            monthly_limit REAL,
            quarterly_limit REAL,
            yearly_limit REAL,
            alert_threshold_pct REAL DEFAULT 80.0,
            critical_threshold_pct REAL DEFAULT 95.0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spend_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT UNIQUE NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT,
            data_json TEXT,
            acknowledged INTEGER DEFAULT 0,
            acknowledged_by INTEGER,
            acknowledged_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spend_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            period TEXT NOT NULL,
            total_spend REAL,
            invoice_count INTEGER,
            supplier_count INTEGER,
            avg_invoice REAL,
            max_invoice REAL,
            top_supplier TEXT,
            top_supplier_spend REAL,
            maintenance_count INTEGER DEFAULT 0,
            maintenance_cost_estimate REAL DEFAULT 0,
            data_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_spend_overview(months: int = 12) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) as total_invoices,
            ROUND(COALESCE(SUM(betrag_brutto), 0), 2) as total_spend,
            ROUND(COALESCE(AVG(betrag_brutto), 0), 2) as avg_invoice,
            ROUND(COALESCE(MAX(betrag_brutto), 0), 2) as max_invoice,
            ROUND(COALESCE(MIN(NULLIF(betrag_brutto, 0)), 0), 2) as min_invoice,
            COUNT(DISTINCT rechnungsaussteller) as unique_suppliers
        FROM invoices
        WHERE betrag_brutto > 0
    """)
    totals = dict(cursor.fetchone())

    cursor.execute("""
        SELECT 
            strftime('%Y-%m', datum) as period,
            COUNT(*) as invoice_count,
            ROUND(SUM(betrag_brutto), 2) as total_spend,
            ROUND(AVG(betrag_brutto), 2) as avg_spend,
            COUNT(DISTINCT rechnungsaussteller) as suppliers
        FROM invoices
        WHERE datum IS NOT NULL AND datum != ''
            AND strftime('%Y-%m', datum) >= strftime('%Y-%m', date('now', ?))
            AND betrag_brutto > 0
        GROUP BY period
        ORDER BY period
    """, (f"-{months} months",))
    monthly_trend = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT 
            rechnungsaussteller as supplier,
            COUNT(*) as invoice_count,
            ROUND(SUM(betrag_brutto), 2) as total_spend,
            ROUND(AVG(betrag_brutto), 2) as avg_spend,
            MIN(datum) as first_invoice,
            MAX(datum) as last_invoice
        FROM invoices
        WHERE betrag_brutto > 0 AND rechnungsaussteller IS NOT NULL
        GROUP BY rechnungsaussteller
        ORDER BY total_spend DESC
    """)
    suppliers = [dict(row) for row in cursor.fetchall()]

    total_spend = totals["total_spend"]
    cumulative = 0
    for s in suppliers:
        cumulative += s["total_spend"]
        s["spend_pct"] = round((s["total_spend"] / total_spend * 100) if total_spend > 0 else 0, 1)
        s["cumulative_pct"] = round((cumulative / total_spend * 100) if total_spend > 0 else 0, 1)

    hhi = sum((s["spend_pct"] / 100) ** 2 for s in suppliers) * 10000
    concentration_level = "hoch" if hhi > 2500 else "mittel" if hhi > 1500 else "niedrig"

    cursor.execute("""
        SELECT 
            COUNT(*) as total_requests,
            SUM(CASE WHEN urgency = 'critical' THEN 1 ELSE 0 END) as critical,
            SUM(CASE WHEN urgency = 'high' THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN urgency = 'normal' THEN 1 ELSE 0 END) as normal
        FROM maintenance_requests
    """)
    maintenance = dict(cursor.fetchone())

    conn.close()

    return {
        "overview": totals,
        "monthly_trend": monthly_trend,
        "suppliers": {
            "list": suppliers[:15],
            "total_count": len(suppliers),
            "concentration": {
                "hhi_index": round(hhi, 0),
                "level": concentration_level,
                "top3_pct": suppliers[2]["cumulative_pct"] if len(suppliers) >= 3 else 0,
                "top5_pct": suppliers[4]["cumulative_pct"] if len(suppliers) >= 5 else 0,
            }
        },
        "maintenance": maintenance,
        "generated_at": datetime.now().isoformat()
    }


def get_supplier_deep_dive(supplier_name: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT rechnungsnummer, datum, betrag_brutto, betrag_netto, 
               mwst_betrag, mwst_satz, waehrung
        FROM invoices
        WHERE rechnungsaussteller LIKE ?
        ORDER BY datum DESC
    """, (f"%{supplier_name}%",))
    invoices = [dict(row) for row in cursor.fetchall()]

    if not invoices:
        conn.close()
        return {"error": f"Kein Lieferant gefunden: {supplier_name}"}

    amounts = [inv["betrag_brutto"] for inv in invoices if inv["betrag_brutto"]]
    monthly = defaultdict(float)
    for inv in invoices:
        if inv["datum"]:
            monthly[inv["datum"][:7]] += inv["betrag_brutto"] or 0

    if len(amounts) > 1:
        mean_val = sum(amounts) / len(amounts)
        variance = sum((x - mean_val) ** 2 for x in amounts) / len(amounts)
        std_dev = math.sqrt(variance)
        cv = (std_dev / mean_val * 100) if mean_val > 0 else 0
    else:
        mean_val = amounts[0] if amounts else 0
        std_dev = 0
        cv = 0

    cursor.execute("""
        SELECT request_id, location, urgency, 
               json_extract(part_info_json, '$.part_name') as part_name, created_at
        FROM maintenance_requests
        WHERE json_extract(part_info_json, '$.manufacturer') LIKE ?
           OR json_extract(recommendation_json, '$.supplier_recommendation') LIKE ?
        ORDER BY created_at DESC
    """, (f"%{supplier_name}%", f"%{supplier_name}%"))
    related_maintenance = [dict(row) for row in cursor.fetchall()]

    conn.close()

    risks = []
    risk_level = "low"
    total = sum(amounts)
    if total > 20000:
        risks.append({"type": "high_spend_volume", "message": f"Hoher Spend: EUR {total:,.2f}", "severity": "warning"})
        risk_level = "medium"
    if cv > 50:
        risks.append({"type": "high_volatility", "message": f"Hohe Streuung: {cv:.0f}%", "severity": "warning"})
        risk_level = "medium"
    if len(amounts) <= 2 and total > 10000:
        risks.append({"type": "single_source_risk", "message": "Wenige Transaktionen, hoher Betrag", "severity": "critical"})
        risk_level = "high"

    return {
        "supplier": supplier_name,
        "summary": {
            "total_invoices": len(invoices),
            "total_spend": round(sum(amounts), 2),
            "avg_invoice": round(mean_val, 2),
            "max_invoice": round(max(amounts), 2) if amounts else 0,
            "min_invoice": round(min(amounts), 2) if amounts else 0,
            "std_deviation": round(std_dev, 2),
            "volatility_pct": round(cv, 1),
            "first_invoice": invoices[-1]["datum"] if invoices else None,
            "last_invoice": invoices[0]["datum"] if invoices else None,
        },
        "monthly_pattern": dict(sorted(monthly.items())),
        "invoices": invoices[:20],
        "related_maintenance": related_maintenance,
        "risk_assessment": {"risk_level": risk_level, "risks": risks}
    }


def run_spend_analysis() -> List[SpendAlert]:
    alerts = []
    alerts.extend(_check_budget_thresholds())
    alerts.extend(_check_spend_anomalies())
    alerts.extend(_check_supplier_spikes())
    alerts.extend(_check_maintenance_cost_trends())
    _save_alerts(alerts)
    return alerts


def _check_budget_thresholds() -> List[SpendAlert]:
    alerts = []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM spend_budgets WHERE is_active = 1")
    budgets = cursor.fetchall()

    if not budgets:
        _create_default_budgets(cursor, conn)
        cursor.execute("SELECT * FROM spend_budgets WHERE is_active = 1")
        budgets = cursor.fetchall()

    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    for budget in budgets:
        budget = dict(budget)
        if budget["monthly_limit"]:
            cursor.execute("""
                SELECT COALESCE(SUM(betrag_brutto), 0) as spent
                FROM invoices WHERE strftime('%Y-%m', datum) = ? AND betrag_brutto > 0
            """, (current_month,))
            monthly_spent = cursor.fetchone()["spent"]
            pct = (monthly_spent / budget["monthly_limit"] * 100) if budget["monthly_limit"] > 0 else 0

            if pct >= budget["critical_threshold_pct"]:
                alerts.append(SpendAlert(
                    alert_id=f"BUDGET-M-{current_month}-{budget['id']}",
                    alert_type="budget_threshold", severity="critical",
                    title=f"Budget KRITISCH: {pct:.0f}%",
                    message=f"{budget['budget_type']}: EUR {monthly_spent:,.2f} / EUR {budget['monthly_limit']:,.2f}",
                    data={"budget_type": budget["budget_type"], "spent": round(monthly_spent, 2),
                          "limit": budget["monthly_limit"], "pct": round(pct, 1)},
                    created_at=now.isoformat()
                ))
            elif pct >= budget["alert_threshold_pct"]:
                alerts.append(SpendAlert(
                    alert_id=f"BUDGET-M-{current_month}-{budget['id']}",
                    alert_type="budget_threshold", severity="warning",
                    title=f"Budget-Warnung: {pct:.0f}%",
                    message=f"{budget['budget_type']}: EUR {monthly_spent:,.2f} / EUR {budget['monthly_limit']:,.2f}",
                    data={"budget_type": budget["budget_type"], "spent": round(monthly_spent, 2),
                          "limit": budget["monthly_limit"], "pct": round(pct, 1)},
                    created_at=now.isoformat()
                ))

    conn.close()
    return alerts


def _check_spend_anomalies() -> List[SpendAlert]:
    alerts = []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT strftime('%Y-%m', datum) as period, SUM(betrag_brutto) as total
        FROM invoices WHERE datum IS NOT NULL AND datum != '' AND betrag_brutto > 0
        GROUP BY period ORDER BY period
    """)
    monthly = [(row["period"], row["total"]) for row in cursor.fetchall()]

    if len(monthly) >= 4:
        amounts = [m[1] for m in monthly if m[1] > 0]
        if len(amounts) >= 3:
            recent = amounts[-6:]
            mean_val = sum(recent) / len(recent)
            variance = sum((x - mean_val) ** 2 for x in recent) / len(recent)
            std_dev = math.sqrt(variance)

            current_month = datetime.now().strftime("%Y-%m")
            cursor.execute("""
                SELECT COALESCE(SUM(betrag_brutto), 0) as total
                FROM invoices WHERE strftime('%Y-%m', datum) = ? AND betrag_brutto > 0
            """, (current_month,))
            current_spend = cursor.fetchone()["total"]

            threshold = mean_val + (2 * std_dev) if std_dev > 0 else mean_val * 1.5
            if current_spend > threshold and current_spend > 0:
                alerts.append(SpendAlert(
                    alert_id=f"ANOMALY-{current_month}",
                    alert_type="anomaly", severity="warning",
                    title=f"Anomalie: Hohe Ausgaben {current_month}",
                    message=f"EUR {current_spend:,.2f} vs. Durchschnitt EUR {mean_val:,.2f}",
                    data={"current": round(current_spend, 2), "average": round(mean_val, 2),
                          "threshold": round(threshold, 2)},
                    created_at=datetime.now().isoformat()
                ))

    conn.close()
    return alerts


def _check_supplier_spikes() -> List[SpendAlert]:
    alerts = []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    prev_months = [(now - timedelta(days=30 * i)).strftime("%Y-%m") for i in range(1, 4)]

    cursor.execute("""
        SELECT rechnungsaussteller, SUM(betrag_brutto) as current_spend
        FROM invoices WHERE strftime('%Y-%m', datum) = ? AND betrag_brutto > 0
        GROUP BY rechnungsaussteller
    """, (current_month,))
    current = {row["rechnungsaussteller"]: row["current_spend"] for row in cursor.fetchall()}

    placeholders = ",".join(["?" for _ in prev_months])
    cursor.execute(f"""
        SELECT rechnungsaussteller, AVG(monthly_total) as avg_spend
        FROM (
            SELECT rechnungsaussteller, strftime('%Y-%m', datum) as period, SUM(betrag_brutto) as monthly_total
            FROM invoices WHERE strftime('%Y-%m', datum) IN ({placeholders}) AND betrag_brutto > 0
            GROUP BY rechnungsaussteller, period
        ) GROUP BY rechnungsaussteller
    """, prev_months)
    historical = {row["rechnungsaussteller"]: row["avg_spend"] for row in cursor.fetchall()}

    for supplier, current_spend in current.items():
        avg_spend = historical.get(supplier, 0)
        if avg_spend > 0 and current_spend > avg_spend * 1.5 and current_spend > 500:
            increase_pct = ((current_spend - avg_spend) / avg_spend) * 100
            alerts.append(SpendAlert(
                alert_id=f"SPIKE-{supplier[:20]}-{current_month}",
                alert_type="supplier_spike",
                severity="warning" if increase_pct < 100 else "critical",
                title=f"Spike: {supplier}",
                message=f"+{increase_pct:.0f}% | EUR {current_spend:,.2f} vs. Avg EUR {avg_spend:,.2f}",
                data={"supplier": supplier, "current": round(current_spend, 2),
                      "average": round(avg_spend, 2), "increase_pct": round(increase_pct, 1)},
                created_at=datetime.now().isoformat()
            ))

    conn.close()
    return alerts


def _check_maintenance_cost_trends() -> List[SpendAlert]:
    alerts = []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT urgency, COUNT(*) as cnt FROM maintenance_requests
        WHERE created_at >= datetime('now', '-30 days') GROUP BY urgency
    """)
    recent = {row["urgency"]: row["cnt"] for row in cursor.fetchall()}
    total_recent = sum(recent.values())
    critical_count = recent.get("critical", 0)

    if critical_count >= 2:
        alerts.append(SpendAlert(
            alert_id=f"MAINT-CRITICAL-{datetime.now().strftime('%Y-%m')}",
            alert_type="maintenance_cost", severity="critical",
            title=f"{critical_count} kritische Wartungen (30d)",
            message=f"{total_recent} gesamt, {critical_count} kritisch",
            data={"total": total_recent, "critical": critical_count},
            created_at=datetime.now().isoformat()
        ))

    cursor.execute("""
        SELECT json_extract(part_info_json, '$.part_name') as part_name,
               json_extract(part_info_json, '$.category') as category,
               COUNT(*) as cnt, GROUP_CONCAT(location, ', ') as locations
        FROM maintenance_requests WHERE created_at >= datetime('now', '-90 days')
        GROUP BY part_name HAVING cnt >= 2 ORDER BY cnt DESC
    """)
    for part in cursor.fetchall():
        part = dict(part)
        alerts.append(SpendAlert(
            alert_id=f"MAINT-RECURRING-{part['part_name'][:20]}",
            alert_type="maintenance_cost", severity="warning",
            title=f"Wiederkehrend: {part['part_name']}",
            message=f"{part['cnt']}x in 90d | {part['locations']}",
            data={"part_name": part["part_name"], "count": part["cnt"]},
            created_at=datetime.now().isoformat()
        ))

    conn.close()
    return alerts


def _create_default_budgets(cursor, conn):
    cursor.execute("""
        SELECT ROUND(AVG(monthly_total), 2) as avg_monthly
        FROM (
            SELECT strftime('%Y-%m', datum) as period, SUM(betrag_brutto) as monthly_total
            FROM invoices WHERE datum IS NOT NULL AND datum != '' AND betrag_brutto > 0
            GROUP BY period HAVING monthly_total > 0
        )
    """)
    stats = cursor.fetchone()
    avg_monthly = stats[0] if stats and stats[0] else 15000
    monthly_limit = round(avg_monthly * 1.2, -2)

    cursor.execute("""
        INSERT INTO spend_budgets (budget_type, reference_key, monthly_limit, quarterly_limit, yearly_limit)
        VALUES ('global', 'all', ?, ?, ?)
    """, (monthly_limit, monthly_limit * 3, monthly_limit * 12))
    conn.commit()


def _save_alerts(alerts: List[SpendAlert]):
    if not alerts:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for alert in alerts:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO spend_alerts (alert_id, alert_type, severity, title, message, data_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (alert.alert_id, alert.alert_type, alert.severity,
                  alert.title, alert.message, json.dumps(alert.data, ensure_ascii=False)))
        except Exception:
            pass
    conn.commit()
    conn.close()


def forecast_spend(months_ahead: int = 3) -> List[SpendForecast]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%Y-%m', datum) as period, SUM(betrag_brutto) as total
        FROM invoices WHERE datum IS NOT NULL AND datum != '' AND betrag_brutto > 0
        GROUP BY period HAVING total > 0 ORDER BY period
    """)
    history = cursor.fetchall()
    conn.close()

    if len(history) < 3:
        return []

    amounts = [h[1] for h in history]
    weights = [1, 1.5, 2, 2.5, 3]
    recent = amounts[-5:]
    w = weights[-len(recent):]
    weighted_avg = sum(a * wt for a, wt in zip(recent, w)) / sum(w)

    recent_6 = amounts[-6:]
    n = len(recent_6)
    if n >= 3:
        x_mean = (n - 1) / 2
        y_mean = sum(recent_6) / n
        num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent_6))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0
    else:
        slope = 0

    trend = "rising" if slope > weighted_avg * 0.05 else "declining" if slope < -weighted_avg * 0.05 else "stable"
    cv = (math.sqrt(sum((x - weighted_avg) ** 2 for x in recent) / len(recent)) / weighted_avg) if weighted_avg > 0 else 1
    confidence = max(0.3, min(0.95, 1 - cv))

    forecasts = []
    now = datetime.now()
    for i in range(1, months_ahead + 1):
        period = (now + timedelta(days=30 * i)).strftime("%Y-%m")
        predicted = max(0, weighted_avg + (slope * i))
        forecasts.append(SpendForecast(
            period=period, predicted_amount=round(predicted, 2),
            confidence=round(confidence - (i * 0.05), 2), trend=trend,
            basis=f"WMA + trend (n={len(amounts)})"
        ))
    return forecasts


def set_budget(budget_type: str, reference_key: str = "all",
               monthly_limit: float = None, quarterly_limit: float = None,
               yearly_limit: float = None, alert_pct: float = 80.0,
               critical_pct: float = 95.0) -> Dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM spend_budgets WHERE budget_type = ? AND reference_key = ?",
                   (budget_type, reference_key))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            UPDATE spend_budgets SET monthly_limit=COALESCE(?,monthly_limit),
            quarterly_limit=COALESCE(?,quarterly_limit), yearly_limit=COALESCE(?,yearly_limit),
            alert_threshold_pct=?, critical_threshold_pct=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (monthly_limit, quarterly_limit, yearly_limit, alert_pct, critical_pct, existing[0]))
        action = "updated"
    else:
        cursor.execute("""
            INSERT INTO spend_budgets (budget_type, reference_key, monthly_limit, quarterly_limit,
            yearly_limit, alert_threshold_pct, critical_threshold_pct) VALUES (?,?,?,?,?,?,?)
        """, (budget_type, reference_key, monthly_limit, quarterly_limit, yearly_limit, alert_pct, critical_pct))
        action = "created"
    conn.commit()
    conn.close()
    return {"status": action, "budget_type": budget_type, "reference_key": reference_key}


def get_budgets() -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM spend_budgets WHERE is_active = 1")
    budgets = [dict(row) for row in cursor.fetchall()]
    current_month = datetime.now().strftime("%Y-%m")
    for b in budgets:
        cursor.execute("SELECT COALESCE(SUM(betrag_brutto),0) FROM invoices WHERE strftime('%Y-%m',datum)=? AND betrag_brutto>0", (current_month,))
        b["current_month_spent"] = round(cursor.fetchone()[0], 2)
        b["utilization_pct"] = round(b["current_month_spent"] / b["monthly_limit"] * 100, 1) if b["monthly_limit"] else 0
    conn.close()
    return budgets


def get_active_alerts(limit: int = 20) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM spend_alerts WHERE acknowledged = 0
        ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END,
        created_at DESC LIMIT ?
    """, (limit,))
    alerts = []
    for row in cursor.fetchall():
        a = dict(row)
        a["data"] = json.loads(a.pop("data_json", "{}"))
        alerts.append(a)
    conn.close()
    return alerts


def acknowledge_alert(alert_id: str, user_id: int = None) -> Dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE spend_alerts SET acknowledged=1, acknowledged_by=?, acknowledged_at=CURRENT_TIMESTAMP WHERE alert_id=?",
                   (user_id, alert_id))
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return {"acknowledged": updated > 0, "alert_id": alert_id}


init_spend_analytics_db()
