#!/usr/bin/env python3
"""
SBS Deutschland – Geplanter Enterprise-Task (Phase 4b + 5c)

Auszuführen z.B. täglich per Cron:
    0 2 * * * /usr/bin/python3 /var/www/invoice-app/cron_enterprise.py

Aufgaben:
- Eskalation überfälliger Freigaben (> 48h offen) inkl. optionaler E-Mail
- DSGVO: Bereinigung abgelaufener Daten (GoBD-konformer Soft-Delete)
"""

import logging

from approval_workflow import check_escalations
from dsgvo import run_retention_cleanup

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("cron_enterprise")


def main() -> None:
    escalated = check_escalations(notify=True)
    logger.info("Eskalierte Freigaben: %s", escalated)

    cleanup = run_retention_cleanup()
    logger.info(
        "Retention-Cleanup: %s Mandanten, %s Rechnungen markiert",
        cleanup["tenants_processed"],
        cleanup["invoices_marked"],
    )


if __name__ == "__main__":
    main()
