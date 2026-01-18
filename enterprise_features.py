"""
SBS Deutschland - Enterprise Features Erweiterung
==================================================
Erweiterte Funktionen für user_settings mit Slack und Weekly Report

INSTALLATION:
1. Diese Funktionen ersetzen die bestehenden in enterprise_features.py
2. Oder als neue Funktionen hinzufügen
"""

from datetime import datetime
from typing import Dict, Any
import secrets

# Annahme: get_db() ist bereits definiert in enterprise_features.py


def get_user_settings(email: str) -> Dict[str, Any]:
    """
    Holt erweiterte User-Settings inkl. Slack und Weekly Report.
    Gibt Defaults zurück wenn keine Settings existieren.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Versuche alle Spalten zu holen (mit Fallback für fehlende Spalten)
    try:
        settings = cursor.execute("""
            SELECT 
                user_email,
                COALESCE(notification_email, 1) as notification_email,
                COALESCE(notification_slack, 0) as notification_slack,
                slack_webhook_url,
                COALESCE(weekly_report_enabled, 0) as weekly_report_enabled,
                COALESCE(weekly_report_day, 1) as weekly_report_day,
                COALESCE(weekly_report_time, '07:00') as weekly_report_time,
                api_key,
                api_key_created,
                language,
                timezone,
                theme,
                two_factor_enabled,
                updated_at
            FROM user_settings 
            WHERE user_email = ?
        """, (email,)).fetchone()
    except Exception as e:
        # Fallback wenn neue Spalten noch nicht existieren
        print(f"Settings query error (migration needed?): {e}")
        settings = cursor.execute("""
            SELECT 
                user_email,
                notification_email,
                notification_slack,
                api_key
            FROM user_settings 
            WHERE user_email = ?
        """, (email,)).fetchone()
    
    conn.close()
    
    # Defaults wenn keine Settings
    if not settings:
        return {
            "user_email": email,
            "notification_email": True,
            "notification_slack": False,
            "slack_webhook_url": None,
            "weekly_report_enabled": False,
            "weekly_report_day": 1,
            "weekly_report_time": "07:00",
            "api_key": None,
            "api_key_created": None,
            "language": "de",
            "timezone": "Europe/Berlin",
            "theme": "light",
            "two_factor_enabled": False,
            "updated_at": None
        }
    
    # Dict erstellen (row_factory fallback)
    if hasattr(settings, 'keys'):
        return dict(settings)
    else:
        # Tuple to dict mapping
        columns = [
            'user_email', 'notification_email', 'notification_slack',
            'slack_webhook_url', 'weekly_report_enabled', 'weekly_report_day',
            'weekly_report_time', 'api_key', 'api_key_created', 'language',
            'timezone', 'theme', 'two_factor_enabled', 'updated_at'
        ]
        result = {}
        for i, col in enumerate(columns):
            if i < len(settings):
                result[col] = settings[i]
            else:
                result[col] = None
        
        # Defaults für Boolean-Felder
        result['notification_email'] = bool(result.get('notification_email', True))
        result['notification_slack'] = bool(result.get('notification_slack', False))
        result['weekly_report_enabled'] = bool(result.get('weekly_report_enabled', False))
        result['weekly_report_day'] = result.get('weekly_report_day') or 1
        result['weekly_report_time'] = result.get('weekly_report_time') or '07:00'
        
        return result


def update_user_settings(email: str, **kwargs) -> Dict[str, Any]:
    """
    Aktualisiert User-Settings.
    
    Unterstützte kwargs:
    - notification_email: bool
    - notification_slack: bool
    - slack_webhook_url: str
    - weekly_report_enabled: bool
    - weekly_report_day: int (1-7)
    - weekly_report_time: str (HH:MM)
    - language: str
    - timezone: str
    - theme: str
    - two_factor_enabled: bool
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Prüfen ob Eintrag existiert
    existing = cursor.execute(
        "SELECT user_email FROM user_settings WHERE user_email = ?", 
        (email,)
    ).fetchone()
    
    if not existing:
        # Neuen Eintrag erstellen
        cursor.execute(
            "INSERT INTO user_settings (user_email, updated_at) VALUES (?, ?)",
            (email, datetime.now().isoformat())
        )
    
    # Erlaubte Felder
    allowed_fields = {
        'notification_email',
        'notification_slack', 
        'slack_webhook_url',
        'weekly_report_enabled',
        'weekly_report_day',
        'weekly_report_time',
        'language',
        'timezone',
        'theme',
        'two_factor_enabled'
    }
    
    # Updates ausführen
    for key, value in kwargs.items():
        if key in allowed_fields:
            try:
                # Boolean zu Integer für SQLite
                if isinstance(value, bool):
                    value = 1 if value else 0
                
                cursor.execute(
                    f'UPDATE user_settings SET {key} = ?, updated_at = ? WHERE user_email = ?',
                    (value, datetime.now().isoformat(), email)
                )
            except Exception as e:
                print(f"Error updating {key}: {e}")
                # Spalte existiert vielleicht nicht - Migration nötig
                continue
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Einstellungen aktualisiert"}


def get_user_settings_for_notifications(email: str) -> Dict[str, Any]:
    """
    Holt Settings speziell für Notification-Versand.
    Optimiert für scheduled_reports und notification_api.
    """
    settings = get_user_settings(email)
    
    return {
        "email": email,
        "notification_email": settings.get("notification_email", True),
        "notification_slack": settings.get("notification_slack", False),
        "slack_webhook_url": settings.get("slack_webhook_url"),
        "weekly_report_enabled": settings.get("weekly_report_enabled", False),
        "weekly_report_day": settings.get("weekly_report_day", 1),
        "weekly_report_time": settings.get("weekly_report_time", "07:00")
    }


# ============================================================================
# ZUSÄTZLICHE HILFSFUNKTIONEN
# ============================================================================

def ensure_settings_columns():
    """
    Stellt sicher dass alle benötigten Spalten existieren.
    Kann beim App-Start aufgerufen werden.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Spalten die hinzugefügt werden sollen
    new_columns = [
        ("slack_webhook_url", "TEXT DEFAULT NULL"),
        ("weekly_report_enabled", "INTEGER DEFAULT 0"),
        ("weekly_report_day", "INTEGER DEFAULT 1"),
        ("weekly_report_time", "TEXT DEFAULT '07:00'")
    ]
    
    for col_name, col_def in new_columns:
        try:
            cursor.execute(f"ALTER TABLE user_settings ADD COLUMN {col_name} {col_def}")
            print(f"✅ Spalte {col_name} hinzugefügt")
        except Exception as e:
            # Spalte existiert bereits
            if "duplicate column" not in str(e).lower():
                print(f"Spalte {col_name}: {e}")
    
    conn.commit()
    conn.close()


# ============================================================================
# INTEGRATION MIT MAIN.PY
# ============================================================================
"""
In main.py am App-Start aufrufen:

from .enterprise_features import ensure_settings_columns
ensure_settings_columns()  # Stellt sicher dass DB-Schema aktuell ist
"""

# =============================================================================
# PHASE 1: AI INTELLIGENCE LAYER - GPT-4o Financial Analyst
# =============================================================================

def get_ai_financial_analysis(stats: dict, user_name: str) -> str:
    """
    Erzeugt eine intelligente CFO-Analyse via OpenAI GPT-4o.
    Enterprise Standard: Inklusive Error-Handling und Fallback.
    """
    import os
    try:
        from openai import OpenAI
    except ImportError:
        return f"Hallo {user_name}, hier sind Ihre Zahlen: {stats.get('total_invoices')} Rechnungen mit gesamt {stats.get('total_brutto', 0):.2f}€."

    api_key = os.getenv("OPENAI_API_KEY")
    
    # Fallback für Entwicklung/Fehlende Keys
    if not api_key or "HIER_IHR_OPENAI_KEY" in api_key:
        return f"Finanz-Update für {user_name}: Diese Woche wurden {stats.get('total_invoices')} Belege verarbeitet. Gesamtvolumen: {stats.get('total_brutto', 0):.2f}€."

    client = OpenAI(api_key=api_key)

    system_prompt = """
    Du bist 'SBS AI CFO', ein hochprofessioneller Finanzberater für KMUs.
    Analysiere die wöchentlichen Daten präzise:
    - Identifiziere Trends oder Ausreißer.
    - Tonfall: Professionell, direkt, unternehmerisch denkend.
    - Max. 3 Sätze. Nutze Business-Deutsch.
    """

    user_prompt = f"""
    User: {user_name}
    Daten der Woche:
    - Rechnungen gesamt: {stats.get('total_invoices')}
    - Brutto-Volumen: {stats.get('total_brutto', 0):.2f} EUR
    - Netto-Volumen: {stats.get('total_netto', 0):.2f} EUR
    - Top Lieferanten: {stats.get('top_suppliers', 'Keine Daten')}
    
    Erstelle eine kurze Slack-Zusammenfassung für den Geschäftsführer.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        import logging
        logging.error(f"AI Analysis Error: {e}")
        return f"Wöchentlicher Report für {user_name}: {stats.get('total_invoices')} Rechnungen erfolgreich erfasst."

