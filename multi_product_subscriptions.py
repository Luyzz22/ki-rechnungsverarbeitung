#!/usr/bin/env python3
"""
SBS Deutschland – Multi-Product Subscription System
Enterprise SaaS Architecture für Multiple Produkte

Produkte:
- invoice: KI-Rechnungsverarbeitung
- contract: KI-Vertragsanalyse
- bundle: Beide Produkte (Rabatt)
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

DB_PATH = '/var/www/invoice-app/invoices.db'


class Product(Enum):
    """Verfügbare Produkte"""
    INVOICE = "invoice"      # KI-Rechnungsverarbeitung
    CONTRACT = "contract"    # KI-Vertragsanalyse
    BUNDLE = "bundle"        # Beide Produkte


class Plan(Enum):
    """Verfügbare Pläne pro Produkt"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Stripe Price IDs (Live Keys - später in .env)
STRIPE_PRICES = {
    # Invoice Produkt
    "invoice_starter_monthly": "price_invoice_starter_monthly",
    "invoice_starter_yearly": "price_invoice_starter_yearly",
    "invoice_professional_monthly": "price_invoice_professional_monthly",
    "invoice_professional_yearly": "price_invoice_professional_yearly",
    "invoice_enterprise_monthly": "price_invoice_enterprise_monthly",
    "invoice_enterprise_yearly": "price_invoice_enterprise_yearly",
    
    # Contract Produkt
    "contract_starter_monthly": "price_contract_starter_monthly",
    "contract_starter_yearly": "price_contract_starter_yearly",
    "contract_professional_monthly": "price_contract_professional_monthly",
    "contract_professional_yearly": "price_contract_professional_yearly",
    "contract_enterprise_monthly": "price_contract_enterprise_monthly",
    "contract_enterprise_yearly": "price_contract_enterprise_yearly",
    
    # Bundle (beide Produkte, 20% Rabatt)
    "bundle_starter_monthly": "price_bundle_starter_monthly",
    "bundle_starter_yearly": "price_bundle_starter_yearly",
    "bundle_professional_monthly": "price_bundle_professional_monthly",
    "bundle_professional_yearly": "price_bundle_professional_yearly",
    "bundle_enterprise_monthly": "price_bundle_enterprise_monthly",
    "bundle_enterprise_yearly": "price_bundle_enterprise_yearly",
}

# Produkt-Limits
PRODUCT_LIMITS = {
    "invoice": {
        "free": {"invoices_per_month": 5, "features": ["basic_extraction", "csv_export"]},
        "starter": {"invoices_per_month": 100, "features": ["basic_extraction", "csv_export", "xlsx_export", "datev_export"]},
        "professional": {"invoices_per_month": 500, "features": ["all", "api_access", "auto_accounting", "finance_copilot"]},
        "enterprise": {"invoices_per_month": -1, "features": ["all", "api_access", "auto_accounting", "finance_copilot", "dedicated_support", "sla"]},
    },
    "contract": {
        "free": {"contracts_per_month": 3, "features": ["basic_analysis"]},
        "starter": {"contracts_per_month": 25, "features": ["basic_analysis", "json_export", "csv_export"]},
        "professional": {"contracts_per_month": 100, "features": ["all", "api_access", "bulk_upload", "risk_scoring"]},
        "enterprise": {"contracts_per_month": -1, "features": ["all", "api_access", "bulk_upload", "risk_scoring", "dedicated_support", "sla"]},
    },
}

# Preise (EUR, monatlich)
PRICING = {
    "invoice": {
        "free": 0,
        "starter": 49,
        "professional": 149,
        "enterprise": 449,
    },
    "contract": {
        "free": 0,
        "starter": 39,
        "professional": 119,
        "enterprise": 349,
    },
    "bundle": {  # 20% Rabatt auf Summe
        "free": 0,
        "starter": 70,      # statt 88 (49+39)
        "professional": 214, # statt 268 (149+119)
        "enterprise": 638,   # statt 798 (449+349)
    },
}


def init_product_subscriptions_table():
    """Erstellt erweiterte Subscriptions-Tabelle mit Multi-Product Support"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Neue Tabelle für Product-Subscriptions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product TEXT NOT NULL,
            plan TEXT NOT NULL,
            billing_cycle TEXT DEFAULT 'monthly',
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            stripe_price_id TEXT,
            status TEXT DEFAULT 'active',
            usage_limit INTEGER,
            usage_current INTEGER DEFAULT 0,
            current_period_start TEXT,
            current_period_end TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, product)
        )
    ''')
    
    # Index für schnelle Lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_subs_user ON product_subscriptions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_subs_product ON product_subscriptions(product)')
    
    conn.commit()
    conn.close()
    logger.info("✅ Product Subscriptions Tabelle initialisiert")


def get_user_products(user_id: int) -> List[Dict[str, Any]]:
    """
    Holt alle aktiven Produkt-Subscriptions eines Users.
    
    Returns:
        Liste der aktiven Produkte mit Plan-Details
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM product_subscriptions 
        WHERE user_id = ? AND status = 'active'
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def has_product_access(user_id: int, product: str) -> Dict[str, Any]:
    """
    Prüft ob User Zugang zu einem Produkt hat.
    
    Args:
        user_id: User ID
        product: 'invoice' oder 'contract'
        
    Returns:
        Dict mit access, plan, limits, usage
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Prüfe Admin-Status
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if user and user['is_admin']:
        conn.close()
        return {
            "access": True,
            "plan": "enterprise",
            "is_admin": True,
            "usage_limit": -1,
            "usage_current": 0,
            "features": ["all"]
        }
    
    # Prüfe direkte Produkt-Subscription
    cursor.execute('''
        SELECT * FROM product_subscriptions 
        WHERE user_id = ? AND product = ? AND status = 'active'
    ''', (user_id, product))
    
    sub = cursor.fetchone()
    
    # Prüfe auch Bundle
    if not sub:
        cursor.execute('''
            SELECT * FROM product_subscriptions 
            WHERE user_id = ? AND product = 'bundle' AND status = 'active'
        ''', (user_id,))
        sub = cursor.fetchone()
    
    conn.close()
    
    if not sub:
        # Kein Abo - Free Tier
        limits = PRODUCT_LIMITS.get(product, {}).get("free", {})
        return {
            "access": True,  # Free Tier erlaubt
            "plan": "free",
            "is_admin": False,
            "usage_limit": limits.get("invoices_per_month") or limits.get("contracts_per_month", 5),
            "usage_current": 0,  # TODO: Track free usage
            "features": limits.get("features", [])
        }
    
    sub_dict = dict(sub)
    plan = sub_dict.get("plan", "free")
    limits = PRODUCT_LIMITS.get(product, {}).get(plan, {})
    
    return {
        "access": True,
        "plan": plan,
        "is_admin": False,
        "usage_limit": sub_dict.get("usage_limit", -1),
        "usage_current": sub_dict.get("usage_current", 0),
        "features": limits.get("features", []),
        "subscription_id": sub_dict.get("id"),
        "stripe_subscription_id": sub_dict.get("stripe_subscription_id"),
    }


def get_user_dashboard_redirect(user_id: int) -> str:
    """
    Bestimmt wohin User nach Login geleitet wird basierend auf Subscriptions.
    
    Logic:
    1. Nur Invoice → /history (Rechnungen)
    2. Nur Contract → contract.sbsdeutschland.com/upload
    3. Beides/Bundle → /dashboard (Unified Dashboard)
    4. Nichts → /pricing (Preisseite)
    """
    products = get_user_products(user_id)
    
    if not products:
        # Kein Abo - zur Preisseite oder Free-Trial Dashboard
        return "/dashboard"  # Unified Dashboard mit Upsell
    
    product_names = [p["product"] for p in products]
    
    # Bundle oder beide Produkte
    if "bundle" in product_names or ("invoice" in product_names and "contract" in product_names):
        return "/dashboard"  # Unified Dashboard
    
    # Nur Invoice
    if "invoice" in product_names:
        return "/history"
    
    # Nur Contract
    if "contract" in product_names:
        return "https://contract.sbsdeutschland.com/upload"
    
    return "/dashboard"


def create_product_subscription(
    user_id: int,
    product: str,
    plan: str,
    billing_cycle: str = "monthly",
    stripe_customer_id: str = None,
    stripe_subscription_id: str = None,
    stripe_price_id: str = None
) -> int:
    """
    Erstellt neue Produkt-Subscription.
    
    Returns:
        Subscription ID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Berechne Limit
    limits = PRODUCT_LIMITS.get(product, {}).get(plan, {})
    usage_limit = limits.get("invoices_per_month") or limits.get("contracts_per_month", 100)
    
    cursor.execute('''
        INSERT OR REPLACE INTO product_subscriptions 
        (user_id, product, plan, billing_cycle, stripe_customer_id, 
         stripe_subscription_id, stripe_price_id, usage_limit, status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', datetime('now'))
    ''', (user_id, product, plan, billing_cycle, stripe_customer_id,
          stripe_subscription_id, stripe_price_id, usage_limit))
    
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Subscription erstellt: User {user_id}, Product {product}, Plan {plan}")
    return sub_id


def increment_usage(user_id: int, product: str) -> bool:
    """Erhöht Usage-Counter für Produkt"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE product_subscriptions 
        SET usage_current = usage_current + 1, updated_at = datetime('now')
        WHERE user_id = ? AND product = ? AND status = 'active'
    ''', (user_id, product))
    
    # Auch Bundle prüfen
    if cursor.rowcount == 0:
        cursor.execute('''
            UPDATE product_subscriptions 
            SET usage_current = usage_current + 1, updated_at = datetime('now')
            WHERE user_id = ? AND product = 'bundle' AND status = 'active'
        ''', (user_id,))
    
    conn.commit()
    conn.close()
    return True


def reset_monthly_usage():
    """Setzt monatliche Usage zurück (Cronjob)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE product_subscriptions 
        SET usage_current = 0, updated_at = datetime('now')
        WHERE status = 'active'
    ''')
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Monthly usage reset: {affected} subscriptions")
    return affected


# Initialisiere beim Import
init_product_subscriptions_table()


if __name__ == "__main__":
    # Test
    print("Testing Multi-Product Subscriptions...")
    
    # Test User Products
    products = get_user_products(1)
    print(f"User 1 Products: {products}")
    
    # Test Access Check
    access = has_product_access(1, "invoice")
    print(f"User 1 Invoice Access: {access}")
    
    # Test Redirect
    redirect = get_user_dashboard_redirect(1)
    print(f"User 1 Redirect: {redirect}")
