#!/usr/bin/env bash
# =============================================================================
# Install the nginx configuration for the marketing hosts.
#
#   sudo ./enable-nginx.sh --check    validate only — /etc/nginx is not written
#   sudo ./enable-nginx.sh            apply
#
# --check is a genuine read-only preflight. The candidate configuration is
# assembled in a temporary prefix, complete with its own nginx.conf, snippets
# and TLS material, and validated there with `nginx -t -p <tmp>`. Nothing under
# /etc/nginx is created, modified or removed. Proven by
# infra/tests/check-only-immutability.sh, which hashes the whole tree before and
# after.
#
# Apply keeps the belt and braces: back up, install, `nginx -t` in the real tree
# for full-context validation, and revert automatically without reloading if
# that test fails. The app.sbsdeutschland.com server block is never read or
# written by this script.
# =============================================================================
set -euo pipefail

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NGINX_ETC="${NGINX_ETC:-/etc/nginx}"
LE_LIVE="${LE_LIVE:-/etc/letsencrypt/live/sbsdeutschland.com}"
LE_CONF="${LE_CONF:-/etc/letsencrypt/options-ssl-nginx.conf}"
LE_DHPARAM="${LE_DHPARAM:-/etc/letsencrypt/ssl-dhparams.pem}"
SBS_WEB_URL="${SBS_WEB_URL:-http://127.0.0.1:3100/}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

log()  { printf '\033[1m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mWARN:\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31mFAIL:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || fail "must run as root"
command -v nginx >/dev/null || fail "nginx is not installed"

# ---- 0. Preconditions -------------------------------------------------------
log "Checking preconditions"

NGINX_VERSION="$(nginx -v 2>&1 | sed 's|.*/||' | awk '{print $1}')"
NGINX_MAJOR="${NGINX_VERSION%%.*}"
NGINX_MINOR="$(echo "$NGINX_VERSION" | cut -d. -f2)"
NGINX_PATCH="$(echo "$NGINX_VERSION" | cut -d. -f3)"
printf '    nginx        %s\n' "$NGINX_VERSION"

# `http2 on;` exists from 1.25.1. Below that the directive is unknown and
# `nginx -t` fails, so the staged copy is rewritten to the older
# `listen ... ssl http2` form. The repository ships the modern syntax because
# the production host runs 1.26.3.
HTTP2_MODERN=1
if [ "$NGINX_MAJOR" -lt 1 ] \
   || { [ "$NGINX_MAJOR" -eq 1 ] && [ "$NGINX_MINOR" -lt 25 ]; } \
   || { [ "$NGINX_MAJOR" -eq 1 ] && [ "$NGINX_MINOR" -eq 25 ] && [ "${NGINX_PATCH:-0}" -lt 1 ]; }; then
  HTTP2_MODERN=0
fi
printf '    http2 syntax %s\n' \
  "$([ "$HTTP2_MODERN" = 1 ] && echo "http2 on;  (nginx >= 1.25.1)" || echo "listen ... ssl http2  (nginx < 1.25.1)")"

# node is a precondition of the deployment, not of this script, but reporting it
# here makes the preflight a single place to look. Nothing is installed.
if command -v node >/dev/null; then
  printf '    node         %s (%s)\n' "$(node --version)" "$(command -v node)"
else
  warn "node is not on PATH — deploy-artifact.sh will refuse to run"
fi

if curl -fsS -o /dev/null --max-time 5 "$SBS_WEB_URL"; then
  printf '    sbs-web      answering on %s\n' "$SBS_WEB_URL"
else
  if [ "$CHECK_ONLY" = 1 ]; then
    warn "sbs-web is not answering on $SBS_WEB_URL — deploy the artifact before applying"
  else
    fail "sbs-web is not answering on $SBS_WEB_URL — deploy the artifact first"
  fi
fi

# Some kernels and droplets have no IPv6; `listen [::]:...` then fails nginx -t.
HAS_IPV6=1
[ -f /proc/net/if_inet6 ] || HAS_IPV6=0
printf '    ipv6         %s\n' \
  "$([ "$HAS_IPV6" = 1 ] && echo available || echo "unavailable — IPv6 listeners will be removed")"

# A second default_server on the same port is a hard nginx error, so the
# installed configuration has to be inspected. `nginx -T` would be the obvious
# way, but it implies `nginx -t`, and a config test opens the configured `pid`
# path and every `error_log` — creating them when they are absent. That is a
# write outside $STAGE, which --check must not do. The installed tree is
# therefore expanded by reading it: `include` globs are followed recursively and
# comments stripped, and no external process is involved.
expand_config() {
  local file="$1" depth="${2:-0}" line n=0 stripped target base
  [ "$depth" -gt 16 ] && return 0
  [ -r "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    stripped="${line%%#*}"
    case "$stripped" in
      *include*)
        # `include <path>;` — relative paths resolve against the nginx prefix.
        target="$(printf '%s\n' "$stripped" \
          | sed -n 's/^[[:space:]]*include[[:space:]]\+\(.*\);[[:space:]]*$/\1/p' \
          | tr -d '"'"'"'"')"
        if [ -n "$target" ]; then
          case "$target" in /*) ;; *) target="$NGINX_ETC/$target" ;; esac
          for base in $target; do
            [ -f "$base" ] && expand_config "$base" $((depth + 1))
          done
          continue
        fi
        ;;
    esac
    printf '%s:%s:%s\n' "$file" "$n" "$stripped"
  done < "$file"
}

STRIP_DEFAULT=0
DEFAULT_HITS="$STAGE/default-server-hits.txt"
: > "$DEFAULT_HITS"
if [ -r "$NGINX_ETC/nginx.conf" ]; then
  expand_config "$NGINX_ETC/nginx.conf" \
    | grep -E 'listen[^;]*\bdefault_server\b' > "$DEFAULT_HITS" || true
fi
if [ -s "$DEFAULT_HITS" ]; then
  warn "another server block already claims default_server:"
  head -3 "$DEFAULT_HITS" | sed 's/^/      /' >&2
  warn "default_server will be removed from the sbs-web catch-all to avoid a conflict"
  STRIP_DEFAULT=1
fi

# ---- 1. Stage the candidate configuration -----------------------------------
# Everything below writes only inside $STAGE.
log "Staging candidate configuration"
mkdir -p "$STAGE/snippets" "$STAGE/sites" "$STAGE/tmp" "$STAGE/logs" "$STAGE/certs"
cp "$SOURCE_DIR/infra/nginx/snippets/"*.conf "$STAGE/snippets/"
cp "$SOURCE_DIR/infra/nginx/sbs-web.conf"    "$STAGE/sites/sbs-web.conf"

if [ "$HAS_IPV6" = 0 ]; then
  sed -i '/listen \[::\]/d' "$STAGE/sites/sbs-web.conf"
fi
if [ "$STRIP_DEFAULT" = 1 ]; then
  sed -i 's/ default_server;/;/g' "$STAGE/sites/sbs-web.conf"
fi
if [ "$HTTP2_MODERN" = 0 ]; then
  # Collapse the modern pair back into the pre-1.25.1 form.
  sed -i -e 's/^\(\s*\)listen 443 ssl;/\1listen 443 ssl http2;/' \
         -e 's/^\(\s*\)listen \[::\]:443 ssl;/\1listen [::]:443 ssl http2;/' \
         -e '/^\s*http2 on;\s*$/d' "$STAGE/sites/sbs-web.conf"
fi

# TLS material. The real certificate is used read-only when it exists; when it
# does not — which is the normal case before certbot has run — a throwaway
# self-signed pair is generated inside $STAGE so that the preflight is still
# meaningful without touching /etc/letsencrypt.
STAGE_CERT="$LE_LIVE/fullchain.pem"
STAGE_KEY="$LE_LIVE/privkey.pem"
STAGE_SSL_CONF="$LE_CONF"
STAGE_DH="$LE_DHPARAM"
SYNTHETIC_TLS=0

if [ ! -r "$STAGE_CERT" ] || [ ! -r "$STAGE_KEY" ]; then
  SYNTHETIC_TLS=1
  openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
    -keyout "$STAGE/certs/privkey.pem" -out "$STAGE/certs/fullchain.pem" \
    -subj "/CN=sbsdeutschland.com" >/dev/null 2>&1
  STAGE_CERT="$STAGE/certs/fullchain.pem"
  STAGE_KEY="$STAGE/certs/privkey.pem"
fi
if [ ! -r "$STAGE_SSL_CONF" ]; then
  SYNTHETIC_TLS=1
  : > "$STAGE/certs/options-ssl-nginx.conf"
  STAGE_SSL_CONF="$STAGE/certs/options-ssl-nginx.conf"
fi
if [ ! -r "$STAGE_DH" ]; then
  SYNTHETIC_TLS=1
  openssl dhparam -out "$STAGE/certs/dhparam.pem" 2048 >/dev/null 2>&1
  STAGE_DH="$STAGE/certs/dhparam.pem"
fi
[ "$SYNTHETIC_TLS" = 1 ] && printf '    tls          using throwaway material for validation (real certificate not present yet)\n'

# The staged copy points at whatever TLS material was resolved above. The copy
# installed by apply keeps the original /etc/letsencrypt paths.
sed -e "s|$LE_LIVE/fullchain.pem|$STAGE_CERT|g" \
    -e "s|$LE_LIVE/privkey.pem|$STAGE_KEY|g" \
    -e "s|$LE_CONF|$STAGE_SSL_CONF|g" \
    -e "s|$LE_DHPARAM|$STAGE_DH|g" \
    "$STAGE/sites/sbs-web.conf" > "$STAGE/sites/sbs-web.validate.conf"

MIME_TYPES="$NGINX_ETC/mime.types"
[ -r "$MIME_TYPES" ] || MIME_TYPES=""

cat > "$STAGE/nginx.conf" <<CONF
# Synthetic nginx.conf for validation only. Never installed.
worker_processes 1;
error_log $STAGE/logs/error.log warn;
pid $STAGE/nginx.pid;
events { worker_connections 128; }
http {
$([ -n "$MIME_TYPES" ] && echo "    include $MIME_TYPES;")
    default_type application/octet-stream;
    access_log off;
    client_body_temp_path $STAGE/tmp/body;
    proxy_temp_path       $STAGE/tmp/proxy;
    fastcgi_temp_path     $STAGE/tmp/fastcgi;
    uwsgi_temp_path       $STAGE/tmp/uwsgi;
    scgi_temp_path        $STAGE/tmp/scgi;
    include $STAGE/sites/sbs-web.validate.conf;
}
CONF

# ---- 2. Validate the staged configuration -----------------------------------
log "Validating the staged configuration"

# `nginx -t` opens listening sockets. Running it inside a private network
# namespace guarantees it cannot touch the host's ports even transiently.
NGINX_TEST=(nginx -p "$STAGE" -c "$STAGE/nginx.conf" -t)
ISOLATION="host network"
if command -v unshare >/dev/null && unshare -n true >/dev/null 2>&1; then
  NGINX_TEST=(unshare -n -- nginx -p "$STAGE" -c "$STAGE/nginx.conf" -t)
  ISOLATION="private network namespace"
fi
printf '    isolation    %s\n' "$ISOLATION"

if ! "${NGINX_TEST[@]}" 2>&1 | sed 's/^/      /'; then
  fail "the candidate configuration is invalid — nothing was written"
fi

if [ "$CHECK_ONLY" = 1 ]; then
  log "Check complete. /etc/nginx was not written."
  echo
  echo "Verify that claim with: infra/tests/check-only-immutability.sh"
  echo "Re-run without --check to apply."
  exit 0
fi

# ---- 3. Back up what exists -------------------------------------------------
BACKUP="/root/nginx-backup-$(date +%Y%m%d-%H%M%S)"
log "Backing up the current nginx configuration to $BACKUP"
mkdir -p "$BACKUP"
cp -r "$NGINX_ETC/sites-available" "$BACKUP/" 2>/dev/null || true
cp -r "$NGINX_ETC/sites-enabled"   "$BACKUP/" 2>/dev/null || true
[ -d "$NGINX_ETC/snippets" ] && cp -r "$NGINX_ETC/snippets" "$BACKUP/"
nginx -T > "$BACKUP/nginx-T.txt" 2>/dev/null || true

# ---- 4. Install and test in the real tree -----------------------------------
log "Installing"
mkdir -p "$NGINX_ETC/snippets" "$NGINX_ETC/sites-available" "$NGINX_ETC/sites-enabled" /var/www/certbot
install -m 0644 "$STAGE/snippets/"*.conf "$NGINX_ETC/snippets/"
install -m 0644 "$STAGE/sites/sbs-web.conf" "$NGINX_ETC/sites-available/sbs-web.conf"
ln -sfn "$NGINX_ETC/sites-available/sbs-web.conf" "$NGINX_ETC/sites-enabled/sbs-web.conf"

log "Testing in full context"
if ! nginx -t; then
  printf '\033[1;31m==> nginx -t failed — reverting\033[0m\n' >&2
  rm -f "$NGINX_ETC/sites-enabled/sbs-web.conf"
  cp -r "$BACKUP/sites-available/." "$NGINX_ETC/sites-available/" 2>/dev/null || true
  cp -r "$BACKUP/sites-enabled/."   "$NGINX_ETC/sites-enabled/"   2>/dev/null || true
  [ -d "$BACKUP/snippets" ] && cp -r "$BACKUP/snippets/." "$NGINX_ETC/snippets/"
  nginx -t || true
  fail "configuration rejected; nothing was reloaded"
fi

# ---- 5. Reload --------------------------------------------------------------
log "Reloading nginx"
systemctl reload nginx

# ---- 6. Smoke test ----------------------------------------------------------
log "Smoke test"
for host in sbsdeutschland.com www.sbsdeutschland.com industrie.sbsdeutschland.com legal.sbsdeutschland.com; do
  printf '    %-32s %s\n' "$host" "$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $host" http://127.0.0.1/ || echo 000)"
done
printf '    %-32s %s\n' "app.sbsdeutschland.com (unchanged)" \
  "$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: app.sbsdeutschland.com' http://127.0.0.1/ || echo 000)"
printf '    %-32s %s\n' "invoice-app service" "$(systemctl is-active invoice-app 2>/dev/null || echo unknown)"

echo
echo "Rollback:"
echo "  rm $NGINX_ETC/sites-enabled/sbs-web.conf && nginx -t && systemctl reload nginx"
echo "Full restore from: $BACKUP"
