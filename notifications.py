#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung - Notifications Module v3.1
Email & Slack notifications after processing
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, List
import requests

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send email notifications"""
    
    def __init__(self, config: Dict):
        self.enabled = config.get('email', {}).get('enabled', False)
        
        if self.enabled:
            self.smtp_server = config['email']['smtp_server']
            self.smtp_port = config['email']['smtp_port']
            self.username = config['email']['username']
            self.password = config['email']['password']
            self.from_address = config['email']['from_address']
            self.to_addresses = config['email']['to_addresses']
    
    def send_completion_email(self, stats: Dict, exported_files: Dict[str, str]) -> bool:
        """Send email when processing is complete"""
        
        if not self.enabled:
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_address
            msg['To'] = ', '.join(self.to_addresses)
            msg['Subject'] = f"✅ Rechnungsverarbeitung abgeschlossen - {stats['total_invoices']} Rechnungen"
            
            # Email body
            body = self._create_email_body(stats)
            msg.attach(MIMEText(body, 'html'))
            
            # Attach Excel file if available
            if 'xlsx' in exported_files:
                self._attach_file(msg, exported_files['xlsx'])
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {self.to_addresses}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_error_email(self, error_message: str, failed_count: int) -> bool:
        """Send email when processing fails"""
        
        if not self.enabled:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_address
            msg['To'] = ', '.join(self.to_addresses)
            msg['Subject'] = f"❌ Rechnungsverarbeitung fehlgeschlagen - {failed_count} Fehler"
            
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
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info("Error email sent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send error email: {e}")
            return False
    
    def _create_email_body(self, stats: Dict) -> str:
        """Create HTML email body"""
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #00d4ff;">✅ Rechnungsverarbeitung abgeschlossen</h2>
            
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
            
            <p style="margin-top: 30px; color: #888;">
                Diese Email wurde automatisch von der KI-Rechnungsverarbeitung v3.0 generiert.<br>
                © 2025 Luis Schenk
            </p>
        </body>
        </html>
        """
    
    def _attach_file(self, msg: MIMEMultipart, filepath: str):
        """Attach file to email"""
        try:
            with open(filepath, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {Path(filepath).name}'
            )
            
            msg.attach(part)
            
        except Exception as e:
            logger.error(f"Failed to attach file {filepath}: {e}")


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
