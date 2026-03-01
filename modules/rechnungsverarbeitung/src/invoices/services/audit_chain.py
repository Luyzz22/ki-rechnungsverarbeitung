"""SHA-256 Hash-Chain Audit Trail for GoBD compliance.

Each event includes a hash of the previous event, creating an
immutable, tamper-evident chain per document. Any modification
to historical events breaks the chain and is detectable.

GoBD Requirements addressed:
- Nachvollziehbarkeit (traceability)
- Unveraenderbarkeit (immutability)
- Vollstaendigkeit (completeness)
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Genesis hash for first event in any document chain.
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditEntry:
    """Single entry in the hash chain."""

    document_id: str
    tenant_id: str
    sequence_number: int
    event_type: str
    status_from: str | None
    status_to: str | None
    actor: str | None
    timestamp: str  # ISO 8601
    details: dict[str, Any]
    previous_hash: str
    entry_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _compute_hash(
    document_id: str,
    tenant_id: str,
    sequence_number: int,
    event_type: str,
    status_from: str | None,
    status_to: str | None,
    actor: str | None,
    timestamp: str,
    details: dict[str, Any],
    previous_hash: str,
) -> str:
    """Compute SHA-256 hash over all fields including the previous hash."""
    payload = json.dumps(
        {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "sequence_number": sequence_number,
            "event_type": event_type,
            "status_from": status_from,
            "status_to": status_to,
            "actor": actor,
            "timestamp": timestamp,
            "details": details,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditChain:
    """Manages a per-document hash chain of audit events.

    Usage:
        chain = AuditChain(document_id="doc-123", tenant_id="tenant-1")
        entry = chain.append(
            event_type="upload_received",
            status_from=None,
            status_to="uploaded",
            actor="system",
        )
        assert chain.verify()  # True if chain is intact
    """

    def __init__(self, document_id: str, tenant_id: str) -> None:
        self.document_id = document_id
        self.tenant_id = tenant_id
        self._entries: list[AuditEntry] = []

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    @property
    def length(self) -> int:
        return len(self._entries)

    @property
    def last_hash(self) -> str:
        if not self._entries:
            return GENESIS_HASH
        return self._entries[-1].entry_hash

    def append(
        self,
        event_type: str,
        status_from: str | None = None,
        status_to: str | None = None,
        actor: str | None = None,
        details: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> AuditEntry:
        """Append a new event to the chain."""
        ts = (timestamp or datetime.utcnow()).isoformat()
        seq = len(self._entries)
        prev_hash = self.last_hash
        event_details = details or {}

        entry_hash = _compute_hash(
            document_id=self.document_id,
            tenant_id=self.tenant_id,
            sequence_number=seq,
            event_type=event_type,
            status_from=status_from,
            status_to=status_to,
            actor=actor,
            timestamp=ts,
            details=event_details,
            previous_hash=prev_hash,
        )

        entry = AuditEntry(
            document_id=self.document_id,
            tenant_id=self.tenant_id,
            sequence_number=seq,
            event_type=event_type,
            status_from=status_from,
            status_to=status_to,
            actor=actor,
            timestamp=ts,
            details=event_details,
            previous_hash=prev_hash,
            entry_hash=entry_hash,
        )

        self._entries.append(entry)

        logger.info(
            "audit_chain_append",
            extra={
                "document_id": self.document_id,
                "sequence": seq,
                "event_type": event_type,
                "hash": entry_hash[:16] + "...",
            },
        )

        return entry

    def verify(self) -> bool:
        """Verify the entire chain integrity.

        Returns True if all hashes are valid and properly chained.
        """
        if not self._entries:
            return True

        for i, entry in enumerate(self._entries):
            expected_prev = GENESIS_HASH if i == 0 else self._entries[i - 1].entry_hash

            if entry.previous_hash != expected_prev:
                logger.error(
                    "audit_chain_broken",
                    extra={
                        "document_id": self.document_id,
                        "sequence": i,
                        "expected_prev": expected_prev[:16],
                        "actual_prev": entry.previous_hash[:16],
                    },
                )
                return False

            recomputed = _compute_hash(
                document_id=entry.document_id,
                tenant_id=entry.tenant_id,
                sequence_number=entry.sequence_number,
                event_type=entry.event_type,
                status_from=entry.status_from,
                status_to=entry.status_to,
                actor=entry.actor,
                timestamp=entry.timestamp,
                details=entry.details,
                previous_hash=entry.previous_hash,
            )

            if recomputed != entry.entry_hash:
                logger.error(
                    "audit_chain_tampered",
                    extra={
                        "document_id": self.document_id,
                        "sequence": i,
                        "expected_hash": recomputed[:16],
                        "actual_hash": entry.entry_hash[:16],
                    },
                )
                return False

        return True

    @classmethod
    def from_entries(
        cls, document_id: str, tenant_id: str, entries: list[dict[str, Any]]
    ) -> "AuditChain":
        """Reconstruct chain from persisted entries (e.g., DB load)."""
        chain = cls(document_id=document_id, tenant_id=tenant_id)
        for e in sorted(entries, key=lambda x: x["sequence_number"]):
            chain._entries.append(AuditEntry(**e))
        return chain
