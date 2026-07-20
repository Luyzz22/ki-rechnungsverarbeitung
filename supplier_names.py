#!/usr/bin/env python3
"""Lieferantennamen – Bereinigung + kanonisches Gruppieren.

Reine, abhängigkeitsfreie Funktionen, die sowohl im **Schreibpfad** (Extraktion:
kein Dateiname/Müll als Aussteller speichern) als auch im **Lesepfad**
(``supplier_overview``: Schreibweisen-Varianten zu EINEM Lieferanten
zusammenführen) genutzt werden. Dadurch werden Neu-Uploads sauber gespeichert
UND Bestandsdaten in der Übersicht konsolidiert – ohne Reprocessing.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional, Tuple

UNKNOWN = "Unbekannt"

# Dateiendungen, die als Aussteller ein Extraktions-Artefakt sind
_FILE_EXT = re.compile(
    r"\.(pdf|png|jpe?g|tiff?|gif|bmp|webp|xml|docx?|xlsx?|pptx?|csv|txt|zip|eml|msg)$",
    re.IGNORECASE,
)

# Platzhalter/Nicht-Lieferanten (case-insensitiv, nach Trim)
_PLACEHOLDERS = {
    "", "unbekannt", "unknown", "n/a", "na", "k.a.", "ka", "-", "--", "null",
    "none", "nan", "test", "testrechnung", "rechnung", "invoice", "beleg",
    "dokument", "document", "scan", "unbenannt", "untitled",
}


def sanitize_supplier(name: Optional[str]) -> Optional[str]:
    """Bereinigt einen Aussteller-Namen. Gibt ``None`` zurück, wenn der Wert
    offensichtlich KEIN Lieferant ist (Dateiname, Platzhalter, reine Zahl,
    dateiname-artig mit vielen Unterstrichen und ohne Leerzeichen)."""
    if name is None:
        return None
    s = str(name).strip()
    if not s:
        return None
    # Dateiname (mit Endung) -> kein Lieferant
    if _FILE_EXT.search(s):
        return None
    low = s.lower()
    if low in _PLACEHOLDERS:
        return None
    # reine Zahl / Nummer
    if re.fullmatch(r"[\d.,/\-\s]+", s):
        return None
    # dateiname-artig ohne Endung: keine Leerzeichen + mehrere Unterstriche
    # (z. B. "Testrechnung_Mueller_Brandt_2026-001")
    if " " not in s and s.count("_") >= 2:
        return None
    return s


def canonical_key(name: Optional[str]) -> str:
    """Kanonischer Gruppierungs-Schlüssel: case-, interpunktions- und
    whitespace-unabhängig. Beispiele, die denselben Schlüssel ergeben:
    ``'SBS DEUTSCHLAND GMBH & CO.KG'`` / ``'SBS Deutschland GmbH & Co.KG'``;
    ``'AS-Technik / Dipl. Inf. A. Schenk'`` / ``'AS-Technik * Dipl. Inf. A.Schenk'``.
    """
    s = (name or "").lower()
    # alles Nicht-Alphanumerische (inkl. Umlaute/ß erhalten) -> einzelnes Space
    s = re.sub(r"[^0-9a-zäöüß]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def best_display_name(names_with_counts: Iterable[Tuple[str, int]]) -> str:
    """Wählt aus mehreren Original-Schreibweisen einer Gruppe die 'sauberste'.

    Priorität: gemischte Groß-/Kleinschreibung (statt ``ALLCAPS``/``kleinschrift``)
    → häufigste → längste → alphabetisch kleinste (deterministisch).
    ``names_with_counts`` ist ein Iterable aus ``(name, count)``-Tupeln.
    """
    best: Optional[str] = None
    best_key: Optional[Tuple[int, int, int]] = None
    for name, count in names_with_counts:
        mixed = 1 if (any(c.islower() for c in name) and any(c.isupper() for c in name)) else 0
        key = (mixed, int(count), len(name))
        # Höheres key gewinnt; bei Gleichstand die alphabetisch kleinere Schreibweise.
        if best_key is None or key > best_key or (key == best_key and name < best):
            best, best_key = name, key
    return best if best is not None else UNKNOWN
