#!/usr/bin/env python3
"""
SBS Deutschland – Webhook System
Sendet Events an externe Systeme.
"""

import logging
import json
import hmac
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from database import get_connection
import httpx

logger = logging.getLogger(__name__)

# Webhook Event Typen
class WebhookEvent:
    JOB_CREATED = "job.created"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    INVOICE_PROCESSED = "invoice.processed"
    EXPORT_COMPLETED = "export.completed"
    LOW_CONFIDENCE = "invoice.low_confidence"


def create_webhook(
    user_id: int,
    url: str,
    events: List[str],
    name: str = "Webhook",
    secret: str = None
) -> Dict:
    """
    Erstellt einen neuen Webhook.
    
    Args:
        user_id: User-ID
        url: Ziel-URL
        events: Liste der Events (z.B. ["job.completed"])
        name: Beschreibender Name
        secret: Geheimer Key für Signatur
        
    Returns:
        Dict mit Webhook-Daten
    """
    import secrets as sec
    
    if not secret:
        secret = sec.token_hex(32)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO webhooks (user_id, url, events, name, secret, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
    """, (user_id, url, json.dumps(events), name, secret))
    
    webhook_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"Webhook erstellt: {name} -> {url}")
    
    return {
        "id": webhook_id,
        "url": url,
        "events": events,
        "name": name,
        "secret": secret
    }


def get_webhooks(user_id: int) -> List[Dict]:
    """Holt alle Webhooks eines Users."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, url, events, name, is_active, created_at, last_triggered_at, failure_count
        FROM webhooks
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    
    webhooks = cursor.fetchall()
    conn.close()
    
    # Events als Liste parsen
    for wh in webhooks:
        wh['events'] = json.loads(wh['events']) if wh['events'] else []
    
    return webhooks


def delete_webhook(webhook_id: int, user_id: int) -> bool:
    """Löscht einen Webhook."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM webhooks WHERE id = ? AND user_id = ?
    """, (webhook_id, user_id))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0


def sign_payload(payload: str, secret: str) -> str:
    """Erstellt HMAC-SHA256 Signatur."""
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


async def send_webhook(webhook_id: int, event: str, data: Dict):
    """
    Sendet Webhook-Event asynchron.
    
    Args:
        webhook_id: Webhook-ID
        event: Event-Typ
        data: Event-Daten
    """
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM webhooks WHERE id = ? AND is_active = 1", (webhook_id,))
    webhook = cursor.fetchone()
    conn.close()
    
    if not webhook:
        return
    
    payload = {
        "event": event,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    
    payload_str = json.dumps(payload)
    signature = sign_payload(payload_str, webhook['secret'])
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": event
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook['url'], content=payload_str, headers=headers)
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook {webhook_id} erfolgreich: {event}")
                _update_webhook_success(webhook_id)
            else:
                logger.warning(f"Webhook {webhook_id} fehlgeschlagen: {response.status_code}")
                _update_webhook_failure(webhook_id)
                
    except Exception as e:
        logger.error(f"Webhook {webhook_id} Fehler: {e}")
        _update_webhook_failure(webhook_id)


def _update_webhook_success(webhook_id: int):
    """Aktualisiert Webhook nach Erfolg."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE webhooks 
        SET last_triggered_at = ?, failure_count = 0 
        WHERE id = ?
    """, (datetime.now().isoformat(), webhook_id))
    conn.commit()
    conn.close()


def _update_webhook_failure(webhook_id: int):
    """Aktualisiert Webhook nach Fehler. Deaktiviert nach 5 Fehlern."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT failure_count FROM webhooks WHERE id = ?", (webhook_id,))
    row = cursor.fetchone()
    
    if row:
        new_count = (row[0] or 0) + 1
        is_active = 1 if new_count < 5 else 0
        
        cursor.execute("""
            UPDATE webhooks 
            SET failure_count = ?, is_active = ?, last_triggered_at = ?
            WHERE id = ?
        """, (new_count, is_active, datetime.now().isoformat(), webhook_id))
        
        if not is_active:
            logger.warning(f"Webhook {webhook_id} deaktiviert nach 5 Fehlern")
    
    conn.commit()
    conn.close()


async def trigger_webhooks(user_id: int, event: str, data: Dict):
    """
    Triggert alle passenden Webhooks für einen User.
    
    Args:
        user_id: User-ID
        event: Event-Typ
        data: Event-Daten
    """
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, events FROM webhooks 
        WHERE user_id = ? AND is_active = 1
    """, (user_id,))
    
    webhooks = cursor.fetchall()
    conn.close()
    
    tasks = []
    for wh in webhooks:
        events = json.loads(wh['events']) if wh['events'] else []
        if event in events or "*" in events:
            tasks.append(send_webhook(wh['id'], event, data))
    
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Triggered {len(tasks)} webhooks for {event}")
