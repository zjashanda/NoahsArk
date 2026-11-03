#!/usr/bin/env bash
# NoahsArk backup: PostgreSQL custom-format dump + local evidence archive.
#
# SAFE BY DEFAULT: without --execute this script only prints the plan and
# performs read-only prerequisite checks. Nothing is written outside the
# destination directory, and nothing is deleted.
#
# Usage:
#   scripts/backup.sh [--execute] [--dest DIR] [--evidence-root DIR]
#
# Inputs (environment, never logged):
#   DATABASE_URL or NAA_DATABASE_URL
#       postgresql+asyncpg://user:CHANGE_ME@127.0.0.1:5432/noahsark
#       The +asyncpg suffix is rewritten for pg_dump.
#   NAA_BACKUP_DIR       destination (default /var/backups/noahsark)
#   NAA_EVIDENCE_ROOT    evidence root (default $EVIDENCE_STORAGE_ROOT, then
#                        /var/lib/noahsark/evidence)
#
# Exit codes: 0 ok; 1 usage/config error; 2 prerequisite missing; 3 command failed.

set -euo pipefail
umask 077

MODE="dry-run"
DEST="${NAA_BACKUP_DIR:-/var/backups/noahsark}"
EVIDENCE_ROOT="${NAA_EVIDENCE_ROOT:-${EVIDENCE_STORAGE_ROOT:-/var/lib/noahsark/evidence}}"

usage() {
  cat <<'EOF'
NoahsArk backup: PostgreSQL custom-format dump + local evidence archive.

SAFE BY DEFAULT: without --execute this script only prints the plan and
performs read-only prerequisite checks. Nothing is deleted.

Usage: scripts/backup.sh [--execute] [--dry-run] [--dest DIR] [--evidence-root DIR]

Environment:
  DATABASE_URL / NAA_DATABASE_URL   source database (never printed)
  NAA_BACKUP_DIR                    destination (default /var/backups/noahsark)
  NAA_EVIDENCE_ROOT                 evidence root
                                    (default $EVIDENCE_STORAGE_ROOT, then
                                     /var/lib/noahsark/evidence)

Exit codes: 0 ok; 1 usage/config error; 2 prerequisite missing; 3 command failed.
EOF
}

die() {
  local code="$1"
  shift
  printf 'backup: ERROR: %s\n' "$*" >&2
  exit "$code"
}

while (($#)); do
  case "$1" in
    --execute) MODE="execute" ;;
    --dry-run) MODE="dry-run" ;;
    --dest)
      [[ $# -ge 2 ]] || die 1 "--dest requires a value"
      DEST="$2"
      shift
      ;;
    --evidence-root)
      [[ $# -ge 2 ]] || die 1 "--evidence-root requires a value"
      EVIDENCE_ROOT="$2"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) die 1 "unknown argument: $1" ;;
  esac
  shift
done

for tool in pg_dump pg_restore tar sha256sum stat date; do
  command -v "$tool" >/dev/null 2>&1 || die 2 "required tool not found: $tool"
done

RAW_DSN="${NAA_DATABASE_URL:-${DATABASE_URL:-}}"
PG_DSN=""
if [[ -n "$RAW_DSN" ]]; then
  case "$RAW_DSN" in
    postgresql+asyncpg://*) PG_DSN="postgresql://${RAW_DSN#postgresql+asyncpg://}" ;;
    postgresql://*|postgres://*) PG_DSN="$RAW_DSN" ;;
    *) die 1 "DATABASE_URL must start with postgresql+asyncpg://, postgresql:// or postgres://" ;;
  esac
fi

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$DEST/$TIMESTAMP"

printf 'backup mode       : %s\n' "$MODE"
printf 'destination       : %s\n' "$DEST"
printf 'evidence root     : %s\n' "$EVIDENCE_ROOT"
if [[ -n "$PG_DSN" ]]; then
  printf 'database          : configured (value redacted)\n'
else
  printf 'database          : NOT CONFIGURED\n'
fi

if [[ ! -d "$EVIDENCE_ROOT" ]]; then
  printf 'warning           : evidence root does not exist yet: %s\n' "$EVIDENCE_ROOT" >&2
fi

if [[ "$MODE" == "dry-run" ]]; then
  printf '\nplanned output    : %s\n' "$OUT_DIR"
  printf 'planned commands  :\n'
  printf '  pg_dump --dbname=<redacted> --format=custom --no-owner --no-privileges --file=%q/db.dump\n' "$OUT_DIR"
  printf '  tar -C %q -czf %q/evidence.tar.gz %q\n' \
    "$(dirname "$EVIDENCE_ROOT")" "$OUT_DIR" "$(basename "$EVIDENCE_ROOT")"
  printf '  sha256sum db.dump evidence.tar.gz manifest.json > SHA256SUMS  (run inside %s)\n' "$OUT_DIR"
  printf '  pg_restore --list %q/db.dump  (dump readability check)\n' "$OUT_DIR"
  printf '\ndry-run: no files written, nothing deleted.\n'
  if [[ -z "$PG_DSN" ]]; then
    printf 'dry-run: set DATABASE_URL/NAA_DATABASE_URL before --execute.\n' >&2
  fi
  exit 0
fi

[[ -n "$PG_DSN" ]] || die 1 "--execute requires DATABASE_URL or NAA_DATABASE_URL"
[[ -d "$EVIDENCE_ROOT" ]] || die 2 "--execute requires an existing evidence root: $EVIDENCE_ROOT"
[[ ! -e "$OUT_DIR" ]] || die 1 "destination already exists, refusing to overwrite: $OUT_DIR"

install -d -m 0700 "$OUT_DIR"
printf 'backup: writing %s\n' "$OUT_DIR"

pg_dump --dbname="$PG_DSN" --format=custom --no-owner --no-privileges \
  --file="$OUT_DIR/db.dump" || die 3 "pg_dump failed"

pg_restore --list "$OUT_DIR/db.dump" >/dev/null || die 3 "pg_restore --list rejected db.dump"

tar -C "$(dirname "$EVIDENCE_ROOT")" -czf "$OUT_DIR/evidence.tar.gz" \
  "$(basename "$EVIDENCE_ROOT")" || die 3 "evidence archive failed"

tar -tzf "$OUT_DIR/evidence.tar.gz" >/dev/null || die 3 "evidence archive readability check failed"

DB_SHA="$(sha256sum "$OUT_DIR/db.dump" | cut -d' ' -f1)"
EV_SHA="$(sha256sum "$OUT_DIR/evidence.tar.gz" | cut -d' ' -f1)"
DB_BYTES="$(stat -c '%s' "$OUT_DIR/db.dump")"
EV_BYTES="$(stat -c '%s' "$OUT_DIR/evidence.tar.gz")"
PG_VERSION="$(pg_dump --version | head -n 1)"

{
  printf '{\n'
  printf '  "created_utc": "%s",\n' "$TIMESTAMP"
  printf '  "database": {"format": "custom", "file": "db.dump", "sha256": "%s", "bytes": %s},\n' "$DB_SHA" "$DB_BYTES"
  printf '  "evidence": {"file": "evidence.tar.gz", "sha256": "%s", "bytes": %s, "root_basename": "%s"},\n' "$EV_SHA" "$EV_BYTES" "$(basename "$EVIDENCE_ROOT")"
  printf '  "tool": {"pg_dump": "%s"}\n' "$PG_VERSION"
  printf '}\n'
} > "$OUT_DIR/manifest.json"

# Cover the manifest too, so a later checksum check also detects a tampered
# manifest. SHA256SUMS itself is the trust anchor and cannot cover itself.
(
  cd "$OUT_DIR"
  sha256sum db.dump evidence.tar.gz manifest.json > SHA256SUMS
)

chmod -R u=rwX,go= "$OUT_DIR"
printf 'backup: complete\n'
printf '  db.dump        %s bytes sha256=%s\n' "$DB_BYTES" "$DB_SHA"
printf '  evidence.tar.gz %s bytes sha256=%s\n' "$EV_BYTES" "$EV_SHA"
printf '  manifest        %s/manifest.json\n' "$OUT_DIR"
