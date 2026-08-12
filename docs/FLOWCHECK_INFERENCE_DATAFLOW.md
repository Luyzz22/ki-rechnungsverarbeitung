# FlowCheck+ Inference Dataflow

Stand: Phase 1, Inference Policy Foundation.

Diese Datei inventarisiert aktive Codepfade, die externe LLMs oder OCR verwenden. Archiv-, Backup- und Marketingdateien wurden bewusst nicht als aktive Laufzeitpfade bewertet.

## Policy Defaults

- Bestehende Rechnungsdaten: `data_class=invoice_confidential`, `inference_profile=standard`.
- Demo-Daten: `data_class=demo`, `inference_profile=standard`.
- Explizite `professional_secret`- oder `sovereign_secret`-Vorgänge dürfen nicht auf Direct APIs zurückfallen.
- Unbekannte Datenklassen oder Profile werden durch `shared.inference_policy` fail-closed behandelt.

## Inventar

| Codepfad | Provider heute | Verarbeitete Daten | Datenklasse | Profil | Zukünftig zulässig | Guard Phase 1 |
| --- | --- | --- | --- | --- | --- | --- |
| `llm_router.extract_invoice_data` | OpenAI Direct, Anthropic Direct | OCR-/PDF-Rechnungstext, Rechnungsfelder | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `llm_router.extract_with_vision` | OpenAI Direct Vision | PDF-Seitenbild/Base64 aus Rechnung | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local OCR/LLM; Sovereign: Local | Ja |
| `invoice_core.extract_text_from_pdf` | lokale OCR via Tesseract/pdf2image | PDF-Bildseiten und OCR-Text | `invoice_confidential` default | `standard` default | Local OCR | Ja |
| `ocr_optimizer.ocr_with_fallback` / `extract_from_pdf_optimized` | lokale OCR via Tesseract/pdf2image | Bild-/PDF-OCR | `invoice_confidential` default | `standard` default | Local OCR | Ja |
| `ocr_processor.OCRProcessor` | lokale OCR via Tesseract/pdf2image | gescannte PDFs | `invoice_confidential` default | `standard` default | Local OCR | Ja |
| `mbr.llm.generate_narrative_via_llm` | OpenAI Direct | aggregierte MBR-KPIs, Lieferanten-/Budgetzusammenfassungen | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `category_ai.predict_category` | Anthropic Direct | Rechnungsaussteller, Betrag, Artikel, Kategorien | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `auto_accounting.suggest_account_with_llm` | OpenAI Direct | Kontierungsrelevante Rechnungsfelder | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `duplicate_detection.check_similarity_ai` | Anthropic Direct | neue Rechnung und historische Rechnungen desselben Lieferanten | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `enterprise_features.get_ai_financial_analysis` | OpenAI Direct | aggregierte Finanzstatistiken und Top-Lieferanten | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `api_nexus.process_invoice` | indirekt OpenAI/Anthropic via `llm_router`; OCR via `invoice_core` | API-Inhalt/Base64, extrahierter Rechnungstext | `invoice_confidential` default | `standard` default | Serverklassifizierung + Guard; Professional/Sovereign ohne Direct fallback | Ja, über Router/OCR |
| `web.app.run_finance_copilot_llm` | OpenAI Direct | Finance Snapshot mit Rechnungs-/Lieferantenaggregaten | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `web.app.copilot_demo_query` | OpenAI Direct | Demo-Finanzdaten und Nutzerfrage | `demo` | `standard` default | Direct für Demo/Standard | Ja |
| `web.app.chat_with_cfo` | Legacy `LLMRouter.generate_response` mit OpenAI-Konfiguration, aktuell vermutlich inaktiv | Finance DB-Kontext, Top-Lieferanten, Nutzerfrage | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `modules/.../ai_extraction.AIExtractionService` | Gemini Direct, Anthropic Direct fallback | PDF-/Bildbytes, Base64 bei Claude, extrahierte Rechnungsfelder | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `modules/.../ai_kontierung.AIKontierungService` | Gemini Direct, Anthropic Direct fallback | Rechnungsdaten für DATEV/SKR-Kontierung | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `modules/.../finance_copilot.FinanceCopilotService` | Gemini Direct, Anthropic Direct fallback | DB-Kontext zu Rechnungen, Events, Kontierungen | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `modules/.../llama_index_service.LlamaIndexService` | Gemini Direct via LlamaIndex | indexierte Rechnungsmetadaten, Positionen, Fragen | `invoice_confidential` default | `standard` default | Standard: Direct erlaubt; Professional: Azure EU oder Local; Sovereign: Local | Ja |
| `smart_maintenance.recognize_part_from_image` | Gemini Direct | Bild eines Ersatzteils, Techniker-Kontext | `internal` default | `standard` default | Standard: Direct erlaubt; bei höheren Profilen Azure/Local nach Regelwerk | Ja |
| `smart_maintenance.analyze_part_with_hydraulikdoc` | Gemini Direct | Bild eines Ersatzteils, Techniker-Kontext | `internal` default | `standard` default | Standard: Direct erlaubt; bei höheren Profilen Azure/Local nach Regelwerk | Ja |

## Nicht-AI/OCR HTTP-Calls

- `notification_api.py`, `notifications.py`, `api_nexus.py`, `web/app.py`, `email_ingestion.py` enthalten `requests.post()`-Aufrufe zu Webhooks, Slack/Resend oder internen Integrationen. Diese sind keine LLM-/OCR-Endpunkte und wurden nicht über den Inference Guard geführt.

## Bekannte Lücken Nach Phase 1

- Azure OpenAI EU ist nur als Provider-Identität und Policy-Ziel vorbereitet, noch nicht implementiert.
- Azure Document Intelligence EU ist nur als Provider-Identität und Policy-Ziel vorbereitet, noch nicht implementiert.
- Lokale OpenAI-kompatible Inferenz ist nur modelliert, noch nicht implementiert.
- Lokale OCR ist gegatet, aber nicht über eine neue Infrastruktur-/Sandbox-Isolation gehärtet.
- Es gibt noch keine Key-Vault-, Managed-Identity-, Netzwerkisolierungs- oder Private-Link-Integration.
- SQLite bekommt kompatible Policy-Spalten; es gibt keine historische Backfill-Migration über alte Datensätze hinaus.
- `invoice_extraction.py` existiert in diesem Repository nicht; aktive Extraktion liegt in `llm_router.py`, `invoice_core.py` und `modules/rechnungsverarbeitung/src/invoices/services/ai_extraction.py`.
- `api_nexus.process_invoice` nimmt weiterhin externe API-Inhalte entgegen. Phase 1 entscheidet Datenklasse/Profil serverseitig und guardet den LLM/OCR-Call; eine spätere Phase sollte diesen Pfad auf serverseitige Dokument-IDs mit Zugriffsprüfung umstellen.
