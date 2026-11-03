#!/usr/bin/env bash
# One-time / repeatable import into the NoahsArk node inventory.
#
# Contract:
#   --source <sanitized.yaml>        public, non-sensitive metadata only
#   --private-source <refs.yaml>     connection references only (no secret values)
#
# The operator prepares both files OUTSIDE the repo and outside the model
# context. This script refuses a raw connection table (ssh.txt) by name, never
# opens it, and never prints field values. It validates before and after merge
# and writes the public inventory atomically. The private inventory is written
# only as SOPS ciphertext; plaintext exists only in a 700 temporary directory
# that is shredded on exit.
#
# Usage:
#   scripts/node-inventory/import-inventory.sh --source <sanitized.yaml> [--private-source <refs.yaml>] [--dry-run]

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

SOURCE=""
PRIVATE_SOURCE=""
DRY_RUN=0

usage() { sed -n '2,18p' "${BASH_SOURCE[0]}"; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source) SOURCE="${2:-}"; shift 2 ;;
    --private-source) PRIVATE_SOURCE="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown_argument=$1" ;;
  esac
done

[ -n "$SOURCE" ] || die "missing_argument=--source"
require_file "$SOURCE"
refuse_raw_connection_source "$SOURCE"
[ -n "$PRIVATE_SOURCE" ] && { require_file "$PRIVATE_SOURCE"; refuse_raw_connection_source "$PRIVATE_SOURCE"; }

require_python
PUBLIC_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/noahsark-import.XXXXXX")"
chmod 700 "$PUBLIC_TMP_DIR"

cleanup() {
  local f
  for f in "$PUBLIC_TMP_DIR"/*; do
    [ -e "$f" ] || continue
    if command -v shred >/dev/null 2>&1; then
      shred -u "$f" 2>/dev/null || rm -f "$f"
    else
      rm -f "$f"
    fi
  done
  rmdir "$PUBLIC_TMP_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

info "STEP=validate_public_source"
validate_inventory public "$SOURCE" >/dev/null \
  || die "public_source_invalid run=validate-inventory.py --kind public --inventory <source>"

MERGED_PUBLIC="$PUBLIC_TMP_DIR/public.merged.yaml"
SOURCE="$SOURCE" EXISTING="$PUBLIC_INVENTORY" OUT="$MERGED_PUBLIC" ACTOR="$ACTOR" python3 - <<'PY'
import os, sys, datetime, pathlib, yaml

def load(path):
    if not path or not pathlib.Path(path).is_file():
        return {"nodes": []}
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}

source = load(os.environ["SOURCE"])
existing = load(os.environ["EXISTING"])
merged = {}
for node in (existing.get("nodes") or []) + (source.get("nodes") or []):
    if isinstance(node, dict) and "node_id" in node:
        merged[node["node_id"]] = node

document = {
    "schema_version": 1,
    "inventory_id": "noahsark-nodes-public",
    "updated_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "updated_by": os.environ["ACTOR"],
    "nodes": [merged[key] for key in sorted(merged)],
}
with open(os.environ["OUT"], "w", encoding="utf-8") as handle:
    yaml.safe_dump(document, handle, sort_keys=False, allow_unicode=True)
PY
[ "$?" -eq 0 ] || die "public_merge_failed"

validate_inventory public "$MERGED_PUBLIC" >/dev/null \
  || die "merged_public_inventory_invalid"
public_count="$(python3 - "$MERGED_PUBLIC" <<'PY'
import sys, yaml
print(len((yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}).get("nodes") or []))
PY
)" || die "public_count_failed"

ENCRYPTED_TMP=""
private_count=0
if [ -n "$PRIVATE_SOURCE" ]; then
  info "STEP=validate_private_source"
  validate_inventory private "$PRIVATE_SOURCE" >/dev/null \
    || die "private_source_invalid run=validate-inventory.py --kind private --inventory <source>"
  require_cmd sops

  RECIPIENTS="$(python3 - "$SOPS_CONFIG" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as handle:
    config = yaml.safe_load(handle) or {}
keys = []
for rule in config.get("creation_rules") or []:
    for key in str(rule.get("age") or "").split(","):
        key = key.strip()
        if key and "REPLACE" not in key:
            keys.append(key)
print(",".join(dict.fromkeys(keys)))
PY
)"
  [ -n "$RECIPIENTS" ] || die "sops_recipient_missing update=$SOPS_CONFIG"
  [ -n "${SOPS_AGE_KEY_FILE:-}" ] || export SOPS_AGE_KEY_FILE="$LOCAL_ROOT/age/keys.txt"
  [ -f "$SOPS_AGE_KEY_FILE" ] || die "age_identity_missing run=init-local-store.sh --generate-key"

  PLAIN_PRIVATE="$PUBLIC_TMP_DIR/private.merged.yaml"
  if [ -f "$PRIVATE_INVENTORY" ]; then
    info "STEP=decrypt_existing_private_inventory"
    sops -d --input-type yaml "$PRIVATE_INVENTORY" >"$PLAIN_PRIVATE" 2>/dev/null \
      || die "private_inventory_decrypt_failed"
    validate_inventory private "$PLAIN_PRIVATE" >/dev/null \
      || die "existing_private_inventory_invalid"
  else
    : >"$PLAIN_PRIVATE"
  fi

  PRIVATE_SOURCE="$PRIVATE_SOURCE" EXISTING="$PLAIN_PRIVATE" OUT="$PLAIN_PRIVATE" ACTOR="$ACTOR" python3 - <<'PY'
import os, pathlib, datetime, yaml

def load(path):
    path_obj = pathlib.Path(path)
    if not path_obj.is_file() or path_obj.stat().st_size == 0:
        return {"nodes": []}
    with open(path_obj, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}

source = load(os.environ["PRIVATE_SOURCE"])
existing = load(os.environ["EXISTING"])
merged = {}
for node in (existing.get("nodes") or []) + (source.get("nodes") or []):
    if isinstance(node, dict) and "node_id" in node:
        merged[node["node_id"]] = node

document = {
    "schema_version": 1,
    "inventory_id": "noahsark-nodes-private",
    "updated_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "updated_by": os.environ["ACTOR"],
    "nodes": [merged[key] for key in sorted(merged)],
}
with open(os.environ["OUT"], "w", encoding="utf-8") as handle:
    yaml.safe_dump(document, handle, sort_keys=False, allow_unicode=True)
PY
  [ "$?" -eq 0 ] || die "private_merge_failed"

  validate_inventory private "$PLAIN_PRIVATE" >/dev/null \
    || die "merged_private_inventory_invalid"

  # Public/private consistency: every private node must exist publicly with
  # the same alias, and every carried secret must stay a reference.
  PUBLIC_MERGED="$MERGED_PUBLIC" PRIVATE_PLAIN="$PLAIN_PRIVATE" python3 - <<'PY'
import os, sys, yaml

def by_id(path):
    with open(path, encoding="utf-8") as handle:
        return {n["node_id"]: n for n in (yaml.safe_load(handle) or {}).get("nodes") or []}

public = by_id(os.environ["PUBLIC_MERGED"])
private = by_id(os.environ["PRIVATE_PLAIN"])
for node_id, node in private.items():
    if node_id not in public:
        raise SystemExit(f"private_node_missing_from_public:{node_id}")
    if public[node_id].get("ssh_alias") != node.get("ssh_alias"):
        raise SystemExit(f"ssh_alias_mismatch:{node_id}")
PY
  [ "$?" -eq 0 ] || die "public_private_mapping_mismatch"

  ENCRYPTED_TMP="$PUBLIC_TMP_DIR/nodes.enc.yaml"
  sops --encrypt --input-type yaml --output-type yaml --age "$RECIPIENTS" \
    "$PLAIN_PRIVATE" >"$ENCRYPTED_TMP" 2>/dev/null \
    || die "sops_encrypt_failed"
  grep -q '^sops:' "$ENCRYPTED_TMP" || die "sops_header_missing"
  private_count="$(python3 - "$PLAIN_PRIVATE" <<'PY'
import sys, yaml
print(len((yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}).get("nodes") or []))
PY
)" || die "private_count_failed"
fi

if [ "$DRY_RUN" -eq 1 ]; then
  info "DRY_RUN=ok public_nodes=$public_count private_nodes=$private_count"
  audit_event "import_dry_run" "ok" "" "$public_count"
  exit 0
fi

info "STEP=write_public_inventory"
install -m 644 "$MERGED_PUBLIC" "$PUBLIC_INVENTORY.tmp.$$"
mv -f "$PUBLIC_INVENTORY.tmp.$$" "$PUBLIC_INVENTORY"

if [ -n "$PRIVATE_SOURCE" ]; then
  info "STEP=write_encrypted_inventory"
  mkdir -p "$LOCAL_ROOT/backups"
  chmod 700 "$LOCAL_ROOT/backups"
  if [ -f "$PRIVATE_INVENTORY" ]; then
    backup="$LOCAL_ROOT/backups/nodes.enc.yaml.$(date -u +%Y%m%dT%H%M%SZ)"
    install -m 600 "$PRIVATE_INVENTORY" "$backup"
    info "BACKUP=$backup"
  fi
  install -m 644 "$ENCRYPTED_TMP" "$PRIVATE_INVENTORY.tmp.$$"
  mv -f "$PRIVATE_INVENTORY.tmp.$$" "$PRIVATE_INVENTORY"
fi

audit_event "import" "ok" "" "$public_count"
info "IMPORT=ok public_nodes=$public_count private_nodes=$private_count"
info "NEXT run=scripts/node-inventory/verify-nodes.sh --dry-run"
