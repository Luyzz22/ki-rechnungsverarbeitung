#!/usr/bin/env bash
# =============================================================================
# Build a self-contained, verifiable release artifact.
#
# The production host has 1 vCPU and 2 GB RAM and runs a live application, so it
# must never install dependencies or compile. This script runs in CI (or any
# trusted build machine) and produces a tarball that the host only has to verify
# and unpack.
#
#   ./scripts/build-artifact.sh [output-dir]
#
# Output (default dist/):
#   sbs-web-<shortsha>.tar.gz          the runtime artifact
#   sbs-web-<shortsha>.tar.gz.sha256   checksum, in `sha256sum -c` format
#   sbs-web-<shortsha>.manifest.json   provenance
# =============================================================================
set -euo pipefail

OUT_DIR="${1:-dist}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

log() { printf '\033[1m==>\033[0m %s\n' "$*"; }

COMMIT="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
DIRTY=""
if ! git diff --quiet HEAD 2>/dev/null || [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  DIRTY="-dirty"
fi

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# ---- 1. Verify the build output exists ------------------------------------
if [ ! -f ".next/standalone/server.js" ]; then
  echo "ERROR: .next/standalone/server.js is missing." >&2
  echo "Run 'npm run build' first (next.config.mjs sets output: 'standalone')." >&2
  exit 1
fi

# ---- 2. Assemble the runtime tree ------------------------------------------
log "Assembling runtime tree"
RELEASE="$STAGE/sbs-web"
mkdir -p "$RELEASE"
cp -r .next/standalone/. "$RELEASE/"
mkdir -p "$RELEASE/.next"
cp -r .next/static "$RELEASE/.next/static"
[ -d public ] && cp -r public "$RELEASE/public"

# The artifact must run without the repository, so nothing may point back at it.
if [ -e "$RELEASE/.git" ]; then
  echo "ERROR: build output contains a .git entry" >&2
  exit 1
fi

# ---- 3. Refuse to ship anything secret-shaped ------------------------------
log "Scanning for accidental secrets"
if find "$RELEASE" -maxdepth 3 \( -name '.env' -o -name '.env.*' -o -name '*.pem' -o -name 'id_rsa*' \) -print | grep -q .; then
  echo "ERROR: the runtime tree contains environment or key files" >&2
  find "$RELEASE" -maxdepth 3 \( -name '.env' -o -name '.env.*' -o -name '*.pem' -o -name 'id_rsa*' \) -print >&2
  exit 1
fi

# ---- 4. Provenance ---------------------------------------------------------
NODE_VERSION="$(node --version)"
BUILT_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FILE_COUNT="$(find "$RELEASE" -type f | wc -l | tr -d ' ')"
TREE_BYTES="$(du -sb "$RELEASE" | cut -f1)"

cat > "$RELEASE/RELEASE.json" <<JSON
{
  "repository": "SBS-Nexus/sbs-web",
  "commit": "$COMMIT",
  "builtAt": "$BUILT_AT",
  "node": "$NODE_VERSION",
  "files": $FILE_COUNT,
  "bytes": $TREE_BYTES
}
JSON

# ---- 5. Pack deterministically ---------------------------------------------
# Fixed mtime, owner and sort order so the same commit yields the same digest.
mkdir -p "$OUT_DIR"
NAME="sbs-web-${SHORT}${DIRTY}.tar.gz"
log "Packing $OUT_DIR/$NAME"
tar --sort=name \
    --mtime='UTC 2020-01-01' \
    --owner=0 --group=0 --numeric-owner \
    --format=gnu \
    -C "$STAGE" -cf - sbs-web \
  | gzip -n -9 > "$OUT_DIR/$NAME"

( cd "$OUT_DIR" && sha256sum "$NAME" > "$NAME.sha256" )
DIGEST="$(cut -d' ' -f1 < "$OUT_DIR/$NAME.sha256")"

cat > "$OUT_DIR/sbs-web-${SHORT}${DIRTY}.manifest.json" <<JSON
{
  "repository": "SBS-Nexus/sbs-web",
  "commit": "$COMMIT",
  "artifact": "$NAME",
  "sha256": "$DIGEST",
  "builtAt": "$BUILT_AT",
  "node": "$NODE_VERSION",
  "files": $FILE_COUNT,
  "unpackedBytes": $TREE_BYTES
}
JSON

log "Done"
printf '  artifact : %s\n' "$OUT_DIR/$NAME"
printf '  size     : %s\n' "$(du -h "$OUT_DIR/$NAME" | cut -f1)"
printf '  sha256   : %s\n' "$DIGEST"
printf '  commit   : %s\n' "$COMMIT"

if [ -n "$DIRTY" ]; then
  echo
  echo "WARNING: built from a dirty working tree — not a releasable artifact." >&2
fi
