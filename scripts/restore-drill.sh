#!/usr/bin/env bash
# NoahsArk restore drill: verify a backup and restore it into a DRILL-ONLY
# PostgreSQL database and an empty evidence directory.
#
# SAFE BY DEFAULT: without --execute this script only verifies checksums and
# prints the plan. Even with --execute, a destructive restore requires
# --confirm, a target database whose name ends in `_drill`, and a target that
# differs from the configured source database. The script never drops a
# database and never deletes files.
#
# Usage:
#   scripts/restore-drill.sh [--backup-dir DIR] [--target-db NAME_drill]
#                            [--target-dsn DSN] [--evidence-target DIR]
#                            [--execute --confirm]
#
# Inputs:
#   NAA_BACKUP_DIR     parent for backups (default /var/backups/noahsark)
#   NAA_RESTORE_DSN    postgresql://... connection string for the drill DB
#                      (required for --execute; password must not be committed)
#   NAA_EVIDENCE_ROOT  used only to derive the default drill evidence path
#
# Exit codes: 0 ok; 1 usage/config error; 2 prerequisite missing; 3 command failed.

set -euo pipefail
umask 077

MODE="dry-run"
CONFIRMED="no"
BACKUP_PARENT="${NAA_BACKUP_DIR:-/var/backups/noahsark}"
BACKUP_DIR=""
TARGET_DB=""
TARGET_DSN="${NAA_RESTORE_DSN:-}"
EVIDENCE_TARGET=""

usage() {
  cat <<'EOF'
NoahsArk restore drill: verify a backup and restore it into a DRILL-ONLY
PostgreSQL database and an empty evidence directory.

SAFE BY DEFAULT: without --execute this script only verifies checksums and
prints the plan. --execute additionally requires --confirm, a target database
ending in `_drill`, and a target different from DATABASE_URL.

Usage: scripts/restore-drill.sh [--backup-dir DIR] [--target-db NAME_drill]
                                [--target-dsn DSN] [--evidence-target DIR]
                                [--execute --confirm]

Environment:
  NAA_BACKUP_DIR     parent for backups (default /var/backups/noahsark)
  NAA_RESTORE_DSN    postgresql://... for the drill DB (required for --execute)
  DATABASE_URL       used only to refuse restoring over the source database

Exit codes: 0 ok; 1 usage/config error; 2 prerequisite missing; 3 command failed.
EOF
}

die() {
  local code="$1"
  shift
  printf 'restore-drill: ERROR: %s\n' "$*" >&2
  exit "$code"
}

while (($#)); do
  case "$1" in
    --execute) MODE="execute" ;;
    --dry-run) MODE="dry-run" ;;
    --confirm) CONFIRMED="yes" ;;
    --backup-dir)
      [[ $# -ge 2 ]] || die 1 "--backup-dir requires a value"
      BACKUP_DIR="$2"
      shift
      ;;
    --target-db)
      [[ $# -ge 2 ]] || die 1 "--target-db requires a value"
      TARGET_DB="$2"
      shift
      ;;
    --target-dsn)
      [[ $# -ge 2 ]] || die 1 "--target-dsn requires a value"
      TARGET_DSN="$2"
      shift
      ;;
    --evidence-target)
      [[ $# -ge 2 ]] || die 1 "--evidence-target requires a value"
      EVIDENCE_TARGET="$2"
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

for tool in pg_restore tar sha256sum; do
  command -v "$tool" >/dev/null 2>&1 || die 2 "required tool not found: $tool"
done

if [[ -z "$BACKUP_DIR" ]]; then
  [[ -d "$BACKUP_PARENT" ]] || die 2 "no backup directory found under $BACKUP_PARENT; pass --backup-dir"
  BACKUP_DIR="$(find "$BACKUP_PARENT" -mindepth 1 -maxdepth 1 -type d -name '2*' | sort | tail -n 1)"
  [[ -n "$BACKUP_DIR" ]] || die 2 "no timestamped backup under $BACKUP_PARENT; pass --backup-dir"
fi

[[ -d "$BACKUP_DIR" ]] || die 2 "backup directory does not exist: $BACKUP_DIR"
[[ -f "$BACKUP_DIR/db.dump" ]] || die 2 "missing $BACKUP_DIR/db.dump"
[[ -f "$BACKUP_DIR/evidence.tar.gz" ]] || die 2 "missing $BACKUP_DIR/evidence.tar.gz"
[[ -f "$BACKUP_DIR/SHA256SUMS" ]] || die 2 "missing $BACKUP_DIR/SHA256SUMS"
[[ -f "$BACKUP_DIR/manifest.json" ]] || die 2 "missing $BACKUP_DIR/manifest.json"

printf 'restore-drill mode : %s\n' "$MODE"
printf 'backup directory   : %s\n' "$BACKUP_DIR"

printf 'checksums          : '
if (cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS >/dev/null); then
  printf 'OK\n'
else
  die 3 "checksum verification failed"
fi

if [[ -z "$TARGET_DB" ]]; then
  TARGET_DB="noahsark_drill"
fi
[[ "$TARGET_DB" == *_drill ]] || die 1 "target database must end in _drill (got: $TARGET_DB)"
[[ "$TARGET_DB" != "postgres" && "$TARGET_DB" != "template1" ]] || die 1 "refusing system database: $TARGET_DB"

if [[ -n "${DATABASE_URL:-}" ]]; then
  SOURCE_DB="${DATABASE_URL%%\?*}"
  SOURCE_DB="${SOURCE_DB##*/}"
  [[ "$SOURCE_DB" != "$TARGET_DB" ]] || die 1 "target database equals the configured source database: $TARGET_DB"
fi

if [[ -z "$EVIDENCE_TARGET" ]]; then
  EVIDENCE_TARGET="$BACKUP_DIR/restored-evidence-drill"
fi

if [[ "$MODE" == "dry-run" ]]; then
  printf 'target database   : %s\n' "$TARGET_DB"
  printf 'target DSN        : %s\n' "$([[ -n "$TARGET_DSN" ]] && echo 'configured (value redacted)' || echo 'NOT CONFIGURED')"
  printf 'evidence target   : %s\n' "$EVIDENCE_TARGET"
  printf '\nplanned commands  :\n'
  printf '  pg_restore --clean --if-exists --no-owner --no-privileges --dbname=<redacted/%s> %q/db.dump\n' "$TARGET_DB" "$BACKUP_DIR"
  printf '  mkdir -p %q\n' "$EVIDENCE_TARGET"
  printf '  tar -xzf %q/evidence.tar.gz -C %q\n' "$BACKUP_DIR" "$EVIDENCE_TARGET"
  printf '\ndry-run: checksums verified; no database or directory was modified.\n'
  printf 'dry-run: --execute additionally requires --confirm and NAA_RESTORE_DSN.\n'
  exit 0
fi

[[ "$CONFIRMED" == "yes" ]] || die 1 "--execute requires --confirm (destructive restore into the drill target)"
[[ -n "$TARGET_DSN" ]] || die 1 "--execute requires NAA_RESTORE_DSN or --target-dsn"
case "$TARGET_DSN" in
  postgresql://*|postgres://*) ;;
  *) die 1 "target DSN must start with postgresql:// or postgres://" ;;
esac
[[ "${TARGET_DSN%%\?*}" == *"/$TARGET_DB" ]] || die 1 "target DSN does not end with /$TARGET_DB"

if [[ -e "$EVIDENCE_TARGET" ]]; then
  [[ -d "$EVIDENCE_TARGET" ]] || die 1 "evidence target is not a directory: $EVIDENCE_TARGET"
  [[ -z "$(ls -A "$EVIDENCE_TARGET")" ]] || die 1 "evidence target is not empty, refusing to overwrite: $EVIDENCE_TARGET"
else
  install -d -m 0700 "$EVIDENCE_TARGET"
fi

printf 'restore-drill: restoring database into %s (drill only)\n' "$TARGET_DB"
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname="$TARGET_DSN" "$BACKUP_DIR/db.dump" || die 3 "pg_restore failed"

printf 'restore-drill: extracting evidence into %s\n' "$EVIDENCE_TARGET"
tar -xzf "$BACKUP_DIR/evidence.tar.gz" -C "$EVIDENCE_TARGET" || die 3 "evidence extraction failed"

EVIDENCE_FILES="$(find "$EVIDENCE_TARGET" -type f | wc -l)"
printf 'restore-drill: complete (database + %s evidence files)\n' "$EVIDENCE_FILES"
printf 'restore-drill: the drill database was not dropped; retire it explicitly after review.\n'
