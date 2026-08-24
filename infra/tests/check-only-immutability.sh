#!/usr/bin/env bash
# =============================================================================
# Proves that `enable-nginx.sh --check` does not mutate the nginx configuration.
#
# Takes a full fingerprint of the nginx tree — every path, mode, size and
# content hash — runs the preflight, fingerprints again, and fails on any
# difference. It also watches the paths a config test is known to touch outside
# the tree: no backup directory may appear, the pid file must keep whatever
# state it had, no new file may appear under /var/log/nginx, and the running
# nginx master must not be restarted.
#
#   sudo ./infra/tests/check-only-immutability.sh [nginx-etc-dir]
#   sudo ./infra/tests/check-only-immutability.sh --self-test
#
# --self-test proves the detector actually detects: it points the harness at a
# stub that writes into the tree, and requires the harness to report failure.
#
# Defaults to /etc/nginx. Pass another directory to exercise the test against a
# throwaway tree, which is what infra/tests/run-all.sh does.
# =============================================================================
set -euo pipefail

SELF_TEST=0
[ "${1:-}" = "--self-test" ] && { SELF_TEST=1; shift; }

NGINX_ETC="${1:-/etc/nginx}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Overridable so the detector can be pointed at a deliberately mutating stub.
# A test that cannot fail proves nothing; --self-test exercises exactly that.
CHECK_CMD="${CHECK_CMD:-$SOURCE_DIR/infra/scripts/enable-nginx.sh}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

pass() { printf '  \033[1;32mPASS\033[0m %s\n' "$*"; }
fail() { printf '  \033[1;31mFAIL\033[0m %s\n' "$*" >&2; FAILURES=$((FAILURES + 1)); }
FAILURES=0

if [ "$SELF_TEST" = 1 ]; then
  echo "== self-test: the detector must catch a mutating --check =="
  TREE="$WORK/etc-nginx"
  mkdir -p "$TREE/conf.d"
  printf 'events {}\nhttp { include %s/conf.d/*.conf; }\n' "$TREE" > "$TREE/nginx.conf"
  printf 'server { listen 8081; }\n' > "$TREE/conf.d/site.conf"

  STUB="$WORK/mutating-check.sh"
  cat > "$STUB" <<'STUBEOF'
#!/usr/bin/env bash
# Stands in for a preflight that claims to be read-only but is not.
echo "nginx: configuration file syntax is ok"
printf '# written by a badly behaved --check\n' >> "$NGINX_ETC/conf.d/site.conf"
STUBEOF
  chmod +x "$STUB"

  set +e
  CHECK_CMD="$STUB" "$0" "$TREE" > "$WORK/self.log" 2>&1
  SELF_STATUS=$?
  set -e
  sed 's/^/      /' "$WORK/self.log"

  if [ "$SELF_STATUS" -ne 0 ] && grep -q "was modified" "$WORK/self.log"; then
    echo
    echo "check-only immutability self-test: PASS (mutation detected)"
    exit 0
  fi
  echo
  echo "check-only immutability self-test: FAIL — a mutating --check went unnoticed" >&2
  exit 1
fi

fingerprint() {
  # Path, type, mode, size and content hash for every entry, sorted. Symlink
  # targets are recorded rather than followed.
  local root="$1"
  [ -d "$root" ] || { echo "MISSING $root"; return 0; }
  find "$root" -mindepth 0 -print0 2>/dev/null | sort -z | while IFS= read -r -d '' entry; do
    if [ -L "$entry" ]; then
      printf '%s\tlink\t%s\n' "${entry#"$root"}" "$(readlink "$entry")"
    elif [ -d "$entry" ]; then
      printf '%s\tdir\t%s\n' "${entry#"$root"}" "$(stat -c '%a' "$entry")"
    else
      printf '%s\tfile\t%s\t%s\t%s\n' "${entry#"$root"}" \
        "$(stat -c '%a' "$entry")" "$(stat -c '%s' "$entry")" \
        "$(sha256sum "$entry" 2>/dev/null | cut -d' ' -f1)"
    fi
  done
}

count_backups() {
  # `ls -1d glob | wc -l` exits 2 under `set -o pipefail` when nothing matches,
  # which would abort the test silently. Count with a glob instead.
  local n=0 d
  for d in /root/nginx-backup-*; do
    [ -e "$d" ] && n=$((n + 1))
  done
  printf '%s\n' "$n"
}

echo "== enable-nginx.sh --check immutability =="
echo "   tree: $NGINX_ETC"

fingerprint "$NGINX_ETC" > "$WORK/before.txt"
BEFORE_LINES="$(wc -l < "$WORK/before.txt")"
echo "   fingerprinted $BEFORE_LINES entries"

BACKUPS_BEFORE="$(count_backups)"

# `nginx -t` opens the configured `pid` path and every `error_log`, creating
# them when absent. --check must not do that, so the pid file's exact state and
# the set of files under /var/log/nginx are witnesses too. Only the file *names*
# in the log directory are compared: a running nginx appends to its logs, and
# that is not a mutation caused by --check.
pid_state() {
  if [ -e /run/nginx.pid ]; then
    printf 'present size=%s content=%s\n' \
      "$(stat -c '%s' /run/nginx.pid)" "$(tr -d '\n' < /run/nginx.pid)"
  else
    printf 'absent\n'
  fi
}
log_names() {
  [ -d /var/log/nginx ] || { printf 'no-log-dir\n'; return 0; }
  find /var/log/nginx -mindepth 1 -printf '%P\n' 2>/dev/null | sort
}

PID_BEFORE="$(pid_state)"
log_names > "$WORK/logs-before.txt"

# A restart replaces the master pid; a reload keeps it. Either is a failure.
NGINX_MASTER_BEFORE="$(pgrep -f 'nginx: master' 2>/dev/null | sort | tr '\n' ',' || true)"

set +e
NGINX_ETC="$NGINX_ETC" "$CHECK_CMD" --check > "$WORK/check.log" 2>&1
CHECK_STATUS=$?
set -e

sed 's/^/      /' "$WORK/check.log"

fingerprint "$NGINX_ETC" > "$WORK/after.txt"

if [ "$CHECK_STATUS" -ne 0 ]; then
  fail "--check exited $CHECK_STATUS"
else
  pass "--check exited 0"
fi

if diff -u "$WORK/before.txt" "$WORK/after.txt" > "$WORK/diff.txt"; then
  pass "$NGINX_ETC unchanged ($BEFORE_LINES entries, identical hashes)"
else
  fail "$NGINX_ETC was modified:"
  sed 's/^/        /' "$WORK/diff.txt" >&2
fi

BACKUPS_AFTER="$(count_backups)"
if [ "$BACKUPS_BEFORE" = "$BACKUPS_AFTER" ]; then
  pass "no backup directory created"
else
  fail "--check created a backup directory"
fi

PID_AFTER="$(pid_state)"
if [ "$PID_BEFORE" = "$PID_AFTER" ]; then
  pass "/run/nginx.pid untouched ($PID_BEFORE)"
else
  fail "--check altered /run/nginx.pid: $PID_BEFORE -> $PID_AFTER"
fi

log_names > "$WORK/logs-after.txt"
if diff -u "$WORK/logs-before.txt" "$WORK/logs-after.txt" > "$WORK/logs-diff.txt"; then
  pass "no new file under /var/log/nginx"
else
  fail "--check created a log file:"
  sed 's/^/        /' "$WORK/logs-diff.txt" >&2
fi

NGINX_MASTER_AFTER="$(pgrep -f 'nginx: master' 2>/dev/null | sort | tr '\n' ',' || true)"
if [ "$NGINX_MASTER_BEFORE" = "$NGINX_MASTER_AFTER" ]; then
  pass "nginx master unchanged (${NGINX_MASTER_BEFORE:-not running})"
else
  fail "nginx was restarted: ${NGINX_MASTER_BEFORE:-none} -> ${NGINX_MASTER_AFTER:-none}"
fi

if grep -qi "syntax is ok" "$WORK/check.log"; then
  pass "candidate configuration validated"
else
  fail "no successful nginx -t in the output"
fi

echo
[ "$FAILURES" -eq 0 ] && { echo "check-only immutability: PASS"; exit 0; }
echo "check-only immutability: $FAILURES failure(s)"; exit 1
