"""Unit-Tests für die Lieferantennamen-Bereinigung/-Konsolidierung (Enterprise)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from supplier_names import (  # noqa: E402
    UNKNOWN,
    best_display_name,
    canonical_key,
    sanitize_supplier,
)


@pytest.mark.parametrize("raw", [
    "test.pdf", "Rechnung.PDF", "scan_2026.png", "beleg.jpeg", "export.xml",
    "Testrechnung_Mueller_Brandt_2026-001.pdf",
    "Testrechnung_Mueller_Brandt_2026-001",   # dateiname-artig, ohne Endung
    "Unbekannt", "unknown", "n/a", "-", "null", "none", "test", "  ",
    "12345", "2026-001", None,
])
def test_sanitize_drops_non_supplier(raw):
    assert sanitize_supplier(raw) is None


@pytest.mark.parametrize("raw,expected", [
    ("Böttcher AG", "Böttcher AG"),
    ("  SBS Deutschland GmbH & Co.KG  ", "SBS Deutschland GmbH & Co.KG"),
    ("Qonto (Olinda SAS)", "Qonto (Olinda SAS)"),
    ("Anthropic, PBC", "Anthropic, PBC"),
])
def test_sanitize_keeps_real_names(raw, expected):
    assert sanitize_supplier(raw) == expected


def test_canonical_merges_case_and_punctuation():
    assert canonical_key("SBS DEUTSCHLAND GMBH & CO.KG") == canonical_key("SBS Deutschland GmbH & Co.KG")
    assert canonical_key("AS-Technik / Dipl. Inf. A. Schenk") == canonical_key("AS-Technik * Dipl. Inf. A.Schenk")
    # Umlaute bleiben unterscheidend/erhalten
    assert canonical_key("Müller & Brandt Maschinenbau GmbH") == canonical_key("MÜLLER  &  BRANDT   Maschinenbau GmbH")


def test_canonical_distinguishes_different_suppliers():
    assert canonical_key("Schenk Digital Solutions GmbH") != canonical_key("Müller & Brandt Maschinenbau GmbH")


def test_best_display_prefers_mixed_case_then_frequency():
    # gemischte Groß-/Kleinschreibung schlägt ALLCAPS, auch bei geringerer Häufigkeit
    assert best_display_name([
        ("SBS DEUTSCHLAND GMBH & CO.KG", 2),
        ("SBS Deutschland GmbH & Co.KG", 1),
    ]) == "SBS Deutschland GmbH & Co.KG"
    # bei gleicher „Sauberkeit" gewinnt die häufigere, dann längere, dann alphabetisch
    assert best_display_name([("Acme", 1), ("acme", 5), ("ACME", 5)]) == "Acme"


def test_best_display_empty_is_unknown():
    assert best_display_name([]) == UNKNOWN
