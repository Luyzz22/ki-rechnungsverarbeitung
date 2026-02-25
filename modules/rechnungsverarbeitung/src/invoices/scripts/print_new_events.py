from __future__ import annotations

import argparse
from datetime import datetime, timedelta, UTC

from shared.db.session import get_session
from modules.rechnungsverarbeitung.src.invoices.db_models import InvoiceEvent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print invoice events for a given tenant and optional since-minutes filter."
    )
    parser.add_argument("--tenant-id", required=True, help="Tenant-ID (z.B. tenant-a)")
    parser.add_argument(
        "--since-minutes",
        type=int,
        default=60,
        help="Nur Events der letzten X Minuten anzeigen (Default: 60).",
    )
    parser.add_argument(
        "--event-types",
        nargs="*",
        help="Optional: Nur bestimmte Event-Typen filtern (z.B. validation_succeeded booking_succeeded).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cutoff = datetime.now(UTC) - timedelta(minutes=args.since_minutes)

    with get_session() as session:
        query = (
            session.query(InvoiceEvent)
            .filter(
                InvoiceEvent.tenant_id == args.tenant_id,
                InvoiceEvent.created_at >= cutoff,
            )
            .order_by(InvoiceEvent.created_at.asc())
        )

        if args.event_types:
            query = query.filter(InvoiceEvent.event_type.in_(args.event_types))

        events = query.all()

        if not events:
            print(f"[INFO] Keine Events für tenant={args.tenant_id} in den letzten {args.since_minutes} Minuten gefunden.")
            return

        for ev in events:
            print(
                f"[{ev.created_at.isoformat()}] "
                f"tenant={ev.tenant_id} "
                f"doc={ev.document_id} "
                f"type={ev.event_type} "
                f"status={ev.status_from}->{ev.status_to} "
                f"actor={ev.actor}"
            )


if __name__ == "__main__":
    main()
