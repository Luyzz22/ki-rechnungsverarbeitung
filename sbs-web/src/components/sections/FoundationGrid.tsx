/**
 * "Eine technische Grundlage" (§18.3). Only mechanisms that exist in the
 * product repositories are listed — no capability is added because it would
 * round out the grid.
 */
const layers = [
  {
    title: "Dokumente",
    body: "PDF, Tabellen und gescannte Vorlagen werden validiert, bereinigt und strukturiert extrahiert, bevor ein Modell sie sieht.",
    mechanisms: ["Upload-Validierung", "Layout- und Tabellenextraktion", "Sanitisierung eingebetteter Inhalte"],
  },
  {
    title: "Daten",
    body: "Ergebnisse liegen als typisierte Datensätze in einer mandantengetrennten Datenbank, nicht als freier Text in einem Chatverlauf.",
    mechanisms: ["Row-Level-Security", "Schemavalidierte Ergebnisse", "Versionierte Läufe statt Überschreiben"],
  },
  {
    title: "Modelle",
    body: "Anbieter und Modell werden pro Stufe gewählt und mit Auswahlgrund protokolliert. Prompts kommen aus einer Registry mit Release-Stand.",
    mechanisms: ["Prompt-Registry mit Versionen", "Protokollierte Anbieterwahl", "Fallback-Kette statt stiller Ersetzung"],
  },
  {
    title: "Menschliche Prüfung",
    body: "KI-Ausgaben bleiben Entwürfe. Freigabe, Ablehnung und Eskalation sind eigene Zustände mit eigener Berechtigung.",
    mechanisms: ["Review-States am Objekt", "Rollenbasierte Freigabe", "Vier-Augen-Prinzip, wo gefordert"],
  },
  {
    title: "Nachvollziehbarkeit",
    body: "Quelle, Fundstelle, Modell, Prompt-Version, Zeitpunkt und Prüfer bleiben mit dem Ergebnis verbunden – auch im Export.",
    mechanisms: ["Audit Events", "Provenienz am Ergebnis", "Export mit Quellenangabe"],
  },
  {
    title: "Integration",
    body: "Die Systeme fügen sich in vorhandene Identitäts-, Datenbank- und Exportwege ein, statt ein weiteres Führungssystem zu verlangen.",
    mechanisms: ["OIDC / Entra ID / Google Login", "PostgreSQL in EU-Regionen", "DATEV-, CSV- und Markdown-Export"],
  },
];

export function FoundationGrid({ headingLevel: Heading = "h3" }: { headingLevel?: "h2" | "h3" } = {}) {
  return (
    <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-9 md:grid-cols-2 lg:grid-cols-3">
      {layers.map((layer) => (
        <li key={layer.title} className="flex flex-col gap-3 border-t border-[var(--sbs-border)] pt-5">
          <Heading className="sbs-h4 text-[var(--sbs-text-primary)]">{layer.title}</Heading>
          <p className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{layer.body}</p>
          <ul className="mt-1 flex flex-col gap-1.5">
            {layer.mechanisms.map((mechanism) => (
              <li key={mechanism} className="flex items-start gap-2">
                <span
                  aria-hidden="true"
                  className="mt-[0.5rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-accent)]"
                />
                <span className="sbs-mono text-[0.75rem] leading-[1.5] text-[var(--sbs-text-muted)]">{mechanism}</span>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}
