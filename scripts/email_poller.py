#!/usr/bin/env python3
"""Email Ingestion Poller — runs via systemd timer."""
import sys
import os
import logging

sys.path.insert(0, "/var/www/invoice-app")
os.chdir("/var/www/invoice-app")

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("email-poller")

from modules.rechnungsverarbeitung.src.invoices.services.email_ingestion import EmailIngestionService

def main():
    svc = EmailIngestionService()
    results = svc.poll()
    if results:
        logger.info(f"Processed {len(results)} invoice(s) from email")
        for r in results:
            logger.info(f"  {r['file_name']} from {r['sender']} ({r['size_kb']} KB)")
    else:
        logger.info("No new invoices in mailbox")

if __name__ == "__main__":
    main()
