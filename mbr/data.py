from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional

try:
    from zoneinfo import ZoneInfo  # py3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


@dataclass(frozen=True)
class MonthWindow:
    start: date
    end_exclusive: date
    label_de: str
    year: int
    month: int


@dataclass(frozen=True)
class SupplierRow:
    supplier: str
    amount_net: float


@dataclass(frozen=True)
class CategoryRow:
    category_id: int
    category_name: str
    actual_net: float
    budget: float
    variance: float
    variance_pct: Optional[float]


@dataclass(frozen=True)
class MBRData:
    window: MonthWindow
    data_source: str
    coverage_note: str
    total_net: float
    total_gross: float
    invoice_count: int
    top_suppliers: list[SupplierRow]
    categories: list[CategoryRow]


def _month_label_de(y: int, m: int) -> str:
    months = [
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember"
    ]
    return f"{months[m-1]} {y}"


def previous_month_window(tz: str = "Europe/Berlin") -> MonthWindow:
    if ZoneInfo is not None:
        today = datetime.now(ZoneInfo(tz)).date()
    else:
        today = date.today()

    first_this = today.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    start_prev = last_prev.replace(day=1)
    end_excl = first_this

    return MonthWindow(
        start=start_prev,
        end_exclusive=end_excl,
        label_de=_month_label_de(start_prev.year, start_prev.month),
        year=start_prev.year,
        month=start_prev.month,
    )


def _connect_if_needed(db_connection: Any) -> tuple[sqlite3.Connection, bool]:
    if isinstance(db_connection, sqlite3.Connection):
        return db_connection, False
    if isinstance(db_connection, str):
        conn = sqlite3.connect(db_connection, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn, True
    raise TypeError("db_connection must be sqlite3.Connection or path str")


def _safe_float(x: Any) -> float:
    try:
        return float(x) if x is not None else 0.0
    except Exception:
        return 0.0


def aggregate_mbr_data(
    db_connection: Any,
    window: Optional[MonthWindow] = None,
    tz: str = "Europe/Berlin",
    fallback_to_latest_month_if_empty: bool = True,
) -> MBRData:
    """
    Aggregation source-of-truth (based on invoices.db schema):
      - rechnungen: lieferant, rechnungs_datum, netto_betrag, brutto_betrag, kategorie_id
      - budgets: kategorie_id, monat, jahr, betrag
      - budget_kategorien: id, name, aktiv
    """
    conn, should_close = _connect_if_needed(db_connection)
    try:
        conn.row_factory = sqlite3.Row
        win = window or previous_month_window(tz=tz)

        invoice_table = "rechnungen"
        date_col = "rechnungs_datum"
        net_col = "netto_betrag"
        gross_col = "brutto_betrag"
        supplier_col = "lieferant"
        category_col = "kategorie_id"

        # month coverage check
        cur = conn.execute(
            f"SELECT COUNT(*) AS n FROM {invoice_table} WHERE DATE({date_col}) >= DATE(?) AND DATE({date_col}) < DATE(?);",
            (win.start.isoformat(), win.end_exclusive.isoformat()),
        )
        n = int(cur.fetchone()["n"])
        coverage_note = f"Datenbasis: {invoice_table} für {win.label_de}."
        data_source = "invoices.db:rechnungen"

        # fallback to latest month with data (enterprise-safe)
        if n == 0 and fallback_to_latest_month_if_empty:
            cur = conn.execute(f"SELECT MAX(DATE({date_col})) AS d FROM {invoice_table};")
            max_d = cur.fetchone()["d"]
            if max_d:
                d = date.fromisoformat(str(max_d)[:10])
                start = d.replace(day=1)
                if start.month == 12:
                    end_excl = date(start.year + 1, 1, 1)
                else:
                    end_excl = date(start.year, start.month + 1, 1)

                win = MonthWindow(
                    start=start,
                    end_exclusive=end_excl,
                    label_de=_month_label_de(start.year, start.month),
                    year=start.year,
                    month=start.month,
                )

                cur = conn.execute(
                    f"SELECT COUNT(*) AS n FROM {invoice_table} WHERE DATE({date_col}) >= DATE(?) AND DATE({date_col}) < DATE(?);",
                    (win.start.isoformat(), win.end_exclusive.isoformat()),
                )
                n = int(cur.fetchone()["n"])
                coverage_note = (
                    f"Keine Rechnungsdaten im Zielmonat; Fallback auf letzten Monat mit Daten: {win.label_de} "
                    f"(Quelle: {invoice_table})."
                )

        # totals
        cur = conn.execute(
            f"""
            SELECT
              COALESCE(SUM({net_col}), 0) AS total_net,
              COALESCE(SUM({gross_col}), 0) AS total_gross,
              COUNT(*) AS cnt
            FROM {invoice_table}
            WHERE DATE({date_col}) >= DATE(?) AND DATE({date_col}) < DATE(?);
            """,
            (win.start.isoformat(), win.end_exclusive.isoformat()),
        )
        row = cur.fetchone()
        total_net = _safe_float(row["total_net"])
        total_gross = _safe_float(row["total_gross"])
        invoice_count = int(row["cnt"])

        # top suppliers
        cur = conn.execute(
            f"""
            SELECT
              COALESCE(NULLIF(TRIM({supplier_col}), ''), 'Unbekannt') AS supplier,
              COALESCE(SUM({net_col}), 0) AS amount_net
            FROM {invoice_table}
            WHERE DATE({date_col}) >= DATE(?) AND DATE({date_col}) < DATE(?)
            GROUP BY supplier
            ORDER BY amount_net DESC
            LIMIT 5;
            """,
            (win.start.isoformat(), win.end_exclusive.isoformat()),
        )
        top_suppliers = [
            SupplierRow(supplier=str(r["supplier"]), amount_net=_safe_float(r["amount_net"]))
            for r in cur.fetchall()
        ]

        # budgets by category
        cur = conn.execute(
            """
            SELECT
              bk.id AS category_id,
              bk.name AS category_name,
              COALESCE(b.betrag, 0) AS budget
            FROM budget_kategorien bk
            LEFT JOIN budgets b
              ON b.kategorie_id = bk.id AND b.jahr = ? AND b.monat = ?
            WHERE bk.aktiv IS NULL OR bk.aktiv = 1
            ORDER BY bk.name ASC;
            """,
            (win.year, win.month),
        )
        budgets = {int(r["category_id"]): (str(r["category_name"]), _safe_float(r["budget"])) for r in cur.fetchall()}

        # actuals by category
        cur = conn.execute(
            f"""
            SELECT
              COALESCE({category_col}, -1) AS category_id,
              COALESCE(SUM({net_col}), 0) AS actual_net
            FROM {invoice_table}
            WHERE DATE({date_col}) >= DATE(?) AND DATE({date_col}) < DATE(?)
            GROUP BY category_id;
            """,
            (win.start.isoformat(), win.end_exclusive.isoformat()),
        )
        actuals = {int(r["category_id"]): _safe_float(r["actual_net"]) for r in cur.fetchall()}

        # merge
        category_rows: list[CategoryRow] = []
        seen: set[int] = set()

        for cid, (cname, bud) in budgets.items():
            act = actuals.get(cid, 0.0)
            var = act - bud
            var_pct = (var / bud) if bud else None
            category_rows.append(CategoryRow(cid, cname, act, bud, var, var_pct))
            seen.add(cid)

        for cid, act in actuals.items():
            if cid in seen:
                continue
            category_rows.append(CategoryRow(cid, f"Kategorie {cid}", act, 0.0, act, None))

        category_rows.sort(key=lambda r: r.actual_net, reverse=True)

        return MBRData(
            window=win,
            data_source=data_source,
            coverage_note=coverage_note,
            total_net=total_net,
            total_gross=total_gross,
            invoice_count=invoice_count,
            top_suppliers=top_suppliers,
            categories=category_rows,
        )
    finally:
        if should_close:
            conn.close()
