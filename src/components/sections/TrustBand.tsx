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
 * Each claim is scoped to what was actually measured, which is narrower than
 * it is tempting to write:
 *
 *   Sitz       The registered address in src/content/legal/datenschutz.ts. A
 *              registered seat evidences the seat. It does not evidence where
 *              development happens, so this no longer says that.
 *   Betrieb    Scoped to the public web layer on the Frankfurt production host
 *              (docs/web-ecosystem/deployment.md). It says nothing about every
 *              product or any third-party provider, because nothing here
 *              measures those.
 *   Skripte    Verified, not assumed: the built HTML contains no external
 *              <script src>, and no route on any of the three hosts returns a
 *              Set-Cookie header. Note the CSP is named only as an additional
 *              limit on resources — a Content-Security-Policy cannot prevent
 *              first-party cookies, so "keine Cookies" would not have followed
 *              from it. Re-verify with infra/tests/nginx-gates.sh and by
 *              probing Set-Cookie before restoring any stronger wording.
 *   Recht      Names the mechanisms the products provide and states plainly
 *              that which duties apply depends on system, role and context.
 *              No conformity promise, no legal advice, no guarantee.
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
    body: "SBS Deutschland GmbH, In der Dell 19, 69469 Weinheim. Eingetragener Sitz und Anschrift im Impressum.",
    href: "/unternehmen",
  },
  {
    label: "Betrieb",
    headline: "Web-Infrastruktur in Frankfurt",
    body: "Der öffentliche SBS-Web-Layer wird derzeit auf dem Produktionsserver in Frankfurt am Main betrieben. Datenwege einzelner Produkte und angebundener Dienste werden separat dokumentiert.",
    href: "/sicherheit",
  },
  {
    label: "Diese Website",
    headline: "Keine externen Analytics- oder Tracking-Skripte",
    body: "Die öffentliche SBS-Website lädt derzeit keine Analytics-, Tag-Manager- oder extern gehosteten Font-Skripte. Die restriktive Content-Security-Policy begrenzt zusätzlich zulässige Ressourcen.",
    href: "/datenschutz",
  },
  {
    label: "Rechtsrahmen",
    headline: "DSGVO und EU AI Act als Pflichtenheft",
    body: "Die Produkte unterstützen nachvollziehbare Governance-Prozesse durch Herkunftsangaben, Modellversionen, Prüfschritte und dokumentierte Freigaben. Welche gesetzlichen Pflichten im konkreten Einsatz gelten, hängt von System, Rolle und Nutzungskontext ab.",
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
