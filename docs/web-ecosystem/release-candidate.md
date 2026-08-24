# Release Candidate

Prepared 2026-08-20. **Not deployed.** No DNS record, no certificate and no
public nginx routing exists for the division hostnames.

## Identity

```
Repository        SBS-Nexus/sbs-web            private, migration complete
Branch            main
Artifact          sbs-web-<short-sha>.tar.gz   ~25 MB packed, ~78 MB unpacked
Built with        node v22.x, Next.js 16.3.1
Reproducible      yes, except three per-build key files — see below
```

The digest is not written here, because it is derived from the commit and a
commit that recorded its own digest could never be correct. The authoritative
values live in the artifact's sidecar:

```bash
cat dist/sbs-web-*.manifest.json     # repository, commit, artifact, sha256, builtAt, node
sha256sum -c dist/sbs-web-*.tar.gz.sha256
```

CI publishes both alongside every build of `main`. The artifact is packed with a
fixed mtime, owner and sort order, and carries only commit-derived facts inside
the tarball; build time and node version live in the sidecar manifest so they
cannot perturb the digest. `next.config.mjs` derives `BUILD_ID` from the commit
rather than letting Next.js generate a random one, because that id is embedded
in every rendered page and otherwise changed all 228 output files on every
build.

Three files still differ between builds and always will:

```
.next/prerender-manifest.json                  draft-mode signing/encryption keys
.next/server/server-reference-manifest.js      server-action encryption key
.next/server/server-reference-manifest.json
```

Next.js generates those cryptographic keys per build. They are deliberately
**not** pinned: a key derivable from the commit is not a key, and this
repository holds no secrets to pin them from. The site uses neither draft mode
nor server actions, so their values never matter.

`./scripts/verify-reproducible.sh` enforces exactly this: it builds twice from
scratch and fails if anything outside that list differs. Verification on the
host is unaffected — it checks the SHA256 of the artifact CI actually
published, not a rebuild.

## Gates

Every gate below ran against the **unpacked artifact** on 127.0.0.1:3100, not
against a development server.

| Gate | Result | Evidence |
| --- | --- | --- |
| Clean clone + `npm ci` | PASS | 371 packages |
| Typecheck | PASS | `tsc --noEmit`, 0 errors |
| Lint | PASS | `eslint .`, 0 errors, 0 warnings |
| Build | PASS | 38 routes; 36 static, 2 host-dependent |
| Artifact reproducibility | PASS | `verify-reproducible.sh`: two clean builds identical except three per-build key files |
| Links | PASS | 55 pages across 3 hostnames, 0 dead, 6/6 external product URLs 200 |
| Content / claim guard | PASS | 23 routes, 0 findings |
| Responsive | PASS | 27 routes × 6 viewports, no overflow, no small tap target, one `h1` |
| Accessibility | PASS | 25 routes; landmarks, heading order, focus, keyboard menus, reduced motion |
| Security — dependencies | PASS | `npm audit --omit=dev`: 0 vulnerabilities |
| Security — headers | PASS | verified through real nginx, exactly one value per header |
| nginx configuration | PASS | `nginx -t` on nginx 1.26.3, the host's version; and on 1.24.0 through the compatibility rewrite |
| `--check` is read-only | PASS | `/etc/nginx` hashed before and after; identical |
| Deployment gates B–F | PASS | accept on 303; roll back on 500, on `inactive`, and before unpacking if already unhealthy; no nginx reload |
| Legacy redirects | PASS | 29 paths, all 301 to a live destination |
| systemd unit | PASS | `systemd-analyze verify` |
| Read-only filesystem | PASS | every route answers with the release tree read-only |
| Deploy health matrix | PASS | 12/12 checks the deploy script runs before activating |

## Measurements

```
First load, gzip        283 KB   (27 HTML + 189 JS/CSS + 66 fonts, 0 images)
Server process RSS      159 MB   against MemoryHigh=384M / MemoryMax=512M
Cumulative layout shift 0.0000
```

Measured in a sandbox, not on the production host and not with real users.

## Known limitations

1. **Not deployed anywhere.** Steps 2 to 6 of `deployment.md` have not been run.
2. **No Lighthouse run** — unavailable in this environment. The §65 targets are
   not claimed as achieved; only CLS has a real measurement.
3. **No automated colour-contrast audit.** The palette was designed against
   WCAG 2.2 AA ratios but not machine-verified.
4. **The host's own nginx configuration is unknown.** `enable-nginx.sh --check`
   must be run there before applying: it detects the two host-specific unknowns,
   an existing `default_server` and IPv6 availability. The check writes nothing —
   it stages a complete candidate in a temporary prefix and validates it there,
   and `infra/tests/check-only-immutability.sh` proves the tree is byte-for-byte
   identical afterwards.
5. **`unsafe-inline` remains in `script-src`** — required by Next.js App Router
   unless static rendering is abandoned. Accepted, with the reasoning recorded
   in the CSP snippet and the review.
6. **AuftragsKI is still absent** — no code, deployment or domain has been found
   for it in any accessible repository.
7. **`SBS-Nexus/*` sibling repositories were never audited** — outside session
   scope. None is the deployment target of a live domain found during the audit.

## Repository status

Migration **complete**. `SBS-Nexus/sbs-web` is private and its `main` branch is
the authoritative history for this layer.

```
origin   https://github.com/SBS-Nexus/sbs-web.git
main     f24fcee4c4543470a0345ac6086ac41b358137db
```

The extraction was verified lossless: the subtree split reproduced tree hash
`b12b6ed43ded22ce246656494db36f8fe6965ece`, identical to the source directory.

### Recovery sources

Kept deliberately, not leftovers. Do not delete them until the site has been
publicly live and stable:

| Where | What it holds |
| --- | --- |
| `Luyzz22/ki-rechnungsverarbeitung` @ `claude/sbs-deutschland-ecosystem-rebuild-824fi4` | The original rebuild branch at `fbdf56bacd117163dce18e24893977f00ec1f109`, with `sbs-web/` still a subdirectory. Untouched. |
| `Luyzz22/ki-rechnungsverarbeitung` @ `claude/sbs-web-standalone` | The extracted history exactly as it was pushed to the new origin. Superseded by `SBS-Nexus/sbs-web` and safe to delete once that repository is backed up. |

To re-create the standalone repository from the source branch, should that ever
be necessary:

```bash
git clone --branch claude/sbs-web-standalone --single-branch \
  https://github.com/Luyzz22/ki-rechnungsverarbeitung.git sbs-web
cd sbs-web
git remote set-url origin https://github.com/SBS-Nexus/sbs-web.git
git branch -m claude/sbs-web-standalone main
git push -u origin main
```

## Production host

Measured on the host on 2026-08-20, read-only:

```
OS         Ubuntu 25.04 (Plucky)
nginx      1.26.3
Memory     1.9 GiB total, ~1.0 GiB available
Disk       ~34 GB free on /
invoice-app.service   active, 127.0.0.1:8000 -> HTTP 303
app.sbsdeutschland.com  HTTP 303      sbsdeutschland.com  HTTP 301
Free ports 3100 (sbs-web), 3199 (staging health check)
```

Earlier revisions assumed Ubuntu 24.04 with nginx 1.24.0. That was an inference
from the OS, never a measurement, and it was wrong. Everything that depended on
it has been corrected; test evidence gathered on 1.24.0 is still quoted where it
is accurate and labelled as historical.

**Node is a precondition, never an action.** Nothing in this repository installs
or upgrades node. Before the first deployment, verify it on the host by hand:

```bash
command -v node
node --version        # must be >= 20
```

`deploy-artifact.sh` additionally resolves the interpreter the systemd unit will
actually use — `/usr/bin/env node` resolves against systemd's PATH, not root's —
checks that one too, and runs the staging health check with it.
