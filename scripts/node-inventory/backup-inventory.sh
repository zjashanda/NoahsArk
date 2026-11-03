#!/usr/bin/env bash
# Ciphertext-only backup of the node inventory.
#
# Backs up public-inventory.yaml, .sops.yaml, and nodes.enc.yaml (if present)
# into the repo-external local store with 700/600 permissions and a receipt.
# Only ciphertext is copied: no decrypted inventory and no age identity.
#
# Usage:
#   scripts/node-inventory/backup-inventory.sh [--label NAME]
#   scripts/node-inventory/backup-inventory.sh --verify <backup_dir>

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

LABEL=""
VERIFY_DIR=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --label) LABEL="${2:-}"; shift 2 ;;
    --verify) VERIFY_DIR="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) die "unknown_argument=$1" ;;
  esac
done

[[ "${LABEL:-x}" =~ ^[A-Za-z0-9._-]{1,32}$ ]] || die "unsafe_label"

verify_backup() {
  local dir="$1"
  [ -d "$dir" ] || die "backup_dir_missing=$dir"
  [ -f "$dir/MANIFEST.json" ] || die "backup_manifest_missing"
  python3 - "$dir" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
for name, expected in manifest["files"].items():
    path = root / name
    if not path.is_file():
        raise SystemExit(f"missing={name}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"checksum_mismatch={name}")
print(f"BACKUP_VERIFY=ok files={len(manifest['files'])}")
PY
}

if [ -n "$VERIFY_DIR" ]; then
  require_cmd python3
  verify_backup "$VERIFY_DIR"
  exit 0
fi

require_cmd python3
require_file "$PUBLIC_INVENTORY"
validate_inventory public "$PUBLIC_INVENTORY" >/dev/null || die "public_inventory_invalid"
ensure_local_dirs
mkdir -p "$LOCAL_ROOT/backups"
chmod 700 "$LOCAL_ROOT/backups"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$LOCAL_ROOT/backups/inventory-$STAMP${LABEL:+-$LABEL}"
mkdir -p "$DEST"
chmod 700 "$DEST"

install -m 600 "$PUBLIC_INVENTORY" "$DEST/public-inventory.yaml"
if [ -f "$SOPS_CONFIG" ]; then
  install -m 600 "$SOPS_CONFIG" "$DEST/sops-config.yaml"
fi
if [ -f "$PRIVATE_INVENTORY" ]; then
  install -m 600 "$PRIVATE_INVENTORY" "$DEST/nodes.enc.yaml"
fi

python3 - "$DEST" <<'PY'
import hashlib, json, pathlib, sys, datetime
root = pathlib.Path(sys.argv[1])
files = {}
for path in sorted(root.iterdir()):
    if path.name == "MANIFEST.json" or not path.is_file():
        continue
    files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
manifest = {
    "created_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "files": files,
    "contains_plaintext_secrets": False,
    "contains_age_identity": False,
}
(root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
[ "$?" -eq 0 ] || die "manifest_write_failed"
chmod 600 "$DEST/MANIFEST.json"
verify_backup "$DEST" || die "backup_verify_failed"
audit_event "backup" "ok"
info "BACKUP_DIR=$DEST"
info "RESTORE manual=copy nodes.enc.yaml back to $PRIVATE_INVENTORY then run verify-nodes.sh --dry-run"
