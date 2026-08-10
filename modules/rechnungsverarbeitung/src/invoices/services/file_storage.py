"""Persistent File Storage for Invoice PDFs.

Stores uploaded files on disk with tenant isolation.
Path pattern: /storage/invoices/{tenant_id}/{document_id}/{filename}
"""
from __future__ import annotations

import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STORAGE_ROOT = Path("/var/www/invoice-app/storage/invoices")


class UnsafeStoragePathError(ValueError):
    """Raised when a storage path component could escape tenant storage."""


def _validate_component(value: str, label: str) -> str:
    """Return a safe single path component or fail closed.

    User-controlled upload names must never be interpreted as filesystem paths.
    Reject path separators, absolute/traversal components and NUL bytes while
    preserving legitimate Unicode and whitespace inside a filename.
    """
    component = str(value or "")
    if not component or component in {".", ".."}:
        raise UnsafeStoragePathError(f"invalid_{label}")
    if "\x00" in component or "/" in component or "\\" in component:
        raise UnsafeStoragePathError(f"invalid_{label}")
    if Path(component).is_absolute():
        raise UnsafeStoragePathError(f"invalid_{label}")
    return component


class FileStorageService:
    """Stores and retrieves invoice files on disk with fail-closed path isolation."""

    def __init__(self, root: Path = STORAGE_ROOT):
        root.mkdir(parents=True, exist_ok=True)
        self.root = root.resolve()

    def _path(self, tenant_id: str, document_id: str, file_name: str | None = None) -> Path:
        tenant = _validate_component(tenant_id, "tenant_id")
        document = _validate_component(document_id, "document_id")
        parts = [tenant, document]
        if file_name is not None:
            parts.append(_validate_component(file_name, "file_name"))

        candidate = self.root.joinpath(*parts).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise UnsafeStoragePathError("storage_path_escape")
        return candidate

    def store(self, tenant_id: str, document_id: str, file_name: str, content: bytes) -> str:
        """Store file and return the storage path."""
        file_path = self._path(tenant_id, document_id, file_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Resolve again after directory creation to catch a pre-existing symlink
        # in the tenant/document hierarchy before writing customer content.
        file_path = self._path(tenant_id, document_id, file_name)
        file_path.write_bytes(content)
        logger.info("stored invoice file (%s bytes)", len(content))
        return str(file_path)

    def retrieve(self, tenant_id: str, document_id: str, file_name: str) -> Optional[bytes]:
        """Retrieve file content by tenant-scoped path."""
        file_path = self._path(tenant_id, document_id, file_name)
        if file_path.is_file():
            return file_path.read_bytes()
        return None

    def get_path(self, tenant_id: str, document_id: str, file_name: str) -> Optional[Path]:
        """Get the tenant-scoped filesystem path for a stored file."""
        file_path = self._path(tenant_id, document_id, file_name)
        return file_path if file_path.is_file() else None

    def delete(self, tenant_id: str, document_id: str) -> bool:
        """Delete all files for a tenant-scoped document."""
        doc_dir = self._path(tenant_id, document_id)
        if doc_dir.is_dir():
            shutil.rmtree(doc_dir)
            return True
        return False

    def list_files(self, tenant_id: str, document_id: str) -> list[str]:
        """List files for a tenant-scoped document."""
        doc_dir = self._path(tenant_id, document_id)
        if doc_dir.is_dir():
            return [f.name for f in doc_dir.iterdir() if f.is_file()]
        return []

    def get_tenant_usage(self, tenant_id: str) -> dict:
        """Get storage usage for a tenant."""
        tenant = _validate_component(tenant_id, "tenant_id")
        tenant_dir = self.root.joinpath(tenant).resolve(strict=False)
        if not tenant_dir.is_relative_to(self.root):
            raise UnsafeStoragePathError("storage_path_escape")
        if not tenant_dir.is_dir():
            return {"files": 0, "bytes": 0}
        total_files = 0
        total_bytes = 0
        for f in tenant_dir.rglob("*"):
            if f.is_file():
                total_files += 1
                total_bytes += f.stat().st_size
        return {"files": total_files, "bytes": total_bytes}
