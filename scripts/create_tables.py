from __future__ import annotations

from src.db import Base, engine
from src.invoices.db_models import Invoice


def main() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
