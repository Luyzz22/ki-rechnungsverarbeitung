"""E-Mail Ingestion Service — IMAP Polling, Auto-Upload, Slack Alerts."""
from __future__ import annotations

import email
import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime
from email.header import decode_header
from typing import Any, Optional

import imapclient
import requests
from dotenv import load_dotenv
from sqlalchemy import text

from shared.db.session import get_session

load_dotenv()
logger = logging.getLogger(__name__)


class UnmappedEmailSenderError(RuntimeError):
    """Fail-closed tenant resolution failure without sender PII."""


class EmailIngestionService:
    """Polls IMAP inbox for invoice attachments, processes and uploads them."""

    ALLOWED_EXTENSIONS = {".pdf", ".xml", ".png", ".jpg", ".jpeg"}
    ALLOWED_MIMES = {
        "application/pdf", "text/xml", "application/xml",
        "image/png", "image/jpeg",
    }

    def __init__(self):
        self.host = os.getenv("IMAP_HOST", "")
        self.user = os.getenv("IMAP_USER", "")
        self.password = os.getenv("IMAP_PASSWORD", "")
        self.folder = os.getenv("IMAP_FOLDER", "INBOX")
        self.processed_folder = os.getenv("IMAP_PROCESSED_FOLDER", "Processed")
        self.quarantine_folder = os.getenv("IMAP_QUARANTINE_FOLDER", "Quarantine")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        self.upload_dir = os.getenv("UPLOAD_DIR", "/var/www/invoice-app/uploads")

    def poll(self) -> list[dict[str, Any]]:
        """Poll IMAP inbox for new invoice emails. Returns list of processed items."""
        if not all([self.host, self.user, self.password]):
            logger.warning("IMAP not configured, skipping poll")
            return []

        results = []
        try:
            with imapclient.IMAPClient(self.host, ssl=True) as client:
                client.login(self.user, self.password)
                client.select_folder(self.folder, readonly=False)

                # Search for unseen messages
                msg_ids = client.search(["UNSEEN"])
                logger.info(f"email_poll: {len(msg_ids)} new messages")

                if not msg_ids:
                    return []

                for uid, data in client.fetch(msg_ids, ["RFC822", "ENVELOPE"]).items():
                    try:
                        result = self._process_message(uid, data, client)
                        if result:
                            results.extend(result)
                    except Exception as e:
                        logger.error(f"email_process_error uid={uid}: {e}")

        except Exception as e:
            logger.error(f"imap_connection_error: {e}")
            self._notify_slack(f"IMAP Fehler: {e}", is_error=True)

        if results:
            self._notify_slack_summary(results)

        return results

    def _process_message(self, uid: int, data: dict, client: imapclient.IMAPClient) -> list[dict]:
        """Process a single email message, extract invoice attachments."""
        raw = data[b"RFC822"]
        msg = email.message_from_bytes(raw)

        sender = self._decode_header(msg.get("From", ""))
        subject = self._decode_header(msg.get("Subject", ""))

        logger.info(f"email_processing: uid={uid} from={sender} subject={subject}")

        # Tenant resolution must succeed before any customer file is persisted.
        # Unknown senders are quarantined instead of being assigned to a fallback tenant.
        try:
            tenant_id = self._resolve_tenant(sender)
        except UnmappedEmailSenderError:
            logger.warning("email_tenant_resolution_failed uid=%s reason=unmapped_sender", uid)
            self._move_message(client, uid, self.quarantine_folder)
            return []

        attachments = []
        for part in msg.walk():
            content_type = part.get_content_type()
            filename = part.get_filename()
            if not filename:
                continue

            filename = self._decode_header(filename)
            ext = os.path.splitext(filename)[1].lower()

            if ext not in self.ALLOWED_EXTENSIONS:
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            # Save file
            file_id = str(uuid.uuid4())
            safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
            save_path = os.path.join(self.upload_dir, f"{file_id}_{safe_name}")
            os.makedirs(self.upload_dir, exist_ok=True)

            with open(save_path, "wb") as f:
                f.write(payload)

            file_hash = hashlib.sha256(payload).hexdigest()

            # Create invoice record
            doc_id = str(uuid.uuid4())
            self._create_invoice_record(
                document_id=doc_id,
                file_name=filename,
                file_path=save_path,
                file_hash=file_hash,
                mime_type=content_type,
                sender=sender,
                subject=subject,
                tenant_id=tenant_id,
            )

            attachments.append({
                "document_id": doc_id,
                "file_name": filename,
                "sender": sender,
                "subject": subject,
                "size_kb": round(len(payload) / 1024, 1),
                "file_hash": file_hash[:16],
            })

        # Mark as seen / move to processed
        if attachments:
            self._move_message(client, uid, self.processed_folder)

        return attachments

    def _create_invoice_record(self, document_id: str, file_name: str, file_path: str,
                                file_hash: str, mime_type: str, sender: str,
                                subject: str, tenant_id: str):
        """Insert invoice into database with uploaded status."""
        with get_session() as s:
            s.execute(text("""
                INSERT INTO invoices (document_id, tenant_id, document_type, file_name,
                    mime_type, uploaded_by, uploaded_at, source_system, status)
                VALUES (:did, :tid, :dtype, :fname, :mime, :upby, :now, :src, 'uploaded')
            """), {
                "did": document_id, "tid": tenant_id, "dtype": "invoice",
                "fname": file_name, "mime": mime_type,
                "upby": f"email:{sender}", "now": datetime.utcnow(),
                "src": "email-ingestion",
            })

            # Create upload event
            s.execute(text("""
                INSERT INTO invoice_events (id, document_id, tenant_id, event_type,
                    status_from, status_to, actor, created_at, details)
                VALUES (:id, :did, :tid, 'uploaded', NULL, 'uploaded', :actor, :now, :details)
            """), {
                "id": str(uuid.uuid4()), "did": document_id, "tid": tenant_id,
                "actor": "email-ingestion",
                "now": datetime.utcnow(),
                "details": json.dumps({"source": "email", "sender": sender, "subject": subject, "hash": file_hash}),
            })
            s.commit()

    def _resolve_tenant(self, sender: str) -> str:
        """Resolve sender email to an explicit tenant mapping; fail closed if absent."""
        email_addr = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", sender or "")
        if not email_addr:
            raise UnmappedEmailSenderError("sender_address_missing")

        addr = email_addr.group().lower()
        with get_session() as s:
            row = s.execute(
                text("SELECT tenant_id FROM users WHERE email = :e"), {"e": addr}
            ).fetchone()

        if row and row[0] and str(row[0]).strip():
            return str(row[0]).strip()
        raise UnmappedEmailSenderError("sender_tenant_mapping_missing")

    def _move_message(self, client: imapclient.IMAPClient, uid: int, folder: str) -> None:
        """Move a message to a controlled folder without exposing message contents."""
        if not folder:
            return
        try:
            try:
                client.create_folder(folder)
            except Exception:
                pass  # Folder may already exist.
            client.move([uid], folder)
        except Exception as exc:
            logger.warning(
                "email_move_failed uid=%s target=%s error=%s",
                uid,
                folder,
                type(exc).__name__,
            )

    def _decode_header(self, value: str) -> str:
        """Decode email header value."""
        if not value:
            return ""
        parts = decode_header(value)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return " ".join(decoded)

    def _notify_slack(self, message: str, is_error: bool = False):
        """Send notification to Slack."""
        if not self.slack_webhook:
            return
        icon = "\u274c" if is_error else "\ud83d\udce7"
        try:
            requests.post(self.slack_webhook, json={"text": f"{icon} *E-Mail Ingestion*: {message}"}, timeout=5)
        except Exception as e:
            logger.warning(f"slack_notify_error: {e}")

    def _notify_slack_summary(self, results: list[dict]):
        """Send summary of processed emails to Slack."""
        if not self.slack_webhook:
            return
        lines = [f"\ud83d\udce7 *E-Mail Ingestion: {len(results)} Rechnung(en) verarbeitet*\n"]
        for r in results[:5]:
            lines.append(f"  \u2022 `{r['file_name']}` von {r['sender']} ({r['size_kb']} KB)")
        if len(results) > 5:
            lines.append(f"  ... und {len(results) - 5} weitere")
        try:
            requests.post(self.slack_webhook, json={"text": "\n".join(lines)}, timeout=5)
        except Exception:
            pass
