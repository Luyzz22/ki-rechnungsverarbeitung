#!/usr/bin/env python3
"""
SBS Deutschland – Enterprise Dashboard KPIs (Phase 4a)

Tenant-isolierte Kennzahlen für das Dashboard:
- Rechnungen heute / Monat / Quartal
- Automatisierungsquote (% ohne manuelle Korrektur)
- Offene Freigaben (Anzahl + älteste)
- Anomalie-Alerts (aktive Warnungen)
- 30-Tage-Trend (Verarbeitungsvolumen) als einfaches SVG

Tenant-Isolation: ``jobs.user_id = tenant_id``.
"""

from __future__ import annotations

import html
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from database import get_connection
from supplier_overview import count_active_anomalies

logger = logging.getLogger(__name__)

# SBS Design
SBS_PRIMARY = "#003856"
SBS_ACCENT = "#FFB900"


def _count_since(cursor, tenant_id: int, since_iso: str) -> int:
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        WHERE j.user_id = ?
          AND COALESCE(i.deleted, 0) = 0
          AND COALESCE(CAST(i.created_at AS TEXT), CAST(j.created_at AS TEXT)) >= ?
        """,
        (int(tenant_id), since_iso),
    )
    return int(cursor.fetchone()[0] or 0)


def get_kpis(tenant_id: int) -> Dict[str, Any]:
    """Berechnet alle Dashboard-KPIs für einen Tenant."""
    conn = get_connection()
    cursor = conn.cursor()

    today = date.today()
    start_today = today.isoformat()
    start_month = today.replace(day=1).isoformat()
    quarter_start_month = 3 * ((today.month - 1) // 3) + 1
    start_quarter = today.replace(month=quarter_start_month, day=1).isoformat()

    count_today = _count_since(cursor, tenant_id, start_today)
    count_month = _count_since(cursor, tenant_id, start_month)
    count_quarter = _count_since(cursor, tenant_id, start_quarter)

    # Automatisierungsquote
    cursor.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN COALESCE(i.manual_correction, 0) = 0 THEN 1 ELSE 0 END) AS automated
        FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        WHERE j.user_id = ?
          AND COALESCE(i.deleted, 0) = 0
        """,
        (int(tenant_id),),
    )
    row = cursor.fetchone()
    total = int(row[0] or 0)
    automated = int(row[1] or 0)
    automation_rate = round((automated / total) * 100, 1) if total else 0.0

    # Offene Freigaben (Anzahl + älteste)
    open_approvals = 0
    oldest_approval = None
    try:
        cursor.execute(
            """
            SELECT COUNT(*), MIN(created_at)
            FROM freigabe_requests
            WHERE tenant_id = ? AND status = 'offen'
            """,
            (int(tenant_id),),
        )
        ar = cursor.fetchone()
        open_approvals = int(ar[0] or 0)
        oldest_approval = ar[1]
    except Exception:  # pragma: no cover - Tabelle evtl. noch nicht migriert
        pass

    conn.close()

    oldest_age_hours = None
    if oldest_approval:
        try:
            dt = datetime.fromisoformat(oldest_approval)
            oldest_age_hours = round((datetime.now() - dt).total_seconds() / 3600, 1)
        except (ValueError, TypeError):
            oldest_age_hours = None

    # Anomalie-Alerts
    try:
        anomaly_alerts = count_active_anomalies(tenant_id)
    except Exception:  # pragma: no cover
        anomaly_alerts = 0

    trend = get_trend(tenant_id, days=30)

    return {
        "count_today": count_today,
        "count_month": count_month,
        "count_quarter": count_quarter,
        "automation_rate": automation_rate,
        "total_invoices": total,
        "open_approvals": open_approvals,
        "oldest_approval": oldest_approval,
        "oldest_age_hours": oldest_age_hours,
        "anomaly_alerts": anomaly_alerts,
        "trend": trend,
    }


def get_trend(tenant_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Verarbeitungsvolumen pro Tag der letzten ``days`` Tage (lückenlos)."""
    conn = get_connection()
    cursor = conn.cursor()
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    cursor.execute(
        """
        SELECT substr(COALESCE(CAST(i.created_at AS TEXT), CAST(j.created_at AS TEXT)), 1, 10) AS day, COUNT(*) AS cnt
        FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        WHERE j.user_id = ?
          AND COALESCE(i.deleted, 0) = 0
          AND substr(COALESCE(CAST(i.created_at AS TEXT), CAST(j.created_at AS TEXT)), 1, 10) >= ?
        GROUP BY day
        """,
        (int(tenant_id), since),
    )
    counts = {r[0]: int(r[1] or 0) for r in cursor.fetchall() if r[0]}
    conn.close()

    series: List[Dict[str, Any]] = []
    for offset in range(days):
        d = (date.today() - timedelta(days=days - 1 - offset)).isoformat()
        series.append({"date": d, "count": counts.get(d, 0)})
    return series


def render_trend_svg(trend: List[Dict[str, Any]], width: int = 720, height: int = 180) -> str:
    """Rendert den 30-Tage-Trend als einfaches, eingebettetes SVG (keine JS-Abhängigkeit)."""
    if not trend:
        return '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

    pad_l, pad_r, pad_t, pad_b = 36, 12, 12, 24
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    max_count = max((p["count"] for p in trend), default=0)
    y_max = max(max_count, 1)
    n = len(trend)
    step = plot_w / max(n - 1, 1)

    points = []
    for idx, p in enumerate(trend):
        x = pad_l + idx * step
        y = pad_t + plot_h - (p["count"] / y_max) * plot_h
        points.append((x, y))

    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    # Fläche unter der Linie
    area = (
        f"{pad_l:.1f},{pad_t + plot_h:.1f} "
        + polyline
        + f" {pad_l + (n - 1) * step:.1f},{pad_t + plot_h:.1f}"
    )

    baseline_y = pad_t + plot_h
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" role="img" aria-label="30-Tage-Trend Verarbeitungsvolumen">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        # y-Achsen-Beschriftung
        f'<text x="4" y="{pad_t + 8}" font-size="10" fill="#666">{y_max}</text>',
        f'<text x="4" y="{baseline_y}" font-size="10" fill="#666">0</text>',
        f'<line x1="{pad_l}" y1="{baseline_y}" x2="{width - pad_r}" y2="{baseline_y}" stroke="#e0e0e0" stroke-width="1"/>',
        f'<polygon points="{area}" fill="{SBS_ACCENT}" fill-opacity="0.18"/>',
        f'<polyline points="{polyline}" fill="none" stroke="{SBS_PRIMARY}" stroke-width="2"/>',
    ]
    # Datenpunkt-Marker (nur Endpunkt, um SVG schlank zu halten)
    last_x, last_y = points[-1]
    parts.append(
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3" fill="{SBS_ACCENT}" stroke="{SBS_PRIMARY}"/>'
    )
    # x-Achsen-Beschriftung (erster/letzter Tag)
    first_label = html.escape(trend[0]["date"][5:])
    last_label = html.escape(trend[-1]["date"][5:])
    parts.append(f'<text x="{pad_l}" y="{height - 6}" font-size="10" fill="#666">{first_label}</text>')
    parts.append(
        f'<text x="{width - pad_r}" y="{height - 6}" font-size="10" fill="#666" text-anchor="end">{last_label}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)
