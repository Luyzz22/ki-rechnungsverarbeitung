#!/usr/bin/env bash
# =============================================================================
# Install a pre-built, verified release artifact on the production host.
#
# The host has 1 vCPU and 2 GB RAM and runs the live invoice application on port
# 8000. It therefore never installs dependencies and never compiles: CI produces
# the artifact, this script only verifies and activates it.
#
#   sudo ./deploy-artifact.sh sbs-web-<sha>.tar.gz [expected-sha256]
#
# If the checksum is not given, a sidecar <artifact>.sha256 is required.
#
# Releases are content-addressed directories under /var/www/sbs-web-releases and
# activated by moving a symlink, so a rollback is one symlink move.
# =============================================================================
set -euo pipefail

ARTIFACT="${1:-}"
EXPECTED="${2:-}"

RELEASES_DIR="${RELEASES_DIR:-/var/www/sbs-web-releases}"
CURRENT_LINK="${CURRENT_LINK:-/var/www/sbs-web}"
SERVICE="${SERVICE:-sbs-web}"
PORT="${PORT:-3100}"
STAGING_PORT="${STAGING_PORT:-3199}"
KEEP_RELEASES="${KEEP_RELEASES:-3}"
STATE_DIR="${STATE_DIR:-/var/log/sbs-web}"
RUN_USER="${RUN_USER:-www-data}"

log()  { printf '\033[1m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mFAIL:\033[0m %s\n' "$*" >&2; exit 1; }

[ -n "$ARTIFACT" ] || fail "usage: deploy-artifact.sh <artifact.tar.gz> [expected-sha256]"
[ -f "$ARTIFACT" ] || fail "artifact not found: $ARTIFACT"
[ "$(id -u)" = "0" ] || fail "must run as root"

# ---- 0. Preconditions -------------------------------------------------------
log "Checking preconditions"

NODE_BIN="$(command -v node || true)"
[ -n "$NODE_BIN" ] || fail "node is not installed on this host"
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
[ "$NODE_MAJOR" -ge 20 ] || fail "node $NODE_MAJOR is too old; the runtime needs >= 20"
printf '    node        %s (%s)\n' "$(node --version)" "$NODE_BIN"

id -u "$RUN_USER" >/dev/null 2>&1 || fail "service user '$RUN_USER' does not exist"

# The artifact unpacks to roughly 80 MB; keep a comfortable margin plus the
# retained releases.
AVAIL_KB="$(df -Pk /var/www | awk 'NR==2 {print $4}')"
[ "$AVAIL_KB" -gt 512000 ] || fail "less than 500 MB free on /var/www ($AVAIL_KB KB)"
printf '    disk free   %s MB on /var/www\n' "$((AVAIL_KB / 1024))"

MEM_AVAIL_MB="$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)"
printf '    mem avail   %s MB\n' "$MEM_AVAIL_MB"
[ "$MEM_AVAIL_MB" -gt 200 ] || fail "less than 200 MB available memory; refusing to deploy"

ss -lntp 2>/dev/null | grep -q ":$STAGING_PORT " && fail "staging port $STAGING_PORT is already in use"

# ---- 1. Verify the artifact -------------------------------------------------
log "Verifying artifact integrity"
if [ -z "$EXPECTED" ]; then
  [ -f "$ARTIFACT.sha256" ] || fail "no checksum given and no sidecar $ARTIFACT.sha256"
  ( cd "$(dirname "$ARTIFACT")" && sha256sum -c "$(basename "$ARTIFACT").sha256" ) \
    || fail "checksum mismatch"
  EXPECTED="$(cut -d' ' -f1 < "$ARTIFACT.sha256")"
else
  ACTUAL="$(sha256sum "$ARTIFACT" | cut -d' ' -f1)"
  [ "$ACTUAL" = "$EXPECTED" ] || fail "checksum mismatch: expected $EXPECTED, got $ACTUAL"
fi
printf '    sha256      %s\n' "$EXPECTED"

# ---- 2. Record the state we are moving away from ----------------------------
mkdir -p "$STATE_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
PREVIOUS_TARGET=""
[ -L "$CURRENT_LINK" ] && PREVIOUS_TARGET="$(readlink -f "$CURRENT_LINK")"
{
  echo "date:         $(date --iso-8601=seconds)"
  echo "artifact:     $(basename "$ARTIFACT")"
  echo "sha256:       $EXPECTED"
  echo "node:         $(node --version)"
  echo "previous:     ${PREVIOUS_TARGET:-none}"
  echo "sbs-web:      $(systemctl is-active "$SERVICE" 2>/dev/null || echo not-installed)"
  echo "invoice-app:  $(systemctl is-active invoice-app 2>/dev/null || echo unknown)"
  echo "nginx:        $(systemctl is-active nginx 2>/dev/null || echo unknown)"
  echo "mem-before:   $(free -m | awk '/^Mem:/ {print "total="$2" used="$3" avail="$7}')"
  echo "disk-before:  $(df -h /var/www | awk 'NR==2 {print $3" used, "$4" free"}')"
} | tee "$STATE_DIR/deploy-$STAMP.state"

# ---- 3. Unpack --------------------------------------------------------------
RELEASE="$RELEASES_DIR/$STAMP-${EXPECTED:0:12}"
log "Unpacking to $RELEASE"
mkdir -p "$RELEASES_DIR"
rm -rf "$RELEASE"
mkdir -p "$RELEASE"
tar -xzf "$ARTIFACT" -C "$RELEASE" --strip-components=1
[ -f "$RELEASE/server.js" ] || fail "artifact does not contain server.js"
chown -R "$RUN_USER":"$RUN_USER" "$RELEASE"
chmod -R go-w "$RELEASE"

if [ -f "$RELEASE/RELEASE.json" ]; then
  printf '    provenance  %s\n' "$(tr -d '\n ' < "$RELEASE/RELEASE.json")"
fi

# ---- 4. Health-check the new release before it goes live --------------------
log "Health-checking on port $STAGING_PORT"
STAGING_PID=""
cleanup_staging() { [ -n "$STAGING_PID" ] && kill "$STAGING_PID" 2>/dev/null || true; }
trap cleanup_staging EXIT

setsid sudo -u "$RUN_USER" env PORT="$STAGING_PORT" HOSTNAME=127.0.0.1 NODE_ENV=production \
  node "$RELEASE/server.js" > "$STATE_DIR/staging-$STAMP.log" 2>&1 &
STAGING_PID=$!

for _ in $(seq 1 40); do
  curl -fsS -o /dev/null "http://127.0.0.1:$STAGING_PORT/" && break
  sleep 1
done

STAGING_OK=1
check() {
  local path="$1" want="$2" host="${3:-}"
  local code
  if [ -n "$host" ]; then
    code="$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $host" "http://127.0.0.1:$STAGING_PORT$path")"
  else
    code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$STAGING_PORT$path")"
  fi
  if [ "$code" = "$want" ]; then
    printf '    ok   %-46s %s\n' "${host:+$host}$path" "$code"
  else
    printf '    FAIL %-46s %s (want %s)\n' "${host:+$host}$path" "$code" "$want"
    STAGING_OK=0
  fi
}

check "/"                       200
check "/plattform"              200
check "/plattform/flowcheck"    200
check "/academy"                200
check "/sitemap.xml"            200
check "/robots.txt"             200
check "/gibtsnicht"             404
check "/"                       200 "industrie.sbsdeutschland.com"
check "/produkte/normpilot"     200 "industrie.sbsdeutschland.com"
check "/"                       200 "legal.sbsdeutschland.com"
check "/produkte/kanzleiai"     200 "legal.sbsdeutschland.com"
# The internal URL space must not be reachable under an unknown hostname.
check "/industrie/produkte"     404 "unknown.example.com"

[ "$STAGING_OK" = "1" ] || fail "staging health checks failed — nothing was activated"

cleanup_staging
STAGING_PID=""
trap - EXIT
sleep 1

# ---- 5. Activate atomically -------------------------------------------------
log "Activating release"
ln -sfn "$RELEASE" "$CURRENT_LINK.staged"
mv -Tf "$CURRENT_LINK.staged" "$CURRENT_LINK"

install -m 0644 "$(dirname "${BASH_SOURCE[0]}")/../systemd/sbs-web.service" /etc/systemd/system/sbs-web.service
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null 2>&1 || true
systemctl restart "$SERVICE"

LIVE_OK=0
for _ in $(seq 1 40); do
  if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/"; then LIVE_OK=1; break; fi
  sleep 1
done

rollback() {
  printf '\033[1;31m==> Rolling back\033[0m\n' >&2
  if [ -n "$PREVIOUS_TARGET" ] && [ -d "$PREVIOUS_TARGET" ]; then
    ln -sfn "$PREVIOUS_TARGET" "$CURRENT_LINK.staged"
    mv -Tf "$CURRENT_LINK.staged" "$CURRENT_LINK"
    systemctl restart "$SERVICE" || true
    echo "    restored $PREVIOUS_TARGET" >&2
  else
    systemctl stop "$SERVICE" || true
    echo "    no previous release; service stopped" >&2
  fi
}

if [ "$LIVE_OK" != "1" ]; then
  rollback
  fail "service did not become healthy on port $PORT"
fi

# ---- 6. The invoice application must be untouched ---------------------------
log "Verifying the invoice application"
INVOICE_STATE="$(systemctl is-active invoice-app 2>/dev/null || echo unknown)"
INVOICE_CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:8000/ || echo 000)"
printf '    invoice-app %s, port 8000 -> %s\n' "$INVOICE_STATE" "$INVOICE_CODE"

if [ "$INVOICE_STATE" != "active" ]; then
  rollback
  fail "invoice-app is '$INVOICE_STATE' after deployment — rolled back"
fi

# ---- 7. Prune old releases --------------------------------------------------
log "Pruning old releases (keeping $KEEP_RELEASES)"
CURRENT_TARGET="$(readlink -f "$CURRENT_LINK")"
# shellcheck disable=SC2012
ls -1dt "$RELEASES_DIR"/*/ 2>/dev/null | tail -n +$((KEEP_RELEASES + 1)) | while read -r old; do
  old="${old%/}"
  [ "$(readlink -f "$old")" = "$CURRENT_TARGET" ] && continue
  [ "$(readlink -f "$old")" = "$PREVIOUS_TARGET" ] && continue
  echo "    removing $old"
  rm -rf "$old"
done

{
  echo "mem-after:    $(free -m | awk '/^Mem:/ {print "total="$2" used="$3" avail="$7}')"
  echo "disk-after:   $(df -h /var/www | awk 'NR==2 {print $3" used, "$4" free"}')"
  echo "active:       $CURRENT_TARGET"
} | tee -a "$STATE_DIR/deploy-$STAMP.state"

log "Deployed. nginx was NOT reloaded — see infra/scripts/enable-nginx.sh"
echo
echo "Rollback:"
echo "  ln -sfn ${PREVIOUS_TARGET:-<previous-release>} $CURRENT_LINK.staged && mv -Tf $CURRENT_LINK.staged $CURRENT_LINK && systemctl restart $SERVICE"
