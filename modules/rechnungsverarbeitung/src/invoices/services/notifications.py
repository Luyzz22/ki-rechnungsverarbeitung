"""Notification Service – Slack + Email alerts for invoice events.

Sends notifications on key lifecycle events:
- Neue Rechnung hochgeladen
- KI-Kontierung abgeschlossen
- Freigabe erforderlich
- DATEV Export abgeschlossen
- Fehler/Warnungen

Works standalone via Slack Webhooks. n8n integration optional.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

STATUS_EMOJI = {
    "uploaded": "📄",
    "classified": "🏷️",
    "validated": "✅",
    "validation_failed": "❌",
    "suggested": "🤖",
    "approved": "✅",
    "rejected": "🚫",
    "exported": "📤",
    "archived": "📦",
}

STATUS_LABELS = {
    "uploaded": "Hochgeladen",
    "classified": "Klassifiziert",
    "validated": "Validiert",
    "validation_failed": "Validierung fehlgeschlagen",
    "suggested": "KI-Kontierung",
    "approved": "Freigegeben",
    "rejected": "Abgelehnt",
    "exported": "DATEV exportiert",
    "archived": "Archiviert",
}


class NotificationService:
    """Multi-channel notification service."""

    def __init__(self) -> None:
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        self.n8n_webhook = os.getenv("N8N_WEBHOOK_URL", "")
        self.enabled = bool(self.slack_webhook or self.n8n_webhook)

    def notify_transition(
        self,
        document_id: str,
        file_name: str,
        from_status: str,
        to_status: str,
        actor: str | None = None,
        details: dict[str, Any] | None = None,
        tenant_id: str = "",
    ) -> bool:
        """Send notification for a state transition."""
        if not self.enabled:
            return False

        # Only notify on key events
        if to_status not in ("suggested", "approved", "rejected", "exported", "validation_failed"):
            return False

        emoji = STATUS_EMOJI.get(to_status, "📋")
        label = STATUS_LABELS.get(to_status, to_status)
        actor_str = f" von *{actor}*" if actor else ""

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {label}", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Datei:*\n{file_name}"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{from_status} → {to_status}"},
                    {"type": "mrkdwn", "text": f"*ID:*\n`{document_id[:12]}...`"},
                    {"type": "mrkdwn", "text": f"*Aktion:*\n{label}{actor_str}"},
                ],
            },
        ]

        # Add details for specific transitions
        if to_status == "suggested" and details:
            konto = details.get("konto", "")
            confidence = details.get("confidence", 0)
            model = details.get("model", "")
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🤖 *KI-Vorschlag:* Konto {konto} | Confidence: {confidence:.0%} | Model: {model}",
                },
            })

        if to_status == "exported" and details:
            batch = details.get("datev_batch", "")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"📤 *DATEV Batch:* `{batch}`"},
            })

        if to_status == "approved":
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "✅ Rechnung freigegeben — bereit für DATEV Export"},
            })

        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"SBS Nexus Finance • {tenant_id} • {datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC"},
            ],
        })

        payload = {"blocks": blocks, "text": f"{emoji} {label}: {file_name}"}

        sent = False
        if self.slack_webhook:
            sent = self._send_slack(payload) or sent
        if self.n8n_webhook:
            sent = self._send_n8n(document_id, file_name, from_status, to_status, actor, details, tenant_id) or sent

        return sent

    def _send_slack(self, payload: dict) -> bool:
        """Send to Slack webhook."""
        try:
            with httpx.Client(timeout=10) as client:
                r = client.post(self.slack_webhook, json=payload)
                if r.status_code == 200:
                    logger.info("slack_notification_sent")
                    return True
                logger.warning(f"slack_error: {r.status_code} {r.text}")
        except Exception as e:
            logger.error(f"slack_send_failed: {e}")
        return False

    def _send_n8n(
        self,
        document_id: str,
        file_name: str,
        from_status: str,
        to_status: str,
        actor: str | None,
        details: dict | None,
        tenant_id: str,
    ) -> bool:
        """Send to n8n webhook for workflow automation."""
        try:
            payload = {
                "event": "invoice_transition",
                "document_id": document_id,
                "file_name": file_name,
                "from_status": from_status,
                "to_status": to_status,
                "actor": actor,
                "details": details or {},
                "tenant_id": tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            with httpx.Client(timeout=10) as client:
                r = client.post(self.n8n_webhook, json=payload)
                if r.status_code in (200, 201):
                    logger.info("n8n_notification_sent")
                    return True
                logger.warning(f"n8n_error: {r.status_code}")
        except Exception as e:
            logger.error(f"n8n_send_failed: {e}")
        return False
