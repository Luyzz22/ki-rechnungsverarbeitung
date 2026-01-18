"""
SBS Deutschland - Notification API Endpoints
=============================================
Neue API-Endpoints für Enterprise Notification Features.

INSTALLATION:
1. Diese Datei nach /var/www/invoice-app/app/notification_api.py kopieren
2. In main.py importieren: from .notification_api import register_notification_routes
3. Nach app = FastAPI() aufrufen: register_notification_routes(app)
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def register_notification_routes(app):
    """Registriert alle Notification-bezogenen API Endpoints"""
    
    # ==========================================================================
    # SLACK ENDPOINTS
    # ==========================================================================
    
    @app.post("/api/settings/slack")
    async def api_save_slack_settings(request: Request):
        """Speichert Slack Webhook URL - Professional+ Feature"""
        from .auth import get_user_info
        user = get_user_info(request)
        
        if not user.get("email"):
            return {"success": False, "error": "Nicht eingeloggt"}
        
        # Plan Check - Slack ab Professional
        from .usage_tracking import get_user_plan
        plan = get_user_plan(user["email"])
        if plan.get("plan_id") not in ["professional", "enterprise"] and not user.get("is_admin", False):
            return {
                "success": False, 
                "error": "Slack Integration ist ab dem Professional Plan verfügbar.",
                "upgrade_required": True
            }
        
        form = await request.form()
        enabled = form.get("enabled") == "true"
        webhook_url = form.get("webhook_url", "").strip()
        
        # Validierung
        if enabled and webhook_url:
            if not webhook_url.startswith("https://hooks.slack.com/"):
                return {"success": False, "error": "Ungültige Slack Webhook URL. URL muss mit https://hooks.slack.com/ beginnen."}
        
        # Speichern
        from .enterprise_features import update_user_settings
        result = update_user_settings(
            user["email"],
            notification_slack=enabled,
            slack_webhook_url=webhook_url if enabled else None
        )
        
        # Audit Log
        try:
            from .enterprise_features import log_audit
            log_audit(
                user["email"], 
                "slack_settings_updated", 
                "settings", 
                None, 
                f"Slack {'aktiviert' if enabled else 'deaktiviert'}",
                request.client.host if request.client else None,
                user.get("name", "Unknown")
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")
        
        return {"success": True, "message": "Slack-Einstellungen gespeichert"}
    
    
    @app.post("/api/settings/slack/test")
    async def api_test_slack_webhook(request: Request):
        """Testet Slack Webhook URL - Professional+ Feature"""
        from .auth import get_user_info
        user = get_user_info(request)
        
        if not user.get("email"):
            return {"success": False, "error": "Nicht eingeloggt"}
        
        # Plan Check
        from .usage_tracking import get_user_plan
        plan = get_user_plan(user["email"])
        if plan.get("plan_id") not in ["professional", "enterprise"] and not user.get("is_admin", False):
            return {"success": False, "error": "Professional oder Enterprise Plan erforderlich"}
        
        form = await request.form()
        webhook_url = form.get("webhook_url", "").strip()
        
        if not webhook_url:
            return {"success": False, "error": "Keine Webhook URL angegeben"}
        
        if not webhook_url.startswith("https://hooks.slack.com/"):
            return {"success": False, "error": "Ungültige Slack Webhook URL"}
        
        # Test durchführen
        import requests
        
        try:
            test_message = {
                "text": "✅ SBS Deutschland - Slack Test erfolgreich!",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Slack Integration aktiv",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Die Verbindung zu *SBS Deutschland* wurde erfolgreich hergestellt.\n\n*Benutzer:* {user.get('name', user['email'])}\n*Zeit:* {datetime.now().strftime('%d.%m.%Y %H:%M Uhr')}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Sie erhalten ab jetzt Benachrichtigungen zu:\n• 📄 Verarbeitete Rechnungen\n• ⏰ Wichtige Fristen\n• 📊 Wöchentliche Reports"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "🔗 <https://app.sbsdeutschland.com|SBS Deutschland öffnen>"
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=test_message, timeout=10)
            
            if response.status_code == 200:
                # Log erfolgreichen Test
                _log_notification(user["email"], "slack_test", "slack_webhook", "sent", "Test erfolgreich")
                return {"success": True, "message": "Test-Nachricht erfolgreich an Slack gesendet!"}
            else:
                _log_notification(user["email"], "slack_test", "slack_webhook", "failed", f"HTTP {response.status_code}")
                return {"success": False, "error": f"Slack API Fehler: {response.status_code} - {response.text[:100]}"}
                
        except requests.exceptions.Timeout:
            _log_notification(user["email"], "slack_test", "slack_webhook", "failed", "Timeout")
            return {"success": False, "error": "Zeitüberschreitung - Slack Webhook nicht erreichbar"}
        except requests.exceptions.RequestException as e:
            _log_notification(user["email"], "slack_test", "slack_webhook", "failed", str(e))
            return {"success": False, "error": f"Verbindungsfehler: {str(e)}"}
        except Exception as e:
            logger.error(f"Slack test error: {e}")
            return {"success": False, "error": f"Unbekannter Fehler: {str(e)}"}
    
    
    # ==========================================================================
    # WEEKLY REPORT ENDPOINTS
    # ==========================================================================
    
    @app.post("/api/settings/weekly-report")
    async def api_save_weekly_report(request: Request):
        """Speichert Wöchentlicher Report Settings - Enterprise Feature"""
        from .auth import get_user_info
        user = get_user_info(request)
        
        if not user.get("email"):
            return {"success": False, "error": "Nicht eingeloggt"}
        
        # Plan Check - Weekly Report nur Enterprise
        from .usage_tracking import get_user_plan
        plan = get_user_plan(user["email"])
        if plan.get("plan_id") != "enterprise" and not user.get("is_admin", False):
            return {
                "success": False, 
                "error": "Wöchentliche Reports sind nur im Enterprise Plan verfügbar.",
                "upgrade_required": True
            }
        
        form = await request.form()
        enabled = form.get("enabled") == "true"
        day = int(form.get("day", 1))  # 1=Montag bis 7=Sonntag
        time = form.get("time", "07:00")
        
        # Validierung
        if day < 1 or day > 7:
            return {"success": False, "error": "Ungültiger Wochentag"}
        
        # Zeit validieren
        try:
            datetime.strptime(time, "%H:%M")
        except ValueError:
            return {"success": False, "error": "Ungültiges Zeitformat (HH:MM erwartet)"}
        
        # Speichern
        from .enterprise_features import update_user_settings
        result = update_user_settings(
            user["email"],
            weekly_report_enabled=enabled,
            weekly_report_day=day,
            weekly_report_time=time
        )
        
        # Audit Log
        try:
            from .enterprise_features import log_audit
            day_names = {1: "Montag", 2: "Dienstag", 3: "Mittwoch", 4: "Donnerstag", 5: "Freitag", 6: "Samstag", 7: "Sonntag"}
            log_audit(
                user["email"], 
                "weekly_report_updated", 
                "settings", 
                None, 
                f"Wöchentlicher Report {'aktiviert (' + day_names.get(day, str(day)) + ' ' + time + ')' if enabled else 'deaktiviert'}",
                request.client.host if request.client else None,
                user.get("name", "Unknown")
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")
        
        return {"success": True, "message": f"Wöchentlicher Report {'aktiviert' if enabled else 'deaktiviert'}"}
    
    
    @app.post("/api/reports/send-now")
    async def api_send_report_now(request: Request):
        """Sendet sofort einen wöchentlichen Report - Enterprise Feature"""
        from .auth import get_user_info
        user = get_user_info(request)
        
        if not user.get("email"):
            return {"success": False, "error": "Nicht eingeloggt"}
        
        # Plan Check
        from .usage_tracking import get_user_plan
        plan = get_user_plan(user["email"])
        if plan.get("plan_id") != "enterprise" and not user.get("is_admin", False):
            return {"success": False, "error": "Enterprise Plan erforderlich"}
        
        # Report generieren und senden
        result = _generate_and_send_weekly_report(user["email"], user.get("name", "User"))
        
        return result
    
    
    @app.get("/api/reports/preview")
    async def api_preview_report(request: Request):
        """Zeigt Vorschau des wöchentlichen Reports - Enterprise Feature"""
        from .auth import get_user_info
        user = get_user_info(request)
        
        if not user.get("email"):
            return {"success": False, "error": "Nicht eingeloggt"}
        
        # Statistiken der letzten 7 Tage holen
        stats = _get_weekly_stats(user["email"])
        
        return {
            "success": True,
            "preview": True,
            "stats": stats,
            "period": "Letzte 7 Tage"
        }
    
    
    logger.info("✅ Notification API Endpoints registriert")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _log_notification(user_email: str, notification_type: str, channel: str, status: str, message: str = None):
    """Loggt eine Notification in die Datenbank"""
    try:
        from .database import get_connection
        conn = get_connection()
        conn.execute("""
            INSERT INTO notification_log (user_email, notification_type, channel, status, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_email, notification_type, channel, status, message, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to log notification: {e}")


def _get_weekly_stats(user_email: str) -> dict:
    """Holt Statistiken der letzten 7 Tage"""
    from datetime import timedelta
    
    try:
        from .database import get_connection
        conn = get_connection()
        
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        # Rechnungen
        invoices = conn.execute("""
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(brutto), 0) as total_brutto,
                COALESCE(SUM(netto), 0) as total_netto,
                COALESCE(AVG(brutto), 0) as avg_brutto
            FROM invoices 
            WHERE created_at >= ?
        """, (week_ago,)).fetchone()
        
        # Top Lieferanten
        top_suppliers = conn.execute("""
            SELECT supplier_name, COUNT(*) as count, SUM(brutto) as total
            FROM invoices
            WHERE created_at >= ? AND supplier_name IS NOT NULL
            GROUP BY supplier_name
            ORDER BY total DESC
            LIMIT 5
        """, (week_ago,)).fetchall()
        
        conn.close()
        
        return {
            "total_invoices": invoices[0] or 0,
            "total_brutto": round(invoices[1] or 0, 2),
            "total_netto": round(invoices[2] or 0, 2),
            "average_brutto": round(invoices[3] or 0, 2),
            "top_suppliers": [{"name": s[0], "count": s[1], "total": round(s[2] or 0, 2)} for s in top_suppliers],
            "period_start": week_ago[:10],
            "period_end": datetime.now().strftime("%Y-%m-%d")
        }
        
    except Exception as e:
        logger.error(f"Error getting weekly stats: {e}")
        return {
            "total_invoices": 0,
            "total_brutto": 0,
            "total_netto": 0,
            "average_brutto": 0,
            "top_suppliers": [],
            "error": str(e)
        }


def _generate_and_send_weekly_report(user_email: str, user_name: str) -> dict:
    """Generiert und sendet den wöchentlichen Report"""
    import requests
    
    # Settings holen
    try:
        from .enterprise_features import get_user_settings
        settings = get_user_settings(user_email)
    except:
        settings = {}
    
    # Stats holen
    stats = _get_weekly_stats(user_email)
    
    results = {"email": False, "slack": False}
    errors = []
    
    # E-Mail senden
    if settings.get("notification_email", True):
        try:
            email_result = _send_weekly_email(user_email, user_name, stats)
            results["email"] = email_result
            _log_notification(user_email, "weekly_report", "email", "sent" if email_result else "failed")
        except Exception as e:
            errors.append(f"E-Mail: {str(e)}")
            _log_notification(user_email, "weekly_report", "email", "failed", str(e))
    
    # Slack senden
    if settings.get("notification_slack") and settings.get("slack_webhook_url"):
        try:
            slack_result = _send_weekly_slack(settings["slack_webhook_url"], user_name, stats)
            results["slack"] = slack_result
            _log_notification(user_email, "weekly_report", "slack_webhook", "sent" if slack_result else "failed")
        except Exception as e:
            errors.append(f"Slack: {str(e)}")
            _log_notification(user_email, "weekly_report", "slack_webhook", "failed", str(e))
    
    success = results["email"] or results["slack"]
    
    return {
        "success": success,
        "results": results,
        "stats": stats,
        "errors": errors if errors else None
    }


def _send_weekly_email(user_email: str, user_name: str, stats: dict) -> bool:
    """Sendet wöchentlichen Report per E-Mail"""
    import os
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except ImportError:
        logger.warning("SendGrid not available")
        return False
    
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        logger.warning("SENDGRID_API_KEY not set")
        return False
    
    # HTML Email
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', Arial, sans-serif; background: #f4f7fa; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #003856, #00507a); color: white; padding: 32px; text-align: center; }}
            .header h1 {{ margin: 0 0 8px; font-size: 24px; }}
            .header p {{ margin: 0; opacity: 0.9; }}
            .content {{ padding: 32px; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 24px 0; }}
            .stat-card {{ background: #f8fafc; border-radius: 12px; padding: 20px; text-align: center; }}
            .stat-value {{ font-size: 28px; font-weight: 700; color: #003856; }}
            .stat-label {{ font-size: 14px; color: #64748b; margin-top: 4px; }}
            .cta-btn {{ display: inline-block; background: #FFB900; color: #003856; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 24px; }}
            .footer {{ background: #f8fafc; padding: 24px; text-align: center; color: #64748b; font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Wöchentlicher Report</h1>
                <p>{stats.get('period_start', '')} bis {stats.get('period_end', '')}</p>
            </div>
            <div class="content">
                <p>Hallo {user_name},</p>
                <p>hier ist Ihre wöchentliche Zusammenfassung der Rechnungsverarbeitung:</p>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_invoices']}</div>
                        <div class="stat-label">Rechnungen</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_brutto']:.2f} €</div>
                        <div class="stat-label">Gesamt Brutto</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_netto']:.2f} €</div>
                        <div class="stat-label">Gesamt Netto</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['average_brutto']:.2f} €</div>
                        <div class="stat-label">Durchschnitt</div>
                    </div>
                </div>
                
                <center>
                    <a href="https://app.sbsdeutschland.com/analytics" class="cta-btn">
                        📈 Vollständige Analytics ansehen
                    </a>
                </center>
            </div>
            <div class="footer">
                <p>© {datetime.now().year} SBS Deutschland GmbH & Co. KG</p>
                <p>In der Dell 19, 69469 Weinheim</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        message = Mail(
            from_email="noreply@sbsdeutschland.com",
            to_emails=user_email,
            subject=f"📊 Ihr wöchentlicher Report - {stats['total_invoices']} Rechnungen",
            html_content=html_content
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        return response.status_code in [200, 201, 202]
        
    except Exception as e:
        logger.error(f"SendGrid error: {e}")
        return False


def _send_weekly_slack(webhook_url: str, user_name: str, stats: dict) -> bool:
    """Sendet wöchentlichen Report an Slack"""
    import requests
    
    # Top Suppliers formatieren
    suppliers_text = ""
    for i, s in enumerate(stats.get("top_suppliers", [])[:3], 1):
        suppliers_text += f"{i}. {s['name']}: {s['count']} Rechnungen ({s['total']:.2f} €)\n"
    
    if not suppliers_text:
        suppliers_text = "Keine Daten"
    
    message = {
        "text": f"📊 Wöchentlicher Report - {stats['total_invoices']} Rechnungen",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Wöchentlicher Report",
                    "emoji": True
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📅 {stats.get('period_start', '')} bis {stats.get('period_end', '')}"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*📄 Rechnungen*\n{stats['total_invoices']}"},
                    {"type": "mrkdwn", "text": f"*💰 Brutto*\n{stats['total_brutto']:.2f} €"},
                    {"type": "mrkdwn", "text": f"*📊 Netto*\n{stats['total_netto']:.2f} €"},
                    {"type": "mrkdwn", "text": f"*📈 Durchschnitt*\n{stats['average_brutto']:.2f} €"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🏆 Top Lieferanten*\n{suppliers_text}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📈 Analytics öffnen", "emoji": True},
                        "url": "https://app.sbsdeutschland.com/analytics",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📄 Rechnungen", "emoji": True},
                        "url": "https://app.sbsdeutschland.com/history"
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(webhook_url, json=message, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Slack send error: {e}")
        return False
