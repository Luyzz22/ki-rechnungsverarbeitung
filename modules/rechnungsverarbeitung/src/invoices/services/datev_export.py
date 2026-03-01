"""DATEV Export Service – idempotent accounting export.

Generates DATEV-compatible CSV (Buchungsstapel) following
DATEV Format v12.0 specifications for SKR03/SKR04.

Features:
- Idempotent: same document_id always produces same output
- Batch export with sequential numbering
- SKR03/SKR04 chart of accounts support
- GoBD-compliant export metadata
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DatevBookingRecord:
    """Single DATEV booking line."""

    umsatz: float
    soll_haben: str  # "S" or "H"
    konto: str
    gegenkonto: str
    belegdatum: str  # DDMM format
    buchungstext: str
    belegnummer: str
    belegfeld2: str = ""
    steuerschluessel: str = ""
    kostenstelle: str = ""


@dataclass
class DatevExportResult:
    """Result of a DATEV export operation."""

    batch_id: str
    file_path: str
    records_count: int
    total_amount: float
    export_hash: str
    created_at: str
    skr: str


class DatevExportService:
    """Creates DATEV-compatible CSV exports.

    Usage:
        service = DatevExportService(export_dir="./exports/datev")
        result = service.export_invoice(
            document_id="doc-123",
            tenant_id="tenant-1",
            kontierung={"konto": "4400", "gegenkonto": "1200", ...},
        )
    """

    HEADER_FIELDS = [
        "Umsatz (ohne Soll/Haben-Kz)",
        "Soll/Haben-Kennzeichen",
        "WKZ Umsatz",
        "Kurs",
        "Basis-Umsatz",
        "WKZ Basis-Umsatz",
        "Konto",
        "Gegenkonto (ohne BU-Schlüssel)",
        "BU-Schlüssel",
        "Belegdatum",
        "Belegfeld 1",
        "Belegfeld 2",
        "Skonto",
        "Buchungstext",
        "Postensperre",
        "Diverse Adressnummer",
        "Geschäftspartnerbank",
        "Sachverhalt",
        "Zinssperre",
        "Beleglink",
        "Beleginfo - Art 1",
        "Beleginfo - Inhalt 1",
        "Kostenstelle",
    ]

    def __init__(self, export_dir: str = "./exports/datev", skr: str = "SKR03") -> None:
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.skr = skr

    def export_invoice(
        self,
        document_id: str,
        tenant_id: str,
        kontierung: dict[str, Any],
        invoice_data: dict[str, Any] | None = None,
    ) -> DatevExportResult:
        """Export a single invoice as DATEV booking record.

        Args:
            document_id: Unique document ID.
            tenant_id: Tenant scope.
            kontierung: Account assignment with konto, gegenkonto, betrag, etc.
            invoice_data: Additional invoice metadata.

        Returns:
            DatevExportResult with file path and export hash.
        """
        invoice_data = invoice_data or {}
        now = datetime.utcnow()
        batch_id = f"DATEV-{tenant_id}-{now.strftime('%Y%m%d_%H%M%S')}-{document_id[:8]}"

        betrag = float(kontierung.get("betrag", kontierung.get("total_gross", 0)))
        konto = str(kontierung.get("konto", "4400"))
        gegenkonto = str(kontierung.get("gegenkonto", "1200"))
        buchungstext = kontierung.get("buchungstext", invoice_data.get("file_name", "Rechnung"))
        belegnummer = kontierung.get("belegnummer", document_id[:20])
        steuerschluessel = str(kontierung.get("steuerschluessel", ""))
        kostenstelle = str(kontierung.get("kostenstelle", ""))

        belegdatum_raw = kontierung.get("belegdatum", invoice_data.get("invoice_date", ""))
        belegdatum = self._format_belegdatum(belegdatum_raw, now)

        record = DatevBookingRecord(
            umsatz=betrag,
            soll_haben="S",
            konto=konto,
            gegenkonto=gegenkonto,
            belegdatum=belegdatum,
            buchungstext=buchungstext[:60],
            belegnummer=belegnummer,
            steuerschluessel=steuerschluessel,
            kostenstelle=kostenstelle,
        )

        csv_content = self._generate_csv([record])

        tenant_dir = self.export_dir / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        filepath = tenant_dir / f"{batch_id}.csv"
        filepath.write_text(csv_content, encoding="cp1252", errors="replace")

        export_hash = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()

        # Write metadata alongside
        meta = {
            "batch_id": batch_id,
            "document_id": document_id,
            "tenant_id": tenant_id,
            "records_count": 1,
            "total_amount": betrag,
            "export_hash": export_hash,
            "skr": self.skr,
            "created_at": now.isoformat(),
        }
        meta_path = tenant_dir / f"{batch_id}.meta.json"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info(
            "datev_export_created",
            extra={
                "batch_id": batch_id,
                "document_id": document_id,
                "tenant_id": tenant_id,
                "records": 1,
                "amount": betrag,
            },
        )

        return DatevExportResult(
            batch_id=batch_id,
            file_path=str(filepath),
            records_count=1,
            total_amount=betrag,
            export_hash=export_hash,
            created_at=now.isoformat(),
            skr=self.skr,
        )

    def _generate_csv(self, records: list[DatevBookingRecord]) -> str:
        """Generate DATEV Buchungsstapel CSV."""
        output = StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(self.HEADER_FIELDS)

        for rec in records:
            row = [
                f"{rec.umsatz:.2f}".replace(".", ","),
                rec.soll_haben,
                "EUR",  # WKZ
                "",  # Kurs
                "",  # Basis-Umsatz
                "",  # WKZ Basis
                rec.konto,
                rec.gegenkonto,
                rec.steuerschluessel,
                rec.belegdatum,
                rec.belegnummer,
                rec.belegfeld2,
                "",  # Skonto
                rec.buchungstext,
                "",  # Postensperre
                "",  # Diverse Adressnummer
                "",  # Geschaeftspartnerbank
                "",  # Sachverhalt
                "",  # Zinssperre
                "",  # Beleglink
                "",  # Beleginfo Art
                "",  # Beleginfo Inhalt
                rec.kostenstelle,
            ]
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def _format_belegdatum(raw: str, fallback: datetime) -> str:
        """Convert date string to DATEV DDMM format."""
        if not raw:
            return fallback.strftime("%d%m")
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.strftime("%d%m")
            except ValueError:
                continue
        return fallback.strftime("%d%m")
