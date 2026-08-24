import Link from "next/link";

/**
 * Trust band.
 *
 * Everything here is a checkable fact, because §3 of CLAUDE.md forbids
 * conformity badges and `npm run check:content` fails the build on them. The
 * distinction is deliberate and worth keeping: "DSGVO-konform" is a claim about
 * an operation nobody has audited, while "Sitz in Weinheim" and "Server in
 * Frankfurt" are claims about facts. The second kind is also the more
 * persuasive one, because a buyer can verify it.
 *
 * Sources:
 *   Sitz            src/content/legal/datenschutz.ts (Impressum/Anschrift)
 *   Hosting         docs/web-ecosystem/deployment.md — the production host
 *   Keine Tracker   enforced by the CSP in infra/nginx/snippets and by the
 *                   absence of any third-party script in this repository
 *   DSGVO / AI Act  named as the obligations they are, with the mechanism the
 *                   products provide — never as a certificate
 */

type Item = {
  label: string;
  headline: string;
  body: string;
  href?: string;
};

const items: Item[] = [
  {
    label: "Standort",
    headline: "Weinheim, Deutschland",
    body: "SBS Deutschland GmbH, In der Dell 19, 69469 Weinheim. Entwicklung und Ansprechpartner im Land, nicht nur eine Vertriebsadresse.",
    href: "/unternehmen",
  },
  {
    label: "Betrieb",
    headline: "Server in Frankfurt am Main",
    body: "Die Anwendungen laufen auf Infrastruktur in Deutschland. Wo Daten verarbeitet werden, steht im Verzeichnis der Verarbeitungstätigkeiten — nicht in einer Fußnote.",
    href: "/sicherheit",
  },
  {
    label: "Diese Website",
    headline: "Keine Tracker, keine Cookies",
    body: "Kein Analytics, kein Tag Manager, keine Schriften von fremden Servern. Die Content-Security-Policy verbietet es technisch, nicht nur redaktionell.",
    href: "/datenschutz",
  },
  {
    label: "Rechtsrahmen",
    headline: "DSGVO und EU AI Act als Pflichtenheft",
    body: "Auftragsverarbeitung nach Art. 28 DSGVO, Löschkonzept, Auskunftsfähigkeit. Für den EU AI Act liefern die Produkte die Nachweise, die Ihre Rolle als Betreiber verlangt: Herkunft, Modellversion, Prüfschritt, Freigabe.",
    href: "/sicherheit",
  },
];

export function TrustBand() {
  return (
    <section aria-labelledby="vertrauen" className="sbs-trust-band">
      <div className="sbs-container">
        <h2 id="vertrauen" className="sbs-trust-band__heading">
          Was überprüfbar ist
        </h2>
        <p className="sbs-trust-band__lead">
          Wir führen hier keine Siegel auf, die niemand geprüft hat. Was folgt,
          können Sie nachlesen oder nachmessen.
        </p>

        <ul className="sbs-trust-band__grid">
          {items.map((item, index) => (
            <li
              key={item.headline}
              className="sbs-trust-band__item"
              style={{ "--sbs-stagger": `${index * 70}ms` } as React.CSSProperties}
            >
              <p className="sbs-eyebrow">{item.label}</p>
              <p className="sbs-trust-band__item-headline">{item.headline}</p>
              <p className="sbs-body-sm">{item.body}</p>
              {item.href ? (
                <Link href={item.href} className="sbs-trust-band__link">
                  Nachlesen
                  <span aria-hidden="true" className="sbs-trust-band__link-arrow">→</span>
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
