"""Stripe Subscription Service — Plans, Checkout, Webhooks."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

import stripe
from dotenv import load_dotenv
from sqlalchemy import text

from shared.db.session import get_session

load_dotenv()
logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Plan definitions
PLANS = {
    "starter": {
        "name": "Starter",
        "price_monthly": 0,
        "invoices_per_month": 50,
        "users": 1,
        "features": ["ki_erkennung", "datev_csv", "email_support"],
        "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER", ""),
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 14900,  # cents
        "invoices_per_month": 500,
        "users": 5,
        "features": [
            "ki_erkennung", "ki_dual", "datev_native", "freigabe_workflow",
            "email_ingestion", "finance_copilot", "priority_support",
        ],
        "stripe_price_id": os.getenv("STRIPE_PRICE_PROFESSIONAL", ""),
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": None,
        "invoices_per_month": -1,  # unlimited
        "users": -1,
        "features": [
            "ki_erkennung", "ki_dual", "datev_native", "freigabe_workflow",
            "email_ingestion", "finance_copilot", "sso_saml", "api_access",
            "custom_integrations", "dedicated_manager", "on_premise", "sla_99_9",
        ],
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE", ""),
    },
}


class SubscriptionService:
    """Manages Stripe subscriptions, checkout sessions, and plan enforcement."""

    def get_plans(self) -> list[dict[str, Any]]:
        """Return available plans."""
        return [
            {
                "id": plan_id,
                "name": p["name"],
                "price_monthly": p["price_monthly"],
                "invoices_per_month": p["invoices_per_month"],
                "users": p["users"],
                "features": p["features"],
            }
            for plan_id, p in PLANS.items()
        ]

    def get_tenant_subscription(self, tenant_id: str) -> dict[str, Any]:
        """Get current subscription for a tenant."""
        with get_session() as s:
            row = s.execute(text("""
                SELECT plan, status, stripe_customer_id, stripe_subscription_id,
                       current_period_end, invoices_used, created_at
                FROM subscriptions WHERE tenant_id = :t
            """), {"t": tenant_id}).fetchone()

        if not row:
            return {
                "plan": "starter", "status": "active",
                "invoices_used": 0, "invoices_limit": 50,
                "features": PLANS["starter"]["features"],
            }

        plan_data = PLANS.get(row[0], PLANS["starter"])
        return {
            "plan": row[0],
            "status": row[1],
            "stripe_customer_id": row[2],
            "stripe_subscription_id": row[3],
            "current_period_end": row[4].isoformat() if row[4] else None,
            "invoices_used": row[5] or 0,
            "invoices_limit": plan_data["invoices_per_month"],
            "features": plan_data["features"],
            "created_at": row[6].isoformat() if row[6] else None,
        }

    def create_checkout_session(self, tenant_id: str, plan_id: str,
                                 user_email: str, success_url: str,
                                 cancel_url: str) -> dict[str, Any]:
        """Create a Stripe Checkout session for subscription."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured")

        plan = PLANS.get(plan_id)
        if not plan or not plan["stripe_price_id"]:
            raise ValueError(f"Plan '{plan_id}' not available")

        # Get or create Stripe customer
        customer_id = self._get_or_create_customer(tenant_id, user_email)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"tenant_id": tenant_id, "plan_id": plan_id},
            subscription_data={"metadata": {"tenant_id": tenant_id, "plan_id": plan_id}},
        )

        return {"checkout_url": session.url, "session_id": session.id}

    def create_portal_session(self, tenant_id: str, return_url: str) -> dict[str, Any]:
        """Create Stripe Customer Portal session for managing subscription."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured")

        with get_session() as s:
            row = s.execute(text(
                "SELECT stripe_customer_id FROM subscriptions WHERE tenant_id = :t"
            ), {"t": tenant_id}).fetchone()

        if not row or not row[0]:
            raise ValueError("No active subscription found")

        session = stripe.billing_portal.Session.create(
            customer=row[0], return_url=return_url,
        )
        return {"portal_url": session.url}

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict[str, Any]:
        """Process Stripe webhook events."""
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            raise ValueError(f"Webhook verification failed: {e}")

        event_type = event["type"]
        data = event["data"]["object"]
        logger.info(f"stripe_webhook: {event_type}")

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(data)
        elif event_type == "customer.subscription.updated":
            self._handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            self._handle_subscription_deleted(data)
        elif event_type == "invoice.payment_failed":
            self._handle_payment_failed(data)

        return {"event": event_type, "processed": True}

    def check_invoice_limit(self, tenant_id: str) -> dict[str, Any]:
        """Check if tenant can process more invoices."""
        sub = self.get_tenant_subscription(tenant_id)
        limit = sub["invoices_limit"]
        used = sub["invoices_used"]

        if limit == -1:  # unlimited
            return {"allowed": True, "used": used, "limit": "unlimited", "remaining": "unlimited"}

        remaining = max(0, limit - used)
        return {"allowed": remaining > 0, "used": used, "limit": limit, "remaining": remaining}

    def increment_usage(self, tenant_id: str) -> None:
        """Increment invoice usage counter for tenant."""
        with get_session() as s:
            s.execute(text("""
                UPDATE subscriptions SET invoices_used = invoices_used + 1
                WHERE tenant_id = :t
            """), {"t": tenant_id})
            s.commit()

    # --- Internal ---
    def _get_or_create_customer(self, tenant_id: str, email: str) -> str:
        with get_session() as s:
            row = s.execute(text(
                "SELECT stripe_customer_id FROM subscriptions WHERE tenant_id = :t"
            ), {"t": tenant_id}).fetchone()

        if row and row[0]:
            return row[0]

        customer = stripe.Customer.create(email=email, metadata={"tenant_id": tenant_id})
        return customer.id

    def _handle_checkout_completed(self, session: dict) -> None:
        tenant_id = session.get("metadata", {}).get("tenant_id")
        plan_id = session.get("metadata", {}).get("plan_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if not tenant_id:
            return

        with get_session() as s:
            existing = s.execute(text("SELECT id FROM subscriptions WHERE tenant_id = :t"), {"t": tenant_id}).fetchone()
            if existing:
                s.execute(text("""
                    UPDATE subscriptions SET plan = :plan, status = 'active',
                        stripe_customer_id = :cid, stripe_subscription_id = :sid, updated_at = :now
                    WHERE tenant_id = :t
                """), {"plan": plan_id, "cid": customer_id, "sid": subscription_id, "t": tenant_id, "now": datetime.utcnow()})
            else:
                s.execute(text("""
                    INSERT INTO subscriptions (id, tenant_id, plan, status, stripe_customer_id,
                        stripe_subscription_id, invoices_used, created_at)
                    VALUES (:id, :t, :plan, 'active', :cid, :sid, 0, :now)
                """), {"id": str(uuid.uuid4()), "t": tenant_id, "plan": plan_id, "cid": customer_id, "sid": subscription_id, "now": datetime.utcnow()})
            s.commit()
        logger.info(f"subscription_activated: tenant={tenant_id} plan={plan_id}")

    def _handle_subscription_updated(self, subscription: dict) -> None:
        tenant_id = subscription.get("metadata", {}).get("tenant_id")
        if not tenant_id:
            return
        status = subscription.get("status")
        period_end = datetime.fromtimestamp(subscription.get("current_period_end", 0))
        with get_session() as s:
            s.execute(text("""
                UPDATE subscriptions SET status = :s, current_period_end = :pe, invoices_used = 0, updated_at = :now
                WHERE tenant_id = :t
            """), {"s": status, "pe": period_end, "t": tenant_id, "now": datetime.utcnow()})
            s.commit()

    def _handle_subscription_deleted(self, subscription: dict) -> None:
        tenant_id = subscription.get("metadata", {}).get("tenant_id")
        if not tenant_id:
            return
        with get_session() as s:
            s.execute(text("UPDATE subscriptions SET status = 'canceled', plan = 'starter', updated_at = :now WHERE tenant_id = :t"),
                      {"t": tenant_id, "now": datetime.utcnow()})
            s.commit()
        logger.info(f"subscription_canceled: tenant={tenant_id}")

    def _handle_payment_failed(self, invoice: dict) -> None:
        customer_id = invoice.get("customer")
        logger.warning(f"payment_failed: customer={customer_id}")


    def get_usage(self, tenant_id: str) -> dict:
        """Get billing usage for tenant."""
        with get_session() as s:
            row = s.execute(
                text("SELECT plan, status, invoices_used, invoices_limit FROM subscriptions WHERE tenant_id = :t"),
                {"t": tenant_id},
            ).fetchone()
            if not row:
                return {"plan": "none", "status": "inactive", "used": 0, "limit": 0}
            return {
                "plan": row[0],
                "status": row[1],
                "used": row[2] or 0,
                "limit": row[3] if row[3] else "unlimited",
            }
