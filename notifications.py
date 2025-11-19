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
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from dotenv import load_dotenv

load_dotenv()

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
                © 2025 SBS Deutschland GmbH &amp; Co. KG
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
