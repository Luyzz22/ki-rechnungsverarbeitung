# Release Candidate

Prepared 2026-08-20. **Not deployed.** No DNS record, no certificate and no
public nginx routing exists for the division hostnames.

## Identity

```
Repository        SBS-Nexus/sbs-web            (see "Repository status" below)
Branch            main
Artifact          sbs-web-<short-sha>.tar.gz   ~25 MB packed, ~78 MB unpacked
Built with        node v22.x, Next.js 16.3.1
Reproducible      yes — a second build of the same commit yields the same digest
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
cannot perturb the digest. Rebuilding the same commit anywhere reproduces the
same SHA256, which is what makes a CI artifact verifiable on the host.

## Gates

Every gate below ran against the **unpacked artifact** on 127.0.0.1:3100, not
against a development server.

| Gate | Result | Evidence |
| --- | --- | --- |
| Clean clone + `npm ci` | PASS | 371 packages |
| Typecheck | PASS | `tsc --noEmit`, 0 errors |
| Lint | PASS | `eslint .`, 0 errors, 0 warnings |
| Build | PASS | 38 routes; 36 static, 2 host-dependent |
| Artifact reproducibility | PASS | identical SHA256 on rebuild |
| Links | PASS | 55 pages across 3 hostnames, 0 dead, 6/6 external product URLs 200 |
| Content / claim guard | PASS | 23 routes, 0 findings |
| Responsive | PASS | 27 routes × 6 viewports, no overflow, no small tap target, one `h1` |
| Accessibility | PASS | 25 routes; landmarks, heading order, focus, keyboard menus, reduced motion |
| Security — dependencies | PASS | `npm audit --omit=dev`: 0 vulnerabilities |
| Security — headers | PASS | verified through real nginx, exactly one value per header |
| nginx configuration | PASS | `nginx -t` on nginx 1.24.0 |
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
   an existing `default_server` and IPv6 availability.
5. **`unsafe-inline` remains in `script-src`** — required by Next.js App Router
   unless static rendering is abandoned. Accepted, with the reasoning recorded
   in the CSP snippet and the review.
6. **AuftragsKI is still absent** — no code, deployment or domain has been found
   for it in any accessible repository.
7. **`SBS-Nexus/*` sibling repositories were never audited** — outside session
   scope. None is the deployment target of a live domain found during the audit.

## Repository status

The target repository `SBS-Nexus/sbs-web` **could not be created**: the GitHub
App authorised for this session is not permitted to create repositories in the
`SBS-Nexus` organisation.

```
POST https://api.github.com/orgs/SBS-Nexus/repos
403 Resource not accessible by integration
```

Read access to the organisation works and existing `SBS-Nexus` repositories
report `can_push: true`; only repository *creation* is refused. The session also
cannot attach a repository from a second owner, so it could not have pushed
there in any case.

The extraction itself is complete and verified. To finish the migration:

```bash
# 1. Create the repository — via the GitHub UI, or with a token that has
#    administration:write on the organisation:
gh repo create SBS-Nexus/sbs-web --private \
  --description "Public web ecosystem for SBS Deutschland"

# 2. Push the prepared history
git clone --branch claude/sbs-web-standalone --single-branch \
  https://github.com/Luyzz22/ki-rechnungsverarbeitung.git sbs-web
cd sbs-web
git remote set-url origin https://github.com/SBS-Nexus/sbs-web.git
git branch -m claude/sbs-web-standalone main
git push -u origin main
```

The branch `claude/sbs-web-standalone` in `Luyzz22/ki-rechnungsverarbeitung`
holds the extracted repository exactly as it should appear at the new origin:
root-level Next.js application, seventeen commits, no reference back to the
source repository. It exists only because the work had to be persisted somewhere
this session was allowed to push; delete it once the migration is done.

`claude/sbs-deutschland-ecosystem-rebuild-824fi4` is untouched at
`fbdf56bacd117163dce18e24893977f00ec1f109` and remains the recovery source.
