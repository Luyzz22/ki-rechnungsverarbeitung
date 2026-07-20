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


def test_canonical_preserves_non_latin_unicode():
    """P1: nicht-lateinische Schriften/Akzente dürfen NICHT auf einen leeren
    Schlüssel kollabieren (sonst würden verschiedene Lieferanten zusammengeführt)."""
    assert canonical_key("東京商事") == "東京商事"
    assert canonical_key("北京贸易") == "北京贸易"
    assert canonical_key("東京商事") != canonical_key("北京贸易")
    assert canonical_key("東京商事") != ""
    # akzentuierte lateinische Namen bleiben unterscheidbar
    assert canonical_key("Électricité SA") != canonical_key("Àlectricité SA")
    assert canonical_key("Café Küper") != ""


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


def test_get_suppliers_handles_hybridrow_rows(monkeypatch):
    """Prod-Regression: unter PostgreSQL liefert _fetch_invoices HybridRow-Objekte
    (kein item-assignment). get_suppliers darf die Row NICHT mutieren – sonst
    'HybridRow' object does not support item assignment (500)."""
    import supplier_overview as so
    from db_compat import HybridRow

    cols = ["id", "supplier", "amount", "invoice_date", "created_at"]
    rows = [
        HybridRow(cols, [1, "SBS Deutschland GmbH & Co.KG", 1880.20, "2025-09-29", "2025-09-29T10:00:00"]),
        HybridRow(cols, [2, "SBS DEUTSCHLAND GMBH & CO.KG", 1880.20, "2025-09-29", "2025-09-30T10:00:00"]),
        HybridRow(cols, [3, "test.pdf", 0.0, "2026-06-09", "2026-06-09T10:00:00"]),
    ]
    monkeypatch.setattr(so, "_fetch_invoices", lambda tid: rows)

    suppliers = so.get_suppliers(1, sort_by="volumen")
    names = [s["name"] for s in suppliers]
    # Varianten gemergt (saubere Schreibweise), Dateiname → Unbekannt
    assert "SBS Deutschland GmbH & Co.KG" in names
    assert "test.pdf" not in names and "Unbekannt" in names
    sbs = next(s for s in suppliers if s["name"].lower().startswith("sbs"))
    assert sbs["count"] == 2 and sbs["total"] == 3760.40
