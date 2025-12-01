#!/usr/bin/env python3
"""
SBS Deutschland – System Alerts
Überwacht System und sendet Warnungen bei Problemen.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Alert Typen
class AlertType:
    DB_ERROR = "db_error"
    HIGH_ERROR_RATE = "high_error_rate"
    DISK_SPACE = "disk_space"
    BACKUP_MISSING = "backup_missing"
    API_FAILURES = "api_failures"
    LOW_CONFIDENCE_SPIKE = "low_confidence_spike"


class SystemMonitor:
    """Überwacht Systemzustand und sendet Alerts."""
    
    THRESHOLDS = {
        'disk_usage_percent': 90,
        'error_rate_percent': 10,
        'backup_max_age_hours': 48,
        'low_confidence_percent': 30,
    }
    
    def __init__(self):
        self.alerts_sent = {}  # Verhindert Spam
    
    def check_all(self) -> List[Dict]:
        """Führt alle Checks durch."""
        alerts = []
        
        alerts.extend(self._check_disk_space())
        alerts.extend(self._check_backup_age())
        alerts.extend(self._check_error_rate())
        alerts.extend(self._check_confidence_rate())
        
        return alerts
    
    def _check_disk_space(self) -> List[Dict]:
        """Prüft Festplattenplatz."""
        alerts = []
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            percent_used = (used / total) * 100
            
            if percent_used > self.THRESHOLDS['disk_usage_percent']:
                alerts.append({
                    'type': AlertType.DISK_SPACE,
                    'severity': 'critical' if percent_used > 95 else 'warning',
                    'message': f"Festplatte {percent_used:.1f}% voll ({free // (1024**3)} GB frei)",
                    'value': percent_used
                })
        except Exception as e:
            logger.error(f"Disk check failed: {e}")
        
        return alerts
    
    def _check_backup_age(self) -> List[Dict]:
        """Prüft Alter des letzten Backups."""
        alerts = []
        try:
            backup_dir = Path("/var/www/invoice-app/backups")
            if not backup_dir.exists():
                alerts.append({
                    'type': AlertType.BACKUP_MISSING,
                    'severity': 'critical',
                    'message': "Kein Backup-Verzeichnis gefunden!",
                    'value': None
                })
                return alerts
            
            backups = list(backup_dir.glob("invoices_backup_*.db*"))
            if not backups:
                alerts.append({
                    'type': AlertType.BACKUP_MISSING,
                    'severity': 'critical',
                    'message': "Keine Backups vorhanden!",
                    'value': None
                })
                return alerts
            
            latest = max(backups, key=lambda p: p.stat().st_mtime)
            age_hours = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600
            
            if age_hours > self.THRESHOLDS['backup_max_age_hours']:
                alerts.append({
                    'type': AlertType.BACKUP_MISSING,
                    'severity': 'warning',
                    'message': f"Letztes Backup ist {age_hours:.0f} Stunden alt",
                    'value': age_hours
                })
        except Exception as e:
            logger.error(f"Backup check failed: {e}")
        
        return alerts
    
    def _check_error_rate(self) -> List[Dict]:
        """Prüft Fehlerrate der letzten 24h."""
        alerts = []
        try:
            from database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM jobs
                WHERE created_at > datetime('now', '-24 hours')
            """)
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 0:
                error_rate = (row[1] / row[0]) * 100
                if error_rate > self.THRESHOLDS['error_rate_percent']:
                    alerts.append({
                        'type': AlertType.HIGH_ERROR_RATE,
                        'severity': 'warning',
                        'message': f"Hohe Fehlerrate: {error_rate:.1f}% der Jobs fehlgeschlagen",
                        'value': error_rate
                    })
        except Exception as e:
            logger.error(f"Error rate check failed: {e}")
        
        return alerts
    
    def _check_confidence_rate(self) -> List[Dict]:
        """Prüft Rate niedriger Konfidenz."""
        alerts = []
        try:
            from database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN confidence < 0.5 THEN 1 ELSE 0 END) as low_conf
                FROM invoices
                WHERE created_at > datetime('now', '-24 hours')
            """)
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 10:  # Mindestens 10 Rechnungen
                low_rate = (row[1] / row[0]) * 100
                if low_rate > self.THRESHOLDS['low_confidence_percent']:
                    alerts.append({
                        'type': AlertType.LOW_CONFIDENCE_SPIKE,
                        'severity': 'warning',
                        'message': f"Viele Rechnungen mit niedriger Konfidenz: {low_rate:.1f}%",
                        'value': low_rate
                    })
        except Exception as e:
            logger.error(f"Confidence check failed: {e}")
        
        return alerts
    
    def send_alert_email(self, alerts: List[Dict]):
        """Sendet Alert-Email."""
        if not alerts:
            return
        
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
        except ImportError:
            logger.warning("SendGrid nicht verfügbar")
            return
        
        api_key = os.getenv('SENDGRID_API_KEY')
        if not api_key:
            logger.warning("SENDGRID_API_KEY nicht gesetzt")
            return
        
        # HTML Email
        alert_rows = "\n".join([
            f"<tr><td style='padding:10px;border-bottom:1px solid #eee;'>"
            f"<span style='color:{'#ef4444' if a['severity']=='critical' else '#f59e0b'};'>●</span> "
            f"{a['message']}</td></tr>"
            for a in alerts
        ])
        
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
            <div style="background:#003856;color:white;padding:20px;text-align:center;">
                <h2>⚠️ System Alert</h2>
            </div>
            <div style="padding:20px;">
                <p>Folgende Probleme wurden erkannt:</p>
                <table style="width:100%;border-collapse:collapse;">
                    {alert_rows}
                </table>
                <p style="margin-top:20px;">
                    <a href="https://app.sbsdeutschland.com/admin" 
                       style="background:#003856;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;">
                       Admin Dashboard öffnen
                    </a>
                </p>
            </div>
        </div>
        """
        
        try:
            message = Mail(
                from_email='alerts@sbsdeutschland.com',
                to_emails=['info@sbsdeutschland.com'],
                subject=f'⚠️ System Alert: {len(alerts)} Problem(e) erkannt',
                html_content=html
            )
            
            sg = SendGridAPIClient(api_key)
            sg.send(message)
            logger.info(f"System-Alert Email gesendet: {len(alerts)} Alerts")
            
        except Exception as e:
            logger.error(f"Alert-Email fehlgeschlagen: {e}")


def run_system_check():
    """Führt System-Check durch und sendet ggf. Alerts."""
    monitor = SystemMonitor()
    alerts = monitor.check_all()
    
    if alerts:
        logger.warning(f"System-Check: {len(alerts)} Probleme gefunden")
        for alert in alerts:
            logger.warning(f"  - [{alert['severity']}] {alert['message']}")
        
        monitor.send_alert_email(alerts)
    else:
        logger.info("System-Check: Keine Probleme gefunden")
    
    return alerts


def get_system_status() -> Dict:
    """Holt aktuellen System-Status für API."""
    monitor = SystemMonitor()
    alerts = monitor.check_all()
    
    return {
        'status': 'critical' if any(a['severity'] == 'critical' for a in alerts) 
                  else 'warning' if alerts else 'healthy',
        'alerts': alerts,
        'checked_at': datetime.now().isoformat()
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_system_check()
