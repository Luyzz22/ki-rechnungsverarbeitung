from __future__ import annotations

from shared.db.session import Base, engine
from modules.rechnungsverarbeitung.src.invoices.db_models import Invoice, InvoiceEvent


def main() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()

