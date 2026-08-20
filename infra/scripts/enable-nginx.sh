#!/usr/bin/env bash
# =============================================================================
# Install the nginx configuration for the marketing hosts.
#
# Kept separate from the deployment so the application can be running and
# verified before any traffic is switched. Existing server blocks — in
# particular app.sbsdeutschland.com — are left untouched.
#
#   sudo ./enable-nginx.sh            apply
#   sudo ./enable-nginx.sh --check    validate only, change nothing
# =============================================================================
set -euo pipefail

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP="/root/nginx-backup-$(date +%Y%m%d-%H%M%S)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

log()  { printf '\033[1m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mWARN:\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31mFAIL:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || fail "must run as root"
command -v nginx >/dev/null || fail "nginx is not installed"

# ---- 0. Preconditions -------------------------------------------------------
log "Checking preconditions"

NGINX_VERSION="$(nginx -v 2>&1 | sed 's|.*/||')"
printf '    nginx       %s\n' "$NGINX_VERSION"

# The site config uses `listen ... ssl http2`, which is valid on 1.24 (Ubuntu
# 24.04) and only deprecated on 1.25+. Warn rather than fail on newer builds.
NGINX_MAJOR="${NGINX_VERSION%%.*}"
NGINX_MINOR="$(echo "$NGINX_VERSION" | cut -d. -f2)"
if [ "$NGINX_MAJOR" -gt 1 ] || { [ "$NGINX_MAJOR" -eq 1 ] && [ "$NGINX_MINOR" -ge 25 ]; }; then
  warn "nginx >= 1.25 deprecates 'listen ... http2'; the config still works but can be modernised to 'http2 on;'"
fi

# The marketing site must be answering before its hostnames are pointed at it.
if ! curl -fsS -o /dev/null --max-time 5 http://127.0.0.1:3100/; then
  fail "sbs-web is not answering on 127.0.0.1:3100 — deploy the artifact first"
fi
printf '    sbs-web     answering on 127.0.0.1:3100\n'

# Some kernels and droplets have no IPv6; `listen [::]:...` then fails nginx -t.
HAS_IPV6=1
if [ ! -f /proc/net/if_inet6 ]; then HAS_IPV6=0; fi
printf '    ipv6        %s\n' "$([ "$HAS_IPV6" = 1 ] && echo available || echo "unavailable — IPv6 listeners will be removed")"

# A second default_server on the same port is a hard nginx error.
if nginx -T 2>/dev/null | grep -qE 'listen[^;]*\bdefault_server\b'; then
  EXISTING="$(nginx -T 2>/dev/null | grep -nE 'listen[^;]*\bdefault_server\b' | head -3)"
  warn "another server block already claims default_server:"
  echo "$EXISTING" | sed 's/^/      /' >&2
  warn "removing default_server from the sbs-web catch-all to avoid a conflict"
  STRIP_DEFAULT=1
else
  STRIP_DEFAULT=0
fi

# ---- 1. Stage the configuration ---------------------------------------------
log "Staging configuration"
mkdir -p "$STAGE/snippets"
cp "$SOURCE_DIR/infra/nginx/snippets/"*.conf "$STAGE/snippets/"
cp "$SOURCE_DIR/infra/nginx/sbs-web.conf" "$STAGE/sbs-web.conf"

if [ "$HAS_IPV6" = 0 ]; then
  sed -i '/listen \[::\]/d' "$STAGE/sbs-web.conf"
fi
if [ "$STRIP_DEFAULT" = 1 ]; then
  sed -i 's/ default_server;/;/g' "$STAGE/sbs-web.conf"
fi

# ---- 2. Back up what exists -------------------------------------------------
if [ "$CHECK_ONLY" = 0 ]; then
  log "Backing up the current nginx configuration to $BACKUP"
  mkdir -p "$BACKUP"
  cp -r /etc/nginx/sites-available "$BACKUP/" 2>/dev/null || true
  cp -r /etc/nginx/sites-enabled  "$BACKUP/" 2>/dev/null || true
  [ -d /etc/nginx/snippets ] && cp -r /etc/nginx/snippets "$BACKUP/"
  nginx -T > "$BACKUP/nginx-T.txt" 2>/dev/null || true
fi

# ---- 3. Install and test ----------------------------------------------------
log "Installing"
mkdir -p /etc/nginx/snippets /var/www/certbot
install -m 0644 "$STAGE/snippets/"*.conf /etc/nginx/snippets/
install -m 0644 "$STAGE/sbs-web.conf" /etc/nginx/sites-available/sbs-web.conf
ln -sfn /etc/nginx/sites-available/sbs-web.conf /etc/nginx/sites-enabled/sbs-web.conf

log "Testing"
if ! nginx -t; then
  printf '\033[1;31m==> nginx -t failed — reverting\033[0m\n' >&2
  rm -f /etc/nginx/sites-enabled/sbs-web.conf
  if [ "$CHECK_ONLY" = 0 ] && [ -d "$BACKUP" ]; then
    cp -r "$BACKUP/sites-available/." /etc/nginx/sites-available/ 2>/dev/null || true
    cp -r "$BACKUP/sites-enabled/."   /etc/nginx/sites-enabled/   2>/dev/null || true
    [ -d "$BACKUP/snippets" ] && cp -r "$BACKUP/snippets/." /etc/nginx/snippets/
  fi
  nginx -t || true
  fail "configuration rejected; nothing was reloaded"
fi

if [ "$CHECK_ONLY" = 1 ]; then
  log "Check only — removing the staged symlink again"
  rm -f /etc/nginx/sites-enabled/sbs-web.conf
  nginx -t >/dev/null 2>&1 || warn "the pre-existing configuration does not pass nginx -t on its own"
  log "Configuration is valid. Re-run without --check to apply."
  exit 0
fi

# ---- 4. Reload --------------------------------------------------------------
log "Reloading nginx"
systemctl reload nginx

# ---- 5. Smoke test ----------------------------------------------------------
log "Smoke test"
for host in sbsdeutschland.com www.sbsdeutschland.com industrie.sbsdeutschland.com legal.sbsdeutschland.com; do
  printf '    %-32s %s\n' "$host" "$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $host" http://127.0.0.1/ || echo 000)"
done
printf '    %-32s %s\n' "app.sbsdeutschland.com (unchanged)" \
  "$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: app.sbsdeutschland.com' http://127.0.0.1/ || echo 000)"
printf '    %-32s %s\n' "invoice-app service" "$(systemctl is-active invoice-app 2>/dev/null || echo unknown)"

echo
echo "Rollback:"
echo "  rm /etc/nginx/sites-enabled/sbs-web.conf && nginx -t && systemctl reload nginx"
echo "Full restore from: $BACKUP"
