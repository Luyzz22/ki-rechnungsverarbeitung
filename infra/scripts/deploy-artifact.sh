#!/usr/bin/env bash
# =============================================================================
# Install a pre-built, verified release artifact on the production host.
#
# The host runs Ubuntu 25.04 with 1 vCPU and 1.9 GiB of RAM, and carries the live
# invoice application on port 8000. It therefore never installs dependencies and never compiles: CI produces
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
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
RUN_USER="${RUN_USER:-www-data}"

INVOICE_SERVICE="${INVOICE_SERVICE:-invoice-app}"
INVOICE_URL="${INVOICE_URL:-http://127.0.0.1:8000/}"
# The live application answers 303 on / (redirect to the login page), so a bare
# 2xx check would reject a perfectly healthy host. Accept 2xx and 3xx; treat
# 4xx, 5xx and 000 (connection refused, DNS failure, timeout) as unhealthy.
INVOICE_ACCEPT="${INVOICE_ACCEPT:-^[23][0-9][0-9]$}"
INVOICE_ATTEMPTS="${INVOICE_ATTEMPTS:-3}"

log()  { printf '\033[1m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mFAIL:\033[0m %s\n' "$*" >&2; exit 1; }

# ---- invoice-app health -----------------------------------------------------
# The invoice application is the reason this host is careful. A deployment that
# leaves it unable to serve must not stand, so its health is a gate both before
# and after activation: unhealthy beforehand aborts without touching anything,
# unhealthy afterwards rolls the new release back.
#
# Health is BOTH conditions, never either one alone. A unit can be `active`
# while the worker inside it is wedged and answering 502, and an endpoint can
# answer while systemd is mid-restart.
invoice_state() { systemctl is-active "$INVOICE_SERVICE" 2>/dev/null || echo unknown; }

invoice_code() {
  # curl prints 000 on a connection failure *and* exits non-zero, so `|| echo
  # 000` would concatenate two codes. Swallow the status and use what it wrote.
  local code=""
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$INVOICE_URL" 2>/dev/null)" || true
  printf '%s\n' "${code:-000}"
}

INVOICE_STATE="unknown"
INVOICE_CODE="000"

invoice_healthy() {
  # Sets INVOICE_STATE and INVOICE_CODE to the last observation either way, so
  # the caller can report the exact code it rejected on. Retries briefly: one
  # dropped connection should not roll back a good release, but an application
  # that is genuinely down stays down across all attempts.
  local attempt
  for attempt in $(seq 1 "$INVOICE_ATTEMPTS"); do
    INVOICE_STATE="$(invoice_state)"
    INVOICE_CODE="$(invoice_code)"
    if [ "$INVOICE_STATE" = "active" ] \
       && printf '%s' "$INVOICE_CODE" | grep -qE "$INVOICE_ACCEPT"; then
      return 0
    fi
    if [ "$attempt" -lt "$INVOICE_ATTEMPTS" ]; then sleep 2; fi
  done
  return 1
}

[ -n "$ARTIFACT" ] || fail "usage: deploy-artifact.sh <artifact.tar.gz> [expected-sha256]"
[ -f "$ARTIFACT" ] || fail "artifact not found: $ARTIFACT"
[ "$(id -u)" = "0" ] || fail "must run as root"

# ---- 0. Preconditions -------------------------------------------------------
log "Checking preconditions"

# node is a precondition, never an action. This script does not install, upgrade
# or switch node — a runtime change on a host running a live application is an
# operator decision, not a side effect of a deployment. Before the first
# deployment, verify the interpreter by hand on the host:
#
#     command -v node
#     node --version        # must be >= 20 for the Next.js 16 standalone server
#
# If it is missing or too old, install it deliberately and re-run.
NODE_BIN="$(command -v node || true)"
[ -n "$NODE_BIN" ] || fail "node is not on PATH; install node >= 20 on the host first (this script never installs it)"
NODE_MAJOR="$("$NODE_BIN" -p 'process.versions.node.split(".")[0]')"
[ "$NODE_MAJOR" -ge 20 ] || fail "node $NODE_MAJOR is too old; the runtime needs >= 20 (upgrade it deliberately — this script will not)"
printf '    node        %s (%s)\n' "$("$NODE_BIN" --version)" "$NODE_BIN"

# The unit starts the server with `/usr/bin/env node`, which resolves against
# systemd's PATH — not root's, and not the deploying operator's. A node that
# satisfies the check above while being absent from systemd's PATH would pass
# here and fail at start, so resolve and check that one too, and run the staging
# health check with it: staging is only evidence if it exercises the same
# interpreter the service will use.
SYSTEMD_PATH="${SYSTEMD_PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"
SERVICE_NODE="$(PATH="$SYSTEMD_PATH" command -v node || true)"
[ -n "$SERVICE_NODE" ] || fail "node is not on systemd's PATH ($SYSTEMD_PATH); the unit's 'env node' would fail at start"
SERVICE_NODE_MAJOR="$("$SERVICE_NODE" -p 'process.versions.node.split(".")[0]')"
[ "$SERVICE_NODE_MAJOR" -ge 20 ] \
  || fail "the node on systemd's PATH is $SERVICE_NODE_MAJOR ($SERVICE_NODE); the runtime needs >= 20"
if [ "$SERVICE_NODE" != "$NODE_BIN" ]; then
  printf '    node (unit) %s (%s) — differs from the shell'"'"'s node\n' \
    "$("$SERVICE_NODE" --version)" "$SERVICE_NODE"
else
  printf '    node (unit) same binary\n'
fi

id -u "$RUN_USER" >/dev/null 2>&1 || fail "service user '$RUN_USER' does not exist"

# The artifact unpacks to roughly 80 MB; keep a comfortable margin plus the
# retained releases.
DISK_TARGET="$(dirname "$RELEASES_DIR")"
[ -d "$DISK_TARGET" ] || DISK_TARGET="/"
AVAIL_KB="$(df -Pk "$DISK_TARGET" | awk 'NR==2 {print $4}')"
[ "$AVAIL_KB" -gt 512000 ] || fail "less than 500 MB free on $DISK_TARGET ($AVAIL_KB KB)"
printf '    disk free   %s MB on %s\n' "$((AVAIL_KB / 1024))" "$DISK_TARGET"

MEM_AVAIL_MB="$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)"
printf '    mem avail   %s MB\n' "$MEM_AVAIL_MB"
[ "$MEM_AVAIL_MB" -gt 200 ] || fail "less than 200 MB available memory; refusing to deploy"

ss -lntp 2>/dev/null | grep -q ":$STAGING_PORT " && fail "staging port $STAGING_PORT is already in use"

# Establish the invoice application's health before anything is unpacked. If it
# is already unhealthy, this deployment is not the cause and rolling back after
# the fact would blame the wrong release — so refuse to start instead.
if invoice_healthy; then
  printf '    invoice-app %s, %s -> %s\n' "$INVOICE_STATE" "$INVOICE_URL" "$INVOICE_CODE"
else
  fail "$INVOICE_SERVICE is unhealthy before deployment (state=$INVOICE_STATE, http=$INVOICE_CODE) — nothing was changed"
fi
INVOICE_STATE_BEFORE="$INVOICE_STATE"
INVOICE_CODE_BEFORE="$INVOICE_CODE"

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
  echo "node:         $("$SERVICE_NODE" --version) ($SERVICE_NODE)"
  echo "previous:     ${PREVIOUS_TARGET:-none}"
  echo "sbs-web:      $(systemctl is-active "$SERVICE" 2>/dev/null || echo not-installed)"
  echo "invoice-before: state=$INVOICE_STATE_BEFORE http=$INVOICE_CODE_BEFORE"
  echo "nginx:        $(systemctl is-active nginx 2>/dev/null || echo unknown)"
  echo "mem-before:   $(free -m | awk '/^Mem:/ {print "total="$2" used="$3" avail="$7}')"
  echo "disk-before:  $(df -h "$DISK_TARGET" | awk 'NR==2 {print $3" used, "$4" free"}')"
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
  "$SERVICE_NODE" "$RELEASE/server.js" > "$STATE_DIR/staging-$STAMP.log" 2>&1 &
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

install -m 0644 "$(dirname "${BASH_SOURCE[0]}")/../systemd/sbs-web.service" "$SYSTEMD_DIR/sbs-web.service"
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
if invoice_healthy; then
  printf '    invoice-app %s, %s -> %s (accepted)\n' \
    "$INVOICE_STATE" "$INVOICE_URL" "$INVOICE_CODE"
  echo "invoice-after:  state=$INVOICE_STATE http=$INVOICE_CODE accepted" \
    >> "$STATE_DIR/deploy-$STAMP.state"
else
  printf '    invoice-app %s, %s -> %s (rejected)\n' \
    "$INVOICE_STATE" "$INVOICE_URL" "$INVOICE_CODE" >&2
  echo "invoice-after:  state=$INVOICE_STATE http=$INVOICE_CODE REJECTED" \
    >> "$STATE_DIR/deploy-$STAMP.state"
  rollback
  fail "$INVOICE_SERVICE is unhealthy after deployment (state=$INVOICE_STATE, http=$INVOICE_CODE) — rolled back"
fi

# ---- 7. Prune old releases --------------------------------------------------
log "Pruning old releases (keeping $KEEP_RELEASES)"
CURRENT_TARGET="$(readlink -f "$CURRENT_LINK")"
# `ls glob` exits non-zero when nothing matches, and `set -o pipefail` would
# turn that into a failed deployment at the very last step.
# shellcheck disable=SC2012
{ ls -1dt "$RELEASES_DIR"/*/ 2>/dev/null || true; } | tail -n +$((KEEP_RELEASES + 1)) | while read -r old; do
  old="${old%/}"
  [ "$(readlink -f "$old")" = "$CURRENT_TARGET" ] && continue
  [ "$(readlink -f "$old")" = "$PREVIOUS_TARGET" ] && continue
  echo "    removing $old"
  rm -rf "$old"
done

{
  echo "mem-after:    $(free -m | awk '/^Mem:/ {print "total="$2" used="$3" avail="$7}')"
  echo "disk-after:   $(df -h "$DISK_TARGET" | awk 'NR==2 {print $3" used, "$4" free"}')"
  echo "active:       $CURRENT_TARGET"
} | tee -a "$STATE_DIR/deploy-$STAMP.state"

log "Deployed. nginx was NOT reloaded — see infra/scripts/enable-nginx.sh"
echo
echo "Rollback:"
echo "  ln -sfn ${PREVIOUS_TARGET:-<previous-release>} $CURRENT_LINK.staged && mv -Tf $CURRENT_LINK.staged $CURRENT_LINK && systemctl restart $SERVICE"
