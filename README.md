# 🤖 SBS KI-Rechnungsverarbeitung

![Tests](https://github.com/Luyzz22/ki-rechnungsverarbeitung/actions/workflows/tests.yml/badge.svg)

> **Automatische Rechnungsverarbeitung mit Multi-Model KI für den deutschen Mittelstand**

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()
[![Status](https://img.shields.io/badge/Status-Production-success.svg)]()

---

## 📋 Übersicht

Eine KI-gestützte Lösung zur automatischen Verarbeitung von Eingangsrechnungen. Das System kombiniert mehrere KI-Modelle für zuverlässige Extraktion und liefert DATEV-kompatible Exporte für Steuerberater und mittelständische Unternehmen im DACH-Raum.

### 🎯 Kernfunktionen

- ✅ **Multi-Model KI**: Kombination aus GPT-4o und Claude für zuverlässige Extraktion
- ✅ **DATEV-Export**: Nahtlose Integration für Steuerberater und Buchhaltung
- ✅ **Dubletten-Erkennung**: Automatische Prüfung auf doppelte Rechnungen
- ✅ **Plausibilitätsprüfung**: Validierung von Beträgen und Pflichtangaben
- ✅ **Batch-Processing**: Mehrere Rechnungen parallel verarbeiten (8 Threads)
- ✅ **Flexible Exporte**: Excel, CSV und DATEV-Format
- ✅ **Email-Benachrichtigung**: Automatische Benachrichtigung bei Fertigstellung
- ✅ **DSGVO-orientierte Verarbeitung**: Hosting in Deutschland (EU)

---

## 🏗️ Projektstruktur
```
/var/www/invoice-app/
├── web/
│   ├── app.py                 # FastAPI Hauptanwendung
│   ├── templates/             # Jinja2 HTML-Templates (20 Seiten)
│   │   └── _archive/          # Archivierte Template-Backups
│   ├── static/
│   │   ├── css/
│   │   │   ├── design-tokens.css  # Design-System Variablen
│   │   │   ├── components.css     # UI-Komponenten
│   │   │   └── main.css           # Haupt-Stylesheet
│   │   ├── js/main.js         # Frontend JavaScript
│   │   ├── landing/           # Landing Pages (13 Seiten)
│   │   │   └── _archive/      # Archivierte Backups
│   │   └── preise/            # Preise-Seite
│   ├── sbshomepage/           # Corporate Pages (10 Seiten)
│   │   └── _archive/          # Archivierte Backups
│   └── _archive/              # Archivierte Web-Backups
│
├── database.py                # SQLite Datenbankfunktionen
├── invoice_core.py            # KI-Verarbeitung
├── duplicate_detection.py     # Dubletten-Erkennung
├── plausibility.py            # Plausibilitätsprüfung
├── datev_exporter.py          # DATEV-Export
├── export.py                  # Excel/CSV Export
├── cost_tracker.py            # Kosten-Tracking
│
├── data/
│   ├── invoices.db            # Rechnungsdaten
│   ├── users.db               # Benutzerdaten
│   └── analytics.db           # Analytics-Daten
│
└── _archive/                  # Archivierte Python-Backups
```

---

## 🎨 Design-System

Das Projekt verwendet ein konsistentes Design-System (seit v4.0).

### CSS-Variablen (design-tokens.css)
```css
/* Primärfarben */
--color-primary: #003856;      /* SBS Blau */
--color-accent: #FFB900;       /* SBS Gelb */

/* Semantische Farben */
--color-success: #10B981;
--color-warning: #F59E0B;
--color-error: #EF4444;
```

### UI-Komponenten (components.css)

- **Buttons**: `.btn`, `.btn-primary`, `.btn-accent`, `.btn-secondary`
- **Cards**: `.card`, `.stat-card`, `.export-card`
- **Forms**: `.form-input`, `.form-label`, `.form-error`
- **Tables**: `.data-table`, `.table-responsive`
- **Badges**: `.badge`, `.badge-success`, `.badge-warning`
- **Upload**: `.upload-dropzone`, `.dropzone--active`

---

## 📞 Kontakt

**SBS Deutschland GmbH & Co. KG**

- 📧 info@sbsdeutschland.com
- 📞 +49 6201 80 6109
- 🌐 www.sbsdeutschland.com
- 📍 In der Dell 19, 69469 Weinheim

---

## 📄 Lizenz

Proprietary - © 2025 SBS Deutschland GmbH & Co. KG

---

**Made with ❤️ in Weinheim**
