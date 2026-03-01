"""GoBD Evidence Package Generator.

Creates sealed, tamper-evident ZIP archives containing:
- Original document (PDF/XML)
- Complete audit chain (JSON)
- Validation reports
- Processing metadata
- SHA-256 manifest of all contents

GoBD Requirements:
- Aufbewahrungspflicht (10 years retention)
- Unveraenderbarkeit (sealed archive)
- Vollstaendigkeit (all artifacts included)
- Nachpruefbarkeit (verifiable manifest)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from modules.rechnungsverarbeitung.src.invoices.services.audit_chain import (
    AuditChain,
)

logger = logging.getLogger(__name__)


@dataclass
class EvidenceArtifact:
    """A single file to include in the evidence package."""

    filename: str
    content: bytes
    description: str = ""
    mime_type: str = "application/octet-stream"


@dataclass
class EvidenceManifest:
    """Manifest documenting all artifacts and their checksums."""

    document_id: str
    tenant_id: str
    created_at: str
    generator: str = "SBS Nexus Finance v1.0"
    gobd_retention_years: int = 10
    artifacts: list[dict[str, str]] = field(default_factory=list)
    chain_verified: bool = False
    chain_length: int = 0
    manifest_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at,
            "generator": self.generator,
            "gobd_retention_years": self.gobd_retention_years,
            "retention_until": str(
                datetime.fromisoformat(self.created_at).year + self.gobd_retention_years
            ),
            "artifacts": self.artifacts,
            "chain_verified": self.chain_verified,
            "chain_length": self.chain_length,
            "manifest_hash": self.manifest_hash,
        }


class GoBDEvidenceService:
    """Creates and manages GoBD-compliant evidence packages.

    Usage:
        service = GoBDEvidenceService(evidence_dir="./evidence")
        path = service.create_package(
            document_id="doc-123",
            tenant_id="tenant-1",
            audit_chain=chain,
            artifacts=[
                EvidenceArtifact("rechnung.pdf", pdf_bytes, "Original invoice"),
            ],
        )
    """

    def __init__(self, evidence_dir: str = "./evidence") -> None:
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def create_package(
        self,
        document_id: str,
        tenant_id: str,
        audit_chain: AuditChain,
        artifacts: list[EvidenceArtifact] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Create a sealed GoBD evidence ZIP package.

        Args:
            document_id: Unique document identifier.
            tenant_id: Tenant scope.
            audit_chain: Complete hash chain for the document.
            artifacts: Additional files (original doc, reports, etc.).
            metadata: Extra metadata to include.

        Returns:
            Path to the created ZIP archive.
        """
        artifacts = artifacts or []
        now = datetime.utcnow()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")

        # Verify chain before sealing
        chain_verified = audit_chain.verify()
        if not chain_verified:
            logger.warning(
                "gobd_chain_unverified",
                extra={"document_id": document_id},
            )

        # Build manifest
        manifest = EvidenceManifest(
            document_id=document_id,
            tenant_id=tenant_id,
            created_at=now.isoformat(),
            chain_verified=chain_verified,
            chain_length=audit_chain.length,
        )

        # Create ZIP in memory
        zip_buffer = BytesIO()
        file_hashes: list[dict[str, str]] = []

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Audit chain
            chain_json = json.dumps(
                [e.to_dict() for e in audit_chain.entries],
                indent=2,
                ensure_ascii=False,
            ).encode("utf-8")
            zf.writestr("audit_chain.json", chain_json)
            file_hashes.append({
                "filename": "audit_chain.json",
                "sha256": hashlib.sha256(chain_json).hexdigest(),
                "description": "Complete SHA-256 hash chain",
                "size_bytes": str(len(chain_json)),
            })

            # 2. Additional artifacts
            for artifact in artifacts:
                zf.writestr(artifact.filename, artifact.content)
                file_hashes.append({
                    "filename": artifact.filename,
                    "sha256": hashlib.sha256(artifact.content).hexdigest(),
                    "description": artifact.description,
                    "mime_type": artifact.mime_type,
                    "size_bytes": str(len(artifact.content)),
                })

            # 3. Extra metadata
            if metadata:
                meta_json = json.dumps(metadata, indent=2, ensure_ascii=False).encode("utf-8")
                zf.writestr("processing_metadata.json", meta_json)
                file_hashes.append({
                    "filename": "processing_metadata.json",
                    "sha256": hashlib.sha256(meta_json).hexdigest(),
                    "description": "Processing metadata",
                    "size_bytes": str(len(meta_json)),
                })

            # 4. Manifest (hash of all other files)
            manifest.artifacts = file_hashes
            manifest_content = json.dumps(
                manifest.to_dict(), indent=2, ensure_ascii=False
            )
            manifest_hash = hashlib.sha256(
                manifest_content.encode("utf-8")
            ).hexdigest()
            manifest.manifest_hash = manifest_hash

            # Re-serialize with hash included
            final_manifest = json.dumps(
                manifest.to_dict(), indent=2, ensure_ascii=False
            ).encode("utf-8")
            zf.writestr("manifest.json", final_manifest)

        # Write to disk
        tenant_dir = self.evidence_dir / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        filename = f"evidence_{document_id}_{timestamp_str}.zip"
        filepath = tenant_dir / filename

        filepath.write_bytes(zip_buffer.getvalue())

        logger.info(
            "gobd_evidence_created",
            extra={
                "document_id": document_id,
                "tenant_id": tenant_id,
                "path": str(filepath),
                "artifacts_count": len(file_hashes),
                "chain_verified": chain_verified,
                "size_bytes": filepath.stat().st_size,
            },
        )

        return filepath

    def verify_package(self, filepath: Path) -> dict[str, Any]:
        """Verify integrity of an existing evidence package.

        Returns verification report with status and details.
        """
        result: dict[str, Any] = {
            "filepath": str(filepath),
            "verified": False,
            "errors": [],
            "artifacts_checked": 0,
        }

        if not filepath.exists():
            result["errors"].append("File not found")
            return result

        with zipfile.ZipFile(filepath, "r") as zf:
            # Load manifest
            try:
                manifest_raw = zf.read("manifest.json")
                manifest = json.loads(manifest_raw)
            except (KeyError, json.JSONDecodeError) as e:
                result["errors"].append(f"Manifest error: {e}")
                return result

            # Verify each artifact hash
            for artifact in manifest.get("artifacts", []):
                fname = artifact["filename"]
                expected_hash = artifact["sha256"]

                try:
                    content = zf.read(fname)
                    actual_hash = hashlib.sha256(content).hexdigest()
                    if actual_hash != expected_hash:
                        result["errors"].append(
                            f"{fname}: hash mismatch (expected {expected_hash[:16]}, got {actual_hash[:16]})"
                        )
                    result["artifacts_checked"] += 1
                except KeyError:
                    result["errors"].append(f"{fname}: missing from archive")

        result["verified"] = len(result["errors"]) == 0
        return result
