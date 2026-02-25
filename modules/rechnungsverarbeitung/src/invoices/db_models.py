from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import Base

class InvoiceEvent(Base):
    __tablename__ = "invoice_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    event_type: Mapped[str] = mapped_column(String, nullable=False)
    status_from: Mapped[str | None] = mapped_column(String, nullable=True)
    status_to: Mapped[str | None] = mapped_column(String, nullable=True)

    actor: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Freies JSON-Feld für zusätzliche Infos (Scores, Source-System, etc.)
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False, default="invoice")
    file_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    source_system: Mapped[str] = mapped_column(String(128), nullable=False, default="ki-rechnungsverarbeitung")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="uploaded")
