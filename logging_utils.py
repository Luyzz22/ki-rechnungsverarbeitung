"""
SBS Deutschland – Logging Utilities
Strukturiertes Logging mit Kontext.
"""

import logging
from typing import Optional, Dict, Any
from functools import wraps
import time


# Logger für verschiedene Module
def get_logger(name: str) -> logging.Logger:
    """Holt oder erstellt einen Logger"""
    return logging.getLogger(name)


class LogContext:
    """Kontext-Manager für strukturiertes Logging"""
    
    def __init__(
        self,
        logger: logging.Logger,
        job_id: str = None,
        invoice_id: int = None,
        user_id: int = None,
        filename: str = None,
        **extra
    ):
        self.logger = logger
        self.context = {
            k: v for k, v in {
                "job_id": job_id,
                "invoice_id": invoice_id,
                "user_id": user_id,
                "filename": filename,
                **extra
            }.items() if v is not None
        }
    
    def _format_message(self, message: str) -> str:
        """Fügt Kontext zum Message hinzu"""
        if not self.context:
            return message
        ctx_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
        return f"{message} [{ctx_str}]"
    
    def info(self, message: str, **extra):
        self.logger.info(self._format_message(message), extra={**self.context, **extra})
    
    def warning(self, message: str, **extra):
        self.logger.warning(self._format_message(message), extra={**self.context, **extra})
    
    def error(self, message: str, **extra):
        self.logger.error(self._format_message(message), extra={**self.context, **extra})
    
    def debug(self, message: str, **extra):
        self.logger.debug(self._format_message(message), extra={**self.context, **extra})


def log_execution_time(logger: logging.Logger):
    """Decorator zum Loggen der Ausführungszeit"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start
            logger.info(f"{func.__name__} completed in {duration:.2f}s")
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.info(f"{func.__name__} completed in {duration:.2f}s")
            return result
        
        if hasattr(func, '__wrapped__'):
            return async_wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def log_job_event(
    logger: logging.Logger,
    job_id: str,
    event: str,
    **details
):
    """Loggt ein Job-Event mit Kontext"""
    ctx = LogContext(logger, job_id=job_id)
    ctx.info(f"Job {event}", **details)


def log_invoice_event(
    logger: logging.Logger,
    job_id: str,
    invoice_id: int,
    event: str,
    filename: str = None,
    **details
):
    """Loggt ein Invoice-Event mit Kontext"""
    ctx = LogContext(logger, job_id=job_id, invoice_id=invoice_id, filename=filename)
    ctx.info(f"Invoice {event}", **details)


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    job_id: str = None,
    invoice_id: int = None,
    filename: str = None,
    **extra
):
    """Loggt einen Fehler mit vollem Kontext"""
    ctx = LogContext(
        logger,
        job_id=job_id,
        invoice_id=invoice_id,
        filename=filename,
        error_type=type(error).__name__,
        **extra
    )
    ctx.error(str(error))
