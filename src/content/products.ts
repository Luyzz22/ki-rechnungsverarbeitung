import type { Product } from "./types";

/**
 * Central product registry (§92).
 *
 * Every entry is derived from the product's own repository: README, PRODUCT.md,
 * source modules and the live deployment. No customer names, certifications,
 * accuracy figures, adoption numbers or SLAs appear here, because none of them
 * are verified in the sources.
 */
export const products: Product[] = [
  /* ====================================================================== */
  /*  INDUSTRIE                                                             */
  /* ====================================================================== */
  {
    slug: "normpilot",
    name: "NormPilot Industrie",
    shortName: "NormPilot",
    division: "industry",
    tagline: "Aus verstreuten Auditunterlagen wird eine prüfbare Evidence Matrix.",
    description:
      "NormPilot ordnet vorhandene PDFs, Excel-Listen, Prüfberichte und QM-Dokumente einzelnen Anforderungen zu, markiert fehlende Nachweise als Gap Finding und überführt jedes Finding in eine reviewbare Maßnahme. Am Ende steht ein exportierbares Evidence Pack mit Quelle, Fundstelle, Modellversion, Zeitstempel und Review-Status.",
    outcome: "Audit-Readiness aus Bestandsdaten – nachvollziehbar bis zur Fundstelle.",
    audience: [
      "Qualitätsmanagement und QM-Beauftragte",
      "Operations und Werksleitung",
      "Compliance und Informationssicherheit im Industrieumfeld",
      "Externe Auditbegleitung und Beratung",
    ],
    capabilities: [
      {
        title: "Requirement Sets statt Normvolltexte",
        description:
          "Anforderungen werden als eigene Requirement Items geführt und mit Nachweisen verknüpft. NormPilot speichert und liefert keine ISO-, DIN-, IATF- oder VDA-Normvolltexte aus.",
      },
      {
        title: "Evidence Mapping mit Fundstelle",
        description:
          "Jede Zuordnung hält fest, aus welchem Dokument und welcher Stelle der Nachweis stammt. Ohne Quelle entsteht kein bestätigter Nachweis.",
      },
      {
        title: "Gap Findings mit Severity",
        description:
          "Fehlende oder schwache Nachweise werden als Finding mit Schweregrad erfasst statt stillschweigend übergangen.",
      },
      {
        title: "Corrective Actions mit Verantwortlichkeit",
        description:
          "Aus Findings entstehen Maßnahmen mit Zuständigkeit und Status – die Brücke zwischen Auditbefund und Umsetzung.",
      },
      {
        title: "Human Review vor Freigabe",
        description:
          "KI-Ausgaben bleiben Entwürfe. Erst die Prüfung durch eine fachverantwortliche Person überführt sie in einen freigegebenen Zustand.",
      },
      {
        title: "Evidence Pack Export",
        description:
          "Markdown- und CSV-Export der Evidence Matrix inklusive Quellen, Prompt-Version, Modell/Provider, Zeitstempel und Review-Status.",
      },
    ],
    pipeline: [
      { id: "docs", label: "Bestandsdokumente", detail: "PDF, XLSX, Prüfberichte, Zertifikate, Schulungsnachweise", annotation: "intake" },
      { id: "requirements", label: "Requirement Set", detail: "Anforderungen als eigene, referenzierbare Items", annotation: "scope" },
      { id: "mapping", label: "Evidence Mapping", detail: "Nachweis ↔ Anforderung inklusive Fundstelle", annotation: "map" },
      { id: "gaps", label: "Gap Findings", detail: "Lücken mit Schweregrad statt stiller Annahme", annotation: "severity" },
      { id: "actions", label: "Corrective Actions", detail: "Maßnahme, Zuständigkeit, Status", annotation: "plan" },
      { id: "review", label: "Human Review", detail: "Fachverantwortliche Freigabe vor Export", annotation: "gate", human: true },
      { id: "pack", label: "Evidence Pack", detail: "Markdown/CSV mit vollständiger Provenienz", annotation: "export" },
    ],
    workflow: {
      before: [
        "Nachweise liegen verteilt auf Laufwerken, in Postfächern und Ordnern.",
        "Der Auditstand entsteht kurz vor dem Termin aus Erinnerung und Suche.",
        "Ob eine Anforderung wirklich belegt ist, weiß nur die Person, die zuletzt gesucht hat.",
      ],
      after: [
        "Jede Anforderung trägt entweder einen Nachweis mit Fundstelle oder ein offenes Gap Finding.",
        "Lücken haben einen Schweregrad, eine Maßnahme und eine Zuständigkeit.",
        "Das Evidence Pack lässt sich jederzeit mit vollständiger Provenienz exportieren.",
      ],
    },
    governance: [
      "KI-Ausgaben sind gekennzeichnete Entwürfe und ersetzen keine fachliche Prüfung.",
      "AuditEvent-Logging für audit-relevante Aktionen, tamper-evidenter Audit-Trail.",
      "Tenant-Isolation und Provider-Call-Schutz sind durch Offline-Smoke-Tests abgedeckt.",
      "Kein automatisches Zertifizierungsurteil und keine Zusicherung eines bestandenen Audits.",
      "Keine personenbezogenen Daten in Logs, Tests, Seeds oder Screenshots.",
    ],
    integrations: ["Markdown-/CSV-Export", "PostgreSQL (EU-Region)", "SSO über OIDC-Provider", "SCIM-Endpunkte"],
    graphic: "evidence-matrix",
    primaryAction: { label: "NormPilot öffnen", href: "https://app.normpilot-industrie.de", external: true },
    secondaryAction: { label: "Pilot besprechen", href: "/industrie/kontakt?product=normpilot" },
    repositories: ["Luyzz22/normpilot-industrie"],
    relatedSlugs: ["hydraulikdoc", "flowcheck"],
    relatedReason:
      "Weitere Lösungen für technische Nachweis- und Dokumentenprozesse: HydraulikDoc liefert die quellengebundene Antwort am Asset, FlowCheck AI+ die belegseitige Nachweiskette.",
    href: "/industrie/produkte/normpilot",
  },
  {
    slug: "hydraulikdoc",
    name: "HydraulikDoc",
    shortName: "HydraulikDoc",
    division: "industry",
    tagline: "Antworten aus dem technischen Handbuch – mit Seitenzahl statt Vermutung.",
    description:
      "HydraulikDoc verbindet Anlagenregister, technische PDF-Dokumentation und Zustandsdaten zu einer kontrollierten Beweiskette. Eine Antwort ohne gültige Quellenmarke wird verworfen und gar nicht erst gespeichert. Jeder Entwurf bleibt Entwurf, bis eine berechtigte Person ihn annimmt, ablehnt oder eskaliert.",
    outcome: "Von der technischen Dokumentation zur belegten Entscheidung an der Anlage.",
    audience: [
      "Servicetechnik und Instandhaltung",
      "Instandhaltungsleitung und Reliability Engineering",
      "Fluid- und Zustandsüberwachungs-Spezialisten",
      "IT-Betrieb, Informationssicherheit und Datenschutz",
    ],
    capabilities: [
      {
        title: "Asset-gebundene Dokumentation",
        description:
          "Dokumente hängen an einem registrierten Asset mit Standort und Kritikalität – nicht in einem anonymen Dateiablagen-Pool.",
      },
      {
        title: "Strukturierte Extraktion inklusive Tabellen",
        description:
          "Technische PDFs werden über Layout-Extraktion aufbereitet, sodass Grenzwerttabellen und Kennfelder abfragbar bleiben.",
      },
      {
        title: "Hybrid Retrieval mit erzwungenem Tenant-Filter",
        description:
          "Volltext- und Vektorsuche laufen ausschließlich über mandantengefilterte Evidenz. Das Modell darf nur diese Evidenz verwenden.",
      },
      {
        title: "Zitatvalidierung als Sperre",
        description:
          "Ein Output ohne gültige Quellenmarke wird verworfen und nicht persistiert. Fehlende Belege führen zu keiner Antwort, nicht zu einer plausiblen.",
      },
      {
        title: "Deterministische Zustands- und Fluidbewertung",
        description:
          "Zustands- und Ölindikatoren werden regelbasiert gegen anlagenbezogene Betriebsgrenzen bewertet – nachvollziehbar und ohne Modellvarianz.",
      },
      {
        title: "Review-gebundener Export",
        description:
          "Nur akzeptierte Ergebnisse lassen sich durch Rollen mit Export-Berechtigung als Nachweis ausleiten.",
      },
    ],
    pipeline: [
      { id: "asset", label: "Asset-Registrierung", detail: "Anlage mit Standort und Kritikalität", annotation: "context" },
      { id: "upload", label: "Dokument-Intake", detail: "Validierung, Malware-Scan, private Speicherung", annotation: "guarded" },
      { id: "extract", label: "Layout-Extraktion", detail: "Text, Tabellen und Struktur aus dem technischen PDF", annotation: "parse" },
      { id: "retrieval", label: "Hybrid Retrieval", detail: "Tenant-gefilterte Evidenz, keine Fremdmandanten", annotation: "scoped" },
      { id: "answer", label: "Quellengebundener Entwurf", detail: "Ohne gültige Quellenmarke wird verworfen", annotation: "cited" },
      { id: "review", label: "Human Review", detail: "Annehmen, ablehnen oder Experten anfordern", annotation: "gate", human: true },
      { id: "export", label: "Nachweis-Export", detail: "Nur akzeptierte Ergebnisse, rollenbegrenzt", annotation: "export" },
    ],
    workflow: {
      before: [
        "Grenzwerte stehen in einem PDF, das in der Schicht niemand durchsucht.",
        "Antworten entstehen aus Erfahrung und lassen sich nicht belegen.",
        "Dokumente liegen in einer Sammelablage ohne Bezug zur Anlage.",
      ],
      after: [
        "Dokumente hängen am registrierten Asset mit Standort und Kritikalität.",
        "Antworten führen Quelle und Seite mit; ohne Beleg entsteht keine Antwort.",
        "Nur menschlich angenommene Ergebnisse sind exportierbar.",
      ],
    },
    governance: [
      "Modell-, Deployment-, Region-, Prompt-, Zeit-, Nutzer- und Quellenprovenienz werden pro Entwurf gespeichert.",
      "Row-Level-Security in PostgreSQL inklusive Tenant-Stammdaten, mit getrennter Lifecycle-Rolle.",
      "Prompt-Injection-Abwehr und gesperrte Verwendungszwecke greifen vor jedem Modellaufruf.",
      "Löschung und Fristablauf werden über Dokumentspeicher, Suchindex und Datenbank propagiert und auditiert.",
      "Keine autonome Maschinensteuerung, keine Safety-PLC-Anbindung, keine Beschäftigtenleistungsbewertung.",
    ],
    integrations: ["Azure AI Document Intelligence", "Azure AI Search", "Azure OpenAI", "Microsoft Entra ID", "PostgreSQL Flexible Server"],
    graphic: "manual-retrieval",
    primaryAction: { label: "Produktarchitektur ansehen", href: "/industrie/produkte/hydraulikdoc#architektur" },
    secondaryAction: { label: "Zugang anfragen", href: "/industrie/kontakt?product=hydraulikdoc" },
    repositories: ["Luyzz22/sbs-service-knowledge-os", "Luyzz22/sbs-hydraulikdoc (Vorgänger)"],
    relatedSlugs: ["normpilot", "flowcheck"],
    relatedReason:
      "Weitere Lösungen für technische Nachweis- und Dokumentenprozesse: NormPilot bündelt die Auditsicht, FlowCheck AI+ die kaufmännische Nachweiskette dahinter.",
    href: "/industrie/produkte/hydraulikdoc",
  },

  /* ====================================================================== */
  /*  LEGAL                                                                 */
  /* ====================================================================== */
  {
    slug: "kanzleiai",
    name: "KanzleiAI",
    shortName: "KanzleiAI",
    division: "legal",
    tagline: "Vertragsanalyse, bei der jeder Befund seine Herkunft mitführt.",
    description:
      "KanzleiAI analysiert Verträge in einer zweistufigen Pipeline: strukturierte Extraktion, danach Risiko- und Handlungsbewertung. Beide Stufen sind schemavalidiert, versioniert und protokolliert – inklusive gewähltem Anbieter, Modell, Prompt-Version und Auswahlgrund pro Lauf.",
    outcome: "Verträge verstehen, Risiken nachvollziehen, Entscheidungen dokumentieren.",
    audience: [
      "Kanzleien und Legal-Teams",
      "Unternehmensjuristinnen und -juristen",
      "Legal Operations",
      "Einkauf und Vertragsmanagement",
    ],
    capabilities: [
      {
        title: "Zweistufige, schemavalidierte Pipeline",
        description:
          "Stufe 1 extrahiert Vertragsstruktur, Stufe 2 bewertet Risiko und Handlungsbedarf. Ergebnisse werden gegen ein Schema validiert, bevor sie gespeichert werden.",
      },
      {
        title: "Prompt-Governance statt freier Prompts",
        description:
          "Produktionsprompts stammen aus einer zentralen Registry mit Definition und Release. Fehlt ein Release, gilt der explizite Registry-Default – kein stiller Drift.",
      },
      {
        title: "Nachvollziehbares Provider-Routing",
        description:
          "Pro Stufe wird ein Primärmodell gewählt und die Fallback-Kette protokolliert. Auswahlgrund, Anbieter und Modell hängen am jeweiligen Lauf.",
      },
      {
        title: "Lokale Redaction vor jedem Cloud-Aufruf",
        description:
          "Originaldokument, Seitenbilder und das Re-Identifikations-Mapping verlassen den Server nicht. In die Cloud geht ausschließlich der minimierte Payload.",
      },
      {
        title: "Human Review pro Finding",
        description:
          "Jedes Finding lässt sich einzeln bewerten, kommentieren und im Text anpassen – rollenbasiert und mit eigenem Prüfzustand am Lauf.",
      },
      {
        title: "Mandantentrennung auf Datenbankebene",
        description:
          "Row-Level-Security trennt Analyseläufe, Findings und Reviews je Mandant – nicht nur in der Anwendungslogik.",
      },
    ],
    pipeline: [
      { id: "intake", label: "Dokument-Intake", detail: "Vertrag im Mandantenkontext", annotation: "tenant" },
      { id: "redact", label: "Lokale Redaction", detail: "Sanitize, OCR, Detect, Redact, Minimize", annotation: "local" },
      { id: "gate", label: "Policy Gate", detail: "Fail-closed: Unsicherheit blockiert statt durchzulassen", annotation: "fail-closed" },
      { id: "extraction", label: "Strukturierte Extraktion", detail: "Parteien, Laufzeit, Kündigung, Haftung, Gerichtsstand", annotation: "stage 1" },
      { id: "risk", label: "Risiko & Handlungsbedarf", detail: "Findings mit Schweregrad und Begründung", annotation: "stage 2" },
      { id: "review", label: "Human Review", detail: "Finding annehmen, anpassen oder verwerfen", annotation: "gate", human: true },
      { id: "audit", label: "Audit Trail", detail: "Lauf, Prompt-Version, Modell, Entscheidung", annotation: "record" },
    ],
    workflow: {
      before: [
        "Vertragsprüfung skaliert nicht mit dem Volumen.",
        "Wer ein Modell nutzt, schickt das vollständige Dokument in die Cloud.",
        "Was geprüft wurde und mit welchem Modell, ist im Nachhinein nicht rekonstruierbar.",
      ],
      after: [
        "Struktur und Risiko entstehen in zwei getrennten, schemavalidierten Stufen.",
        "Original, Seitenbilder und Mapping bleiben lokal; in die Cloud geht der minimierte Payload.",
        "Prompt-Version, Modell, Anbieter, Auswahlgrund und Prüfentscheidung hängen am Lauf.",
      ],
    },
    governance: [
      "Jede Analyse erzeugt einen neuen Lauf; vorherige Ergebnisse werden nicht überschrieben.",
      "Prompt-Key und -Version, Modell, Anbieter und Auswahlgrund werden pro Lauf persistiert.",
      "Row-Level-Security trennt Analyseläufe, Findings und Reviews je Mandant.",
      "Ein Golden-Set-Evaluationslauf prüft Schema, Extraktion und Findings ohne Mandantendaten.",
      "Die lokale Redaction ist fail-closed: unklare Befunde eskalieren, statt durchzugehen.",
    ],
    integrations: ["OpenAI", "Anthropic", "Google Gemini", "OpenAI-kompatible Endpunkte", "PostgreSQL mit RLS", "OIDC / Google / Microsoft Login"],
    graphic: "contract-analysis",
    primaryAction: { label: "KanzleiAI öffnen", href: "https://www.kanzlei-ai.com", external: true },
    secondaryAction: { label: "Demo vereinbaren", href: "/legal/kontakt?product=kanzleiai" },
    repositories: ["Luyzz22/kanzlei-ai", "Luyzz22/contract-analyzer-backend (Vorgänger-Backend)"],
    relatedSlugs: ["compliancehub"],
    relatedReason:
      "Vertragsanalyse mit anschließender Governance: ComplianceHub führt Befunde, Kontrollen und Nachweise in einen prüfbaren Governance-Bestand über.",
    href: "/legal/produkte/kanzleiai",
  },
  {
    slug: "compliancehub",
    name: "ComplianceHub",
    shortName: "ComplianceHub",
    division: "legal",
    tagline: "KI-Systeme, Pflichten, Kontrollen und Nachweise in einem Bestand.",
    description:
      "ComplianceHub verbindet ein mandantenfähiges KI-System-Inventar mit Risikoklassifikation, Policy-Auswertung, Verstößen, Maßnahmen und Board-Reporting. Die Klassifikation folgt der Entscheidungslogik des EU AI Act; jede Auswertung erzeugt Audit-Events mit Akteur, Aktion und Objekt.",
    outcome: "Regulatorische Pflichten werden zu zugewiesener, prüfbarer Arbeit.",
    audience: [
      "Compliance und Governance",
      "Informationssicherheit und AI Governance",
      "Datenschutz und DSB",
      "Vorstand, Aufsicht, Prüfung und Beratung",
    ],
    capabilities: [
      {
        title: "KI-System-Inventar je Mandant",
        description:
          "Registrierte KI-Systeme mit Verantwortlichen, Kritikalität und Attributen bilden die Grundlage jeder weiteren Bewertung.",
      },
      {
        title: "Risikoklassifikation nach EU-AI-Act-Logik",
        description:
          "Entscheidungsbaum entlang Art. 6: prohibited → high risk → limited risk → minimal risk, unter Berücksichtigung der Annex-I/III-Kategorien.",
      },
      {
        title: "Policy Engine mit expliziten Regeln",
        description:
          "Regeln wie „High risk requires DPIA“ oder „High criticality requires valid owner“ werden ausgewertet und erzeugen versionierte Violations.",
      },
      {
        title: "Gap-Analyse als Aggregat",
        description:
          "Systeme je Risikostufe und AI-Act-Kategorie verdichten sich zu einer Übersicht, die als Grundlage für Board-Reporting taugt.",
      },
      {
        title: "Transparenz- und Folgenabschätzungs-Register",
        description:
          "Art.-50- und DSGVO-Transparenznachweise sowie versionierte DSFA/FRIA-Datensätze mit Vier-Augen-Freigabe und Konsultations-Gates.",
      },
      {
        title: "Audit Events und Evidence",
        description:
          "Policy-Auswertungen und Lifecycle-Änderungen werden mit Akteur, Aktion, Objekt und Verstoßanzahl protokolliert.",
      },
    ],
    pipeline: [
      { id: "inventory", label: "KI-System-Inventar", detail: "System, Zweck, Verantwortliche, Kritikalität", annotation: "register" },
      { id: "classify", label: "Risikoklassifikation", detail: "EU AI Act Art. 6, Annex I/III", annotation: "art. 6" },
      { id: "policy", label: "Policy Evaluation", detail: "Regelwerk je Mandant, versioniert", annotation: "rules" },
      { id: "violations", label: "Violations", detail: "Verstoß mit Regelbezug und Zeitpunkt", annotation: "finding" },
      { id: "gap", label: "Gap-Analyse", detail: "Aggregation je Risikostufe und Kategorie", annotation: "aggregate" },
      { id: "review", label: "Human Review & Vier-Augen", detail: "Freigabe durch benannte Verantwortliche", annotation: "gate", human: true },
      { id: "evidence", label: "Evidence & Board Report", detail: "Nachweise, Maßnahmen, Entscheidungshistorie", annotation: "report" },
    ],
    workflow: {
      before: [
        "KI-Systeme entstehen in Fachbereichen, ohne zentrale Übersicht.",
        "Regulatorische Pflichten stehen in Dokumenten statt in zugewiesener Arbeit.",
        "Für Prüfungen wird der Nachweis nachträglich zusammengesucht.",
      ],
      after: [
        "Ein mandantenfähiges Inventar führt System, Zweck, Verantwortliche und Kritikalität.",
        "Klassifikation und Policy-Auswertung erzeugen Verstöße mit Regelbezug und Zuständigkeit.",
        "Nachweise, Freigaben und Entscheidungen liegen als Bestand vor, nicht als E-Mail-Verlauf.",
      ],
    },
    governance: [
      "Mandanten-, Rollen- und Release-Grenzen sind fail-closed ausgelegt.",
      "DSFA/FRIA-Datensätze sind versioniert und tragen Vier-Augen-Freigabe sowie Konsultations-Gates.",
      "Öffentliche Routen, Enterprise-Routen und Release-Profile bleiben technisch getrennt.",
      "Die Plattform unterstützt Governance und Dokumentation – sie erteilt keine Rechtsauskunft und keine Konformitätsbestätigung.",
      "Es liegen keine freigegebenen Kundenlogos, Testimonials, Zertifikate oder Produktionsbenchmarks vor; deshalb werden hier keine gezeigt.",
    ],
    integrations: ["Microsoft Entra ID / OIDC", "Azure OpenAI mit Managed Identity", "PostgreSQL", "CSV-Import für System-Inventare"],
    graphic: "risk-governance",
    primaryAction: { label: "Governance-Prozess ansehen", href: "/legal/produkte/compliancehub#prozess" },
    secondaryAction: { label: "Pilotzugang anfragen", href: "/legal/kontakt?product=compliancehub" },
    repositories: ["Luyzz22/Compliance-Hub"],
    relatedSlugs: ["kanzleiai"],
    relatedReason:
      "Governance mit belastbarer Vertragsbasis: KanzleiAI liefert die Vertrags- und Klauselbefunde, die in ComplianceHub zu Kontrollen und Nachweisen werden.",
    href: "/legal/produkte/compliancehub",
  },

  /* ====================================================================== */
  /*  CROSS-VERTICAL                                                        */
  /* ====================================================================== */
  {
    slug: "flowcheck",
    name: "FlowCheck AI+",
    shortName: "FlowCheck AI+",
    division: "cross_vertical",
    tagline: "Eingangsrechnungen von der Erfassung bis zum DATEV-Export – mit Freigabe dazwischen.",
    description:
      "FlowCheck AI+ erfasst Eingangsrechnungen, extrahiert die Pflichtangaben, prüft auf Dubletten und Plausibilität, schlägt eine Kontierung nach SKR03/SKR04 vor und übergibt nach menschlicher Freigabe an den Export. Prozess- und Exportereignisse landen im Audit-Trail.",
    outcome: "Belegverarbeitung, die vor dem Export durch eine Freigabe geht.",
    audience: [
      "Finanzbuchhaltung und Rechnungswesen",
      "Steuerkanzleien und Mandantenbetreuung",
      "Einkauf und kaufmännisches Backoffice",
      "Geschäftsführung im Mittelstand",
    ],
    capabilities: [
      {
        title: "Extraktion der Pflichtangaben",
        description:
          "Rechnungsnummer, Lieferant, Datum, Fälligkeit, Netto, Brutto und Währung werden strukturiert erfasst statt abgetippt.",
      },
      {
        title: "Dublettenerkennung",
        description:
          "Doppelt eingereichte Rechnungen werden erkannt und mit Begründung markiert, bevor sie in die Freigabe gehen.",
      },
      {
        title: "Plausibilitätsprüfung",
        description:
          "Beträge und Pflichtangaben werden gegeneinander geprüft; auffällige Belege gehen in die Klärung statt in den Export.",
      },
      {
        title: "Kontierungsvorschlag SKR03/SKR04",
        description:
          "Ein Vorschlag, keine Buchung: die Zuordnung bleibt bis zur Freigabe änderbar.",
      },
      {
        title: "Freigabe-Workflow mit Rollen",
        description:
          "Upload, Prüfung und Freigabe sind getrennte Rechte. Ohne Freigabeberechtigung entsteht kein Export.",
      },
      {
        title: "Export und Monatsbericht",
        description:
          "DATEV-kompatibler Export sowie Excel und CSV; zusätzlich ein editierbarer Monatsbericht als PPTX aus den eigenen Daten.",
      },
    ],
    pipeline: [
      { id: "intake", label: "Beleg-Intake", detail: "PDF, PNG oder JPG im Nutzerkontext", annotation: "upload" },
      { id: "extract", label: "Strukturierte Extraktion", detail: "Pflichtangaben statt Freitext", annotation: "extract" },
      { id: "duplicate", label: "Dubletten & Plausibilität", detail: "Auffälligkeit mit Begründung", annotation: "check" },
      { id: "account", label: "Kontierungsvorschlag", detail: "SKR03 / SKR04, änderbar", annotation: "propose" },
      { id: "approve", label: "Freigabe", detail: "Rollenbasierte Prüfung und Freigabe", annotation: "gate", human: true },
      { id: "export", label: "Export", detail: "DATEV-kompatibel, Excel, CSV", annotation: "export" },
      { id: "audit", label: "Audit-Trail", detail: "Prozess- und Exportereignisse", annotation: "record" },
    ],
    workflow: {
      before: [
        "Eingangsrechnungen verteilen sich über Einzelpostfächer und Ablagen.",
        "Pflichtangaben werden abgetippt, Dubletten fallen erst im Zahllauf auf.",
        "Wer wann freigegeben hat, steht in einer E-Mail.",
      ],
      after: [
        "Belege werden zentral erfasst und strukturiert extrahiert.",
        "Dubletten und unplausible Beträge gehen in die Klärung statt in den Export.",
        "Freigaben sind rollenbasiert und landen mit dem Export im Audit-Trail.",
      ],
    },
    governance: [
      "Alle Abfragen filtern auf die Nutzer- bzw. Mandantenzuordnung; Datenisolation ist Pflicht, nicht Option.",
      "Rollenmodell von owner bis viewer trennt Upload, Freigabe, Berichte und Nutzerverwaltung.",
      "Prozess- und Exportereignisse werden als Audit-Trail protokolliert.",
      "Aussagen zu DSGVO, GoBD, E-Rechnung und EU AI Act sind einsatz- und vertragsabhängig und bleiben fachlich zu prüfen.",
    ],
    integrations: ["DATEV-kompatibler Export", "Excel / CSV", "Google Workspace SSO", "E-Mail-Benachrichtigung"],
    graphic: "invoice-automation",
    primaryAction: { label: "FlowCheck AI+ App öffnen", href: "https://app.sbsdeutschland.com", external: true },
    secondaryAction: { label: "Gespräch vereinbaren", href: "/kontakt?product=flowcheck" },
    repositories: ["Luyzz22/ki-rechnungsverarbeitung", "Luyzz22/belegflow-ai-site"],
    relatedSlugs: ["normpilot", "kanzleiai"],
    relatedReason:
      "Belege sind selten das Ende der Kette: NormPilot verknüpft sie mit Auditanforderungen, KanzleiAI mit dem zugrunde liegenden Vertrag.",
    href: "/plattform/flowcheck",
  },

  /* ====================================================================== */
  /*  UNABHÄNGIG / SBS LABS                                                 */
  /* ====================================================================== */
  {
    slug: "releaseproof",
    name: "ReleaseProof",
    shortName: "ReleaseProof",
    division: "independent",
    tagline: "Ein definierter Jira-Release-Scope wird zu deterministischer Freigabe-Evidenz.",
    description:
      "ReleaseProof wertet einen ausgewählten Jira-Release-Scope gegen sieben feste Regeln aus und liefert Score, Findings und eine Evidence-Matrix auf Issue-Ebene. Die Auswertung ist deterministisch und verwendet keine generative KI. Die Freigabeentscheidung bleibt beim Team.",
    outcome: "Release-Readiness als überprüfbare Evidenz statt als Bauchgefühl.",
    audience: [
      "Engineering- und Release-Verantwortliche",
      "Quality Engineering",
      "Regulierte oder kontrollierte Softwareteams",
    ],
    capabilities: [
      {
        title: "Sieben deterministische Regeln",
        description:
          "Akzeptanzkriterien vorhanden, akzeptierter Workflow-Status, keine offenen Subtasks, keine blockierenden Links, korrekte Release-Version, kein Blocker-Label, Freigabemarker vorhanden.",
      },
      {
        title: "Zwei Scope-Modi",
        description:
          "VERSION_ONLY oder JQL_SCOPE. Im JQL-Modus bleibt ein Issue mit fehlender oder falscher fixVersion sichtbar und fällt durch die Versionsregel.",
      },
      {
        title: "Evidence-Matrix auf Issue-Ebene",
        description:
          "Jedes Issue trägt sein Regelergebnis. Der Bericht zeigt, warum ein Release rot ist – nicht nur dass er es ist.",
      },
      {
        title: "Nur Leserechte",
        description:
          "Die Forge-App fordert `read:jira-work` und `storage:app` an. Schreibrechte auf Jira werden nicht angefragt.",
      },
    ],
    pipeline: [
      { id: "config", label: "Scope konfigurieren", detail: "Textquelle und VERSION_ONLY oder JQL_SCOPE", annotation: "setup" },
      { id: "collect", label: "Issue-Population sammeln", detail: "Vollständige Erfassung, sonst Abbruch", annotation: "read-only" },
      { id: "rules", label: "Sieben Regeln auswerten", detail: "Deterministisch, ohne generative KI", annotation: "deterministic" },
      { id: "matrix", label: "Evidence-Matrix", detail: "Regelergebnis je Issue", annotation: "evidence" },
      { id: "decide", label: "Go / No-Go", detail: "Die Entscheidung bleibt im Kundenprozess", annotation: "gate", human: true },
    ],
    workflow: {
      before: [
        "Release-Readiness wird in einer Besprechung geschätzt.",
        "Fehlende Akzeptanzkriterien fallen erst nach dem Deployment auf.",
        "Der Nachweis für die Freigabeentscheidung existiert nur als Protokollnotiz.",
      ],
      after: [
        "Sieben feste Regeln laufen deterministisch gegen den definierten Scope.",
        "Jedes Issue trägt sein Regelergebnis in der Evidence-Matrix.",
        "Der Bericht zeigt, was korrigiert werden muss – die Entscheidung bleibt beim Team.",
      ],
    },
    governance: [
      "Die Analyse ist deterministisch und verwendet keine generative KI.",
      "Unerwartete Jira-Strukturen, unvollständige Paginierung oder unsichere Mappings brechen die Analyse ab, statt ein Teilergebnis auszuweisen.",
      "Öffentliche Ergebnisansichten enthalten keine vollständigen Beschreibungs- und Akzeptanzkriterientexte.",
      "ReleaseProof unterstützt eine Entscheidung – es gibt keinen Release frei und bestätigt keine Konformität.",
    ],
    integrations: ["Atlassian Forge", "Jira Cloud (nur lesend)"],
    graphic: "release-evidence",
    primaryAction: { label: "releaseproof.com öffnen", href: "https://releaseproof.com", external: true },
    repositories: ["Luyzz22/releaseproof-web", "Luyzz22/releaseproof-jira"],
    relatedSlugs: [],
    relatedReason: "",
    href: "/labs/releaseproof",
  },
];

export const productBySlug = (slug: string): Product | undefined =>
  products.find((product) => product.slug === slug);

export const productsByDivision = (division: Product["division"]): Product[] =>
  products.filter((product) => product.division === division);

/** Products surfaced under the industry site: own products + the cross-vertical one. */
export const industryProducts = (): Product[] => productsByDivision("industry");

export const legalProducts = (): Product[] => productsByDivision("legal");

export const crossVerticalProducts = (): Product[] => productsByDivision("cross_vertical");

export const independentProducts = (): Product[] => productsByDivision("independent");

export const relatedProducts = (product: Product): Product[] =>
  product.relatedSlugs
    .map((slug) => productBySlug(slug))
    .filter((entry): entry is Product => Boolean(entry));
