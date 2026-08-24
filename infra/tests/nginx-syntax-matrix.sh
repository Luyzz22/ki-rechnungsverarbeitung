#!/usr/bin/env bash
# =============================================================================
# Validates the HTTP/2 syntax decision against real nginx binaries.
#
#   sudo ./infra/tests/nginx-syntax-matrix.sh
#
# infra/nginx/sbs-web.conf ships the modern form:
#
#     listen 443 ssl;
#     http2 on;
#
# which is correct and non-deprecated on the production host (1.26.3). The older
# `listen ... ssl http2` form still works there but is deprecated and logs a
# warning on every config test. Shipping the modern form is therefore right —
# but only if compatibility is kept deliberately rather than dropped, so
# enable-nginx.sh rewrites its staged copy back to the old form when it finds an
# nginx below 1.25.1.
#
# This test proves all three halves of that claim against real binaries:
#
#   1. the shipped file validates on >= 1.25.1
#   2. the shipped file is genuinely rejected below 1.25.1 — so the rewrite is
#      load-bearing, not decoration
#   3. enable-nginx.sh --check succeeds on both, i.e. the rewrite works
#
# Set NGINX_MODERN / NGINX_LEGACY to point at the two binaries. If the legacy
# binary is absent the version-specific cases are reported as skipped rather
# than silently passing.
# =============================================================================
set -euo pipefail

NGINX_MODERN="${NGINX_MODERN:-$(command -v nginx || true)}"
NGINX_LEGACY="${NGINX_LEGACY:-/usr/local/bin/nginx-1.24}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

FAILURES=0
pass() { printf '  \033[1;32mPASS\033[0m %s\n' "$*"; }
fail() { printf '  \033[1;31mFAIL\033[0m %s\n' "$*" >&2; FAILURES=$((FAILURES + 1)); }
skip() { printf '  \033[1;33mSKIP\033[0m %s\n' "$*"; }

[ "$(id -u)" = "0" ] || { echo "must run as root" >&2; exit 2; }
[ -n "$NGINX_MODERN" ] || { echo "no nginx binary found" >&2; exit 2; }

version_of() { "$1" -v 2>&1 | sed 's|.*/||' | awk '{print $1}'; }

echo "== nginx HTTP/2 syntax matrix =="
printf '   modern: %s (%s)\n' "$NGINX_MODERN" "$(version_of "$NGINX_MODERN")"
if [ -x "$NGINX_LEGACY" ]; then
  printf '   legacy: %s (%s)\n' "$NGINX_LEGACY" "$(version_of "$NGINX_LEGACY")"
else
  printf '   legacy: not installed\n'
fi
echo

# Throwaway TLS material, generated once. The DH group is RFC 7919 ffdhe2048 —
# a published, standard parameter set, so it is instant and always large enough
# for a modern OpenSSL. `openssl dhparam 1024` is rejected outright ("dh key too
# small"), which would look like a syntax error and mask the real result.
TLS="$WORK/tls"
mkdir -p "$TLS"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TLS/key.pem" \
  -out "$TLS/cert.pem" -days 1 -subj "/CN=sbs-test" >/dev/null 2>&1
: > "$TLS/options-ssl-nginx.conf"
cat > "$TLS/dh.pem" <<'DH'
-----BEGIN DH PARAMETERS-----
MIIBCAKCAQEA//////////+t+FRYortKmq/cViAnPTzx2LnFg84tNpWp4TZBFGQz
+8yTnc4kmz75fS/jY2MMddj2gbICrsRhetPfHtXV/WVhJDP1H18GbtCFY2VVPe0a
87VXE15/V8k1mE8McODmi3fipona8+/och3xWKE2rec1MKzKT0g6eXq8CrGCsyT7
YdEIqUuyyOP7uWrat2DX9GgdT0Kj3jlN9K5W7edjcrsZCwenyO4KbXCeAvzhzffi
7MA0BM0oNC9hkXL+nOmFg/+OTxIy7vKBg8P+OxtMb61zO7X8vC7CIAXFjvGDfRaD
ssbzSibBsu/6iGtCOGEoXJf//////////wIBAg==
-----END DH PARAMETERS-----
DH

# Validate a server-block file in isolation, in its own prefix, in a private
# network namespace where available so no host port is touched.
validate_with() {
  local bin="$1" conf="$2" dir status
  dir="$(mktemp -d -p "$WORK")"
  mkdir -p "$dir/logs" "$dir/tmp" "$dir/snippets"
  cp "$SOURCE_DIR/infra/nginx/snippets/"*.conf "$dir/snippets/"

  sed -e "s|/etc/letsencrypt/live/sbsdeutschland.com/fullchain.pem|$TLS/cert.pem|g" \
      -e "s|/etc/letsencrypt/live/sbsdeutschland.com/privkey.pem|$TLS/key.pem|g" \
      -e "s|/etc/letsencrypt/options-ssl-nginx.conf|$TLS/options-ssl-nginx.conf|g" \
      -e "s|/etc/letsencrypt/ssl-dhparams.pem|$TLS/dh.pem|g" \
      -e "s|include snippets/|include $dir/snippets/|g" \
      -e '/listen \[::\]/d' \
      "$conf" > "$dir/site.conf"

  cat > "$dir/nginx.conf" <<CONF
worker_processes 1;
error_log $dir/logs/error.log warn;
pid $dir/nginx.pid;
events { worker_connections 128; }
http {
    default_type application/octet-stream;
    access_log off;
    client_body_temp_path $dir/tmp/body;
    proxy_temp_path       $dir/tmp/proxy;
    fastcgi_temp_path     $dir/tmp/fastcgi;
    uwsgi_temp_path       $dir/tmp/uwsgi;
    scgi_temp_path        $dir/tmp/scgi;
    include $dir/site.conf;
}
CONF

  set +e
  if command -v unshare >/dev/null && unshare -n true >/dev/null 2>&1; then
    unshare -n -- "$bin" -p "$dir" -c "$dir/nginx.conf" -t > "$dir/out.txt" 2>&1
  else
    "$bin" -p "$dir" -c "$dir/nginx.conf" -t > "$dir/out.txt" 2>&1
  fi
  status=$?
  set -e
  cat "$dir/out.txt"
  return $status
}

SHIPPED="$SOURCE_DIR/infra/nginx/sbs-web.conf"

# ---- 1. the shipped file on the production version --------------------------
if validate_with "$NGINX_MODERN" "$SHIPPED" > "$WORK/modern.txt" 2>&1; then
  pass "shipped config validates on nginx $(version_of "$NGINX_MODERN")"
else
  fail "shipped config rejected by nginx $(version_of "$NGINX_MODERN"):"
  sed 's/^/        /' "$WORK/modern.txt" >&2
fi

# It must not merely pass — it must pass without the deprecation warning, which
# is the whole reason for choosing this form.
if grep -qi 'deprecated' "$WORK/modern.txt"; then
  fail "the shipped config still triggers a deprecation warning:"
  grep -i 'deprecated' "$WORK/modern.txt" | sed 's/^/        /' >&2
else
  pass "no deprecation warning on the production version"
fi

# ---- 2. the shipped file on the legacy version -------------------------------
if [ -x "$NGINX_LEGACY" ]; then
  if validate_with "$NGINX_LEGACY" "$SHIPPED" > "$WORK/legacy.txt" 2>&1; then
    fail "nginx $(version_of "$NGINX_LEGACY") accepted 'http2 on;' — the rewrite in enable-nginx.sh would be unnecessary, re-check the version gate"
  else
    if grep -q 'unknown directive "http2"' "$WORK/legacy.txt"; then
      pass "nginx $(version_of "$NGINX_LEGACY") rejects 'http2 on;' — the rewrite is load-bearing"
    else
      fail "nginx $(version_of "$NGINX_LEGACY") failed for an unexpected reason:"
      sed 's/^/        /' "$WORK/legacy.txt" >&2
    fi
  fi
else
  skip "no legacy nginx installed — cannot prove the rewrite is load-bearing"
fi

# ---- 3. enable-nginx.sh --check on both versions -----------------------------
# The script picks up `nginx` from PATH, so a shim selects the binary under test.
check_with() {
  local bin="$1" label="$2" shim
  shim="$(mktemp -d -p "$WORK")"
  printf '#!/bin/sh\nexec %s "$@"\n' "$bin" > "$shim/nginx"
  chmod +x "$shim/nginx"
  PATH="$shim:$PATH" "$SOURCE_DIR/infra/scripts/enable-nginx.sh" --check \
    > "$WORK/check-$label.txt" 2>&1
}

if check_with "$NGINX_MODERN" modern; then
  pass "--check succeeds on nginx $(version_of "$NGINX_MODERN")"
else
  fail "--check failed on nginx $(version_of "$NGINX_MODERN"):"
  sed 's/^/        /' "$WORK/check-modern.txt" >&2
fi
grep -q 'http2 syntax http2 on;' "$WORK/check-modern.txt" \
  && pass "modern syntax selected for $(version_of "$NGINX_MODERN")" \
  || fail "the modern syntax was not selected on $(version_of "$NGINX_MODERN")"

if [ -x "$NGINX_LEGACY" ]; then
  if check_with "$NGINX_LEGACY" legacy; then
    pass "--check succeeds on nginx $(version_of "$NGINX_LEGACY") via the rewrite"
  else
    fail "--check failed on nginx $(version_of "$NGINX_LEGACY"):"
    sed 's/^/        /' "$WORK/check-legacy.txt" >&2
  fi
  grep -q 'http2 syntax listen ... ssl http2' "$WORK/check-legacy.txt" \
    && pass "legacy syntax selected for $(version_of "$NGINX_LEGACY")" \
    || fail "the legacy syntax was not selected on $(version_of "$NGINX_LEGACY")"
else
  skip "no legacy nginx installed — compatibility path unverified here"
fi

echo
[ "$FAILURES" -eq 0 ] && { echo "nginx syntax matrix: PASS"; exit 0; }
echo "nginx syntax matrix: $FAILURES failure(s)"; exit 1
