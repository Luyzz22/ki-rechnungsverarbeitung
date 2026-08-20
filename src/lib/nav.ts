import { products } from "@/content/products";
import { solutionsByDivision } from "@/content/solutions";
import { academyCourses } from "@/content/academy";
import type { SiteKey } from "@/content/site";

export type NavLink = {
  label: string;
  href: string;
  description?: string;
  external?: boolean;
};

export type NavColumn = {
  title: string;
  links: NavLink[];
};

export type NavItem = {
  label: string;
  href?: string;
  /** Presence of columns turns the item into a mega-menu trigger. */
  columns?: NavColumn[];
  /** Optional featured panel in the right-hand column of the mega menu. */
  featured?: {
    eyebrow: string;
    title: string;
    body: string;
    href: string;
    graphic: "network" | "evidence" | "contract";
  };
};

const productLink = (slug: string): NavLink => {
  const product = products.find((entry) => entry.slug === slug);
  if (!product) throw new Error(`Unknown product in navigation: ${slug}`);
  return { label: product.name, href: product.href, description: product.tagline };
};

const industryProductLinks: NavLink[] = ["normpilot", "hydraulikdoc"].map(productLink);
const legalProductLinks: NavLink[] = ["kanzleiai", "compliancehub"].map(productLink);

const industrySolutionLinks: NavLink[] = solutionsByDivision("industry").map((solution) => ({
  label: solution.title,
  href: solution.href,
}));

const legalSolutionLinks: NavLink[] = solutionsByDivision("legal").map((solution) => ({
  label: solution.title,
  href: solution.href,
}));

const academyLinks: NavLink[] = academyCourses.map((course) => ({
  label: course.name,
  href: `/academy#${course.slug}`,
  description: course.tagline,
}));

export const corporateNav: NavItem[] = [
  {
    label: "Industrie",
    href: "/industrie",
    columns: [
      { title: "Produkte", links: industryProductLinks },
      { title: "Lösungen", links: industrySolutionLinks },
      {
        title: "Bereich",
        links: [
          { label: "SBS Industrie Übersicht", href: "/industrie" },
          { label: "Plattform & Architektur", href: "/industrie/plattform" },
          { label: "Kontakt Industrie", href: "/industrie/kontakt" },
        ],
      },
    ],
    featured: {
      eyebrow: "Ausgewählt",
      title: "NormPilot Industrie",
      body: "Bestandsdokumente werden zur Evidence Matrix – mit Fundstelle, Gap Finding und Maßnahme.",
      href: "/industrie/produkte/normpilot",
      graphic: "evidence",
    },
  },
  {
    label: "Legal",
    href: "/legal",
    columns: [
      { title: "Produkte", links: legalProductLinks },
      { title: "Lösungen", links: legalSolutionLinks },
      {
        title: "Bereich",
        links: [
          { label: "SBS Legal Übersicht", href: "/legal" },
          { label: "Governance & Datenwege", href: "/legal/governance" },
          { label: "Kontakt Legal", href: "/legal/kontakt" },
        ],
      },
    ],
    featured: {
      eyebrow: "Ausgewählt",
      title: "KanzleiAI",
      body: "Lokale Redaction, minimierter Payload, Human Review pro Finding – die Datenwege sind Teil des Produkts.",
      href: "/legal/produkte/kanzleiai",
      graphic: "contract",
    },
  },
  {
    label: "Plattform",
    href: "/plattform",
    columns: [
      {
        title: "Gemeinsame Grundlage",
        links: [
          { label: "Technische Grundlage", href: "/plattform", description: "Dokumente, Extraktion, Human Review, Audit Trail" },
          { label: "Sicherheit & Datenwege", href: "/sicherheit", description: "Mandantentrennung, Rollen, Protokollierung" },
        ],
      },
      {
        title: "Geschäftsübergreifend",
        links: [productLink("flowcheck")],
      },
      {
        title: "SBS Labs",
        links: [productLink("releaseproof")],
      },
    ],
    featured: {
      eyebrow: "Architektur",
      title: "Ein Weg, drei Geschäftsbereiche",
      body: "Dokument, Extraktion, Modell, menschliche Prüfung, Ausgabe, Nachweis – in Industrie und Legal derselbe Ablauf.",
      href: "/plattform",
      graphic: "network",
    },
  },
  {
    label: "Academy",
    href: "/academy",
    columns: [
      { title: "Lernpfade", links: academyLinks },
      {
        title: "Über die Academy",
        links: [
          { label: "SBS Academy", href: "/academy", description: "Eigenständige Lernangebote, unabhängig von Industrie und Legal" },
        ],
      },
    ],
  },
  {
    label: "Unternehmen",
    href: "/unternehmen",
    columns: [
      {
        title: "SBS Deutschland",
        links: [
          { label: "Über uns", href: "/unternehmen" },
          { label: "Beratung & Services", href: "/unternehmen#consulting" },
          { label: "Sicherheit & Datenwege", href: "/sicherheit" },
          { label: "Kontakt", href: "/kontakt" },
        ],
      },
      {
        title: "Rechtliches",
        links: [
          { label: "Impressum", href: "/impressum" },
          { label: "Datenschutz", href: "/datenschutz" },
        ],
      },
    ],
  },
];

export const industryNav: NavItem[] = [
  {
    label: "Produkte",
    href: "/industrie/produkte",
    columns: [
      { title: "Produkte", links: industryProductLinks },
      {
        title: "Geschäftsübergreifend",
        links: [productLink("flowcheck")],
      },
    ],
    featured: {
      eyebrow: "Ausgewählt",
      title: "HydraulikDoc",
      body: "Antworten aus dem technischen Handbuch – ohne gültige Quellenmarke entsteht keine Antwort.",
      href: "/industrie/produkte/hydraulikdoc",
      graphic: "evidence",
    },
  },
  {
    label: "Lösungen",
    href: "/industrie/loesungen",
    columns: [{ title: "Nach Aufgabe", links: industrySolutionLinks }],
  },
  { label: "Plattform", href: "/industrie/plattform" },
  { label: "Kontakt", href: "/industrie/kontakt" },
];

export const legalNav: NavItem[] = [
  {
    label: "Produkte",
    href: "/legal/produkte",
    columns: [{ title: "Produkte", links: legalProductLinks }],
    featured: {
      eyebrow: "Ausgewählt",
      title: "ComplianceHub",
      body: "KI-System-Inventar, Risikoklassifikation nach Art. 6, Policy-Auswertung und Nachweise in einem Bestand.",
      href: "/legal/produkte/compliancehub",
      graphic: "contract",
    },
  },
  {
    label: "Lösungen",
    href: "/legal/loesungen",
    columns: [{ title: "Nach Aufgabe", links: legalSolutionLinks }],
  },
  { label: "Governance", href: "/legal/governance" },
  { label: "Kontakt", href: "/legal/kontakt" },
];

export function navForSite(site: SiteKey): NavItem[] {
  if (site === "industry") return industryNav;
  if (site === "legal") return legalNav;
  return corporateNav;
}

export function ctaForSite(site: SiteKey): NavLink {
  if (site === "industry") return { label: "Demo anfragen", href: "/industrie/kontakt" };
  if (site === "legal") return { label: "Demo anfragen", href: "/legal/kontakt" };
  return { label: "Demo anfragen", href: "/kontakt" };
}
