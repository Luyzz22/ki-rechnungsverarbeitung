#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung - Notifications Module v3.2
Email (SendGrid) & Slack notifications after processing
"""

import os
import logging
import base64
from pathlib import Path
from typing import Dict, List
import requests
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send email notifications via SendGrid"""
    
    def __init__(self, config: Dict):
        self.enabled = config.get('email', {}).get('enabled', False)
        self.api_key = os.getenv('SENDGRID_API_KEY')
        
        if self.enabled and not self.api_key:
            logger.warning("SendGrid API key not found - email disabled")
            self.enabled = False
        
        if self.enabled:
            self.from_address = 'info@sbsdeutschland.com'
            self.to_addresses = config['email'].get('to_addresses', [])
    
    def send_completion_email(self, stats: Dict, exported_files: Dict[str, str]) -> bool:
        """Send email when processing is complete"""
        
        if not self.enabled:
            return False
        
        try:
            subject = f"✅ Rechnungsverarbeitung abgeschlossen - {stats['total_invoices']} Rechnungen"
            body = self._create_email_body(stats)
            
            message = Mail(
                from_email=self.from_address,
                to_emails=self.to_addresses,
                subject=subject,
                html_content=body
            )
            
            # Attach Excel file if available
            if 'xlsx' in exported_files:
                filepath = exported_files['xlsx']
                if Path(filepath).exists():
                    with open(filepath, 'rb') as f:
                        file_data = base64.b64encode(f.read()).decode()
                    
                    attachment = Attachment(
                        FileContent(file_data),
                        FileName(Path(filepath).name),
                        FileType('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        Disposition('attachment')
                    )
                    message.attachment = attachment
            
            # Send via SendGrid
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent to {self.to_addresses}")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_error_email(self, error_message: str, failed_count: int) -> bool:
        """Send email when processing fails"""
        
        if not self.enabled:
            return False
        
        try:
            subject = f"❌ Rechnungsverarbeitung fehlgeschlagen - {failed_count} Fehler"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #ff0000;">❌ Verarbeitung fehlgeschlagen</h2>
                <p><strong>Fehlgeschlagene PDFs:</strong> {failed_count}</p>
                <p><strong>Fehler:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px;">{error_message}</pre>
                <p>Bitte prüfe die Log-Datei für Details.</p>
            </body>
            </html>
            """
            
            message = Mail(
                from_email=self.from_address,
                to_emails=self.to_addresses,
                subject=subject,
                html_content=body
            )
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info("Error email sent")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to send error email: {e}")
            return False
    
    def _create_email_body(self, stats: Dict) -> str:
        """Create HTML email body"""
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background: #003856; color: white; padding: 20px; text-align: center;">
                <h2>✅ Rechnungsverarbeitung abgeschlossen</h2>
            </div>
            
            <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                <tr style="background: #f0f0f0;">
                    <th style="padding: 10px; text-align: left;">Statistik</th>
                    <th style="padding: 10px; text-align: right;">Wert</th>
                </tr>
                <tr>
                    <td style="padding: 10px;">Verarbeitete Rechnungen</td>
                    <td style="padding: 10px; text-align: right;"><strong>{stats['total_invoices']}</strong></td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 10px;">Gesamtbetrag (Brutto)</td>
                    <td style="padding: 10px; text-align: right; color: #00aa00;"><strong>{stats['total_brutto']:.2f}€</strong></td>
                </tr>
                <tr>
                    <td style="padding: 10px;">Gesamtbetrag (Netto)</td>
                    <td style="padding: 10px; text-align: right;">{stats['total_netto']:.2f}€</td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 10px;">MwSt. Total</td>
                    <td style="padding: 10px; text-align: right;">{stats['total_mwst']:.2f}€</td>
                </tr>
                <tr>
                    <td style="padding: 10px;">Durchschnitt</td>
                    <td style="padding: 10px; text-align: right;">{stats['average_brutto']:.2f}€</td>
                </tr>
            </table>
            
            <p style="margin-top: 20px;">Die Excel-Datei ist als Anhang beigefügt.</p>
            
            <p style="margin-top: 30px; text-align: center;">
                <a href="https://app.sbsdeutschland.com/" 
                   style="background: #FFB900; color: #003856; padding: 12px 24px; 
                          text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Weitere Rechnungen verarbeiten
                </a>
            </p>
            
            <p style="margin-top: 30px; color: #888; font-size: 12px;">
                Diese Email wurde automatisch von der KI-Rechnungsverarbeitung generiert.<br>
                © 2026 SBS Deutschland GmbH &amp; Co. KG
            </p>
        </body>
        </html>
        """


class SlackNotifier:
    """Send Slack notifications"""
    
    def __init__(self, config: Dict):
        self.enabled = config.get('slack', {}).get('enabled', False)
        
        if self.enabled:
            self.webhook_url = config['slack']['webhook_url']
    
    def send_completion_notification(self, stats: Dict) -> bool:
        """Send Slack message when processing is complete"""
        
        if not self.enabled:
            return False
        
        try:
            message = {
                "text": "✅ Rechnungsverarbeitung abgeschlossen",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Rechnungsverarbeitung abgeschlossen"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Rechnungen:*\n{stats['total_invoices']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Gesamt (Brutto):*\n{stats['total_brutto']:.2f}€"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Gesamt (Netto):*\n{stats['total_netto']:.2f}€"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Durchschnitt:*\n{stats['average_brutto']:.2f}€"
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(self.webhook_url, json=message)
            response.raise_for_status()
            
            logger.info("Slack notification sent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def send_error_notification(self, error_message: str, failed_count: int) -> bool:
        """Send Slack message when processing fails"""
        
        if not self.enabled:
            return False
        
        try:
            message = {
                "text": "❌ Rechnungsverarbeitung fehlgeschlagen",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Rechnungsverarbeitung fehlgeschlagen"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Fehlgeschlagene PDFs:* {failed_count}\n\n*Fehler:*\n```{error_message}```"
                        }
                    }
                ]
            }
            
            response = requests.post(self.webhook_url, json=message)
            response.raise_for_status()
            
            logger.info("Slack error notification sent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack error notification: {e}")
            return False


class NotificationManager:
    """Manage all notifications"""
    
    def __init__(self, config: Dict):
        self.config = config.get('notifications', {})
        self.email_notifier = EmailNotifier(self.config)
        self.slack_notifier = SlackNotifier(self.config)
    
    def notify_completion(self, stats: Dict, exported_files: Dict[str, str]):
        """Send completion notifications to all enabled channels"""
        
        results = {}
        
        # Email
        if self.email_notifier.enabled:
            results['email'] = self.email_notifier.send_completion_email(stats, exported_files)
        
        # Slack
        if self.slack_notifier.enabled:
            results['slack'] = self.slack_notifier.send_completion_notification(stats)
        
        return results
    
    def notify_error(self, error_message: str, failed_count: int):
        """Send error notifications to all enabled channels"""
        
        results = {}
        
        # Email
        if self.email_notifier.enabled:
            results['email'] = self.email_notifier.send_error_email(error_message, failed_count)
        
        # Slack
        if self.slack_notifier.enabled:
            results['slack'] = self.slack_notifier.send_error_notification(error_message, failed_count)
        
        return results


# Convenience function
def send_notifications(config: Dict, stats: Dict, exported_files: Dict[str, str]):
    """
    Send notifications after processing
    
    Usage:
        from notifications import send_notifications
        send_notifications(config.config, stats, exported_files)
    """
    manager = NotificationManager(config)
    return manager.notify_completion(stats, exported_files)

def send_completion_email(user_email: str, job_data: dict, stats: dict) -> bool:
    """Send professional HTML email notification"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import os
    
    # Gmail credentials from .env
    gmail_user = os.getenv('GMAIL_USER', 'noreply@sbsdeutschland.com')
    gmail_password = os.getenv('GMAIL_APP_PASSWORD')
    
    if not gmail_password:
        print("⚠️  Gmail password not configured")
        return False
    
    # Load HTML template
    template_path = '/var/www/invoice-app/email_templates/completion.html'
    try:
        with open(template_path, 'r') as f:
            html_template = f.read()
    except:
        print("⚠️  Email template not found")
        return False
    
    # Replace placeholders
    job_url = f"https://app.sbsdeutschland.com/job/{job_data.get('batch_id', '')}"
    html_content = html_template.replace('{{total_invoices}}', str(stats.get('total_invoices', 0)))
    html_content = html_content.replace('{{successful}}', str(job_data.get('successful', 0)))
    html_content = html_content.replace('{{total_amount}}', f"{stats.get('total_brutto', 0):.2f}")
    html_content = html_content.replace('{{total_netto}}', f"{stats.get('total_netto', 0):.2f}")
    html_content = html_content.replace('{{total_mwst}}', f"{stats.get('total_mwst', 0):.2f}")
    html_content = html_content.replace('{{job_url}}', job_url)
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"✅ {stats.get('total_invoices', 0)} Rechnungen verarbeitet ({stats.get('total_brutto', 0):.2f}€)"
    msg['From'] = f"SBS Deutschland <{gmail_user}>"
    msg['To'] = user_email
    
    # Plain text fallback
    text_content = f"""
SBS Deutschland - Rechnungsverarbeitung abgeschlossen

{stats.get('total_invoices', 0)} Rechnungen wurden erfolgreich verarbeitet.
Gesamtsumme: {stats.get('total_brutto', 0):.2f}€

Jetzt ansehen: {job_url}
    """
    
    msg.attach(MIMEText(text_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))
    
    # Send email
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False
def send_sendgrid_email(user_email: str, job_data: dict, stats: dict) -> bool:
    """Send professional HTML email via SendGrid API"""
    import os
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    
    api_key = os.getenv('SENDGRID_API_KEY')
    from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@sbsdeutschland.com')
    
    if not api_key:
        logger.warning("SendGrid API key not found")
        return False
    
    # Load HTML template
    template_path = '/var/www/invoice-app/email_templates/completion.html'
    try:
        with open(template_path, 'r') as f:
            html_template = f.read()
    except Exception as e:
        logger.error(f"Email template not found: {e}")
        return False
    
    # Replace placeholders
    job_url = f"https://app.sbsdeutschland.com/job/{job_data.get('batch_id', job_data.get('job_id', ''))}"
    html_content = html_template.replace('{{total_invoices}}', str(stats.get('total_invoices', 0)))
    html_content = html_content.replace('{{successful}}', str(job_data.get('successful', 0)))
    html_content = html_content.replace('{{total_amount}}', f"{stats.get('total_brutto', 0):.2f}")
    html_content = html_content.replace('{{total_netto}}', f"{stats.get('total_netto', 0):.2f}")
    html_content = html_content.replace('{{total_mwst}}', f"{stats.get('total_mwst', 0):.2f}")
    html_content = html_content.replace('{{job_url}}', job_url)
    
    # Create SendGrid message
    message = Mail(
        from_email=from_email,
        to_emails=user_email,
        subject=f"✅ {stats.get('total_invoices', 0)} Rechnungen verarbeitet ({stats.get('total_brutto', 0):.2f}€)",
        html_content=html_content
    )
    
    # Send via SendGrid
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info(f"✅ SendGrid email sent to {user_email} (Status: {response.status_code})")
        return True
    except Exception as e:
        logger.error(f"❌ SendGrid error: {e}")
        return False


class LowConfidenceNotifier:
    """Benachrichtigt bei Rechnungen mit niedriger KI-Konfidenz"""
    
    THRESHOLD = 0.5  # Unter 50% = Warnung
    
    @staticmethod
    def check_and_notify(job_id: str, invoices: list, config: dict = None):
        """
        Prüft Invoices auf niedrige Konfidenz und sendet ggf. Warnung.
        
        Args:
            job_id: Job-ID
            invoices: Liste der Rechnungen
            config: Notification-Konfiguration
        """
        low_conf = [
            inv for inv in invoices 
            if (inv.get('confidence') or 0) < LowConfidenceNotifier.THRESHOLD
        ]
        
        if not low_conf:
            logger.info(f"✅ Job {job_id}: Alle Rechnungen haben hohe Konfidenz")
            return
        
        logger.warning(
            f"⚠️ Job {job_id}: {len(low_conf)} Rechnungen mit niedriger Konfidenz (<{LowConfidenceNotifier.THRESHOLD*100}%)"
        )
        
        # Details loggen
        for inv in low_conf:
            conf = inv.get('confidence', 0) * 100
            nr = inv.get('rechnungsnummer') or inv.get('invoice_number') or 'unbekannt'
            logger.warning(f"   - Rechnung {nr}: {conf:.0f}% Konfidenz")
        
        # Optional: Email senden
        if config and config.get('email', {}).get('enabled'):
            LowConfidenceNotifier._send_warning_email(job_id, low_conf, config)
    
    @staticmethod
    def _send_warning_email(job_id: str, low_conf_invoices: list, config: dict):
        """Sendet Warn-Email für niedrige Konfidenz."""
        if not SENDGRID_AVAILABLE:
            return
        
        api_key = os.getenv('SENDGRID_API_KEY')
        if not api_key:
            return
        
        to_addresses = config.get('email', {}).get('to_addresses', [])
        if not to_addresses:
            return
        
        # Email-Inhalt
        invoice_list = "\n".join([
            f"• {inv.get('rechnungsnummer', 'unbekannt')}: {(inv.get('confidence', 0) * 100):.0f}% Konfidenz"
            for inv in low_conf_invoices[:10]  # Max 10
        ])
        
        html_content = f"""
        <h2>⚠️ Rechnungen mit niedriger KI-Konfidenz</h2>
        <p><strong>Job-ID:</strong> {job_id}</p>
        <p><strong>Anzahl:</strong> {len(low_conf_invoices)} Rechnungen unter 50% Konfidenz</p>
        <h3>Betroffene Rechnungen:</h3>
        <pre>{invoice_list}</pre>
        <p style="color: #666;">
            Bitte prüfen Sie diese Rechnungen manuell in der 
            <a href="https://app.sbsdeutschland.com/job/{job_id}">Job-Übersicht</a>.
        </p>
        """
        
        try:
            message = Mail(
                from_email='info@sbsdeutschland.com',
                to_emails=to_addresses,
                subject=f'⚠️ {len(low_conf_invoices)} Rechnungen benötigen Prüfung - Job {job_id[:8]}',
                html_content=html_content
            )
            
            sg = SendGridAPIClient(api_key)
            sg.send(message)
            logger.info(f"📧 Low-Confidence Warnung gesendet für Job {job_id}")
        except Exception as e:
            logger.error(f"❌ Email-Versand fehlgeschlagen: {e}")


def check_low_confidence(job_id: str, invoices: list, config: dict = None):
    """Shortcut-Funktion für LowConfidenceNotifier."""
    LowConfidenceNotifier.check_and_notify(job_id, invoices, config)
