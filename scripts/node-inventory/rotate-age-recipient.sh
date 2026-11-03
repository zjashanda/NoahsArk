#!/usr/bin/env bash
# Rotate the age recipient of the encrypted node inventory.
#
# Adds one or more new age recipients, removes the old recipient(s) when
# --remove-old is given, rewrites .sops.yaml, and re-encrypts the data key of
# nodes.enc.yaml with `sops updatekeys`. The new key must be able to decrypt
# before the old key is removed.
#
# True revocation note: old ciphertext in Git history stays decryptable by the
# old key. Rotating recipients protects future writes only. If a key leaked,
# rotate every referenced SSH/agent credential and treat Git history as
# compromised, as described in docs/delivery/node-inventory-management.md.
#
# Usage:
#   scripts/node-inventory/rotate-age-recipient.sh --new-recipient age1... [--remove-old] [--dry-run]

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

NEW_RECIPIENTS=""
REMOVE_OLD=0
DRY_RUN=0

usage() { sed -n '2,16p' "${BASH_SOURCE[0]}"; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --new-recipient) NEW_RECIPIENTS="${NEW_RECIPIENTS:+$NEW_RECIPIENTS,}${2:-}"; shift 2 ;;
    --remove-old) REMOVE_OLD=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown_argument=$1" ;;
  esac
done

[ -n "$NEW_RECIPIENTS" ] || die "missing_argument=--new-recipient"
python3 - "$NEW_RECIPIENTS" <<'PY' || die "invalid_recipient"
import re, sys
for key in sys.argv[1].split(","):
    key = key.strip()
    if not re.fullmatch(r"age1[0-9a-z]{20,}", key):
        raise SystemExit(1)
PY

require_cmd sops
require_file "$SOPS_CONFIG"
[ -n "${SOPS_AGE_KEY_FILE:-}" ] || export SOPS_AGE_KEY_FILE="$LOCAL_ROOT/age/keys.txt"
[ -f "$SOPS_AGE_KEY_FILE" ] || die "age_identity_missing"

if [ "$DRY_RUN" -eq 0 ] && [ -f "$PRIVATE_INVENTORY" ]; then
  backup="$LOCAL_ROOT/backups/nodes.enc.yaml.pre-rotate.$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$LOCAL_ROOT/backups"
  chmod 700 "$LOCAL_ROOT/backups"
  install -m 600 "$PRIVATE_INVENTORY" "$backup"
  info "BACKUP=$backup"
fi

NEW_RECIPIENTS="$NEW_RECIPIENTS" REMOVE_OLD="$REMOVE_OLD" SOPS_CONFIG="$SOPS_CONFIG" python3 - <<'PY'
import os, pathlib, yaml

path = pathlib.Path(os.environ["SOPS_CONFIG"])
config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
new = [key.strip() for key in os.environ["NEW_RECIPIENTS"].split(",") if key.strip()]
rules = config.setdefault("creation_rules", [])
if not rules:
    rules.append({"path_regex": r"(^|/)config/node-inventory/nodes\.enc\.yaml$"})
for rule in rules:
    existing = [key.strip() for key in str(rule.get("age") or "").split(",") if key.strip()]
    existing = [key for key in existing if "REPLACE" not in key]
    recipients = ([] if os.environ["REMOVE_OLD"] == "1" else existing)
    for key in new:
        if key not in recipients:
            recipients.append(key)
    rule["age"] = ",".join(recipients)
path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
PY
[ "$?" -eq 0 ] || die "sops_config_update_failed"

if [ "$DRY_RUN" -eq 1 ]; then
  info "DRY_RUN=ok sops_config_updated=planned"
  exit 0
fi

if [ -f "$PRIVATE_INVENTORY" ]; then
  sops updatekeys --yes "$PRIVATE_INVENTORY" >/dev/null 2>&1 || die "sops_updatekeys_failed"
  sops -d --input-type yaml "$PRIVATE_INVENTORY" >/dev/null 2>&1 || die "decrypt_after_rotation_failed"
  info "ROTATION=ok inventory=$PRIVATE_INVENTORY"
else
  warn "encrypted_inventory_absent=rotation_deferred"
fi
audit_event "age_rotate" "ok"
