#!/usr/bin/env python3
"""
SBS Deutschland – Lieferanten-Übersicht (Phase 4c)

Aggregiert Lieferantendaten pro Tenant und berechnet einen Risiko-Score.

Der Risiko-Score orientiert sich an den Heuristiken aus
``modules/.../services/anomaly_detection.py`` (unbekannter/neuer Lieferant,
Betrags-Ausreißer, Rundbeträge), implementiert sie hier jedoch direkt auf dem
SQLite-Schema der Hauptanwendung (Tabelle ``invoices`` + ``jobs``-JOIN).

Tenant-Isolation: ``COALESCE(invoices.tenant_id, jobs.user_id) = tenant_id``
(tenant_id bevorzugt, jobs.user_id nur als Legacy-Fallback).
"""

from __future__ import annotations

import logging
import statistics
from typing import Any, Dict, List, Optional

from database import get_connection
from supplier_names import UNKNOWN, best_display_name, canonical_key, sanitize_supplier

logger = logging.getLogger(__name__)

_VALID_SORTS = {"volumen", "risiko", "name"}


def _clean_supplier(raw: Any) -> str:
    """Bereinigter Anzeigename für einen gespeicherten Aussteller (Dateinamen/
    Platzhalter → 'Unbekannt'). Konsolidiert Bestandsdaten im Lesepfad."""
    return sanitize_supplier(raw) or UNKNOWN


def _fetch_invoices(tenant_id: int) -> List[Dict[str, Any]]:
    """Holt alle (nicht gelöschten) Rechnungen des Tenants."""
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT i.id,
               COALESCE(NULLIF(TRIM(i.rechnungsaussteller), ''), 'Unbekannt') AS supplier,
               COALESCE(i.betrag_brutto, 0)            AS amount,
               i.datum                                  AS invoice_date,
               COALESCE(CAST(i.created_at AS TEXT), CAST(j.created_at AS TEXT)) AS created_at
        FROM invoices i
        LEFT JOIN jobs j ON i.job_id = j.job_id
        WHERE COALESCE(i.tenant_id, j.user_id) = ?
          AND COALESCE(i.deleted, 0) = 0
        """,
        (int(tenant_id),),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def _supplier_risk(invoices: List[Dict[str, Any]], global_avg: float) -> Dict[str, Any]:
    """Berechnet Risiko-Score (0-100) für die Rechnungen EINES Lieferanten."""
    amounts = [float(i["amount"] or 0) for i in invoices]
    count = len(amounts)
    score = 0
    reasons: List[str] = []

    # 1. Unbekannter / neuer Lieferant (wenig Historie)
    if count <= 1:
        score += 50
        reasons.append("Neuer/unbekannter Lieferant (nur 1 Rechnung)")
    elif count == 2:
        score += 20
        reasons.append("Wenig Historie (2 Rechnungen)")

    # 2. Betrags-Ausreißer innerhalb des Lieferanten (> 2σ)
    if count >= 3:
        avg = statistics.mean(amounts)
        try:
            stdev = statistics.pstdev(amounts)
        except statistics.StatisticsError:
            stdev = 0
        if stdev > 0:
            max_dev = max(abs(a - avg) for a in amounts) / stdev
            if max_dev > 3:
                score += 30
                reasons.append(f"Starker Betrags-Ausreißer ({max_dev:.1f}σ)")
            elif max_dev > 2:
                score += 15
                reasons.append(f"Betrags-Ausreißer ({max_dev:.1f}σ)")

    # 3. Ungewöhnlich hohes Volumen vs. globalem Schnitt
    if global_avg > 0:
        supplier_max = max(amounts) if amounts else 0
        if supplier_max > global_avg * 5:
            score += 15
            reasons.append("Einzelbetrag deutlich über Gesamtdurchschnitt")

    # 4. Rundbeträge (mögliche Schätzungen)
    round_amounts = [a for a in amounts if a > 100 and a == int(a) and a % 100 == 0]
    if round_amounts and len(round_amounts) >= max(1, count // 2):
        score += 10
        reasons.append("Überwiegend Rundbeträge")

    score = min(100, score)
    if score >= 60:
        label = "hoch"
    elif score >= 30:
        label = "mittel"
    else:
        label = "niedrig"

    return {"risk_score": score, "risk_label": label, "risk_reasons": reasons}


def get_suppliers(tenant_id: int, sort_by: str = "volumen") -> List[Dict[str, Any]]:
    """Liefert die Lieferanten-Übersicht des Tenants.

    Pro Lieferant: Rechnungsanzahl, Gesamtvolumen, Ø-Betrag, letzte Rechnung
    und Risiko-Score.
    """
    if sort_by not in _VALID_SORTS:
        sort_by = "volumen"

    invoices = _fetch_invoices(tenant_id)
    if not invoices:
        return []

    all_amounts = [float(i["amount"] or 0) for i in invoices]
    global_avg = statistics.mean(all_amounts) if all_amounts else 0.0

    # Kanonisch gruppieren: Schreibweisen-Varianten (Case/Interpunktion) UND
    # bereinigte Dateinamen/Platzhalter fallen zu EINEM Lieferanten zusammen.
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for inv in invoices:
        display = _clean_supplier(inv.get("supplier"))
        inv["_display"] = display
        grouped.setdefault(canonical_key(display), []).append(inv)

    suppliers: List[Dict[str, Any]] = []
    for items in grouped.values():
        # saubersten Anzeigenamen aus den Original-Schreibweisen der Gruppe wählen
        name_counts: Dict[str, int] = {}
        for i in items:
            name_counts[i["_display"]] = name_counts.get(i["_display"], 0) + 1
        name = best_display_name(name_counts.items())
        amounts = [float(i["amount"] or 0) for i in items]
        total = round(sum(amounts), 2)
        count = len(items)
        avg = round(total / count, 2) if count else 0.0
        # letzte Rechnung anhand Rechnungsdatum, Fallback created_at
        dates = [i.get("invoice_date") or i.get("created_at") or "" for i in items]
        last_date = max(dates) if dates else ""
        risk = _supplier_risk(items, global_avg)
        suppliers.append(
            {
                "name": name,
                "count": count,
                "total": total,
                "avg": avg,
                "last_date": (last_date or "")[:10],
                **risk,
            }
        )

    if sort_by == "name":
        suppliers.sort(key=lambda s: s["name"].lower())
    elif sort_by == "risiko":
        suppliers.sort(key=lambda s: s["risk_score"], reverse=True)
    else:  # volumen
        suppliers.sort(key=lambda s: s["total"], reverse=True)

    return suppliers


def get_supplier_detail(tenant_id: int, supplier: str) -> Dict[str, Any]:
    """Detailansicht eines Lieferanten inkl. Rechnungshistorie.

    Matcht kanonisch (case-/interpunktions-unabhängig), damit ein in der
    Übersicht zusammengeführter Lieferant auch im Detail alle seine Rechnungen
    zeigt – inkl. bereinigter Dateinamen/Platzhalter unter 'Unbekannt'.
    """
    key = canonical_key(_clean_supplier(supplier))
    all_invoices = _fetch_invoices(tenant_id)
    invoices = [i for i in all_invoices if canonical_key(_clean_supplier(i.get("supplier"))) == key]
    invoices.sort(key=lambda i: (i.get("invoice_date") or i.get("created_at") or ""), reverse=True)

    all_amounts = [float(i["amount"] or 0) for i in all_invoices]
    global_avg = statistics.mean(all_amounts) if all_amounts else 0.0

    amounts = [float(i["amount"] or 0) for i in invoices]
    total = round(sum(amounts), 2)
    count = len(invoices)
    # sauberster Anzeigename der Gruppe (Fallback: übergebener Name)
    name_counts: Dict[str, int] = {}
    for i in invoices:
        disp = _clean_supplier(i.get("supplier"))
        name_counts[disp] = name_counts.get(disp, 0) + 1
    display_name = best_display_name(name_counts.items()) if name_counts else (supplier or UNKNOWN)
    summary = {
        "name": display_name,
        "count": count,
        "total": total,
        "avg": round(total / count, 2) if count else 0.0,
        **(_supplier_risk(invoices, global_avg) if invoices else
           {"risk_score": 0, "risk_label": "niedrig", "risk_reasons": []}),
    }
    return {"summary": summary, "invoices": invoices}


def count_active_anomalies(tenant_id: int) -> int:
    """Anzahl Lieferanten mit hohem Risiko (für Dashboard-Alert-KPI)."""
    return sum(1 for s in get_suppliers(tenant_id, "risiko") if s["risk_label"] == "hoch")
