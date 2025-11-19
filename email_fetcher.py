#!/usr/bin/env python3
"""
Email Inbox Fetcher - Automatisch Rechnungen aus Emails verarbeiten
"""

import imaplib
import email
from email.header import decode_header
import os
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

logger = logging.getLogger(__name__)

class EmailFetcher:
    def __init__(self, config: dict):
        self.config = config
        self.connection = None
        
    def connect(self) -> bool:
        """Connect to IMAP server"""
        try:
            self.connection = imaplib.IMAP4_SSL(
                self.config['imap_server'],
                self.config.get('imap_port', 993)
            )
            self.connection.login(
                self.config['username'],
                self.config['password']
            )
            logger.info(f"Connected to {self.config['imap_server']}")
            return True
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def fetch_new_emails(self) -> List[Tuple[str, str, str, List[str]]]:
        """
        Fetch new emails with PDF attachments
        Returns: List of (message_id, from_addr, subject, [pdf_paths])
        """
        from database import is_email_processed
        
        if not self.connection:
            if not self.connect():
                return []
        
        results = []
        
        try:
            # Select folder
            folder = self.config.get('folder', 'INBOX')
            self.connection.select(folder)
            
            # Build search criteria
            criteria = ['UNSEEN']
            
            if self.config.get('filter_from'):
                criteria.append(f'FROM "{self.config["filter_from"]}"')
            
            if self.config.get('filter_subject'):
                criteria.append(f'SUBJECT "{self.config["filter_subject"]}"')
            
            # Search for emails
            search_query = ' '.join(criteria) if len(criteria) > 1 else criteria[0]
            status, messages = self.connection.search(None, search_query)
            
            if status != 'OK':
                logger.error("Email search failed")
                return []
            
            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} matching emails")
            
            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = self.connection.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Get message ID
                    message_id = msg.get('Message-ID', str(uuid.uuid4()))
                    
                    # Skip if already processed
                    if is_email_processed(message_id):
                        continue
                    
                    # Get sender and subject
                    from_addr = self._decode_header(msg.get('From', ''))
                    subject = self._decode_header(msg.get('Subject', ''))
                    
                    # Extract PDF attachments
                    pdf_paths = self._extract_pdfs(msg)
                    
                    if pdf_paths:
                        results.append((message_id, from_addr, subject, pdf_paths))
                        logger.info(f"Email '{subject}' has {len(pdf_paths)} PDF(s)")
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
        
        return results
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ''
        
        decoded_parts = decode_header(header)
        result = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                result += part
        return result
    
    def _extract_pdfs(self, msg) -> List[str]:
        """Extract PDF attachments from email"""
        pdf_paths = []
        
        # Create temp directory for this batch
        temp_dir = Path('/var/www/invoice-app/uploads') / f"email_{uuid.uuid4().hex[:8]}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            
            filename = part.get_filename()
            if not filename:
                continue
            
            # Decode filename
            filename = self._decode_header(filename)
            
            # Check if PDF
            if filename.lower().endswith('.pdf'):
                filepath = temp_dir / filename
                
                # Save attachment
                with open(filepath, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                
                pdf_paths.append(str(filepath))
                logger.info(f"Saved PDF: {filename}")
        
        return pdf_paths


def check_inbox_and_process():
    """Main function to check inbox and process new PDFs"""
    from database import get_email_config, save_processed_email
    from invoice_core import InvoiceProcessor
    from export import ExportManager
    
    # Get config
    config = get_email_config()
    if not config or not config.get('enabled'):
        logger.info("Email inbox not configured or disabled")
        return
    
    # Fetch emails
    fetcher = EmailFetcher(config)
    new_emails = fetcher.fetch_new_emails()
    fetcher.disconnect()
    
    if not new_emails:
        logger.info("No new emails with PDFs")
        return
    
    # Process each email
    processor = InvoiceProcessor()
    
    for message_id, from_addr, subject, pdf_paths in new_emails:
        try:
            logger.info(f"Processing email: {subject}")
            
            # Process PDFs
            results = []
            for pdf_path in pdf_paths:
                data = processor.process_invoice(pdf_path)
                if data:
                    results.append(data)
            
            # Export results
            if results:
                manager = ExportManager()
                exported = manager.export_all(results, ['xlsx', 'csv'])
                
                # Generate job_id
                job_id = str(uuid.uuid4())
                
                # Save to database
                from database import save_job, save_invoices
                
                stats = {
                    'total_brutto': sum(r.get('betrag_brutto', 0) or 0 for r in results),
                    'total_netto': sum(r.get('betrag_netto', 0) or 0 for r in results),
                    'total_mwst': sum(r.get('mwst_betrag', 0) or 0 for r in results),
                    'average_brutto': sum(r.get('betrag_brutto', 0) or 0 for r in results) / len(results)
                }
                
                job_data = {
                    'status': 'completed',
                    'total': len(pdf_paths),
                    'successful': len(results),
                    'failed': [],
                    'total_amount': stats['total_brutto'],
                    'stats': stats,
                    'exported_files': exported,
                    'created_at': datetime.now().isoformat(),
                    'completed_at': datetime.now().isoformat()
                }
                
                save_job(job_id, job_data)
                save_invoices(job_id, results)
                
                # Mark email as processed
                save_processed_email(message_id, from_addr, subject, job_id, len(pdf_paths))
                
                logger.info(f"Processed {len(results)} invoices from email '{subject}'")
            
        except Exception as e:
            logger.error(f"Error processing email '{subject}': {e}")
            continue


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    check_inbox_and_process()
