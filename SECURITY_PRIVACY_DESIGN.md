# Security & Privacy by Design – KI-Rechnungsverarbeitung (SBS-Nexus)

## 1. Ziel
Dieses Modul verarbeitet Eingangsrechnungen für Industrie-KMU im DACH-Raum.
Ziel ist ein Enterprise-fähiges, DSGVO-konformes Design gemäß Art. 25 DSGVO
(Privacy by Design & Default).[web:147][web:230]

## 2. Datenkategorien (hochlevel)
- Rechnungsdaten:
  - Rechnungsnummer, Rechnungsdatum, Beträge, Währung
  - Kreditor/Debitor (Firma, optional Ansprechpartner)
  - Zahlungsbedingungen (Zahlungsziel, Skonto)
  - Steuerinformationen (USt-Nummer, Steuersätze)
  - Bankinformationen (IBAN/BIC), falls im Dokument enthalten[web:211][web:213]
- System-/Nutzungsdaten:
  - Zeitpunkte der Verarbeitung
  - Technischer Benutzer / System-User-ID
  - Mandant / Kunde (Tenant-Kontext)

## 3. Datenschutz-Risiken (Auszug)
- Unbefugter Zugriff auf Finanz-/Bankdaten
- Vermischung von Rechnungsdaten verschiedener Mandanten (fehlende Mandantentrennung)
- Übermäßiges Logging von personenbezogenen / sensiblen Daten (Logs als Neben-Datenbank)[web:196][web:226]
- Unklare Löschfristen für Rechnungs- und Logdaten

## 4. Maßnahmen (Designprinzipien)
- Multi-Tenancy:
  - Jede Rechnung wird einem eindeutigen `tenant_id` zugeordnet.
  - Alle Abfragen und Indizes berücksichtigen `tenant_id` zur logischen Datentrennung.[web:163][web:198]
- Datenminimierung:
  - Nur die für Extraktion, Validierung und Übergabe an nachgelagerte Systeme erforderlichen Felder verarbeiten.
  - Keine IBAN/Adressdaten in Anwendungs-Logs; Verwendung von Hashes/Pseudonymisierung, wo möglich.[web:196][web:217]
- Logging & Audit:
  - Logs enthalten nur technische IDs (tenant_id, document_type, invoice_id_hash, Status, Timestamp).
  - Keine Roh-PDFs oder Vollinhalte in Logs.
  - Definierte Aufbewahrungsfrist für Logs (z.B. 6–12 Monate) mit automatisierter Löschung.[web:196][web:226]
- Zugriffskontrolle:
  - Zugriff nur für authentifizierte Benutzer mit Rollen (z.B. Finance, Admin).
  - Perspektivisch Integration in zentrale RBAC-/SSO-Schicht der SBS-Nexus-Plattform.[web:142][web:228]

## 5. Mandanten- & Dokumentmodell (Zielbild)
Jedes Dokument (Rechnung) erhält mindestens folgende Metadaten:
- `tenant_id` (Mandant / Firma / Werk)
- `document_type = "invoice"`
- `uploaded_by` (technische User-ID)
- `source_system = "ki-rechnungsverarbeitung"`
- `processed_at` (Zeitpunkt der Verarbeitung)

Diese Struktur ist mit anderen SBS-Nexus-Modulen (HydraulikDoc, Verträge, Wartung)
abgestimmt, um ein einheitliches Enterprise-Datenmodell zu gewährleisten.[web:128][web:194]

Weitere Details werden während der Implementierung iterativ ergänzt.

## 6. Metadaten-Schema für Rechnungsdokumente (v1)

Jede Rechnung im System soll mindestens folgende Metadaten besitzen:

- `id`: Interne technische ID der Rechnung (UUID oder vergleichbar)
- `tenant_id`: Mandant / Firma / Werk, dient der strikten Datenisolierung[web:195][web:232][web:244]
- `document_type`: Immer `"invoice"` für dieses Modul
- `file_name`: Original-Dateiname der hochgeladenen Rechnung
- `mime_type`: Dateityp (z.B. application/pdf)
- `uploaded_by`: Technische User-ID, die den Upload/Import ausgelöst hat[web:248][web:252]
- `uploaded_at`: Zeitpunkt des Uploads
- `processed_at`: Zeitpunkt, an dem die Rechnung erfolgreich extrahiert/validiert wurde
- `source_system`: z.B. `"ki-rechnungsverarbeitung"` oder nachgelagertes ERP/DMS
- `status`: z.B. `uploaded`, `processing`, `processed`, `error`[web:248]

Dieses Schema lehnt sich an etablierte Multi-Tenant- und Dokumentmodelle an,
bei denen `tenant_id` konsequent zur Isolation genutzt wird und `document_type`
eine einheitliche Behandlung verschiedener Dokumentarten ermöglicht.[web:195][web:232][web:250]
