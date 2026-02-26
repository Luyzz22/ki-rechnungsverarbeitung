#!/usr/bin/env python3
"""
SBS Nexus – Daily Spend Analysis Cron
Runs via crontab, triggers alert engine + webhook notifications.
"""
import sys
import os
sys.path.insert(0, "/var/www/invoice-app")
os.chdir("/var/www/invoice-app")

from dotenv import load_dotenv
load_dotenv()

from spend_analytics import run_spend_analysis
from api_nexus import fire_webhook_event
from datetime import datetime

def main():
    print(f"[{datetime.now().isoformat()}] Starting daily spend analysis...")
    
    alerts = run_spend_analysis()
    
    critical = [a for a in alerts if a.severity == "critical"]
    warnings = [a for a in alerts if a.severity == "warning"]
    
    print(f"  Results: {len(alerts)} alerts ({len(critical)} critical, {len(warnings)} warnings)")
    
    if critical:
        fire_webhook_event("spend.alert_critical", {
            "alert_count": len(critical),
            "alerts": [{"id": a.alert_id, "title": a.title, "severity": a.severity} for a in critical],
            "source": "daily_cron"
        })
        print(f"  Webhook fired: spend.alert_critical ({len(critical)} alerts)")
    
    if alerts:
        fire_webhook_event("spend.analysis_complete", {
            "total": len(alerts),
            "critical": len(critical),
            "warnings": len(warnings),
            "source": "daily_cron"
        })
        print(f"  Webhook fired: spend.analysis_complete")
    
    print(f"[{datetime.now().isoformat()}] Done.")

if __name__ == "__main__":
    main()
