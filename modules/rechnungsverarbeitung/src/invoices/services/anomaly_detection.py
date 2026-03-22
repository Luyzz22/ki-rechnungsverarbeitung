"""Anomaly Detection Service.

Uses statistical analysis + optional Gemini AI to detect:
1. Unusual amounts (>2 std dev from supplier average)
2. New/unknown suppliers
3. Frequency anomalies (too many invoices in short period)
4. Round-number patterns (potential fraud indicator)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Anomaly:
    anomaly_type: str
    severity: str  # low, medium, high, critical
    description: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.anomaly_type,
            "severity": self.severity,
            "description": self.description,
            "details": self.details,
        }


class AnomalyDetectionService:

    def analyze(self, session: Any, tenant_id: str, document_id: str) -> list[Anomaly]:
        from sqlalchemy import text
        anomalies: list[Anomaly] = []

        current = session.execute(text("""
            SELECT document_id, supplier, total_amount, invoice_number, invoice_date, uploaded_at
            FROM invoices WHERE document_id = :d AND tenant_id = :t
        """), {"d": document_id, "t": tenant_id}).fetchone()

        if not current or not current[2]:
            return anomalies

        supplier = current[1] or "Unbekannt"
        amount = float(current[2])

        # 1. Amount anomaly — compare to supplier history
        stats = session.execute(text("""
            SELECT AVG(total_amount), STDDEV(total_amount), COUNT(*), MAX(total_amount), MIN(total_amount)
            FROM invoices
            WHERE tenant_id = :t AND supplier = :s AND total_amount IS NOT NULL AND document_id != :d
        """), {"t": tenant_id, "s": supplier, "d": document_id}).fetchone()

        if stats and stats[0] and stats[2] >= 2:
            avg_amount = float(stats[0])
            stddev = float(stats[1]) if stats[1] else 0
            count = stats[2]

            if stddev > 0 and abs(amount - avg_amount) > 2 * stddev:
                deviation = abs(amount - avg_amount) / stddev
                anomalies.append(Anomaly(
                    anomaly_type="unusual_amount",
                    severity="high" if deviation > 3 else "medium",
                    description=f"Betrag {amount:.2f}€ weicht stark vom Durchschnitt ab ({avg_amount:.2f}€ ± {stddev:.2f}€)",
                    details={"amount": amount, "avg": avg_amount, "stddev": stddev, "deviation_sigma": round(deviation, 1), "history_count": count},
                ))

            if amount > float(stats[3]) * 1.5:
                anomalies.append(Anomaly(
                    anomaly_type="amount_spike",
                    severity="high",
                    description=f"Betrag 50% über bisherigem Maximum ({float(stats[3]):.2f}€)",
                    details={"amount": amount, "previous_max": float(stats[3])},
                ))

        # 2. New supplier check
        supplier_count = session.execute(text("""
            SELECT COUNT(*) FROM invoices
            WHERE tenant_id = :t AND supplier = :s AND document_id != :d
        """), {"t": tenant_id, "s": supplier, "d": document_id}).scalar() or 0

        if supplier_count == 0 and amount > 1000:
            anomalies.append(Anomaly(
                anomaly_type="new_supplier",
                severity="medium",
                description=f"Neuer Lieferant '{supplier}' mit Betrag über 1.000€",
                details={"supplier": supplier, "amount": amount, "first_invoice": True},
            ))

        # 3. Round number check
        if amount > 100 and amount == int(amount) and amount % 100 == 0:
            anomalies.append(Anomaly(
                anomaly_type="round_number",
                severity="low",
                description=f"Exakter Rundbetrag ({amount:.0f}€) — ggf. Schätzung statt echter Rechnung",
                details={"amount": amount},
            ))

        # 4. Frequency check (more than 3 from same supplier in 7 days)
        if current[5]:  # uploaded_at
            freq = session.execute(text("""
                SELECT COUNT(*) FROM invoices
                WHERE tenant_id = :t AND supplier = :s AND document_id != :d
                  AND uploaded_at > :d_date - INTERVAL '7 days'
                  AND uploaded_at < :d_date + INTERVAL '7 days'
            """), {"t": tenant_id, "s": supplier, "d": document_id, "d_date": current[5]}).scalar() or 0

            if freq >= 3:
                anomalies.append(Anomaly(
                    anomaly_type="high_frequency",
                    severity="medium",
                    description=f"{freq} Rechnungen von '{supplier}' innerhalb von 7 Tagen",
                    details={"supplier": supplier, "count_7d": freq},
                ))

        logger.info(f"anomaly_check: doc={document_id} anomalies={len(anomalies)}")
        return anomalies
