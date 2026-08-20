# Deployment

Target host: `207.154.200.239`, Ubuntu 24.04, Frankfurt.
The invoice application on port 8000 must keep running throughout.

> This runbook has **not** been executed. The session that produced this code
> had no shell on the DigitalOcean host, and `CLAUDE.md` §2.1 forbids touching
> `/etc` from the repository workspace. Everything below is prepared as
> repository-managed configuration with an exact diff and a rollback, to be
> applied from an authorised infrastructure context.

## Order of operations

The sequence is chosen so that nothing user-visible changes until the new stack
has already proven itself on the host (§57).

```
1. Deploy the application            → nothing public changes
2. Verify locally on port 3100       → nothing public changes
3. Create the two DNS records        → new hostnames start resolving, no TLS yet
4. Expand the certificate            → new hostnames get TLS
5. Enable the nginx configuration    → the switch
6. Verify redirects and both apps
```

Steps 1 and 2 are safe to run at any time. Step 5 is the only one that changes
what a visitor sees, and it is a single symlink plus a reload.

## 0. Record the current state

`infra/scripts/deploy.sh` does this automatically and writes it to
`/var/log/sbs-web/deploy-<timestamp>.state`. Manually:

```bash
hostname; uname -a; cat /etc/os-release
systemctl status nginx --no-pager
systemctl status invoice-app --no-pager
ss -lntp
nginx -T > /root/nginx-before-$(date +%F).conf
git -C /var/www/invoice-app rev-parse HEAD
dig +short sbsdeutschland.com www.sbsdeutschland.com app.sbsdeutschland.com
```

## 1. Deploy the application

```bash
cd /opt/src && git clone https://github.com/Luyzz22/ki-rechnungsverarbeitung.git
cd ki-rechnungsverarbeitung
git checkout claude/sbs-deutschland-ecosystem-rebuild-824fi4
cd sbs-web
./infra/scripts/deploy.sh
```

What the script does:

1. records the current state;
2. `npm ci` and `npm run build`;
3. assembles the standalone output into `/var/www/sbs-web-next`
   (`server.js`, `node_modules`, `.next/static`, `public`);
4. starts it on port **3199** and health-checks `/`, `/industrie`, `/legal`,
   `/plattform`, `/academy` — it aborts if any of them is not 200;
5. only then moves the previous release to `/var/www/sbs-web.previous` and the
   new one into `/var/www/sbs-web`;
6. installs and starts `sbs-web.service`;
7. checks that `invoice-app` is still active and that port 8000 still answers.

nginx is **not** reloaded by this script. After it finishes, the new site is
running on 127.0.0.1:3100 and no visitor can reach it yet.

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3100/
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: industrie.sbsdeutschland.com' http://127.0.0.1:3100/produkte/normpilot
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: legal.sbsdeutschland.com' http://127.0.0.1:3100/produkte/kanzleiai
systemctl is-active invoice-app
```

## 2. DNS

See `domain-routing.md`. Two `A` records at STRATO, nothing else changed.

## 3. Certificates

```bash
sbs-web/infra/scripts/issue-certs.sh
```

Refuses to run until both hostnames resolve. Expands the existing certificate to
four names and finishes with a renewal dry run.

## 4. nginx

```bash
sbs-web/infra/scripts/enable-nginx.sh
```

What it does:

1. copies `sites-available`, `sites-enabled` and `snippets` to
   `/root/nginx-backup-<timestamp>/`;
2. installs the three snippets and `sbs-web.conf`;
3. symlinks it into `sites-enabled`;
4. runs `nginx -t` — **on failure it removes the symlink, restores the backup,
   re-tests and exits non-zero without reloading**;
5. reloads only on success;
6. smoke-tests all four hostnames including `app.sbsdeutschland.com`.

The existing `app.sbsdeutschland.com` server block is never read or written by
this script.

## 5. Verify

```bash
# The three new sites
for h in sbsdeutschland.com industrie.sbsdeutschland.com legal.sbsdeutschland.com; do
  printf '%-34s %s\n' "$h" "$(curl -s -o /dev/null -w '%{http_code}' https://$h/)"
done

# The application must be unaffected
curl -s -o /dev/null -w 'app: %{http_code}\n' https://app.sbsdeutschland.com/
systemctl status invoice-app --no-pager | head -5

# Legacy URLs (see redirects.md for the full list)
curl -s -o /dev/null -w '%{http_code} → %{redirect_url}\n' https://sbsdeutschland.com/sbshomepage/

# Automated gates, run from the checkout
npm run check:links   -- https://sbsdeutschland.com
npm run check:content -- https://sbsdeutschland.com
```

## Rollback

Each step reverses independently, in reverse order of application.

**nginx (undoes the public switch, ~2 seconds):**

```bash
rm /etc/nginx/sites-enabled/sbs-web.conf
nginx -t && systemctl reload nginx
# Full restore if needed:
cp -r /root/nginx-backup-<timestamp>/sites-available/. /etc/nginx/sites-available/
cp -r /root/nginx-backup-<timestamp>/sites-enabled/.   /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

The previous site returns immediately: `web/sbshomepage/` and
`web/static/landing/` are untouched on disk and still served by the invoice
application.

**Application:**

```bash
systemctl stop sbs-web
rm -rf /var/www/sbs-web
mv /var/www/sbs-web.previous /var/www/sbs-web
systemctl start sbs-web
```

**Certificate:** an expanded certificate is a superset. Nothing needs undoing;
if desired, `certbot delete --cert-name sbsdeutschland.com` followed by a fresh
issue for the original two names.

**DNS:** delete the two `A` records. No existing record was modified, so there
is nothing else to restore.

## Operating notes

```bash
systemctl status sbs-web
journalctl -u sbs-web -f
systemctl restart sbs-web
```

Resource profile: one Node process, `MemoryMax=512M` in the unit file, no
database, no writable paths (`ProtectSystem=strict`, empty `ReadWritePaths`), no
secrets. Every page is statically rendered at build time; only `/robots.txt` and
`/sitemap.xml` render per request, because both read the `Host` header.

## Not done in this session

- The runbook has not been executed against the host.
- DNS records have not been created.
- Certificates have not been requested.
- No production Lighthouse run has been performed — see `qa-report.md` for what
  was and was not measured.
