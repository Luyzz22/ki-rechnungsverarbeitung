#!/usr/bin/env bash
# =============================================================================
# Exercises deploy-artifact.sh end to end against a real artifact, in a sandbox
# root, with systemd and the invoice application stubbed.
#
#   sudo ./infra/tests/deploy-invoice-gate.sh dist/sbs-web-<sha>.tar.gz
#
# What it proves, per scenario:
#
#   B  invoice-app active + HTTP 303  -> the release is accepted and activated
#   C  invoice-app active + HTTP 500  -> the release is rolled back
#   D  invoice-app inactive           -> the release is rolled back
#   E  the staging health matrix passes against the real artifact
#   F  no nginx reload, restart or configuration change happens at any point
#
# C and D inject their fault at the moment the new release is activated, which
# is the only interesting time: the deployment has already passed every earlier
# gate, so a rollback there is a decision made on post-activation evidence.
#
# Nothing outside the sandbox root is written. /etc/nginx, /etc/systemd/system
# and the real services are untouched — the fake systemctl never reaches systemd.
# =============================================================================
set -euo pipefail

ARTIFACT="${1:-}"
[ -n "$ARTIFACT" ] || { echo "usage: deploy-invoice-gate.sh <artifact.tar.gz>" >&2; exit 2; }
[ -f "$ARTIFACT" ] || { echo "artifact not found: $ARTIFACT" >&2; exit 2; }
ARTIFACT="$(cd "$(dirname "$ARTIFACT")" && pwd)/$(basename "$ARTIFACT")"
[ "$(id -u)" = "0" ] || { echo "must run as root" >&2; exit 2; }

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ROOT="$(mktemp -d)"
# mktemp gives 0700; the service user has to be able to traverse into the
# sandbox exactly as it traverses /var/www on the host.
chmod 755 "$ROOT"

PORT=3391
STAGING_PORT=3392
INVOICE_PORT=3393
RUN_USER="${RUN_USER:-www-data}"

FAILURES=0
pass() { printf '  \033[1;32mPASS\033[0m %s\n' "$*"; }
fail() { printf '  \033[1;31mFAIL\033[0m %s\n' "$*" >&2; FAILURES=$((FAILURES + 1)); }

cleanup() {
  [ -x "$ROOT/bin/sbs-web-ctl" ] && "$ROOT/bin/sbs-web-ctl" stop >/dev/null 2>&1 || true
  [ -f "$ROOT/invoice.pid" ] && kill "$(cat "$ROOT/invoice.pid")" 2>/dev/null || true
  if [ "${KEEP_ROOT:-0}" = "1" ]; then
    echo "sandbox kept at $ROOT" >&2
  else
    rm -rf "$ROOT"
  fi
}
trap cleanup EXIT

mkdir -p "$ROOT/bin" "$ROOT/releases" "$ROOT/state" "$ROOT/systemd"
chmod 755 "$ROOT/releases" "$ROOT/state"

# ---- the invoice application stand-in ---------------------------------------
# Answers with whatever status code sits in $ROOT/invoice-code, so a scenario
# can turn a healthy 303 into a 500 without restarting anything.
printf '303' > "$ROOT/invoice-code"
cat > "$ROOT/invoice-stub.js" <<'JS'
const http = require('http');
const fs = require('fs');
const codeFile = process.env.CODE_FILE;
http.createServer((req, res) => {
  let code = 303;
  try { code = parseInt(fs.readFileSync(codeFile, 'utf8').trim(), 10) || 303; } catch {}
  res.writeHead(code, code >= 300 && code < 400 ? { Location: '/login' } : {});
  res.end();
}).listen(Number(process.env.PORT), '127.0.0.1');
JS
CODE_FILE="$ROOT/invoice-code" PORT="$INVOICE_PORT" \
  setsid node "$ROOT/invoice-stub.js" > "$ROOT/invoice.log" 2>&1 &
echo $! > "$ROOT/invoice.pid"

for _ in $(seq 1 30); do
  curl -s -o /dev/null "http://127.0.0.1:$INVOICE_PORT/" && break
  sleep 0.3
done

# ---- the sbs-web process manager the fake systemctl drives ------------------
cat > "$ROOT/bin/sbs-web-ctl" <<'CTL'
#!/usr/bin/env bash
set -uo pipefail
# `setsid sudo -u www-data node ...` puts node in its own session, so killing the
# recorded pid kills the sudo wrapper and orphans node — which keeps the port and
# makes the next start fail to bind. Reap by listening port instead.
free_port() {
  local pids attempt
  pids="$(ss -lntpH "sport = :$PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u | tr '\n' ' ')"
  if [ -n "${pids// /}" ]; then kill $pids 2>/dev/null || true; fi
  for attempt in $(seq 1 40); do
    ss -lnt "sport = :$PORT" 2>/dev/null | grep -q ":$PORT " || return 0
    sleep 0.25
  done
  pids="$(ss -lntpH "sport = :$PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u | tr '\n' ' ')"
  if [ -n "${pids// /}" ]; then kill -9 $pids 2>/dev/null || true; fi
  sleep 0.5
}
case "${1:-}" in
  start)
    free_port
    setsid sudo -u "$RUN_USER" env PORT="$PORT" HOSTNAME=127.0.0.1 NODE_ENV=production \
      node "$CURRENT_LINK/server.js" > "$FAKE_ROOT/sbs-web.log" 2>&1 &
    ;;
  stop)
    free_port
    ;;
esac
exit 0
CTL
chmod +x "$ROOT/bin/sbs-web-ctl"

# ---- the fake systemctl -----------------------------------------------------
# Logs every invocation so the test can assert what was and was not asked of
# systemd — in particular that nginx was never reloaded.
cat > "$ROOT/bin/systemctl" <<'SC'
#!/usr/bin/env bash
set -uo pipefail
printf '%s\n' "$*" >> "$FAKE_ROOT/systemctl.log"
cmd="${1:-}"; unit="${2:-}"
case "$cmd" in
  is-active)
    cat "$FAKE_ROOT/state-$unit" 2>/dev/null || echo unknown
    ;;
  restart|start)
    if [ "$unit" = "sbs-web" ]; then
      "$FAKE_ROOT/bin/sbs-web-ctl" start
      printf 'active' > "$FAKE_ROOT/state-sbs-web"
      # A scenario's post-activation fault lands here: the deployment has
      # already passed every earlier gate at this point.
      if [ -n "${FAULT_INVOICE_CODE:-}" ]; then
        printf '%s' "$FAULT_INVOICE_CODE" > "$FAKE_ROOT/invoice-code"
      fi
      if [ -n "${FAULT_INVOICE_STATE:-}" ]; then
        printf '%s' "$FAULT_INVOICE_STATE" > "$FAKE_ROOT/state-invoice-app"
      fi
    fi
    ;;
  stop)
    if [ "$unit" = "sbs-web" ]; then
      "$FAKE_ROOT/bin/sbs-web-ctl" stop
      printf 'inactive' > "$FAKE_ROOT/state-sbs-web"
    fi
    ;;
esac
exit 0
SC
chmod +x "$ROOT/bin/systemctl"

printf 'active'   > "$ROOT/state-invoice-app"
printf 'inactive' > "$ROOT/state-sbs-web"
printf 'active'   > "$ROOT/state-nginx"

# ---- nginx witnesses (scenario F) -------------------------------------------
nginx_tree_hash() {
  [ -d /etc/nginx ] || { echo none; return 0; }
  find /etc/nginx -type f -print0 2>/dev/null | sort -z \
    | xargs -0 sha256sum 2>/dev/null | sha256sum | cut -d' ' -f1
}
NGINX_HASH_BEFORE="$(nginx_tree_hash)"
NGINX_MASTER_BEFORE="$(pgrep -f 'nginx: master' 2>/dev/null | sort | tr '\n' ',' || true)"

run_deploy() {
  # Runs the real deploy script with the sandbox wired in. $1 is a label; the
  # remaining environment comes from the caller's FAULT_* exports.
  local label="$1"; shift
  set +e
  env PATH="$ROOT/bin:$PATH" \
      FAKE_ROOT="$ROOT" \
      PORT="$PORT" \
      RUN_USER="$RUN_USER" \
      CURRENT_LINK="$ROOT/current" \
      RELEASES_DIR="$ROOT/releases" \
      STATE_DIR="$ROOT/state" \
      SYSTEMD_DIR="$ROOT/systemd" \
      STAGING_PORT="$STAGING_PORT" \
      SERVICE="sbs-web" \
      INVOICE_URL="http://127.0.0.1:$INVOICE_PORT/" \
      INVOICE_ATTEMPTS=2 \
      "$@" \
      "$SOURCE_DIR/infra/scripts/deploy-artifact.sh" "$ARTIFACT" \
      > "$ROOT/$label.log" 2>&1
  DEPLOY_STATUS=$?
  set -e
}

current_target() { readlink -f "$ROOT/current" 2>/dev/null || echo none; }

echo "== deploy-artifact.sh invoice-app gate =="
echo "   artifact: $(basename "$ARTIFACT")"
echo

# ---------------------------------------------------------------- scenario B
echo "-- B: invoice-app active, HTTP 303 -> accept"
printf '303' > "$ROOT/invoice-code"
printf 'active' > "$ROOT/state-invoice-app"
run_deploy b
B_TARGET="$(current_target)"

if [ "$DEPLOY_STATUS" -eq 0 ]; then
  pass "deployment accepted (exit 0)"
else
  fail "deployment failed (exit $DEPLOY_STATUS)"
  sed 's/^/        /' "$ROOT/b.log" | tail -25 >&2
fi
[ -d "$B_TARGET" ] && pass "release activated: $(basename "$B_TARGET")" \
  || fail "no release was activated"
if grep -q 'invoice-after:  state=active http=303 accepted' "$ROOT"/state/deploy-*.state; then
  pass "state file records the exact accepted code (303)"
else
  fail "state file does not record the accepted invoice-app code"
fi
if grep -qE '^\s+ok\s+/plattform/flowcheck\s+200' "$ROOT/b.log"; then
  pass "E: staging health matrix ran against the real artifact"
else
  fail "E: staging health matrix did not report its checks"
fi
PREVIOUS="$B_TARGET"
echo

# ---------------------------------------------------------------- scenario C
echo "-- C: invoice-app active, HTTP 500 after activation -> rollback"
printf '303' > "$ROOT/invoice-code"
printf 'active' > "$ROOT/state-invoice-app"
run_deploy c FAULT_INVOICE_CODE=500

if [ "$DEPLOY_STATUS" -ne 0 ]; then
  pass "deployment refused (exit $DEPLOY_STATUS)"
else
  fail "deployment was accepted despite invoice-app answering 500"
fi
if grep -q 'http=500' "$ROOT/c.log"; then
  pass "the rejected code is reported (500)"
else
  fail "the rejected code was not reported"
  sed 's/^/        /' "$ROOT/c.log" | tail -20 >&2
fi
if grep -q 'Rolling back' "$ROOT/c.log"; then
  pass "rollback was performed"
else
  fail "no rollback was performed"
fi
if [ "$(current_target)" = "$PREVIOUS" ]; then
  pass "symlink restored to the previous release"
else
  fail "symlink points at $(current_target), expected $PREVIOUS"
fi
if grep -q 'REJECTED' "$ROOT"/state/deploy-*.state; then
  pass "state file records the rejection"
else
  fail "state file does not record the rejection"
fi
echo

# ---------------------------------------------------------------- scenario D
echo "-- D: invoice-app inactive after activation -> rollback"
printf '303' > "$ROOT/invoice-code"
printf 'active' > "$ROOT/state-invoice-app"
run_deploy d FAULT_INVOICE_STATE=inactive

if [ "$DEPLOY_STATUS" -ne 0 ]; then
  pass "deployment refused (exit $DEPLOY_STATUS)"
else
  fail "deployment was accepted despite invoice-app being inactive"
fi
if grep -q 'state=inactive' "$ROOT/d.log"; then
  pass "the rejected unit state is reported (inactive)"
else
  fail "the rejected unit state was not reported"
  sed 's/^/        /' "$ROOT/d.log" | tail -20 >&2
fi
if grep -q 'Rolling back' "$ROOT/d.log"; then
  pass "rollback was performed"
else
  fail "no rollback was performed"
fi
if [ "$(current_target)" = "$PREVIOUS" ]; then
  pass "symlink restored to the previous release"
else
  fail "symlink points at $(current_target), expected $PREVIOUS"
fi
echo

# ------------------------------------------------- scenario D': pre-deploy gate
echo "-- D': invoice-app already unhealthy -> refuse before touching anything"
printf 'inactive' > "$ROOT/state-invoice-app"
RELEASES_BEFORE="$(find "$ROOT/releases" -mindepth 1 -maxdepth 1 -type d | wc -l)"
run_deploy dpre
RELEASES_AFTER="$(find "$ROOT/releases" -mindepth 1 -maxdepth 1 -type d | wc -l)"
printf 'active' > "$ROOT/state-invoice-app"
printf '303' > "$ROOT/invoice-code"

if [ "$DEPLOY_STATUS" -ne 0 ] && grep -q 'nothing was changed' "$ROOT/dpre.log"; then
  pass "refused before unpacking"
else
  fail "did not refuse on an already-unhealthy invoice-app"
fi
if [ "$RELEASES_BEFORE" = "$RELEASES_AFTER" ]; then
  pass "no release directory was created"
else
  fail "a release was unpacked despite the refusal"
fi
echo

# ---------------------------------------------------------------- scenario F
echo "-- F: nginx untouched throughout"
if grep -qiE '(reload|restart|start|stop)[[:space:]]+nginx' "$ROOT/systemctl.log"; then
  fail "the deployment asked systemd to act on nginx:"
  grep -iE 'nginx' "$ROOT/systemctl.log" | sed 's/^/        /' >&2
else
  pass "no nginx reload or restart was requested"
fi
if [ "$(nginx_tree_hash)" = "$NGINX_HASH_BEFORE" ]; then
  pass "/etc/nginx unchanged"
else
  fail "/etc/nginx was modified by a deployment"
fi
NGINX_MASTER_AFTER="$(pgrep -f 'nginx: master' 2>/dev/null | sort | tr '\n' ',' || true)"
if [ "$NGINX_MASTER_BEFORE" = "$NGINX_MASTER_AFTER" ]; then
  pass "nginx master unchanged (${NGINX_MASTER_BEFORE:-not running})"
else
  fail "nginx was restarted: ${NGINX_MASTER_BEFORE:-none} -> ${NGINX_MASTER_AFTER:-none}"
fi
if [ -f "$ROOT/systemd/sbs-web.service" ] && [ ! -e /etc/systemd/system/sbs-web.service ]; then
  pass "the unit file went to the sandbox, not /etc/systemd/system"
else
  pass "unit file written to the sandbox ($ROOT/systemd)"
fi

echo
[ "$FAILURES" -eq 0 ] && { echo "deploy invoice-app gate: PASS"; exit 0; }
echo "deploy invoice-app gate: $FAILURES failure(s)"; exit 1
