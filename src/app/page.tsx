import Link from "next/link";
import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader, Eyebrow } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { SbsNetworkGraphic } from "@/components/graphics/SbsNetworkGraphic";
import { DivisionSplit } from "@/components/sections/DivisionSplit";
import { FoundationGrid } from "@/components/sections/FoundationGrid";
import { ArchitectureFlow } from "@/components/graphics/ArchitectureFlow";
import { ProductCard } from "@/components/product/ProductCard";
import { productBySlug, productsByDivision } from "@/content/products";
import { academyCourses } from "@/content/academy";
import { pageMetadata, organizationSchema, JsonLd } from "@/lib/seo";
import { sites, linkFor } from "@/content/site";

const PAGE_PATH = "/";

export const metadata: Metadata = pageMetadata({
  path: "/",
  title: "Enterprise-KI für nachvollziehbare Prozesse",
  ogTitle: sites.corporate.defaultTitle,
  description: sites.corporate.defaultDescription,
});

const consulting = [
  {
    title: "SAP Consulting",
    body: "Konzeption, Implementierung und Optimierung in SAP MM, PP und QM – von der Aufnahme bis zum Go-Live.",
    href: "/unternehmen#consulting",
  },
  {
    title: "IT Consulting",
    body: "Digitalisierungsstrategie, Cloud-Migration und IT-Infrastruktur für mittelständische Organisationen.",
    href: "/unternehmen#consulting",
  },
  {
    title: "Quality & Risk Management",
    body: "Qualitätssicherung, Risikomanagement und Projektsteuerung nach etablierten Standards.",
    href: "/unternehmen#consulting",
  },
];

const trust = [
  {
    title: "Mandantentrennung auf Datenbankebene",
    body: "Row-Level-Security trennt Analyseläufe, Dokumente und Nachweise je Mandant – nicht erst in der Anwendungslogik.",
  },
  {
    title: "Menschliche Freigabe als Zustand",
    body: "KI-Ergebnisse bleiben Entwürfe, bis eine berechtigte Person sie annimmt. Ohne Freigabe entsteht kein Export.",
  },
  {
    title: "Nachweisbare Herkunft",
    body: "Quelle, Fundstelle, Modell, Prompt-Version, Zeitpunkt und Prüfer bleiben mit dem Ergebnis verbunden.",
  },
  {
    title: "Rollen statt pauschaler Zugriffe",
    body: "Upload, Prüfung, Freigabe, Export und Verwaltung sind getrennte Rechte mit getrennten Rollen.",
  },
  {
    title: "Fail-closed statt Best Effort",
    body: "Unklare Befunde, fehlende Quellen oder unvollständige Daten blockieren den Ablauf, statt ein plausibles Ergebnis zu erzeugen.",
  },
  {
    title: "Grenzen, die im Produkt stehen",
    body: "Keine automatische Zertifizierungs-, Konformitäts- oder Rechtsentscheidung. Die Verantwortung bleibt bei der Organisation.",
  },
];

export default function CorporateHome() {
  const flowcheck = productBySlug("flowcheck")!;
  const releaseproof = productBySlug("releaseproof")!;
  const industryProducts = productsByDivision("industry");
  const legalProducts = productsByDivision("legal");

  return (
    <SiteChrome siteKey="corporate" path="/">
      <JsonLd data={organizationSchema()} />

      {/* 1 — Hero */}
      <section className="sbs-inverse relative overflow-hidden" data-surface="inverse">
        <div className="sbs-container sbs-section--hero sbs-section">
          <div className="grid grid-cols-[minmax(0,1fr)] items-center gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-16">
            <div className="sbs-measure-hero flex flex-col gap-6">
              <Eyebrow>SBS Deutschland · Industrie und Legal</Eyebrow>
              <h1 className="sbs-display text-[var(--sbs-text-inverse)]">
                KI-Systeme für Prozesse, die nachvollziehbar bleiben müssen.
              </h1>
              <p className="sbs-lead">
                Wir bauen Dokumentintelligenz und Automatisierung für zwei Bereiche, in denen ein
                Ergebnis ohne Herkunft wertlos ist: technische Nachweise in der Industrie und
                Vertrags- und Governance-Arbeit im Recht. Jedes Ergebnis führt Quelle, Modell,
                Prüfschritt und Zeitpunkt mit sich.
              </p>
              <div className="flex flex-wrap gap-3 pt-1">
                <Button href={linkFor(PAGE_PATH, "/industrie")} size="lg">
                  SBS Industrie ansehen
                </Button>
                <Button href={linkFor(PAGE_PATH, "/legal")} variant="inverse" size="lg">
                  SBS Legal ansehen
                </Button>
              </div>
            </div>

            <div className="lg:pl-4">
              <SbsNetworkGraphic currentPath="/" />
            </div>
          </div>
        </div>
      </section>

      {/* 2 — Division split */}
      <Section tone="page" rhythm="wide" labelledBy="bereiche">
        <SectionHeader
          id="bereiche"
          eyebrow="Struktur"
          title="Ein Unternehmen, zwei Geschäftsbereiche"
          lead="Industrie und Legal lösen unterschiedliche Aufgaben, aber sie folgen demselben Ablauf: Dokument, Extraktion, Nachweis, menschliche Prüfung, Ausgabe."
          className="mb-10"
        />
        <DivisionSplit currentPath="/" />
      </Section>

      {/* 3 — One technical foundation */}
      <Section tone="sunken" labelledBy="grundlage">
        <SectionHeader
          id="grundlage"
          eyebrow="Gemeinsame Grundlage"
          title="Sechs Schichten, die in beiden Bereichen gleich funktionieren"
          lead="Was ein Produkt fachlich tut, unterscheidet sich. Wie es verarbeitet, prüft und protokolliert, ist überall dasselbe."
          className="mb-10"
        />
        <FoundationGrid />
        <div className="mt-10">
          <Button href="/plattform" variant="secondary">
            Technische Grundlage im Detail
          </Button>
        </div>
      </Section>

      {/* 4 — Product ecosystem */}
      <Section tone="page" rhythm="wide" labelledBy="produkte">
        <SectionHeader
          id="produkte"
          eyebrow="Produkte"
          title="Vier Produkte, nach Geschäftsbereich geordnet"
          lead="Kein Produktraster, sondern zwei Produktlinien mit eigener Fachlogik – und ein geschäftsübergreifendes Automatisierungsprodukt darunter."
          className="mb-10"
        />

        <div className="flex flex-col gap-10">
          <div>
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
              <h3 className="sbs-h3">SBS Industrie</h3>
              <Link
                href={linkFor(PAGE_PATH, "/industrie/produkte")}
                className="inline-flex min-h-9 items-center text-[0.875rem] font-[560] text-[var(--sbs-accent)] hover:text-[var(--sbs-accent-strong)]"
              >
                Alle Industrie-Produkte →
              </Link>
            </div>
            <div data-division="industry" className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-2">
              {industryProducts.map((product) => (
                <ProductCard key={product.slug} product={product} currentPath="/" />
              ))}
            </div>
          </div>

          <div>
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
              <h3 className="sbs-h3">SBS Legal</h3>
              <Link
                href={linkFor(PAGE_PATH, "/legal/produkte")}
                className="inline-flex min-h-9 items-center text-[0.875rem] font-[560] text-[var(--sbs-accent)] hover:text-[var(--sbs-accent-strong)]"
              >
                Alle Legal-Produkte →
              </Link>
            </div>
            <div data-division="legal" className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-2">
              {legalProducts.map((product) => (
                <ProductCard key={product.slug} product={product} currentPath="/" />
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* 5 — Shared automation */}
      <Section tone="sunken" labelledBy="shared">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1fr)] lg:gap-16">
          <SectionHeader
            id="shared"
            eyebrow="Geschäftsübergreifend"
            title="Finance & Backoffice Automation"
            lead="Belegverarbeitung gehört weder ausschließlich zur Industrie noch zum Recht. FlowCheck AI+ läuft deshalb auf Unternehmensebene und wird dort verlinkt, wo es fachlich gebraucht wird."
          />
          <div className="flex flex-col gap-5">
            <div className="rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-elevated)] p-6">
              <h3 className="sbs-h4">{flowcheck.name}</h3>
              <p className="mt-2 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
                {flowcheck.description}
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Button href={linkFor(PAGE_PATH, flowcheck.href)} variant="secondary">
                  FlowCheck AI+ entdecken
                </Button>
                <Button href={linkFor(PAGE_PATH, flowcheck.primaryAction.href)} variant="quiet" external>
                  {flowcheck.primaryAction.label}
                </Button>
              </div>
            </div>
            <p className="text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
              Innerhalb von SBS Industrie ist FlowCheck AI+ als Backoffice-Baustein verlinkt – es ist
              nicht die Kernidentität des Geschäftsbereichs.
            </p>
          </div>
        </div>
      </Section>

      {/* 6 — Enterprise architecture */}
      <Section tone="inverse" rhythm="wide" labelledBy="architektur">
        <SectionHeader
          id="architektur"
          eyebrow="Architektur"
          title="Derselbe Weg – vom Eingang bis zum Nachweis"
          lead="Was in NormPilot eine Evidence-Zeile ist und in KanzleiAI ein Finding, durchläuft dieselben sechs Stationen. Station vier ist immer ein Mensch."
          className="mb-12"
        />
        <ArchitectureFlow tone="inverse" />
      </Section>

      {/* 7 — Academy */}
      <Section tone="page" labelledBy="academy-titel" id="academy">
        <div data-division="academy" className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1fr)] lg:gap-16">
          <SectionHeader
            id="academy-titel"
            eyebrow="SBS Academy"
            title="Wissen nicht nur automatisieren, sondern aufbauen"
            lead="Die Lernpfade von SBS sind eigenständige Angebote unter eigenen Marken und eigenen Domains. Sie gehören weder zu Industrie noch zu Legal."
          />
          <ul className="grid grid-cols-[minmax(0,1fr)] gap-4 sm:grid-cols-2">
            {academyCourses.map((course) => (
              <li key={course.slug} id={course.slug} className="flex flex-col justify-between gap-5 rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-elevated)] p-6">
                <div className="flex flex-col gap-2">
                  <h3 className="sbs-h4">{course.name}</h3>
                  <p className="text-[0.9375rem] leading-[1.55] text-[var(--sbs-text-secondary)]">
                    {course.tagline}
                  </p>
                </div>
                <Button href={course.url} variant="secondary" external>
                  {course.domain} öffnen
                </Button>
              </li>
            ))}
          </ul>
        </div>
        <div className="mt-8">
          <Button href="/academy" variant="quiet">
            SBS Academy ansehen
          </Button>
        </div>
      </Section>

      {/* 8 — Consulting, deliberately secondary */}
      <Section tone="sunken" rhythm="tight" labelledBy="consulting">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-8 lg:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)] lg:gap-14">
          <div className="flex flex-col gap-3">
            <Eyebrow>Beratung</Eyebrow>
            <h2 id="consulting" className="sbs-h3">
              Beratung neben der Produktarbeit
            </h2>
            <p className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              SBS Deutschland ist aus Beratungsarbeit entstanden und führt sie weiter – ohne sie mit
              den Produkten gleichzusetzen.
            </p>
          </div>
          <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-6 sm:grid-cols-3">
            {consulting.map((item) => (
              <li key={item.title} className="flex flex-col gap-2 border-t border-[var(--sbs-border)] pt-4">
                <h3 className="text-[0.9375rem] font-[620] text-[var(--sbs-text-primary)]">{item.title}</h3>
                <p className="text-[0.8125rem] leading-[1.55] text-[var(--sbs-text-secondary)]">{item.body}</p>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      {/* 9 — Trust through mechanism */}
      <Section tone="page" labelledBy="trust">
        <SectionHeader
          id="trust"
          eyebrow="Vertrauen"
          title="Was wir belegen können — und was nicht"
          lead="Auf dieser Seite stehen keine Zertifikatslogos, keine Kundenlogos und keine Genauigkeitsquoten. Was hier steht, lässt sich im Produkt zeigen."
          className="mb-10"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-8 md:grid-cols-2 lg:grid-cols-3">
          {trust.map((item) => (
            <li key={item.title} className="flex flex-col gap-2.5 border-l-2 border-[var(--sbs-accent)] pl-4">
              <h3 className="text-[0.9375rem] font-[620] text-[var(--sbs-text-primary)]">{item.title}</h3>
              <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{item.body}</p>
            </li>
          ))}
        </ul>
        <p className="mt-8 max-w-[46rem] text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
          Zertifizierungen, Testate, Penetrationstests und vertragliche Zusagen benennen wir erst,
          wenn ein abgeschlossenes Prüfverfahren vorliegt. Aussagen zu DSGVO, GoBD, E-Rechnung und
          EU AI Act sind einsatz- und vertragsabhängig und bleiben fachlich zu prüfen.
        </p>
        <div className="mt-8">
          <Button href="/sicherheit" variant="secondary">
            Sicherheit und Datenwege ansehen
          </Button>
        </div>
      </Section>

      {/* SBS Labs — only because a real independent product exists */}
      <Section tone="sunken" rhythm="tight" labelledBy="labs">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between lg:gap-12">
          <div className="flex max-w-[34rem] flex-col gap-2.5">
            <Eyebrow>SBS Labs</Eyebrow>
            <h2 id="labs" className="sbs-h3">
              Eigenständige Produkte außerhalb der beiden Bereiche
            </h2>
            <p className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              {releaseproof.name} passt weder zu Industrie noch zu Legal — deshalb wird es dort auch
              nicht einsortiert. {releaseproof.tagline}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button href={linkFor(PAGE_PATH, releaseproof.href)} variant="secondary">
              ReleaseProof ansehen
            </Button>
          </div>
        </div>
      </Section>

      {/* 10 — Final CTA with a real choice */}
      <Section tone="inverse" rhythm="wide" labelledBy="cta">
        <div className="flex flex-col items-center gap-10 text-center">
          <SectionHeader
            id="cta"
            eyebrow="Nächster Schritt"
            title="Welche Herausforderung möchten Sie lösen?"
            lead="Wählen Sie den Bereich, der Ihrem Vorhaben entspricht — die Anfrage kommt vorbelegt bei den richtigen Personen an."
            align="center"
          />
          <ul className="grid grid-cols-[minmax(0,1fr)] w-full gap-4 md:grid-cols-3">
            {[
              {
                title: "Industrie",
                body: "Audit-Nachweise, technische Dokumentation, Service und Operations.",
                href: "/industrie/kontakt?division=industry",
                cta: "Industrie-Anfrage",
              },
              {
                title: "Legal",
                body: "Vertragsanalyse, Legal Operations, AI Governance und Compliance-Evidence.",
                href: "/legal/kontakt?division=legal",
                cta: "Legal-Anfrage",
              },
              {
                title: "Allgemeine Anfrage",
                body: "Beratung, geschäftsübergreifende Automatisierung oder ein anderes Anliegen.",
                href: "/kontakt",
                cta: "Kontakt aufnehmen",
              },
            ].map((choice) => (
              <li
                key={choice.title}
                className="flex flex-col items-start gap-3 rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-inverse)] bg-[var(--sbs-bg-inverse-elevated)] p-6 text-left"
              >
                <h3 className="sbs-h4 text-[var(--sbs-text-inverse)]">{choice.title}</h3>
                <p className="flex-1 text-[0.875rem] leading-[1.55] text-[var(--sbs-text-inverse-secondary)]">
                  {choice.body}
                </p>
                <Button href={linkFor(PAGE_PATH, choice.href)} variant="inverse">
                  {choice.cta}
                </Button>
              </li>
            ))}
          </ul>
        </div>
      </Section>
    </SiteChrome>
  );
}
