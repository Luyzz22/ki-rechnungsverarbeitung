"""
Analytics Service for SBS Invoice App.

Provides reusable, read-only analytics functions on top of the invoices database.
Designed to be used by:
- Dashboards (analytics.html, analytics_costs.html)
- Future Finance Copilot (chat-based analytics)
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any


# ------------------------------------------------------------
# DB CONFIG
# ------------------------------------------------------------

def _detect_default_db_path() -> str:
    """
    Detect a sensible default path for the invoices database.

    Preference:
    1) env var INVOICES_DB_PATH
    2) data/invoices.db
    3) invoices.db in project root
    """
    env_path = os.getenv("INVOICES_DB_PATH")
    if env_path:
        return env_path

    base_dir = os.path.dirname(__file__)

    # Try data/invoices.db
    data_path = os.path.join(base_dir, "data", "invoices.db")
    if os.path.exists(data_path):
        return data_path

    # Fallback: invoices.db in root
    root_path = os.path.join(base_dir, "invoices.db")
    return root_path


INVOICES_DB_PATH = _detect_default_db_path()


@contextmanager
def _get_connection(db_path: Optional[str] = None):
    """
    Context manager for read-only SQLite access.

    NOTE:
        We keep this simple on purpose; if you later have a shared
        db connection layer, you can wire this through that instead.
    """
    path = db_path or INVOICES_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ------------------------------------------------------------
# DATA CLASSES (RETURN TYPES)
# ------------------------------------------------------------

@dataclass
class GlobalKpi:
    total_invoices: int
    total_gross: float
    total_net: Optional[float]
    total_vat: Optional[float]
    duplicates_count: int
    period_days: Optional[int]


@dataclass
class VendorCost:
    rechnungsaussteller: str
    invoice_count: int
    total_gross: float


@dataclass
class MonthlyCost:
    year_month: str  # e.g. "2025-11"
    invoice_count: int
    total_gross: float


# ------------------------------------------------------------
# HELPER: DATE RANGE
# ------------------------------------------------------------

def _build_date_filter_clause(
    days: Optional[int],
    date_column: str = "datum",
) -> Tuple[str, Tuple[Any, ...]]:
    """
    Builds a WHERE-clause snippet for a rolling date window.

    Args:
        days: Number of days to look back (None = no restriction).
        date_column: Name of the date column in the table.

    Returns:
        (sql_fragment, params)
    """
    if days is None:
        return "", ()

    # Assume ISO-like string (YYYY-MM-DD) in 'datum'.
    # If your data differs, you can switch to 'created_at' instead.
    start_date = (date.today() - timedelta(days=days)).isoformat()
    clause = f" AND {date_column} >= ? "
    params: Tuple[Any, ...] = (start_date,)
    return clause, params


# ------------------------------------------------------------
# PUBLIC API: GLOBAL KPIs
# ------------------------------------------------------------

def get_global_kpis(
    days: Optional[int] = None,
    db_path: Optional[str] = None,
) -> GlobalKpi:
    """
    Returns global KPIs for invoices over an optional rolling time window.

    Args:
        days: If set, limit to invoices with datum >= today - days.
        db_path: Optional explicit DB path.

    Returns:
        GlobalKpi dataclass instance.
    """
    where_clause = " WHERE 1=1 "
    date_clause, params = _build_date_filter_clause(days, date_column="datum")
    where_clause += date_clause

    sql_total = f"""
        SELECT
            COUNT(*) AS cnt,
            COALESCE(SUM(betrag_brutto), 0) AS total_gross,
            COALESCE(SUM(betrag_netto), NULL) AS total_net,
            COALESCE(SUM(mwst_betrag), NULL) AS total_vat
        FROM invoices
        {where_clause}
    """

    # Heuristische Dubletten: gleiche Kombination aus
    # (rechnungsaussteller, rechnungsnummer, betrag_brutto)
    # -> Gruppen mit COUNT(*) > 1 zählen als Dubletten.
    dup_where = " WHERE 1=1 "
    dup_clause, dup_params = _build_date_filter_clause(days, date_column="datum")
    dup_where += dup_clause

    sql_duplicates = f"""
        SELECT
            SUM(
                CASE WHEN cnt > 1 THEN cnt ELSE 0 END
            ) AS duplicates_count
        FROM (
            SELECT
                rechnungsaussteller,
                rechnungsnummer,
                betrag_brutto,
                COUNT(*) AS cnt
            FROM invoices
            {dup_where}
            GROUP BY rechnungsaussteller, rechnungsnummer, betrag_brutto
        ) AS grouped
    """

    with _get_connection(db_path) as conn:
        cur = conn.cursor()

        # global sums
        cur.execute(sql_total, params)
        row = cur.fetchone()
        total_invoices = int(row["cnt"] or 0)
        total_gross = float(row["total_gross"] or 0.0)
        total_net = float(row["total_net"]) if row["total_net"] is not None else None
        total_vat = float(row["total_vat"]) if row["total_vat"] is not None else None

        # duplicates
        cur.execute(sql_duplicates, dup_params)
        dup_row = cur.fetchone()
        duplicates_count = int(dup_row["duplicates_count"] or 0)

    return GlobalKpi(
        total_invoices=total_invoices,
        total_gross=total_gross,
        total_net=total_net,
        total_vat=total_vat,
        duplicates_count=duplicates_count,
        period_days=days,
    )


# ------------------------------------------------------------
# PUBLIC API: TOP VENDORS
# ------------------------------------------------------------

def get_top_vendors_by_gross(
    days: Optional[int] = None,
    limit: int = 10,
    db_path: Optional[str] = None,
) -> List[VendorCost]:
    """
    Returns top invoice issuers (rechnungsaussteller) by gross amount.

    Args:
        days: Optional rolling window based on 'datum'.
        limit: Max number of vendors.
        db_path: Optional explicit DB path.
    """
    where_clause = " WHERE 1=1 "
    date_clause, params = _build_date_filter_clause(days, date_column="datum")
    where_clause += date_clause

    sql = f"""
        SELECT
            COALESCE(rechnungsaussteller, 'Unbekannt') AS rechnungsaussteller,
            COUNT(*) AS invoice_count,
            COALESCE(SUM(betrag_brutto), 0) AS total_gross
        FROM invoices
        {where_clause}
        GROUP BY rechnungsaussteller
        HAVING total_gross > 0
        ORDER BY total_gross DESC
        LIMIT ?
    """

    params = params + (limit,)

    results: List[VendorCost] = []
    with _get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        for row in cur.fetchall():
            results.append(
                VendorCost(
                    rechnungsaussteller=row["rechnungsaussteller"],
                    invoice_count=int(row["invoice_count"] or 0),
                    total_gross=float(row["total_gross"] or 0.0),
                )
            )

    return results


# ------------------------------------------------------------
# PUBLIC API: MONTHLY COST TREND
# ------------------------------------------------------------

def get_monthly_cost_trend(
    months_back: int = 12,
    db_path: Optional[str] = None,
) -> List[MonthlyCost]:
    """
    Returns a monthly cost trend for the last N months (including current).

    Uses 'datum' if available, otherwise 'created_at' as fallback.
    Assumes ISO-like strings in those columns.
    """
    # Prefer 'datum', fallback to 'created_at'
    date_expr = """
        COALESCE(
            NULLIF(datum, ''),
            NULLIF(created_at, '')
        )
    """

    # Start at the first of the month N-1 months ago (including current month)
    today = date.today()
    year = today.year
    month = today.month - (months_back - 1)
    while month <= 0:
        month += 12
        year -= 1
    start_date = date(year, month, 1).isoformat()

    sql = f"""
        SELECT
            strftime('%Y-%m', {date_expr}) AS ym,
            COUNT(*) AS invoice_count,
            COALESCE(SUM(betrag_brutto), 0) AS total_gross
        FROM invoices
        WHERE {date_expr} >= ?
        GROUP BY ym
        ORDER BY ym ASC
    """

    results: List[MonthlyCost] = []
    with _get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(sql, (start_date,))
        for row in cur.fetchall():
            ym = row["ym"]
            if ym is None:
                # Skip rows without any usable date
                continue
            results.append(
                MonthlyCost(
                    year_month=ym,
                    invoice_count=int(row["invoice_count"] or 0),
                    total_gross=float(row["total_gross"] or 0.0),
                )
            )

    return results


# ------------------------------------------------------------
# CONVENIENCE: SUMMARY SNAPSHOT
# ------------------------------------------------------------

def get_finance_snapshot(
    days: Optional[int] = 90,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    High-level snapshot for the Finance Copilot.

    Returns a dict that can directly be fed into an LLM prompt.
    """
    kpis = get_global_kpis(days=days, db_path=db_path)
    top_vendors = get_top_vendors_by_gross(days=days, db_path=db_path)
    trend = get_monthly_cost_trend(months_back=6, db_path=db_path)

    return {
        "meta": {
            "days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "db_path": db_path or INVOICES_DB_PATH,
        },
        "kpis": {
            "total_invoices": kpis.total_invoices,
            "total_gross": kpis.total_gross,
            "total_net": kpis.total_net,
            "total_vat": kpis.total_vat,
            "duplicates_count": kpis.duplicates_count,
        },
        "top_vendors": [
            {
                "rechnungsaussteller": v.rechnungsaussteller,
                "invoice_count": v.invoice_count,
                "total_gross": v.total_gross,
            }
            for v in top_vendors
        ],
        "monthly_trend": [
            {
                "year_month": m.year_month,
                "invoice_count": m.invoice_count,
                "total_gross": m.total_gross,
            }
            for m in trend
        ],
    }


if __name__ == "__main__":
    # Small manual test helper
    snapshot = get_finance_snapshot(days=90)
    print(f"DB: {snapshot['meta']['db_path']}")
    print(f"Total invoices (last 90d): {snapshot['kpis']['total_invoices']}")
    print(f"Total gross (last 90d): {snapshot['kpis']['total_gross']} EUR")
