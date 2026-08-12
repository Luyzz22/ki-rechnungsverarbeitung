"""Transactional email service via Resend without reusable credentials in mail bodies."""
from __future__ import annotations

import html
import logging
import os
from urllib.parse import quote

import resend
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "luis@sbsdeutschland.de")
PRODUCT_NAME = "BelegFlow AI"
APP_URL = os.getenv("APP_URL", "https://sbsnexus.de").rstrip("/")


class EmailService:
    """Send transactional emails without transmitting passwords or other reusable secrets."""

    @staticmethod
    def _action_url(path: str, action_token: str) -> str:
        if not action_token:
            raise ValueError("action_token is required")
        # Put the sensitive token in the URL fragment. Browsers do not send URL
        # fragments in HTTP requests or Referer headers; the frontend must read
        # the fragment and POST the token to the API action endpoint.
        return f"{APP_URL}{path}#token={quote(action_token, safe='')}"

    @staticmethod
    def _safe(value: object) -> str:
        return html.escape(str(value or ""), quote=True)

    def _send(self, *, to_email: str, subject: str, html_body: str, event: str) -> dict:
        if not resend.api_key:
            logger.warning("transactional_email_skipped event=%s reason=resend_not_configured", event)
            return {"sent": False, "reason": "resend_not_configured"}

        try:
            result = resend.Emails.send({
                "from": f"{PRODUCT_NAME} <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            })
            logger.info("transactional_email_sent event=%s", event)
            return {"sent": True, "email_id": result.get("id")}
        except Exception as exc:
            # Do not echo recipient addresses, provider payloads, tokens, or
            # exception strings into logs/API responses.
            logger.error(
                "transactional_email_failed event=%s error_type=%s",
                event,
                type(exc).__name__,
            )
            return {"sent": False, "reason": "email_delivery_failed"}

    def send_invite(
        self,
        to_email: str,
        inviter_name: str,
        action_token: str,
        role: str,
    ) -> dict:
        """Send a single-use invite link. No temporary password is transmitted."""
        action_url = self._action_url("/auth/accept-invite", action_token)
        safe_inviter = self._safe(inviter_name)
        safe_role = self._safe(role)
        safe_email = self._safe(to_email)
        safe_url = self._safe(action_url)

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
          <div style="text-align: center; margin-bottom: 32px;">
            <div style="display: inline-block; background: #e85d04; color: white; font-weight: 700; padding: 8px 14px; border-radius: 10px; font-size: 14px;">BF</div>
            <span style="font-size: 22px; font-weight: 700; margin-left: 8px; color: #0a0a0a;">{PRODUCT_NAME}</span>
          </div>
          <h1 style="font-size: 24px; font-weight: 700; color: #0a0a0a; margin-bottom: 16px;">Sie wurden eingeladen</h1>
          <p style="color: #525252; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
            <strong>{safe_inviter}</strong> hat Sie als <strong>{safe_role}</strong> zu {PRODUCT_NAME} eingeladen.
            Verwenden Sie den einmaligen Link, um Ihr eigenes Passwort festzulegen.
          </p>
          <div style="background: #f5f5f5; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <p style="margin: 0 0 8px 0; font-size: 13px; color: #737373;">E-Mail</p>
            <p style="margin: 0; font-size: 15px; font-weight: 600; color: #0a0a0a;">{safe_email}</p>
          </div>
          <a href="{safe_url}" style="display: block; text-align: center; background: #e85d04; color: white; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 15px; margin-bottom: 24px;">
            Einladung annehmen
          </a>
          <p style="color: #737373; font-size: 12px; line-height: 1.5;">
            Der Link ist zeitlich begrenzt und verliert nach erfolgreicher Passwortvergabe automatisch seine Gültigkeit.
          </p>
          <p style="color: #a3a3a3; font-size: 12px; text-align: center;">
            {PRODUCT_NAME} — Ein Produkt von SBS Deutschland GmbH & Co. KG
          </p>
        </div>
        """
        return self._send(
            to_email=to_email,
            subject=f"{inviter_name} hat Sie zu {PRODUCT_NAME} eingeladen",
            html_body=html_body,
            event="invite",
        )

    def send_password_reset(self, to_email: str, action_token: str) -> dict:
        """Send a short-lived password-reset link without changing the credential."""
        action_url = self._action_url("/auth/reset-password", action_token)
        safe_url = self._safe(action_url)

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
          <div style="text-align: center; margin-bottom: 32px;">
            <div style="display: inline-block; background: #e85d04; color: white; font-weight: 700; padding: 8px 14px; border-radius: 10px; font-size: 14px;">BF</div>
            <span style="font-size: 22px; font-weight: 700; margin-left: 8px; color: #0a0a0a;">{PRODUCT_NAME}</span>
          </div>
          <h1 style="font-size: 24px; font-weight: 700; color: #0a0a0a; margin-bottom: 16px;">Passwort zurücksetzen</h1>
          <p style="color: #525252; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
            Für Ihr Konto wurde eine Passwort-Zurücksetzung angefordert. Ihr bestehendes Passwort bleibt unverändert, bis Sie den folgenden Link verwenden und ein neues Passwort festlegen.
          </p>
          <a href="{safe_url}" style="display: block; text-align: center; background: #e85d04; color: white; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 15px; margin-bottom: 24px;">
            Neues Passwort festlegen
          </a>
          <p style="color: #737373; font-size: 12px; line-height: 1.5;">
            Wenn Sie diese Anfrage nicht gestellt haben, können Sie die E-Mail ignorieren. Ihr bisheriges Passwort wurde nicht geändert.
          </p>
          <p style="color: #a3a3a3; font-size: 12px; text-align: center;">
            {PRODUCT_NAME} — Ein Produkt von SBS Deutschland GmbH & Co. KG
          </p>
        </div>
        """
        return self._send(
            to_email=to_email,
            subject=f"Passwort für {PRODUCT_NAME} zurücksetzen",
            html_body=html_body,
            event="password_reset",
        )

    def send_welcome(self, to_email: str, name: str) -> dict:
        """Send welcome email after registration."""
        safe_name = self._safe(name)
        dashboard_url = self._safe(f"{APP_URL}/dashboard")
        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
          <div style="text-align: center; margin-bottom: 32px;">
            <div style="display: inline-block; background: #e85d04; color: white; font-weight: 700; padding: 8px 14px; border-radius: 10px; font-size: 14px;">BF</div>
            <span style="font-size: 22px; font-weight: 700; margin-left: 8px; color: #0a0a0a;">{PRODUCT_NAME}</span>
          </div>
          <h1 style="font-size: 24px; font-weight: 700; color: #0a0a0a; margin-bottom: 16px;">Willkommen, {safe_name}!</h1>
          <p style="color: #525252; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
            Ihr Konto bei {PRODUCT_NAME} ist eingerichtet. Sie können jetzt Rechnungen hochladen und die KI-Verarbeitung nutzen.
          </p>
          <div style="background: #f5f5f5; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <p style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: #0a0a0a;">Ihr Starter-Plan beinhaltet:</p>
            <p style="margin: 0; color: #525252; font-size: 14px; line-height: 1.8;">
              50 Rechnungen/Monat &bull; KI-Erkennung &bull; DATEV CSV-Export
            </p>
          </div>
          <a href="{dashboard_url}" style="display: block; text-align: center; background: #e85d04; color: white; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 15px; margin-bottom: 24px;">
            Zum Dashboard
          </a>
          <p style="color: #a3a3a3; font-size: 12px; text-align: center;">
            {PRODUCT_NAME} — Ein Produkt von SBS Deutschland GmbH & Co. KG
          </p>
        </div>
        """
        return self._send(
            to_email=to_email,
            subject=f"Willkommen bei {PRODUCT_NAME}!",
            html_body=html_body,
            event="welcome",
        )
