import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { ProductPage } from "@/components/product/ProductPage";
import { Section, SectionHeader } from "@/components/ui/Section";
import { productBySlug } from "@/content/products";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

const product = productBySlug("flowcheck")!;

export const metadata: Metadata = pageMetadata({
  path: "/plattform/flowcheck",
  title: "FlowCheck AI+",
  description:
    "FlowCheck AI+ erfasst Eingangsrechnungen, prüft auf Dubletten und Plausibilität, schlägt eine Kontierung nach SKR03/SKR04 vor und exportiert nach menschlicher Freigabe DATEV-kompatibel.",
});

const roles = [
  { role: "owner", scope: "Vollzugriff, Abrechnung, Organisation löschen" },
  { role: "admin", scope: "Nutzerverwaltung und Einstellungen" },
  { role: "manager", scope: "Rechnungen freigeben, Teamberichte einsehen" },
  { role: "member", scope: "Hochladen und eigene Daten einsehen" },
  { role: "viewer", scope: "Nur lesender Zugriff auf zugewiesene Daten" },
];

export default function FlowCheckPage() {
  return (
    <SiteChrome siteKey="corporate" path="/plattform/flowcheck">
      <JsonLd
        data={breadcrumbSchema([
          { name: "Plattform", path: "/plattform" },
          { name: "FlowCheck AI+", path: "/plattform/flowcheck" },
        ])}
      />
      <ProductPage
        product={product}
        currentPath="/plattform/flowcheck"
        divisionLabel="Plattform"
        divisionHref="/plattform"
        extraSections={
          <Section tone="page" rhythm="tight" labelledBy="rollen">
            <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-14">
              <SectionHeader
                id="rollen"
                eyebrow="Rollen"
                title="Fünf Rollen, fünf Umfänge"
                lead="Upload, Freigabe, Berichte und Verwaltung sind getrennte Rechte. Wer hochladen darf, darf damit noch nicht freigeben."
              />
              <div className="sbs-scroll-x">
                <table className="w-full min-w-[26rem] border-collapse text-left">
                  <caption className="sr-only">Rollen und ihr Berechtigungsumfang in FlowCheck AI+</caption>
                  <thead>
                    <tr className="border-b border-[var(--sbs-border)]">
                      <th scope="col" className="sbs-mono pb-2 pr-6 text-[0.6875rem] font-[500] uppercase tracking-[0.1em] text-[var(--sbs-text-muted)]">
                        Rolle
                      </th>
                      <th scope="col" className="sbs-mono pb-2 text-[0.6875rem] font-[500] uppercase tracking-[0.1em] text-[var(--sbs-text-muted)]">
                        Umfang
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {roles.map((entry) => (
                      <tr key={entry.role} className="border-b border-[var(--sbs-border-subtle)] last:border-0">
                        <th scope="row" className="sbs-mono py-3 pr-6 text-[0.8125rem] font-[500] text-[var(--sbs-accent-strong)]">
                          {entry.role}
                        </th>
                        <td className="py-3 text-[0.875rem] leading-[1.5] text-[var(--sbs-text-secondary)]">
                          {entry.scope}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Section>
        }
      />
    </SiteChrome>
  );
}
