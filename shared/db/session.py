from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # TODO: Für Entwicklung anpassen, z.B.:
    # "postgresql+psycopg://user:password@localhost:5432/ki_rechnungsverarbeitung"
    "postgresql+psycopg://user:password@localhost:5432/ki_rechnungsverarbeitung",
)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
