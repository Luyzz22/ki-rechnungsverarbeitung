import type { Solution } from "./types";

/**
 * Problem-first solution pages (§24, §33). Each one connects several products
 * around a job the visitor already has a name for.
 */
export const solutions: Solution[] = [
  /* ---------------------------------- Industrie -------------------------- */
  {
    slug: "audit-readiness",
    division: "industry",
    title: "Audit-Readiness",
    problem:
      "Die Nachweise für das nächste Audit existieren – aber verteilt über Laufwerke, Postfächer und Ordner. Niemand kann in vertretbarer Zeit sagen, welche Anforderung wirklich belegt ist.",
    outcome:
      "Eine Evidence Matrix, in der jede Anforderung entweder einen Nachweis mit Fundstelle hat oder ein offenes Gap Finding mit Maßnahme.",
    steps: [
      "Bestandsdokumente aufnehmen: PDFs, Excel-Listen, Prüfberichte, Zertifikate, Schulungsnachweise.",
      "Anforderungen als eigene Requirement Items führen – ohne Normvolltexte zu speichern.",
      "Nachweise zuordnen und die Fundstelle mitführen, damit die Zuordnung prüfbar bleibt.",
      "Lücken als Gap Finding mit Schweregrad sichtbar machen statt sie zu überspringen.",
      "Findings in Maßnahmen mit Zuständigkeit überführen und fachlich freigeben.",
      "Evidence Pack exportieren – mit Quelle, Modellversion, Zeitstempel und Review-Status.",
    ],
    productSlugs: ["normpilot", "hydraulikdoc"],
    href: "/industrie/loesungen/audit-readiness",
  },
  {
    slug: "technische-dokumentation",
    division: "industry",
    title: "Technische Dokumentation",
    problem:
      "Handbücher, Datenblätter und Grenzwerttabellen liegen als PDF vor. Die Antwort steht drin – nur findet sie niemand in der Schicht, in der sie gebraucht wird.",
    outcome:
      "Fragen an den Dokumentenbestand werden mit Quelle und Fundstelle beantwortet; unbelegte Antworten entstehen gar nicht erst.",
    steps: [
      "Dokumente an ein registriertes Asset binden statt in eine Sammelablage zu legen.",
      "Layout-Extraktion aufsetzen, damit Tabellen und Kennfelder abfragbar bleiben.",
      "Retrieval mandantengefiltert betreiben – das Modell sieht nur freigegebene Evidenz.",
      "Antwortentwürfe ohne gültige Quellenmarke verwerfen statt sie zu speichern.",
      "Entwürfe durch berechtigte Personen annehmen, ablehnen oder eskalieren lassen.",
    ],
    productSlugs: ["hydraulikdoc", "normpilot"],
    href: "/industrie/loesungen/technische-dokumentation",
  },
  {
    slug: "service-wartung",
    division: "industry",
    title: "Service & Instandhaltung",
    problem:
      "Zustandsdaten, Ölanalysen und Herstellergrenzen werden getrennt bewertet. Die Entscheidung entsteht aus Erfahrung – und ist im Nachhinein schwer zu begründen.",
    outcome:
      "Zustands- und Fluidbewertung laufen regelbasiert gegen anlagenbezogene Betriebsgrenzen, jede Einschätzung hängt am Asset und an ihrer Quelle.",
    steps: [
      "Anlagen mit Standort und Kritikalität registrieren.",
      "Zustands- und Ölindikatoren gegen anlagenbezogene Betriebsgrenzen bewerten – deterministisch, nicht generativ.",
      "Auffälligkeiten als Incident mit Verantwortlichkeit führen.",
      "Dokumentenrecherche direkt am Asset ausführen, mit Quellenangabe.",
      "Nur akzeptierte Ergebnisse als Nachweis exportieren.",
    ],
    productSlugs: ["hydraulikdoc"],
    href: "/industrie/loesungen/service-wartung",
  },
  {
    slug: "operations",
    division: "industry",
    title: "Operations & Backoffice",
    problem:
      "Der kaufmännische Teil der Produktion – Eingangsrechnungen, Freigaben, Exporte – bindet Zeit, die in der Fertigung fehlt, und ist gleichzeitig nachweispflichtig.",
    outcome:
      "Belegverarbeitung mit Dublettenprüfung, Kontierungsvorschlag und rollenbasierter Freigabe, deren Ereignisse im Audit-Trail landen.",
    steps: [
      "Eingangsrechnungen zentral erfassen statt über Einzelpostfächer zu verteilen.",
      "Pflichtangaben strukturiert extrahieren und auf Plausibilität prüfen.",
      "Dubletten mit Begründung markieren, bevor sie in die Freigabe gehen.",
      "Kontierung nach SKR03/SKR04 vorschlagen und änderbar halten.",
      "Freigabe rollenbasiert erteilen und erst danach exportieren.",
    ],
    productSlugs: ["flowcheck", "normpilot"],
    href: "/industrie/loesungen/operations",
  },
  {
    slug: "document-intelligence",
    division: "industry",
    title: "Document Intelligence",
    problem:
      "Jede Abteilung baut ihre eigene Dokumentenautomatisierung. Am Ende gibt es fünf Extraktionslogiken, aber keine gemeinsame Nachweiskette.",
    outcome:
      "Ein gemeinsamer Weg vom Dokument über die strukturierte Extraktion bis zum menschlich geprüften, exportierbaren Ergebnis.",
    steps: [
      "Dokumenteingang und Validierung vereinheitlichen.",
      "Strukturierte Extraktion statt Freitext-Zusammenfassungen einsetzen.",
      "Ergebnisse gegen ein Schema validieren, bevor sie gespeichert werden.",
      "Menschliche Prüfung als festen Zustand im Ablauf verankern, nicht als optionalen Schritt.",
      "Provenienz – Quelle, Modell, Prompt-Version, Zeitpunkt, Prüfer – mit dem Ergebnis speichern.",
    ],
    productSlugs: ["normpilot", "hydraulikdoc", "flowcheck"],
    href: "/industrie/loesungen/document-intelligence",
  },

  /* ------------------------------------ Legal ---------------------------- */
  {
    slug: "vertragsanalyse",
    division: "legal",
    title: "Vertragsanalyse",
    problem:
      "Vertragsprüfung skaliert nicht mit dem Volumen. Wer auslagert, verliert Nachvollziehbarkeit; wer alles selbst prüft, verliert Zeit.",
    outcome:
      "Strukturierte Extraktion und Risikobefunde als Entwurf, den eine berechtigte Person pro Finding annimmt, anpasst oder verwirft.",
    steps: [
      "Vertrag im Mandantenkontext aufnehmen – Trennung gilt bis auf Datenbankebene.",
      "Lokal redigieren: Original, Seitenbilder und Mapping verlassen den Server nicht.",
      "Policy Gate fail-closed durchlaufen; Unsicherheit blockiert statt durchzulassen.",
      "Struktur extrahieren: Parteien, Laufzeit, Kündigung, Haftung, Gerichtsstand.",
      "Risiko und Handlungsbedarf als Findings mit Schweregrad bewerten.",
      "Jedes Finding einzeln prüfen und die Entscheidung protokollieren.",
    ],
    productSlugs: ["kanzleiai"],
    href: "/legal/loesungen/vertragsanalyse",
  },
  {
    slug: "legal-operations",
    division: "legal",
    title: "Legal Operations",
    problem:
      "Die Rechtsabteilung arbeitet in Postfächern und Dateiablagen. Was geprüft wurde, wann und von wem, lässt sich nur rekonstruieren – nicht abrufen.",
    outcome:
      "Analyseläufe, Findings und Prüfentscheidungen liegen als versionierter Bestand vor, statt als E-Mail-Verlauf.",
    steps: [
      "Analysen als eigenständige Läufe führen – jede Wiederholung erzeugt einen neuen Lauf.",
      "Prompt-Version, Modell, Anbieter und Auswahlgrund pro Lauf festhalten.",
      "Findings rollenbasiert bewerten und Kommentare am Objekt speichern.",
      "Mandantentrennung über Row-Level-Security absichern.",
      "Audit-Events als Grundlage für Rückfragen und Prüfungen nutzen.",
    ],
    productSlugs: ["kanzleiai", "compliancehub"],
    href: "/legal/loesungen/legal-operations",
  },
  {
    slug: "ai-governance",
    division: "legal",
    title: "AI Governance",
    problem:
      "KI-Systeme entstehen in Fachbereichen. Wer sie betreibt, mit welchem Risiko und mit welcher Freigabe, weiß die Governance-Funktion oft zuletzt.",
    outcome:
      "Ein mandantenfähiges KI-System-Inventar mit Risikoklassifikation, Policy-Auswertung und benannten Verantwortlichen.",
    steps: [
      "KI-Systeme mit Zweck, Verantwortlichen und Kritikalität registrieren.",
      "Risiko entlang der EU-AI-Act-Entscheidungslogik klassifizieren.",
      "Policies auswerten und Verstöße versioniert erzeugen.",
      "Transparenz- und Folgenabschätzungsnachweise mit Vier-Augen-Freigabe führen.",
      "Gap-Analyse als Grundlage für Board-Reporting nutzen.",
    ],
    productSlugs: ["compliancehub"],
    href: "/legal/loesungen/ai-governance",
  },
  {
    slug: "compliance-evidence",
    division: "legal",
    title: "Compliance Evidence",
    problem:
      "Für die Prüfung fehlt nicht die Kontrolle, sondern ihr Nachweis: wer hat wann was entschieden und worauf gestützt.",
    outcome:
      "Nachweise, Maßnahmen und Entscheidungshistorie hängen am Objekt und lassen sich als Bericht ausleiten.",
    steps: [
      "Kontrollen an registrierte Systeme und Pflichten binden.",
      "Evidence und Maßnahmen mit Verantwortlichkeit und Frist führen.",
      "Vier-Augen-Freigaben und Konsultations-Gates als Zustand abbilden.",
      "Audit-Events mit Akteur, Aktion, Objekt und Verstoßanzahl protokollieren.",
      "Board-taugliche Aggregation aus dem laufenden Bestand erzeugen.",
    ],
    productSlugs: ["compliancehub", "kanzleiai"],
    href: "/legal/loesungen/compliance-evidence",
  },
  {
    slug: "risikomanagement",
    division: "legal",
    title: "Risikomanagement",
    problem:
      "Vertragsrisiken und Governance-Risiken werden getrennt geführt. Die Verbindung entsteht erst im Schadensfall.",
    outcome:
      "Vertragsbefunde und Governance-Kontrollen laufen im selben Nachweismodell zusammen: Finding, Schweregrad, Maßnahme, Freigabe.",
    steps: [
      "Vertragsrisiken als Findings mit Schweregrad erfassen.",
      "Zugehörige Kontrollen und Pflichten im Governance-Bestand verknüpfen.",
      "Maßnahmen mit Verantwortlichkeit und Frist ableiten.",
      "Freigaben und Prüfschritte als Zustand dokumentieren.",
      "Offene Risiken aggregiert an Leitung und Aufsicht berichten.",
    ],
    productSlugs: ["kanzleiai", "compliancehub"],
    href: "/legal/loesungen/risikomanagement",
  },
];

export const solutionsByDivision = (division: Solution["division"]): Solution[] =>
  solutions.filter((solution) => solution.division === division);

export const solutionBySlug = (
  division: Solution["division"],
  slug: string,
): Solution | undefined =>
  solutions.find((solution) => solution.division === division && solution.slug === slug);
