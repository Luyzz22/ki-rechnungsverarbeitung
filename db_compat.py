#!/usr/bin/env python3
"""
SBS Deutschland – DB-Kompatibilitätsschicht (SQLite ↔ PostgreSQL/Neon)

Aktiv NUR wenn ``DATABASE_URL`` gesetzt ist – sonst bleibt alles bei SQLite
(keine Verhaltensänderung für die bestehende Anwendung).

Die Schicht erlaubt dem Bestandscode, der ``?``-Platzhalter und ein
``sqlite3.Row``-ähnliches Zeilenverhalten erwartet, weitgehend unverändert auf
PostgreSQL zu laufen:

- ``translate_placeholders``: ``?`` → ``%s`` (außerhalb String-Literalen),
  literale ``%`` werden für psycopg zu ``%%`` verdoppelt.
- ``HybridRow``: Zugriff per Index UND per Spaltenname (wie ``sqlite3.Row``),
  ``dict(row)`` funktioniert.
- ``PgConnection``/``PgCursor``: dünner Wrapper; ``lastrowid`` wird – wo möglich –
  über ``RETURNING id`` emuliert; ``PRAGMA`` wird zu einem No-Op.

Bekannte Grenzen (siehe docs/POSTGRES_MIGRATION.md): SQLite-spezifische
Funktionen wie ``strftime``/``substr``/``datetime('now')`` sowie DDL
(``AUTOINCREMENT``, ``PRAGMA table_info``) müssen je Query/Tabelle portiert
werden – dafür ist eine echte Neon-Instanz zum Verifizieren nötig.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, List, Optional, Sequence

logger = logging.getLogger(__name__)


def database_url() -> Optional[str]:
    url = os.getenv("DATABASE_URL")
    return url.strip() if url else None


def is_postgres() -> bool:
    """True, wenn auf PostgreSQL gefahren werden soll (DATABASE_URL gesetzt)."""
    url = database_url()
    return bool(url) and url.startswith(("postgres://", "postgresql://"))


# ---------------------------------------------------------------------------
# DDL-Übersetzung  (SQLite-CREATE-Syntax → PostgreSQL)
# ---------------------------------------------------------------------------
# SQLite: `id INTEGER PRIMARY KEY AUTOINCREMENT`  →  PostgreSQL: `id SERIAL PRIMARY KEY`
# Case-insensitiv und tolerant gegenüber Mehrfach-Whitespace/Zeilenumbrüchen.
_AUTOINCREMENT_RE = re.compile(
    r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
    re.IGNORECASE,
)
# Defensive: ein evtl. allein stehendes AUTOINCREMENT (PostgreSQL kennt es nicht).
_BARE_AUTOINCREMENT_RE = re.compile(r"\s+AUTOINCREMENT\b", re.IGNORECASE)

# `PRAGMA table_info(<tabelle>)` (SQLite) → information_schema-Abfrage (PostgreSQL).
_PRAGMA_TABLE_INFO_RE = re.compile(
    r"^\s*PRAGMA\s+table_info\s*\(\s*[\"'`\[]?(?P<table>\w+)[\"'`\]]?\s*\)\s*;?\s*$",
    re.IGNORECASE,
)
# Spaltenreihenfolge identisch zu SQLite (cid, name, type, notnull, dflt_value, pk),
# damit Bestandscode wie ``col[1]`` (Spaltenname) unverändert funktioniert.
# Wichtig: column_name/data_type sind PostgreSQL-Domains über ``name`` und
# werden von psycopg sonst als bytes geliefert → explizit nach ``text`` casten,
# damit Bestandscode (``'is_admin' in cols``) als str vergleicht.
_PRAGMA_TABLE_INFO_SQL = (
    "SELECT (ordinal_position - 1) AS cid, "
    "column_name::text AS name, "
    "data_type::text AS type, "
    "CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull, "
    "column_default::text AS dflt_value, "
    "0 AS pk "
    "FROM information_schema.columns "
    "WHERE table_name = %s AND table_schema = 'public' "
    "ORDER BY ordinal_position"
)


def translate_ddl(sql: str) -> str:
    """Übersetzt SQLite-DDL-Eigenheiten nach PostgreSQL.

    Aktuell abgedeckt:
    - ``INTEGER PRIMARY KEY AUTOINCREMENT`` → ``SERIAL PRIMARY KEY``
      (PostgreSQL kennt kein ``AUTOINCREMENT``; ``SERIAL`` erzeugt die
      äquivalente Auto-Increment-Sequenz für die ``id``-Spalte).

    Andere Anweisungen bleiben unverändert; insbesondere wird nichts
    übersetzt, wenn keines der Muster vorkommt (kein Risiko für DML).
    """
    translated = _AUTOINCREMENT_RE.sub("SERIAL PRIMARY KEY", sql)
    # Falls AUTOINCREMENT in einer anderen Konstellation auftaucht: entfernen,
    # damit PostgreSQL nicht am unbekannten Schlüsselwort scheitert.
    if "AUTOINCREMENT" in translated.upper():
        translated = _BARE_AUTOINCREMENT_RE.sub("", translated)
    return translated


# ---------------------------------------------------------------------------
# Platzhalter-Übersetzung  ?  →  %s   (und  %  →  %%)
# ---------------------------------------------------------------------------
def translate_placeholders(sql: str) -> str:
    """Übersetzt SQLite-``?``-Platzhalter nach psycopg-``%s``.

    - ``?`` außerhalb einfacher String-Literale wird zu ``%s``.
    - Jedes ``%`` wird zu ``%%`` verdoppelt (psycopg interpretiert ``%`` auf
      Query-String-Ebene – literale Prozentzeichen, z. B. in LIKE-Mustern,
      müssen escaped werden).
    """
    out: List[str] = []
    in_string = False
    quote = ""
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if in_string:
            out.append(ch)
            if ch == quote:
                # verdoppeltes Quote = Escape innerhalb des Strings
                if i + 1 < n and sql[i + 1] == quote:
                    out.append(sql[i + 1])
                    i += 2
                    continue
                in_string = False
            elif ch == "%":
                out[-1] = "%%"
            i += 1
            continue

        if ch in ("'", '"'):
            in_string = True
            quote = ch
            out.append(ch)
        elif ch == "?":
            out.append("%s")
        elif ch == "%":
            out.append("%%")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Zeilen-Objekt mit Index- UND Namenszugriff (wie sqlite3.Row)
# ---------------------------------------------------------------------------
class HybridRow:
    __slots__ = ("_cols", "_vals")

    def __init__(self, cols: Sequence[str], vals: Sequence[Any]):
        self._cols = cols
        self._vals = vals

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._vals[key]
        return self._vals[self._cols.index(key)]

    def keys(self):
        return list(self._cols)

    def __iter__(self):
        return iter(self._vals)

    def __len__(self):
        return len(self._vals)

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, ValueError, IndexError):
            return default


def _hybrid_row_factory(cursor):
    cols = [d[0] for d in (cursor.description or [])]

    def make(values):
        return HybridRow(cols, values)

    return make


# ---------------------------------------------------------------------------
# Connection-/Cursor-Wrapper
# ---------------------------------------------------------------------------
class PgCursor:
    """Dünner Cursor-Wrapper: übersetzt ``?``→``%s`` und emuliert ``lastrowid``."""

    def __init__(self, raw):
        self._cur = raw
        self.lastrowid = None

    # -- Kern --------------------------------------------------------------
    def execute(self, sql: str, params: Sequence[Any] | None = None):
        # `PRAGMA table_info(...)` → echte information_schema-Abfrage, damit
        # nachfolgende fetchall()/col[1]-Zugriffe Spalteninfos liefern.
        m = _PRAGMA_TABLE_INFO_RE.match(sql)
        if m:
            self._cur.execute(_PRAGMA_TABLE_INFO_SQL, [m.group("table")])
            return self

        # Erst DDL (CREATE-Syntax) portieren, dann Platzhalter übersetzen.
        translated = translate_placeholders(translate_ddl(sql))
        stripped = translated.lstrip().lower()

        # Übrige PRAGMA → No-Op (PostgreSQL kennt kein PRAGMA)
        if stripped.startswith("pragma"):
            return self

        # INSERT ohne RETURNING → RETURNING id ergänzen, um lastrowid zu liefern
        emulate_lastrowid = stripped.startswith("insert") and "returning" not in stripped
        try:
            if emulate_lastrowid:
                self._cur.execute(translated.rstrip().rstrip(";") + " RETURNING id", params or [])
                try:
                    row = self._cur.fetchone()
                    self.lastrowid = row[0] if row else None
                except Exception:
                    self.lastrowid = None
            else:
                self._cur.execute(translated, params or [])
        except Exception:
            # Fallback: ohne RETURNING erneut versuchen (z. B. Tabelle ohne id)
            if emulate_lastrowid:
                self._cur.execute(translated, params or [])
                self.lastrowid = None
            else:
                raise
        return self

    def executemany(self, sql: str, seq):
        self._cur.executemany(translate_placeholders(translate_ddl(sql)), seq)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self._cur)

    @property
    def description(self):
        return self._cur.description

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()


class PgConnection:
    """sqlite3-ähnlicher Connection-Wrapper um eine psycopg-Verbindung."""

    def __init__(self, raw):
        self._conn = raw
        # Kompatibilität: Code setzt teils conn.row_factory – wird ignoriert,
        # HybridRow liefert ohnehin Index- und Namenszugriff.
        self.row_factory = None

    def cursor(self):
        return PgCursor(self._conn.cursor())

    def execute(self, sql: str, params: Sequence[Any] | None = None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def connect_postgres() -> PgConnection:
    """Öffnet eine PostgreSQL-Verbindung (psycopg3) mit HybridRow-Factory."""
    import psycopg  # lokal importiert, damit SQLite-Betrieb psycopg nicht braucht

    raw = psycopg.connect(database_url(), row_factory=_hybrid_row_factory)
    return PgConnection(raw)
