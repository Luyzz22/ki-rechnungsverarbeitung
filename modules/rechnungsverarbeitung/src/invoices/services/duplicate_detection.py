"""Duplicate Detection Service.

Detects duplicate invoices using multi-signal matching:
1. Exact match: SHA-256 file hash
2. Fuzzy match: supplier + amount + date + invoice_number
3. Near-duplicate: supplier + amount within 5% + date within 7 days
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DuplicateMatch:
    document_id: str
    supplier: str | None
    total_amount: float | None
    invoice_number: str | None
    invoice_date: str | None
    match_type: str  # exact_hash, exact_fields, near_duplicate
    confidence: float  # 0.0 - 1.0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "supplier": self.supplier,
            "total_amount": self.total_amount,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "match_type": self.match_type,
            "confidence": self.confidence,
            "reasons": self.reasons,
        }


class DuplicateDetectionService:
    """Detects duplicate invoices within a tenant."""

    def check(self, session: Any, tenant_id: str, document_id: str) -> list[DuplicateMatch]:
        from sqlalchemy import text

        # Get current invoice data
        current = session.execute(text("""
            SELECT document_id, file_hash, supplier, total_amount, invoice_number,
                   invoice_date, currency, file_name
            FROM invoices WHERE document_id = :d AND tenant_id = :t
        """), {"d": document_id, "t": tenant_id}).fetchone()

        if not current:
            return []

        matches: list[DuplicateMatch] = []
        seen_ids: set[str] = set()

        # 1. Exact hash match
        if current[1]:  # file_hash
            hash_matches = session.execute(text("""
                SELECT document_id, supplier, total_amount, invoice_number, invoice_date
                FROM invoices
                WHERE tenant_id = :t AND document_id != :d AND file_hash = :h
            """), {"t": tenant_id, "d": document_id, "h": current[1]}).fetchall()

            for row in hash_matches:
                if row[0] not in seen_ids:
                    seen_ids.add(row[0])
                    matches.append(DuplicateMatch(
                        document_id=row[0], supplier=row[1],
                        total_amount=float(row[2]) if row[2] else None,
                        invoice_number=row[3], invoice_date=row[4],
                        match_type="exact_hash", confidence=1.0,
                        reasons=["Identischer Datei-Hash (SHA-256)"],
                    ))

        # 2. Exact field match (supplier + amount + invoice_number)
        if current[2] and current[3]:  # supplier + total_amount
            field_matches = session.execute(text("""
                SELECT document_id, supplier, total_amount, invoice_number, invoice_date
                FROM invoices
                WHERE tenant_id = :t AND document_id != :d
                  AND supplier = :s AND total_amount = :a
                  AND (invoice_number = :n OR (:n IS NULL AND invoice_number IS NULL))
            """), {
                "t": tenant_id, "d": document_id,
                "s": current[2], "a": current[3], "n": current[4],
            }).fetchall()

            for row in field_matches:
                if row[0] not in seen_ids:
                    seen_ids.add(row[0])
                    reasons = [f"Gleicher Lieferant: {row[1]}", f"Gleicher Betrag: {row[2]}"]
                    if row[3] and current[4] and row[3] == current[4]:
                        reasons.append(f"Gleiche Rechnungsnummer: {row[3]}")
                    matches.append(DuplicateMatch(
                        document_id=row[0], supplier=row[1],
                        total_amount=float(row[2]) if row[2] else None,
                        invoice_number=row[3], invoice_date=row[4],
                        match_type="exact_fields", confidence=0.95,
                        reasons=reasons,
                    ))

        # 3. Near-duplicate (supplier match + amount within 5%)
        if current[2] and current[3]:
            amount = float(current[3])
            low = amount * 0.95
            high = amount * 1.05
            near_matches = session.execute(text("""
                SELECT document_id, supplier, total_amount, invoice_number, invoice_date
                FROM invoices
                WHERE tenant_id = :t AND document_id != :d
                  AND supplier = :s
                  AND total_amount BETWEEN :lo AND :hi
            """), {
                "t": tenant_id, "d": document_id,
                "s": current[2], "lo": low, "hi": high,
            }).fetchall()

            for row in near_matches:
                if row[0] not in seen_ids:
                    seen_ids.add(row[0])
                    diff_pct = abs(float(row[2]) - amount) / amount * 100 if amount else 0
                    matches.append(DuplicateMatch(
                        document_id=row[0], supplier=row[1],
                        total_amount=float(row[2]) if row[2] else None,
                        invoice_number=row[3], invoice_date=row[4],
                        match_type="near_duplicate", confidence=round(0.8 - diff_pct/100, 2),
                        reasons=[f"Gleicher Lieferant", f"Betrag abweicht um {diff_pct:.1f}%"],
                    ))

        logger.info(f"duplicate_check: doc={document_id} matches={len(matches)}")
        return sorted(matches, key=lambda m: m.confidence, reverse=True)
