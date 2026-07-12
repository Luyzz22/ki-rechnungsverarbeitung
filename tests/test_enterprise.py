"""Tests für die Enterprise-Features Phase 4 (UI) + Phase 5 (GoBD/Audit/DSGVO)."""

import json
from datetime import datetime, timedelta

import pytest

import approval_workflow
import audit_events
import database
import dsgvo
import enterprise_dashboard
import gobd
from enterprise_db import get_retention_years, get_tenant_id, set_retention_years
from supplier_overview import count_active_anomalies, get_supplier_detail, get_suppliers


class _FakeRequest:
    def __init__(self, session):
        self.session = session


# ---------------------------------------------------------------------------
# enterprise_db
# ---------------------------------------------------------------------------
def test_get_tenant_id_from_session(db):
    assert get_tenant_id(_FakeRequest({"user_id": 7})) == 7
    assert get_tenant_id(_FakeRequest({})) is None


def test_retention_policy_default_and_set(db):
    assert get_retention_years(1) == 10  # GoBD Default
    set_retention_years(1, 6)
    assert get_retention_years(1) == 6


# ---------------------------------------------------------------------------
# Phase 4c – Lieferanten-Übersicht
# ---------------------------------------------------------------------------
def test_supplier_aggregation_and_isolation(db, add_invoice):
    add_invoice("Müller GmbH", 100.0)
    add_invoice("Müller GmbH", 300.0)
    add_invoice("Schmidt AG", 500.0)
    add_invoice("Fremd GmbH", 999.0, tenant=2)  # anderer Mandant

    suppliers = get_suppliers(1, sort_by="volumen")
    names = [s["name"] for s in suppliers]
    assert "Müller GmbH" in names
    assert "Fremd GmbH" not in names  # Tenant-Isolation

    mueller = next(s for s in suppliers if s["name"] == "Müller GmbH")
    assert mueller["count"] == 2
    assert mueller["total"] == 400.0
    assert mueller["avg"] == 200.0


def test_supplier_sort_by_name(db, add_invoice):
    add_invoice("Zeta", 100.0)
    add_invoice("Alpha", 100.0)
    suppliers = get_suppliers(1, sort_by="name")
    assert suppliers[0]["name"] == "Alpha"


def test_new_supplier_high_risk(db, add_invoice):
    add_invoice("Einmalig GmbH", 5000.0)
    suppliers = get_suppliers(1, sort_by="risiko")
    top = suppliers[0]
    assert top["name"] == "Einmalig GmbH"
    assert top["risk_label"] == "hoch"
    assert count_active_anomalies(1) >= 1


def test_supplier_detail(db, add_invoice):
    add_invoice("Detail GmbH", 100.0, invoice_no="A")
    add_invoice("Detail GmbH", 200.0, invoice_no="B")
    detail = get_supplier_detail(1, "Detail GmbH")
    assert detail["summary"]["count"] == 2
    assert len(detail["invoices"]) == 2


# ---------------------------------------------------------------------------
# Phase 4a – Dashboard KPIs
# ---------------------------------------------------------------------------
def test_kpis_counts_and_automation(db, add_invoice):
    add_invoice("A", 100.0, days_ago=0)        # heute
    add_invoice("B", 100.0, days_ago=2)        # diesen Monat (i.d.R.)
    add_invoice("C", 100.0, days_ago=0, manual=1)  # manuell korrigiert

    kpis = enterprise_dashboard.get_kpis(1)
    assert kpis["count_today"] == 2
    assert kpis["total_invoices"] == 3
    # 2 von 3 ohne manuelle Korrektur
    assert kpis["automation_rate"] == pytest.approx(66.7, abs=0.2)
    assert len(kpis["trend"]) == 30


def test_kpis_status_breakdown_matches_list(db, add_invoice):
    """B4: Status-Kacheln (status_breakdown) = Summe der Rechnungsliste."""
    add_invoice("A", 100.0)  # ohne Status → 'neu'
    add_invoice("B", 100.0)
    conn = database.get_connection(); cur = conn.cursor()
    for supplier, status in (("C", "verarbeitet"), ("D", "pruefen"), ("E", "verarbeitet")):
        cur.execute(
            "INSERT INTO invoices (rechnungsaussteller, betrag_brutto, status, tenant_id, created_at) "
            "VALUES (?,?,?,?,?)",
            (supplier, 50.0, status, 1, datetime.now().isoformat()))
    conn.commit(); conn.close()

    kpis = enterprise_dashboard.get_kpis(1)
    sb = kpis["status_breakdown"]
    assert sb.get("neu") == 2
    assert sb.get("verarbeitet") == 2
    assert sb.get("pruefen") == 1
    # Kacheln = Summe der Liste
    assert sum(sb.values()) == kpis["total_invoices"] == 5


def test_kpis_count_month_uses_created_at_not_datum(db):
    """B4: Volumen-KPIs zählen über created_at (Verarbeitungszeitpunkt), nicht
    über das Rechnungsdatum."""
    conn = database.get_connection(); cur = conn.cursor()
    # Rechnungsdatum weit in der Vergangenheit, aber created_at = jetzt
    cur.execute(
        "INSERT INTO invoices (rechnungsaussteller, betrag_brutto, datum, created_at, tenant_id) "
        "VALUES (?,?,?,?,?)",
        ("X", 10.0, "2020-01-01", datetime.now().isoformat(), 1))
    conn.commit(); conn.close()
    kpis = enterprise_dashboard.get_kpis(1)
    assert kpis["count_month"] >= 1  # via created_at gezählt, nicht datum=2020


def test_get_statistics_counts_tenant_invoices(tmp_path, monkeypatch):
    """B4/pg: get_statistics zählt Rechnungen tenant-sicher (LEFT JOIN + COALESCE),
    nicht 0 durch INNER JOIN auf leere jobs; läuft ohne SQLite-only-Konstrukte
    (Identifier-Quote/DATE('now'))."""
    import sqlite3
    from cache import invalidate_cache
    db_file = tmp_path / "stats.db"
    monkeypatch.setattr(database, "_ensure_db_path", lambda: db_file)
    invalidate_cache("statistics")  # Cache-Leak zwischen Tests vermeiden
    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE jobs (job_id TEXT PRIMARY KEY, user_id INTEGER, status TEXT, "
        "created_at TEXT, total_amount REAL, successful INTEGER, total_files INTEGER)")
    conn.execute(
        "CREATE TABLE invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, "
        "rechnungsaussteller TEXT, betrag_brutto REAL, tenant_id INTEGER)")
    conn.execute(
        "INSERT INTO jobs (job_id,user_id,status,created_at,total_amount,successful,total_files) "
        "VALUES ('j1',1,'completed',?,200.0,2,2)", (datetime.now().isoformat(),))
    conn.execute("INSERT INTO invoices (job_id, rechnungsaussteller, betrag_brutto, tenant_id) "
                 "VALUES ('j1','A',100.0,1)")
    # Orphan-Rechnung: nur tenant_id, keine jobs-Zeile → INNER JOIN hätte sie verloren
    conn.execute("INSERT INTO invoices (rechnungsaussteller, betrag_brutto, tenant_id) "
                 "VALUES ('B',100.0,1)")
    conn.commit(); conn.close()

    stats = database.get_statistics(user_id=1)
    assert stats["total_invoices"] == 2  # inkl. Orphan (LEFT JOIN + COALESCE)
    assert stats["total_jobs"] == 1
    # Gesamtsumme + Durchschnitt auf DEMSELBEN Rechnungssatz wie die Zählung
    # (inkl. Orphan-Betrag) – nicht aus jobs.total_amount.
    assert stats["total_amount"] == 200.0
    assert stats["avg_per_invoice"] == 100.0
    assert isinstance(stats["daily_data"], list)
    assert isinstance(stats["top_aussteller"], list)
    invalidate_cache("statistics")


def test_render_trend_svg(db):
    trend = enterprise_dashboard.get_trend(1, days=30)
    svg = enterprise_dashboard.render_trend_svg(trend)
    assert svg.startswith("<svg")
    assert "polyline" in svg


# ---------------------------------------------------------------------------
# Phase 4b – Freigabe-Workflow
# ---------------------------------------------------------------------------
def test_required_stages_by_amount(db):
    rules = approval_workflow.get_rules(1)
    assert [r.role for r in approval_workflow.required_stages(500, rules)] == ["Sachbearbeiter"]
    assert [r.role for r in approval_workflow.required_stages(5000, rules)] == [
        "Sachbearbeiter", "Teamleiter"
    ]
    assert [r.role for r in approval_workflow.required_stages(50000, rules)] == [
        "Sachbearbeiter", "Teamleiter", "Geschäftsführung"
    ]


def test_multistage_approval_flow(db, add_invoice):
    inv = add_invoice("Big AG", 15000.0)
    res = approval_workflow.submit_for_approval(1, inv, 15000.0, user_id=1, notify=False)
    rid = res["request_id"]
    assert res["required_role"] == "Sachbearbeiter"

    open_now = approval_workflow.get_open_approvals(1)
    assert len(open_now) == 1

    r1 = approval_workflow.approve(1, rid, 1, notify=False)
    assert r1["final"] is False and r1["next_role"] == "Teamleiter"
    r2 = approval_workflow.approve(1, rid, 1, notify=False)
    assert r2["final"] is False and r2["next_role"] == "Geschäftsführung"
    r3 = approval_workflow.approve(1, rid, 1, notify=False)
    assert r3["final"] is True and r3["status"] == "freigegeben"

    assert approval_workflow.get_open_approvals(1) == []
    # Rechnung wurde GoBD-gesperrt
    assert gobd.is_locked(inv) is True


def test_reject_approval(db, add_invoice):
    inv = add_invoice("X", 500.0)
    res = approval_workflow.submit_for_approval(1, inv, 500.0, user_id=1, notify=False)
    out = approval_workflow.reject(1, res["request_id"], 1, comment="nicht ok")
    assert out["status"] == "abgelehnt"
    assert approval_workflow.get_open_approvals(1) == []


def test_escalation_after_48h(db, add_invoice):
    inv = add_invoice("Y", 500.0)
    res = approval_workflow.submit_for_approval(1, inv, 500.0, user_id=1, notify=False)
    # künstlich altern lassen
    old = (datetime.now() - timedelta(hours=72)).isoformat(timespec="seconds")
    conn = database.get_connection()
    conn.execute("UPDATE freigabe_requests SET created_at = ? WHERE id = ?", (old, res["request_id"]))
    conn.commit()
    conn.close()

    count = approval_workflow.check_escalations(1)
    assert count == 1
    overdue = approval_workflow.get_open_approvals(1)[0]
    assert overdue["escalated"] == 1
    assert overdue["overdue"] is True


# ---------------------------------------------------------------------------
# Phase 5a – GoBD
# ---------------------------------------------------------------------------
def test_sha256():
    assert gobd.compute_sha256("abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_lock_and_isolation(db, add_invoice):
    inv = add_invoice("L", 100.0)
    assert gobd.is_locked(inv) is False
    gobd.lock_invoice(1, inv, user_id=1)
    assert gobd.is_locked(inv) is True
    # fremder Tenant darf nicht sperren
    with pytest.raises(gobd.GoBDError):
        gobd.lock_invoice(2, inv, user_id=2)


def test_soft_delete_requires_reason(db, add_invoice):
    inv = add_invoice("D", 100.0)
    with pytest.raises(gobd.GoBDError):
        gobd.soft_delete_invoice(1, inv, "", user_id=1)
    assert gobd.soft_delete_invoice(1, inv, "Doppelerfassung", user_id=1) is True
    # soft-gelöschte Rechnung verschwindet aus Lieferantensicht
    assert get_suppliers(1) == []


def test_export_protocol(db):
    rec = gobd.record_export(1, "datev", "spalte1;spalte2\n1;2\n", file_name="export.csv",
                             row_count=1, user_id=1)
    assert len(rec["sha256"]) == 64
    entries = gobd.get_export_protocol(1)
    assert len(entries) == 1
    assert entries[0]["export_type"] == "datev"


# ---------------------------------------------------------------------------
# Phase 5b – Audit-Trail
# ---------------------------------------------------------------------------
def test_audit_log_query_and_isolation(db):
    audit_events.log_event(1, audit_events.AuditEvent.UPLOAD, user_id=1, entity_type="invoice", entity_id=5)
    audit_events.log_event(1, audit_events.AuditEvent.EXPORT, user_id=1)
    audit_events.log_event(2, audit_events.AuditEvent.LOGIN, user_id=2)

    assert audit_events.count_events(1) == 2
    assert audit_events.count_events(2) == 1  # Isolation
    uploads = audit_events.query_events(1, action="upload")
    assert len(uploads) == 1
    assert uploads[0]["entity_id"] == "5"


def test_audit_csv_export(db):
    audit_events.log_event(1, audit_events.AuditEvent.LOGIN, user_id=1)
    csv_data = audit_events.export_csv(1)
    assert "zeitstempel" in csv_data
    assert "login" in csv_data


def test_audit_pagination(db):
    for i in range(5):
        audit_events.log_event(1, audit_events.AuditEvent.UPLOAD, user_id=1, entity_id=i)
    page1 = audit_events.query_events(1, limit=2, offset=0)
    page2 = audit_events.query_events(1, limit=2, offset=2)
    assert len(page1) == 2 and len(page2) == 2
    assert page1[0]["id"] != page2[0]["id"]


# ---------------------------------------------------------------------------
# Phase 5c – DSGVO
# ---------------------------------------------------------------------------
def test_auskunft(db, add_invoice):
    add_invoice("Aus GmbH", 100.0)
    data = dsgvo.get_auskunft(1)
    assert data["user_id"] == 1
    assert data["user"]["email"] == "test@sbs.de"
    assert "password_hash" not in data["user"]
    assert len(data["invoices"]) == 1


def test_anonymize_user(db, add_invoice):
    add_invoice("Anon GmbH", 100.0)
    result = dsgvo.anonymize_user(1, performed_by=1)
    assert result["ok"] is True
    conn = database.get_connection()
    row = conn.execute("SELECT email, name, is_active FROM users WHERE id = 1").fetchone()
    conn.close()
    assert row[0].startswith("anonym-1@")
    assert row[1] == "Anonymisiert"
    assert row[2] == 0


def test_retention_cleanup(db, add_invoice):
    # 11 Jahre alte Rechnung
    old_inv = add_invoice("Alt GmbH", 100.0, days_ago=365 * 11)
    add_invoice("Neu GmbH", 100.0, days_ago=1)
    result = dsgvo.run_retention_cleanup(1)
    assert result["invoices_marked"] == 1
    conn = database.get_connection()
    deleted = conn.execute("SELECT deleted FROM invoices WHERE id = ?", (old_inv,)).fetchone()[0]
    conn.close()
    assert deleted == 1
