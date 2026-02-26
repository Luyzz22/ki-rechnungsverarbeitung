import os
import sys
import logging

# Logging aktivieren um Fehler zu sehen
logging.basicConfig(level=logging.INFO)

try:
    import notification_api
    # Prüfe verfügbare Funktionen in der Datei
    funcs = [f for f in dir(notification_api) if 'slack' in f.lower()]
    print(f"🔍 Verfügbare Slack-Funktionen: {funcs}")
    
    from notification_api import send_slack_weekly_report
except ImportError as e:
    print(f"❌ Import-Fehler: {e}")
    print("Versuche alternativen Import...")
    # Falls die Funktion anders heißt oder verschachtelt ist, hier manueller Workaround:
    def send_slack_weekly_report(url, stats, name):
        # Fallback: Wir nutzen die Logik direkt, falls der Import klemmt
        import requests
        from enterprise_features import get_ai_financial_analysis
        ai_comment = get_ai_financial_analysis(stats, name)
        message = {
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{ai_comment}*"}},
                {"type": "divider"}
            ]
        }
        res = requests.post(url, json=message)
        return res.status_code == 200

# Dummy-Daten
test_stats = {
    "total_invoices": 12,
    "total_brutto": 2450.50,
    "total_netto": 2059.24,
    "top_suppliers": "Amazon, Telekom"
}

# Webhook laden
webhook_url = ""
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("SLACK_WEBHOOK_URL="):
                webhook_url = line.split("=")[1].strip().strip('"')

if not webhook_url:
    webhook_url = input("Bitte Slack Webhook URL eingeben: ")

print(f"🚀 Sende Test mit KI-Kommentar...")
if send_slack_weekly_report(webhook_url, test_stats, "Test Admin"):
    print("✅ Erfolg! Check Slack.")
else:
    print("❌ Fehlgeschlagen.")
