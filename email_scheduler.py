"""
Email Background Scheduler
Checks inbox every N minutes
"""
import schedule
import time
import threading
import logging
from email_fetcher import check_inbox_and_process
from database import get_email_config

logger = logging.getLogger(__name__)

class EmailScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        
    def job(self):
        """Check for new emails and process them"""
        try:
            config = get_email_config()
            if config and config.get('enabled'):
                logger.info("🔍 Checking inbox for new invoices...")
                check_inbox_and_process()
                logger.info("✅ Email check completed")
            else:
                logger.debug("Email monitoring not enabled")
        except Exception as e:
            logger.error(f"❌ Email check failed: {e}")
    
    def start(self):
        """Start the scheduler in background thread"""
        if self.running:
            return
            
        config = get_email_config()
        if not config or not config.get('enabled'):
            logger.info("Email monitoring not enabled")
            return
            
        interval = config.get('check_interval', 300) // 60  # Convert to minutes
        
        schedule.every(interval).minutes.do(self.job)
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
        logger.info(f"📧 Email scheduler started (checking every {interval} minutes)")
    
    def _run(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
        logger.info("Email scheduler stopped")

# Global scheduler instance
email_scheduler = EmailScheduler()
