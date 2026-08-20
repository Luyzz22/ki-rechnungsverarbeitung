# Redirect Matrix

Every URL that carried value on the previous site keeps a permanent destination.
The rules live in `infra/nginx/snippets/sbs-web-redirects.conf` and are included
only in the corporate server block — the two division hosts are new and have no
legacy URL space.

All redirects are **301** (permanent). The application-level host redirects
described in `domain-routing.md` are **308**, because they must preserve the
request method.

## Corporate pages

| Old URL | New URL | Status |
| --- | --- | --- |
| `/sbshomepage/` | `https://sbsdeutschland.com/` | 301 |
| `/sbshomepage` | `https://sbsdeutschland.com/` | 301 |
| `/sbshomepage/index.html` | `https://sbsdeutschland.com/` | 301 |
| `/sbshomepage/unternehmen.html` | `https://sbsdeutschland.com/unternehmen` | 301 |
| `/sbshomepage/kontakt.html` | `https://sbsdeutschland.com/kontakt` | 301 |
| `/sbshomepage/impressum.html` | `https://sbsdeutschland.com/impressum` | 301 |
| `/sbshomepage/datenschutz.html` | `https://sbsdeutschland.com/datenschutz` | 301 |
| `/sbshomepage/agb.html` | `https://sbsdeutschland.com/impressum` | 301 |
| `/sbshomepage/sap-consulting.html` | `https://sbsdeutschland.com/unternehmen#consulting` | 301 |
| `/sbshomepage/it-consulting.html` | `https://sbsdeutschland.com/unternehmen#consulting` | 301 |
| `/sbshomepage/quality-risk-management.html` | `https://sbsdeutschland.com/unternehmen#consulting` | 301 |
| `/sbshomepage/met-pmo.html` | `https://sbsdeutschland.com/unternehmen#consulting` | 301 |
| `/sbshomepage/*` (anything else) | `https://sbsdeutschland.com/` | 301 |

The four consulting pages fold into one section rather than each becoming a
page. §97 of the brief is explicit: a page is justified by its own search intent,
audience, story and conversion path. Four near-identical consulting pages had
one of each between them.

## Product landing pages

| Old URL | New URL | Status |
| --- | --- | --- |
| `/static/landing/` | `https://sbsdeutschland.com/plattform/flowcheck` | 301 |
| `/static/landing/index.html` | `https://sbsdeutschland.com/plattform/flowcheck` | 301 |
| `/static/preise/` | `https://sbsdeutschland.com/plattform/flowcheck` | 301 |
| `/static/landing/hydraulikdoc.html` | `https://industrie.sbsdeutschland.com/produkte/hydraulikdoc` | 301 |
| `/static/landing/hydraulikdoc-enterprise.html` | `…/produkte/hydraulikdoc#architektur` | 301 |
| `/static/landing/hydraulikdoc-docs.html` | `…/produkte/hydraulikdoc` | 301 |
| `/static/landing/hydraulikdoc-partners.html` | `…/produkte/hydraulikdoc` | 301 |
| `/loesungen/vertragsanalyse*` | `https://legal.sbsdeutschland.com/loesungen/vertragsanalyse` | 301 |

## Trust and legal pages

| Old URL | New URL | Status |
| --- | --- | --- |
| `/static/landing/sicherheit.html` | `https://sbsdeutschland.com/sicherheit` | 301 |
| `/static/landing/compliance.html` | `https://sbsdeutschland.com/sicherheit` | 301 |
| `/static/landing/avv.html` | `https://sbsdeutschland.com/sicherheit` | 301 |
| `/static/landing/impressum.html` | `https://sbsdeutschland.com/impressum` | 301 |
| `/static/landing/datenschutz.html` | `https://sbsdeutschland.com/datenschutz` | 301 |
| `/static/landing/agb.html` | `https://sbsdeutschland.com/impressum` | 301 |
| `/static/landing/api.html` | `https://app.sbsdeutschland.com/docs` | 301 |

The Impressum and Datenschutzerklärung are not summarised or rewritten in the
new design. `scripts/extract-legal.mjs` reads the reviewed source documents in
`web/static/landing/` and emits their headings and paragraphs verbatim into
`src/content/legal/`. Re-run it whenever the source documents change:

```bash
node scripts/extract-legal.mjs
```

## Application entry points

These belong to the running invoice application and must keep working
unchanged. They are redirected rather than proxied so the marketing layer never
sits in front of an authenticated flow.

| Old URL | New URL | Status |
| --- | --- | --- |
| `/login` | `https://app.sbsdeutschland.com/login` | 301 |
| `/demo` | `https://app.sbsdeutschland.com/demo` | 301 |
| `/copilot` | `https://app.sbsdeutschland.com/copilot` | 301 |
| `/mbr/*` | `https://app.sbsdeutschland.com/mbr/*` | 301 |

`app.sbsdeutschland.com` itself is untouched: it keeps its own server block, its
own certificate entry and its own upstream on port 8000.

## Verification after the switch

```bash
for url in \
  https://sbsdeutschland.com/sbshomepage/ \
  https://sbsdeutschland.com/sbshomepage/unternehmen.html \
  https://sbsdeutschland.com/sbshomepage/kontakt.html \
  https://sbsdeutschland.com/static/landing/hydraulikdoc.html \
  https://sbsdeutschland.com/static/landing/datenschutz.html \
  https://sbsdeutschland.com/login ; do
  printf '%-62s ' "$url"
  curl -s -o /dev/null -w '%{http_code} → %{redirect_url}\n' "$url"
done
```

Every line must show `301` and a destination that answers `200`.

## Not redirected

- `chat.sbsdeutschland.com` — the certificate has expired and the widget is not
  part of the new sites. It is neither linked nor redirected; decide separately
  whether to renew or retire it.
- `www.sbsnexus.de` — a separate brand with its own site, out of scope here.
- Anything under `/static/landing/_archive/` or `*.bak2026` — backup artefacts
  that were never public entry points.
