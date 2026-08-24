#!/usr/bin/env bash
# =============================================================================
# Runs the shipped nginx configuration for real — on a throwaway port, in its
# own prefix — in front of the site on 127.0.0.1:3100, and checks what only a
# real reverse proxy can show: that each security header carries exactly one
# value (nginx `add_header` does not inherit into a location that declares its
# own, so a duplicate is easy to introduce and invisible in the source), and
# that every legacy redirect lands somewhere alive.
#
#   sudo ./infra/tests/nginx-gates.sh
#
# TLS is stripped and the blocks are collapsed onto one plain-HTTP port, which
# is why nginx warns about conflicting server names — expected here, and not a
# property of the shipped file. /etc/nginx is never read or written.
# =============================================================================
set -uo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
W=$(mktemp -d); chmod 755 "$W"
PORT=8081
trap '[ -f "$W/nginx.pid" ] && kill "$(cat "$W/nginx.pid")" 2>/dev/null; rm -rf "$W"' EXIT

mkdir -p "$W/logs" "$W/tmp" "$W/snippets"
cp "$SRC/infra/nginx/snippets/"*.conf "$W/snippets/"

# Plain-HTTP mirror of the corporate/division blocks: TLS is not what is being
# tested here, the header and redirect behaviour is.
python3 - "$SRC/infra/nginx/sbs-web.conf" "$W" <<'PY'
import re, sys, pathlib
src, w = sys.argv[1], sys.argv[2]
t = pathlib.Path(src).read_text()
t = t.replace('include snippets/', f'include {w}/snippets/')
t = re.sub(r'^\s*(ssl_certificate|ssl_certificate_key|ssl_dhparam|include /etc/letsencrypt).*\n', '', t, flags=re.M)
t = re.sub(r'^\s*listen \[::\].*\n', '', t, flags=re.M)
t = re.sub(r'^\s*http2 on;\s*\n', '', t, flags=re.M)
t = t.replace('listen 443 ssl;', 'listen 8081;')
t = t.replace('listen 80 default_server;', 'listen 8081 default_server;')
t = t.replace('listen 80;', 'listen 8081;')
pathlib.Path(f'{w}/site.conf').write_text(t)
PY

cat > "$W/nginx.conf" <<CONF
worker_processes 1;
error_log $W/logs/error.log warn;
pid $W/nginx.pid;
events { worker_connections 128; }
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    access_log off;
    client_body_temp_path $W/tmp/body;
    proxy_temp_path       $W/tmp/proxy;
    fastcgi_temp_path     $W/tmp/fastcgi;
    uwsgi_temp_path       $W/tmp/uwsgi;
    scgi_temp_path        $W/tmp/scgi;
    include $W/site.conf;
}
CONF

nginx -p "$W" -c "$W/nginx.conf" -t 2>&1 | sed 's/^/    /' || exit 1
nginx -p "$W" -c "$W/nginx.conf"
sleep 1

FAIL=0
pass() { printf '  \033[1;32mPASS\033[0m %s\n' "$*"; }
fail() { printf '  \033[1;31mFAIL\033[0m %s\n' "$*" >&2; FAIL=$((FAIL+1)); }
H() { curl -s -o /dev/null -D - --noproxy '*' -H "Host: $1" "http://127.0.0.1:$PORT$2" 2>/dev/null; }

echo "== security headers (through real nginx $(nginx -v 2>&1 | sed 's|.*/||')) =="
HDRS=$(H sbsdeutschland.com /)
for h in strict-transport-security content-security-policy x-content-type-options referrer-policy permissions-policy x-frame-options; do
  n=$(printf '%s' "$HDRS" | grep -ci "^$h:")
  if [ "$n" = 1 ]; then pass "$h — exactly one value"
  elif [ "$n" = 0 ]; then fail "$h — missing"
  else fail "$h — $n values (duplicated)"; fi
done
printf '%s' "$HDRS" | grep -qi '^server: nginx/[0-9]' && fail "server header leaks version" || pass "server version not advertised"

echo
echo "== legacy redirects =="
PATHS=$(grep -oE '^\s*location = [^ ]+' "$SRC/infra/nginx/snippets/sbs-web-redirects.conf" | awk '{print $3}')
N=0; BAD=0; EXT=0
# The destination host matters: a legacy corporate URL may point at a division
# host, and several point at app.sbsdeutschland.com — the live invoice
# application, which this layer neither serves nor is allowed to touch.
for p in $PATHS; do
  N=$((N+1))
  loc=$(H sbsdeutschland.com "$p" | grep -i '^location:' | tr -d '\r' | sed 's/^[Ll]ocation: //')
  code=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' -H 'Host: sbsdeutschland.com' "http://127.0.0.1:$PORT$p")
  if [ "$code" != "301" ]; then printf '     %-46s %s (want 301)\n' "$p" "$code"; BAD=$((BAD+1)); continue; fi
  dhost=$(printf '%s' "$loc" | sed -E 's|^https?://([^/]+).*|\1|')
  dpath=$(printf '%s' "$loc" | sed -E 's|^https?://[^/]+||; s|#.*||')
  [ -z "$dpath" ] && dpath=/
  case "$dhost" in
    sbsdeutschland.com|www.sbsdeutschland.com|industrie.sbsdeutschland.com|legal.sbsdeutschland.com) ;;
    *) EXT=$((EXT+1)); continue ;;
  esac
  dcode=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' -H "Host: $dhost" "http://127.0.0.1:$PORT$dpath")
  if [ "$dcode" != "200" ] && [ "$dcode" != "301" ]; then
    printf '     %-46s 301 -> %s%s = %s (dead)\n' "$p" "$dhost" "$dpath" "$dcode"; BAD=$((BAD+1))
  fi
done
printf '     %s external destination(s) on app.sbsdeutschland.com — not served by this layer, not checked\n' "$EXT"
[ "$BAD" = 0 ] && pass "$N legacy paths, all 301; $((N-EXT)) destinations verified live, $EXT external" || fail "$BAD of $N legacy paths broken"

echo
echo "== unknown host =="
c=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' -H 'Host: unknown.example.com' "http://127.0.0.1:$PORT/industrie/produkte")
[ "$c" = "404" ] || [ "$c" = "000" ] && pass "internal URL space not reachable under an unknown Host ($c)" || fail "unknown Host returned $c"

echo
[ "$FAIL" -eq 0 ] && { echo "nginx gates: PASS"; exit 0; }
echo "nginx gates: $FAIL failure(s)"; exit 1
