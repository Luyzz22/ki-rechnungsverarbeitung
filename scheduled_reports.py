#!/usr/bin/env python3
"""
SBS Deutschland – Scheduled Reports
Automatische Berichte per Email (täglich, wöchentlich, monatlich).
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database import get_connection

logger = logging.getLogger(__name__)


class ReportType:
    SUMMARY = "summary"           # Zusammenfassung
    INVOICES = "invoices"         # Rechnungsliste
    SUPPLIERS = "suppliers"       # Top-Lieferanten
    ANALYTICS = "analytics"       # Vollständige Analyse


class Schedule:
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


def create_scheduled_report(
    user_id: int,
    name: str,
    report_type: str,
    schedule: str,
    recipients: List[str],
    filters: Dict = None,
    org_id: int = None
) -> Dict:
    """Erstellt einen neuen geplanten Bericht."""
    conn = get_connection()
    cursor = conn.cursor()
    
    next_run = _calculate_next_run(schedule)
    
    cursor.execute("""
        INSERT INTO scheduled_reports 
        (user_id, org_id, name, report_type, schedule, recipients, filters, next_run)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, org_id, name, report_type, schedule,
        json.dumps(recipients), json.dumps(filters or {}),
        next_run.isoformat()
    ))
    
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"Scheduled Report erstellt: {name} ({schedule})")
    
    return {
        "id": report_id,
        "name": name,
        "report_type": report_type,
        "schedule": schedule,
        "next_run": next_run.isoformat()
    }


def _calculate_next_run(schedule: str, from_time: datetime = None) -> datetime:
    """Berechnet nächsten Ausführungszeitpunkt."""
    now = from_time or datetime.now()
    
    # Berichte um 7:00 Uhr morgens
    run_time = now.replace(hour=7, minute=0, second=0, microsecond=0)
    
    if schedule == Schedule.DAILY:
        if now.hour >= 7:
            run_time += timedelta(days=1)
    
    elif schedule == Schedule.WEEKLY:
        # Montags
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour >= 7:
            days_until_monday = 7
        run_time += timedelta(days=days_until_monday)
    
    elif schedule == Schedule.MONTHLY:
        # Am 1. des Monats
        if now.day == 1 and now.hour < 7:
            pass
        else:
            if now.month == 12:
                run_time = run_time.replace(year=now.year + 1, month=1, day=1)
            else:
                run_time = run_time.replace(month=now.month + 1, day=1)
    
    return run_time


def get_user_reports(user_id: int) -> List[Dict]:
    """Holt alle geplanten Berichte eines Users."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM scheduled_reports WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))
    
    reports = cursor.fetchall()
    conn.close()
    
    for r in reports:
        r['recipients'] = json.loads(r['recipients']) if r['recipients'] else []
        r['filters'] = json.loads(r['filters']) if r['filters'] else {}
    
    return reports


def delete_report(report_id: int, user_id: int) -> bool:
    """Löscht einen geplanten Bericht."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM scheduled_reports WHERE id = ? AND user_id = ?
    """, (report_id, user_id))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0


def toggle_report(report_id: int, user_id: int, active: bool) -> bool:
    """Aktiviert/deaktiviert einen Bericht."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE scheduled_reports SET is_active = ? WHERE id = ? AND user_id = ?
    """, (1 if active else 0, report_id, user_id))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0


def get_due_reports() -> List[Dict]:
    """Holt alle Berichte die ausgeführt werden müssen."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM scheduled_reports 
        WHERE is_active = 1 AND next_run <= ?
    """, (datetime.now().isoformat(),))
    
    reports = cursor.fetchall()
    conn.close()
    
    for r in reports:
        r['recipients'] = json.loads(r['recipients']) if r['recipients'] else []
        r['filters'] = json.loads(r['filters']) if r['filters'] else {}
    
    return reports


def mark_report_run(report_id: int):
    """Markiert Bericht als ausgeführt und berechnet nächsten Termin."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT schedule FROM scheduled_reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    
    if row:
        next_run = _calculate_next_run(row[0])
        cursor.execute("""
            UPDATE scheduled_reports 
            SET last_run = ?, next_run = ? 
            WHERE id = ?
        """, (datetime.now().isoformat(), next_run.isoformat(), report_id))
    
    conn.commit()
    conn.close()


def generate_report_content(report: Dict, user_id: int) -> Dict:
    """Generiert den Berichtsinhalt."""
    from database import get_connection
    
    report_type = report.get('report_type', ReportType.SUMMARY)
    filters = report.get('filters', {})
    days = filters.get('days', 30)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    content = {
        "title": report.get('name', 'Bericht'),
        "generated_at": datetime.now().isoformat(),
        "period_days": days
    }
    
    # Basis-Statistiken
    cursor.execute("""
        SELECT 
            COUNT(*) as count,
            COALESCE(SUM(betrag_brutto), 0) as total_brutto,
            COALESCE(SUM(betrag_netto), 0) as total_netto
        FROM invoices i
        JOIN jobs j ON i.job_id = j.job_id
        WHERE j.user_id = ? AND i.created_at > datetime('now', ?)
    """, (user_id, f'-{days} days'))
    
    row = cursor.fetchone()
    content['summary'] = {
        'invoice_count': row[0],
        'total_brutto': round(row[1], 2),
        'total_netto': round(row[2], 2)
    }
    
    if report_type in [ReportType.SUPPLIERS, ReportType.ANALYTICS]:
        # Top Lieferanten
        cursor.execute("""
            SELECT rechnungsaussteller, COUNT(*) as count, SUM(betrag_brutto) as total
            FROM invoices i
            JOIN jobs j ON i.job_id = j.job_id
            WHERE j.user_id = ? AND i.created_at > datetime('now', ?)
            GROUP BY rechnungsaussteller
            ORDER BY total DESC
            LIMIT 10
        """, (user_id, f'-{days} days'))
        
        content['top_suppliers'] = [
            {'name': r[0] or 'Unbekannt', 'count': r[1], 'total': round(r[2] or 0, 2)}
            for r in cursor.fetchall()
        ]
    
    if report_type == ReportType.INVOICES:
        # Rechnungsliste
        cursor.execute("""
            SELECT rechnungsnummer, datum, rechnungsaussteller, betrag_brutto
            FROM invoices i
            JOIN jobs j ON i.job_id = j.job_id
            WHERE j.user_id = ? AND i.created_at > datetime('now', ?)
            ORDER BY i.created_at DESC
            LIMIT 50
        """, (user_id, f'-{days} days'))
        
        content['invoices'] = [
            {'number': r[0], 'date': r[1], 'supplier': r[2], 'amount': r[3]}
            for r in cursor.fetchall()
        ]
    
    conn.close()
    return content


def send_report_email(report: Dict, content: Dict):
    """Sendet Bericht per Email."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        import os
    except ImportError:
        logger.warning("SendGrid nicht verfügbar")
        return False
    
    api_key = os.getenv('SENDGRID_API_KEY')
    if not api_key:
        logger.warning("SENDGRID_API_KEY nicht gesetzt")
        return False
    
    recipients = report.get('recipients', [])
    if not recipients:
        return False
    
    summary = content.get('summary', {})
    
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
        <div style="background:#003856;color:white;padding:24px;text-align:center;">
            <h2 style="margin:0;">📊 {content.get('title', 'Bericht')}</h2>
            <p style="margin:10px 0 0;opacity:0.9;">Automatischer Bericht · {datetime.now().strftime('%d.%m.%Y')}</p>
        </div>
        <div style="padding:24px;background:#f8f9fa;">
            <div style="background:white;border-radius:12px;padding:20px;margin-bottom:20px;">
                <h3 style="margin:0 0 15px;color:#003856;">Zusammenfassung ({content.get('period_days', 30)} Tage)</h3>
                <table style="width:100%;">
                    <tr>
                        <td style="padding:8px 0;"><strong>Rechnungen:</strong></td>
                        <td style="text-align:right;">{summary.get('invoice_count', 0)}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;"><strong>Brutto gesamt:</strong></td>
                        <td style="text-align:right;">{summary.get('total_brutto', 0):,.2f} €</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;"><strong>Netto gesamt:</strong></td>
                        <td style="text-align:right;">{summary.get('total_netto', 0):,.2f} €</td>
                    </tr>
                </table>
            </div>
            <p style="text-align:center;margin-top:20px;">
                <a href="https://app.sbsdeutschland.com/analytics" 
                   style="background:#003856;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;">
                    Vollständige Analyse öffnen
                </a>
            </p>
        </div>
        <div style="padding:16px;text-align:center;color:#6b7280;font-size:12px;">
            SBS Deutschland GmbH & Co. KG · In der Dell 19 · 69469 Weinheim
        </div>
    </div>
    """
    
    try:
        message = Mail(
            from_email='reports@sbsdeutschland.com',
            to_emails=recipients,
            subject=f"📊 {content.get('title', 'Bericht')} - {datetime.now().strftime('%d.%m.%Y')}",
            html_content=html
        )
        
        sg = SendGridAPIClient(api_key)
        sg.send(message)
        logger.info(f"Report-Email gesendet: {report.get('name')}")
        return True
        
    except Exception as e:
        logger.error(f"Report-Email fehlgeschlagen: {e}")
        return False


def run_scheduled_reports():
    """Führt alle fälligen Berichte aus (Cronjob)."""
    reports = get_due_reports()
    logger.info(f"Führe {len(reports)} geplante Berichte aus...")
    
    for report in reports:
        try:
            content = generate_report_content(report, report['user_id'])
            send_report_email(report, content)
            mark_report_run(report['id'])
            logger.info(f"Report '{report['name']}' erfolgreich gesendet")
        except Exception as e:
            logger.error(f"Report '{report['name']}' fehlgeschlagen: {e}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_scheduled_reports()
