#!/usr/bin/env python3
"""Email Ingestion Cron Job."""
import io, logging, sys
sys.path.insert(0, "/var/www/invoice-app")

from dotenv import load_dotenv
load_dotenv("/var/www/invoice-app/.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from modules.rechnungsverarbeitung.src.invoices.services.email_ingestion import EmailIngestionService
from modules.rechnungsverarbeitung.src.invoices.services.invoice_processing import process_invoice_upload
from shared.tenant.context import TenantContext

def process_cb(filename, content, mime_type, tenant_id):
    TenantContext.set_current_tenant(tenant_id)
    meta = process_invoice_upload(
        file_stream=io.BytesIO(content),
        file_name=filename,
        mime_type=mime_type,
        uploaded_by="email-ingestion",
    )
    return meta.id

service = EmailIngestionService()
stats = service.poll_and_process(tenant_id="default", process_callback=process_cb)
print(f"Emails: {stats.emails_checked}, Invoices: {stats.invoices_ingested}, Errors: {stats.errors}")
