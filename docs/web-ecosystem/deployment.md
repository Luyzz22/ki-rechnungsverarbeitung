# Deployment

Target host: `207.154.200.239`, Ubuntu 24.04, Frankfurt, 1 vCPU / 2 GB RAM.
The invoice application on port 8000 must keep running throughout.

> **Not yet executed.** No shell on the target host was available to the session
> that wrote this. Every step below is prepared as repository-managed
> configuration, validated locally against real nginx 1.24 and a real release
> artifact, and paired with a rollback.

## The rule that shapes everything else

**Nothing is built on the production host.** It has one core, two gigabytes of
memory and a live application on it. A Next.js build peaks well above a
gigabyte; running it there would compete with `invoice-app` for both CPU and
RAM, and an out-of-memory kill would take the live application with it.

```
CI / trusted build machine                  Production host
--------------------------                  ---------------
npm ci                                      verify SHA256
npm run typecheck                           unpack to a content-addressed dir
npm run lint                                health-check on port 3199
npm run build                               move the "current" symlink
check:links / check:content                 systemctl restart
scripts/build-artifact.sh          ---->    verify invoice-app still active
  -> tarball + .sha256 + manifest           prune old releases
```

The host receives an already verified runtime artifact and never installs a
dependency or compiles a line.

## Layout on the host

```
/var/www/sbs-web-releases/20260820-143012-46af507adcb9/   unpacked release
/var/www/sbs-web-releases/20260820-101245-7ff5aae3d7ab/   previous release
/var/www/sbs-web  ->  20260820-143012-46af507adcb9        symlink, the active one
/var/log/sbs-web/deploy-<stamp>.state                     what changed, when
```

Activation is a symlink move, so a rollback is also a symlink move.

## Order of operations

Nothing user-visible changes until step 5.

```
1. Build the artifact in CI                -> nothing on the host changes
2. Transfer and deploy it                  -> runs on 127.0.0.1:3100, not public
3. Create the two DNS records              -> hostnames resolve, no TLS yet
4. Expand the certificate                  -> hostnames get TLS
5. Enable the nginx configuration          -> the switch
6. Verify redirects and both applications
```

## 1. Build the artifact

In CI (`.github/workflows/ci.yml` does this on every push to `main`), or on any
trusted machine that is not the production host:

```bash
npm ci
npm run typecheck && npm run lint && npm run build
npm start &
npm run check:links   -- http://127.0.0.1:3100
npm run check:content -- http://127.0.0.1:3100
./scripts/build-artifact.sh dist
```

Output:

```
dist/sbs-web-<sha>.tar.gz           the runtime artifact (~25 MB)
dist/sbs-web-<sha>.tar.gz.sha256    checksum in `sha256sum -c` format
dist/sbs-web-<sha>.manifest.json    commit, digest, build time, node version
```

The tarball is packed deterministically — fixed mtime, owner and sort order — so
the same commit produces the same digest. The script refuses to pack a tree
containing `.env`, `*.pem` or key material, and marks the artifact `-dirty` if
the working tree was not clean.

## 2. Transfer and deploy

```bash
scp dist/sbs-web-<sha>.tar.gz dist/sbs-web-<sha>.tar.gz.sha256 root@207.154.200.239:/tmp/
ssh root@207.154.200.239

cd /opt/src && git clone https://github.com/SBS-Nexus/sbs-web.git   # for the scripts only
cd sbs-web
sudo ./infra/scripts/deploy-artifact.sh /tmp/sbs-web-<sha>.tar.gz
```

What the script does, and where it stops:

1. **Preconditions** — root, node >= 20, the `www-data` user, >= 500 MB free on
   `/var/www`, >= 200 MB available memory, staging port free. Any failure aborts
   before anything is touched.
2. **Integrity** — verifies the SHA256 against the sidecar or the argument.
3. **State record** — writes the previous release, service states, memory and
   disk to `/var/log/sbs-web/deploy-<stamp>.state`.
4. **Unpack** — into a new content-addressed release directory, owned by
   `www-data`, group/other write bits removed.
5. **Health check on port 3199** — twelve checks against the *new* release
   before it can go live: the corporate pages, the sitemap and robots, a 404 for
   an unknown path, both division hostnames including a product page each, and
   a 404 for the internal URL space under an unknown hostname. Any failure
   aborts and **nothing is activated**.
6. **Activate** — symlink move, unit install, `systemctl restart`, then wait for
   port 3100 to answer. If it does not, the previous symlink is restored and the
   service restarted automatically.
7. **Verify the invoice application** — `systemctl is-active invoice-app` and a
   request to port 8000. If the service is not active, the deployment **rolls
   itself back**.
8. **Prune** — keeps the newest three releases plus the previous one.

nginx is **not** reloaded by this script. When it finishes, the new site runs on
127.0.0.1:3100 and no visitor can reach it.

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3100/
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: industrie.sbsdeutschland.com' http://127.0.0.1:3100/produkte/normpilot
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: legal.sbsdeutschland.com'     http://127.0.0.1:3100/produkte/kanzleiai
systemctl is-active invoice-app
```

### Manual fallback

If CI is unavailable and an artifact must be produced by hand, build it on any
machine with node >= 20 — a laptop, a scratch droplet, a container — and copy it
across. Building on the production host is not a supported fallback: use a
second machine, or resize the host deliberately and temporarily with the invoice
application stopped for the duration. That decision is the owner's, not the
deployment script's.

## 3. DNS

See `domain-routing.md`. Two `A` records at STRATO, nothing else changed.

## 4. Certificates

```bash
sudo ./infra/scripts/issue-certs.sh
```

Refuses to run until both hostnames resolve. Expands the existing certificate to
four names and finishes with a renewal dry run.

## 5. nginx

```bash
sudo ./infra/scripts/enable-nginx.sh --check    # validate, change nothing
sudo ./infra/scripts/enable-nginx.sh            # apply
```

Preconditions it enforces before touching anything:

- nginx present; the version is reported, and a warning is printed on 1.25+
  where `listen ... http2` is deprecated. The config targets 1.24 on Ubuntu
  24.04, where `http2 on;` does not exist and would fail `nginx -t`.
- sbs-web already answering on 127.0.0.1:3100.
- IPv6 availability — if `/proc/net/if_inet6` is absent the `listen [::]:...`
  lines are removed from the staged copy, because they would otherwise fail
  `nginx -t`.
- An existing `default_server` elsewhere in the configuration — if one is found,
  `default_server` is stripped from the sbs-web catch-all so the two cannot
  collide.

Then it backs up `sites-available`, `sites-enabled`, `snippets` and the full
`nginx -T` output to `/root/nginx-backup-<stamp>/`, installs the configuration,
runs `nginx -t`, and **reverts automatically without reloading** if the test
fails. The `app.sbsdeutschland.com` server block is never read or written.

## 6. Verify

```bash
for h in sbsdeutschland.com industrie.sbsdeutschland.com legal.sbsdeutschland.com; do
  printf '%-34s %s\n' "$h" "$(curl -s -o /dev/null -w '%{http_code}' https://$h/)"
done

curl -s -o /dev/null -w 'app: %{http_code}\n' https://app.sbsdeutschland.com/
systemctl status invoice-app --no-pager | head -5

curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' https://sbsdeutschland.com/sbshomepage/
curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' https://sbsdeutschland.com/static/landing/security.html
curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' https://www.sbsdeutschland.com/

npm run check:links   -- https://sbsdeutschland.com
npm run check:content -- https://sbsdeutschland.com
```

## Rollback

Each step reverses independently, in reverse order of application.

**nginx — undoes the public switch, about two seconds:**

```bash
rm /etc/nginx/sites-enabled/sbs-web.conf
nginx -t && systemctl reload nginx
# Full restore:
cp -r /root/nginx-backup-<stamp>/sites-available/. /etc/nginx/sites-available/
cp -r /root/nginx-backup-<stamp>/sites-enabled/.   /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

The previous site returns immediately: `web/sbshomepage/` and
`web/static/landing/` are untouched on disk and still served by the invoice
application.

**Release — symlink move:**

```bash
ls -1dt /var/www/sbs-web-releases/*/          # newest first
ln -sfn /var/www/sbs-web-releases/<previous> /var/www/sbs-web.staged
mv -Tf /var/www/sbs-web.staged /var/www/sbs-web
systemctl restart sbs-web
```

`deploy-artifact.sh` prints the exact command for the release it replaced, and
performs this itself if the new release fails its health check or if
`invoice-app` is not active afterwards.

**Certificate:** an expanded certificate is a superset; nothing needs undoing.

**DNS:** delete the two `A` records. No existing record was modified.

## Operating notes

```bash
systemctl status sbs-web
journalctl -u sbs-web -f
systemctl restart sbs-web
ls -1dt /var/www/sbs-web-releases/*/
cat /var/log/sbs-web/deploy-*.state
```

Resource profile: one Node process. `MemoryHigh=384M`, `MemoryMax=512M`,
`CPUWeight=50` so it yields to the invoice application under contention.
Measured steady-state RSS is about 120 MB. No database, no writable paths
(`ProtectSystem=strict` with an empty `ReadWritePaths` — verified: the release
tree can be fully read-only and every route including `/sitemap.xml` still
answers), and no secrets.

## What has and has not been verified

| | |
| --- | --- |
| nginx configuration parses | **Yes** — `nginx -t` against real nginx 1.24.0 |
| Routing, headers, redirects through nginx | **Yes** — nginx in front of the real build, all three hostnames |
| Release artifact runs standalone | **Yes** — unpacked, started, all routes and host routing verified |
| Artifact survives a read-only filesystem | **Yes** — matches `ProtectSystem=strict` |
| systemd unit is valid | **Yes** — `systemd-analyze verify` |
| Deploy health-check matrix | **Yes** — all twelve checks run against a real artifact |
| Deployment on the target host | **No** — no shell available |
| DNS records | **No** — not created |
| TLS certificates | **No** — cannot be issued before DNS resolves |
| Behaviour under the host's real nginx configuration | **No** — run `enable-nginx.sh --check` there first |
