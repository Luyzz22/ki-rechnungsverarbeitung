"""Email Notification Service via Resend API."""
from __future__ import annotations

import logging
import os
from typing import Optional

import resend
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "luis@sbsdeutschland.de")
PRODUCT_NAME = "BelegFlow AI"
APP_URL = os.getenv("APP_URL", "https://sbsnexus.de")


class EmailService:
    """Sends transactional emails via Resend."""

    def send_invite(self, to_email: str, inviter_name: str, temp_password: str, role: str) -> dict:
        """Send team invite email."""
        if not resend.api_key:
            logger.warning("Resend not configured, skipping email")
            return {"sent": False, "reason": "resend_not_configured"}

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
          <div style="text-align: center; margin-bottom: 32px;">
            <div style="display: inline-block; background: #e85d04; color: white; font-weight: 700; padding: 8px 14px; border-radius: 10px; font-size: 14px;">BF</div>
            <span style="font-size: 22px; font-weight: 700; margin-left: 8px; color: #0a0a0a;">{PRODUCT_NAME}</span>
          </div>
          <h1 style="font-size: 24px; font-weight: 700; color: #0a0a0a; margin-bottom: 16px;">Sie wurden eingeladen</h1>
          <p style="color: #525252; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
            <strong>{inviter_name}</strong> hat Sie als <strong>{role}</strong> zu {PRODUCT_NAME} eingeladen.
            Melden Sie sich mit Ihren Zugangsdaten an:
          </p>
          <div style="background: #f5f5f5; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <p style="margin: 0 0 8px 0; font-size: 13px; color: #737373;">E-Mail</p>
            <p style="margin: 0 0 16px 0; font-size: 15px; font-weight: 600; color: #0a0a0a;">{to_email}</p>
            <p style="margin: 0 0 8px 0; font-size: 13px; color: #737373;">Temporaeres Passwort</p>
            <p style="margin: 0; font-size: 15px; font-weight: 600; color: #0a0a0a; font-family: monospace;">{temp_password}</p>
          </div>
          <a href="{APP_URL}/login" style="display: block; text-align: center; background: #e85d04; color: white; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 15px; margin-bottom: 24px;">
            Jetzt anmelden
          </a>
          <p style="color: #a3a3a3; font-size: 12px; text-align: center;">
            {PRODUCT_NAME} — Ein Produkt von SBS Deutschland GmbH & Co. KG
          </p>
        </div>
        """

        try:
            result = resend.Emails.send({
                "from": f"{PRODUCT_NAME} <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": f"{inviter_name} hat Sie zu {PRODUCT_NAME} eingeladen",
                "html": html,
            })
            logger.info(f"invite_email_sent: to={to_email} id={result.get('id','?')}")
            return {"sent": True, "email_id": result.get("id")}
        except Exception as e:
            logger.error(f"resend_error: {e}")
            return {"sent": False, "reason": str(e)}

    def send_welcome(self, to_email: str, name: str) -> dict:
        """Send welcome email after registration."""
        if not resend.api_key:
            return {"sent": False, "reason": "resend_not_configured"}

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
          <div style="text-align: center; margin-bottom: 32px;">
            <div style="display: inline-block; background: #e85d04; color: white; font-weight: 700; padding: 8px 14px; border-radius: 10px; font-size: 14px;">BF</div>
            <span style="font-size: 22px; font-weight: 700; margin-left: 8px; color: #0a0a0a;">{PRODUCT_NAME}</span>
          </div>
          <h1 style="font-size: 24px; font-weight: 700; color: #0a0a0a; margin-bottom: 16px;">Willkommen, {name}!</h1>
          <p style="color: #525252; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
            Ihr Konto bei {PRODUCT_NAME} ist eingerichtet. Sie koennen jetzt Rechnungen hochladen
            und die KI-Verarbeitung nutzen.
          </p>
          <div style="background: #f5f5f5; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <p style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: #0a0a0a;">Ihr Starter-Plan beinhaltet:</p>
            <p style="margin: 0; color: #525252; font-size: 14px; line-height: 1.8;">
              50 Rechnungen/Monat &bull; KI-Erkennung &bull; DATEV CSV-Export
            </p>
          </div>
          <a href="{APP_URL}/dashboard" style="display: block; text-align: center; background: #e85d04; color: white; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 15px; margin-bottom: 24px;">
            Zum Dashboard
          </a>
          <p style="color: #a3a3a3; font-size: 12px; text-align: center;">
            {PRODUCT_NAME} — Ein Produkt von SBS Deutschland GmbH & Co. KG
          </p>
        </div>
        """

        try:
            result = resend.Emails.send({
                "from": f"{PRODUCT_NAME} <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": f"Willkommen bei {PRODUCT_NAME}!",
                "html": html,
            })
            return {"sent": True, "email_id": result.get("id")}
        except Exception as e:
            logger.error(f"resend_welcome_error: {e}")
            return {"sent": False, "reason": str(e)}
