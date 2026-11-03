#!/usr/bin/env bash
# One-time local store initialization for the NoahsArk node inventory.
#
# Creates the repo-external encrypted-store directory layout, optionally
# generates the age identity, and prints ONLY the age public key. The age
# private key never leaves the local machine and is never printed.
#
# Usage:
#   scripts/node-inventory/init-local-store.sh --generate-key [--write-sops-config]
#   scripts/node-inventory/init-local-store.sh --check
#
# This script never reads a connection table and never contacts a node.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

GENERATE_KEY=0
WRITE_CONFIG=0
CHECK_ONLY=0
FORCE=0

usage() {
  sed -n '2,14p' "${BASH_SOURCE[0]}"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --generate-key) GENERATE_KEY=1 ;;
    --write-sops-config) WRITE_CONFIG=1 ;;
    --check) CHECK_ONLY=1 ;;
    --force) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown_argument=$1" ;;
  esac
  shift
done

AGE_DIR="$LOCAL_ROOT/age"
AGE_KEY="$AGE_DIR/keys.txt"
mkdir -p "$AGE_DIR"
chmod 700 "$LOCAL_ROOT" "$AGE_DIR" 2>/dev/null || true

if [ "$CHECK_ONLY" -eq 1 ]; then
  require_no_umask_slack
  if [ -f "$AGE_KEY" ]; then
    mode="$(stat -c '%a' "$AGE_KEY" 2>/dev/null || echo unknown)"
    [ "$mode" = "600" ] || die "age_key_mode=$mode expected=600"
    info "LOCAL_STORE=OK age_key=present mode=600"
  else
    info "LOCAL_STORE=OK age_key=absent"
  fi
  exit 0
fi

ensure_local_dirs
require_no_umask_slack

if [ ! -f "$AGE_KEY" ]; then
  if [ "$GENERATE_KEY" -ne 1 ]; then
    die "age_key_absent run_with=--generate-key"
  fi
  require_cmd age-keygen
  age-keygen -o "$AGE_KEY" >/dev/null 2>&1 || die "age_keygen_failed"
  chmod 600 "$AGE_KEY"
elif [ "$GENERATE_KEY" -eq 1 ] && [ "$FORCE" -eq 1 ]; then
  # Explicit force is the only path that replaces an existing identity.
  # Operators should prefer --write-sops-config or manual rotation instead.
  require_cmd age-keygen
  backup="$AGE_KEY.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  cp -p "$AGE_KEY" "$backup"
  chmod 600 "$backup"
  age-keygen -o "$AGE_KEY" >/dev/null 2>&1 || die "age_keygen_failed"
  chmod 600 "$AGE_KEY"
  warn "age_key_replaced backup_created=$backup"
fi

require_cmd age-keygen
public_key="$(age-keygen -y "$AGE_KEY" 2>/dev/null)" || die "age_public_key_unreadable"
case "$public_key" in
  age1*) ;;
  *) die "age_public_key_invalid" ;;
esac

info "AGE_PUBLIC_KEY=$public_key"

if [ "$WRITE_CONFIG" -eq 1 ]; then
  require_file "$SOPS_CONFIG"
  PUBLIC_KEY="$public_key" SOPS_CONFIG="$SOPS_CONFIG" python3 - <<'PY'
import os, re, pathlib
path = pathlib.Path(os.environ["SOPS_CONFIG"])
key = os.environ["PUBLIC_KEY"]
text = path.read_text(encoding="utf-8")
updated, count = re.subn(
    r"(?m)^(\s*)age:\s*age1REPLACE_WITH_OPERATOR_PUBLIC_KEY\s*$",
    lambda m: f"{m.group(1)}age: {key}",
    text,
)
if count != 1:
    raise SystemExit("sops_config_placeholder_not_found")
path.write_text(updated, encoding="utf-8")
PY
  [ "$?" -eq 0 ] || die "sops_config_update_failed"
  chmod 644 "$SOPS_CONFIG"
  info "SOPS_CONFIG_UPDATED=$SOPS_CONFIG"
fi

for tool in sops age; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    warn "tool_missing=$tool encrypted_store_init_blocked"
  fi
done

audit_event "local_store_init" "ok"
info "NEXT run=scripts/node-inventory/import-inventory.sh --source <sanitized.yaml>"
info "NEXT then=scripts/node-inventory/verify-nodes.sh"
