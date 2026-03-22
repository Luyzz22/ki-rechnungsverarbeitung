"""Persistent File Storage for Invoice PDFs.

Stores uploaded files on disk with tenant isolation.
Path pattern: /storage/invoices/{tenant_id}/{document_id}/{filename}
"""
from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STORAGE_ROOT = Path("/var/www/invoice-app/storage/invoices")


class FileStorageService:
    """Stores and retrieves invoice files on disk."""

    def __init__(self, root: Path = STORAGE_ROOT):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, tenant_id: str, document_id: str, file_name: str, content: bytes) -> str:
        """Store file and return the storage path."""
        tenant_dir = self.root / tenant_id / document_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        file_path = tenant_dir / file_name
        file_path.write_bytes(content)
        logger.info(f"stored: {file_path} ({len(content)} bytes)")
        return str(file_path)

    def retrieve(self, tenant_id: str, document_id: str, file_name: str) -> Optional[bytes]:
        """Retrieve file content by path."""
        file_path = self.root / tenant_id / document_id / file_name
        if file_path.exists():
            return file_path.read_bytes()
        return None

    def get_path(self, tenant_id: str, document_id: str, file_name: str) -> Optional[Path]:
        """Get the filesystem path for a stored file."""
        file_path = self.root / tenant_id / document_id / file_name
        return file_path if file_path.exists() else None

    def delete(self, tenant_id: str, document_id: str) -> bool:
        """Delete all files for a document."""
        doc_dir = self.root / tenant_id / document_id
        if doc_dir.exists():
            shutil.rmtree(doc_dir)
            return True
        return False

    def list_files(self, tenant_id: str, document_id: str) -> list[str]:
        """List all files for a document."""
        doc_dir = self.root / tenant_id / document_id
        if doc_dir.exists():
            return [f.name for f in doc_dir.iterdir() if f.is_file()]
        return []

    def get_tenant_usage(self, tenant_id: str) -> dict:
        """Get storage usage for a tenant."""
        tenant_dir = self.root / tenant_id
        if not tenant_dir.exists():
            return {"files": 0, "bytes": 0}
        total_files = 0
        total_bytes = 0
        for f in tenant_dir.rglob("*"):
            if f.is_file():
                total_files += 1
                total_bytes += f.stat().st_size
        return {"files": total_files, "bytes": total_bytes}
