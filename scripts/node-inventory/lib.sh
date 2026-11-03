#!/usr/bin/env bash
# Shared helpers for the NoahsArk node-inventory scripts.
# Source only; never execute directly. No secret value is ever printed.

set -uo pipefail
umask 077

_NI_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_NI_REPO_ROOT="$(cd "$_NI_SCRIPT_DIR/../.." && pwd)"

INVENTORY_ROOT="${NOAHSARK_INVENTORY_ROOT:-$_NI_REPO_ROOT/config/node-inventory}"
LOCAL_ROOT="${NOAHSARK_LOCAL_STORE:-$HOME/.config/noahsark}"
PUBLIC_INVENTORY="${NOAHSARK_PUBLIC_INVENTORY:-$INVENTORY_ROOT/public-inventory.yaml}"
PRIVATE_INVENTORY="${NOAHSARK_PRIVATE_INVENTORY:-$INVENTORY_ROOT/nodes.enc.yaml}"
LOG_DIR="$LOCAL_ROOT/logs"
AUDIT_LOG="$LOG_DIR/inventory-audit.jsonl"
VALIDATOR="$_NI_SCRIPT_DIR/validate-inventory.py"
SOPS_CONFIG="$INVENTORY_ROOT/.sops.yaml"
ACTOR="${NOAHSARK_ACTOR:-operator}"

die() { printf 'ERROR %s\n' "$*" >&2; exit "${NI_EXIT_CODE:-1}"; }
warn() { printf 'WARN %s\n' "$*" >&2; }
info() { printf '%s\n' "$*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing_tool=$1"
}

require_python() {
  require_cmd python3
  python3 -c 'import yaml, jsonschema' >/dev/null 2>&1 \
    || die "missing_python_dependency=pyyaml_or_jsonschema"
}

require_file() {
  [ -f "$1" ] || die "missing_file=$1"
}

iso_now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

ensure_local_dirs() {
  mkdir -p "$LOG_DIR" "$LOCAL_ROOT/age" "$LOCAL_ROOT/agent"
  chmod 700 "$LOCAL_ROOT" "$LOG_DIR" "$LOCAL_ROOT/age" "$LOCAL_ROOT/agent"
}

require_no_umask_slack() {
  local bad
  bad="$(find "$LOCAL_ROOT" -type d -perm /077 -print -quit 2>/dev/null || true)"
  [ -z "$bad" ] || die "insecure_dir_permissions_under=$LOCAL_ROOT"
}

# Append-only audit event. Only enum/identifier fields are accepted so a
# caller cannot accidentally write a host, user, command line, or stderr.
audit_event() {
  local action="$1" result="$2" node_id="${3:-}" count="${4:-0}"
  ensure_local_dirs
  local payload
  payload="$(ACTION="$action" RESULT="$result" NODE_ID="$node_id" \
    COUNT="$count" ACTOR="$ACTOR" TS="$(iso_now)" python3 -c '
import json, os
def clean(value, limit=64):
    return "".join(ch for ch in value if ch.isalnum() or ch in "-._:/")[:limit]
print(json.dumps({
    "ts": os.environ["TS"],
    "actor": clean(os.environ["ACTOR"]),
    "action": clean(os.environ["ACTION"], 32),
    "node_id": clean(os.environ["NODE_ID"]),
    "result": clean(os.environ["RESULT"], 32),
    "count": int(os.environ["COUNT"] or 0),
}, separators=(",", ":")))
' 2>/dev/null)" || return 0
  printf '%s\n' "$payload" >>"$AUDIT_LOG"
  chmod 600 "$AUDIT_LOG" 2>/dev/null || true
}

validate_inventory() {
  local kind="$1" path="$2"
  shift 2
  require_python
  python3 "$VALIDATOR" --kind "$kind" --inventory "$path" "$@"
}

# Reject the protected raw connection table by name before any read attempt.
# This is a guard, not a parser: the scripts never open that file.
refuse_raw_connection_source() {
  local path="$1" base resolved
  base="$(basename -- "$path")"
  case "$base" in
    ssh.txt|*.ssh.txt)
      die "refused_raw_connection_source basename=$base"
      ;;
  esac
  # Resolve symlinks without opening the file, then re-check the real name and
  # the known in-repo paths. This keeps a link named "inventory.yaml" from
  # smuggling the protected table into the validator.
  resolved="$(realpath -e -- "$path" 2>/dev/null || true)"
  if [ -n "$resolved" ]; then
    case "$(basename -- "$resolved")" in
      ssh.txt|*.ssh.txt)
        die "refused_raw_connection_source resolved_basename=ssh.txt"
        ;;
    esac
    case "$resolved" in
      "$_NI_REPO_ROOT/ssh.txt"|"$_NI_REPO_ROOT/docs/ssh.txt")
        die "refused_raw_connection_source path_in_repo"
        ;;
    esac
  fi
}

# node_id and alias are used as shell/TSV values; enforce the schema alphabet
# again at the boundary so a malformed inventory cannot inject arguments.
is_safe_node_id() { [[ "$1" =~ ^[a-z][a-z0-9-]{1,31}$ ]]; }
is_safe_ssh_alias() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]]; }

inventory_rows() {
  local inventory="${1:-$PUBLIC_INVENTORY}"
  require_python
  require_file "$inventory"
  python3 - "$inventory" <<'PY'
import sys, yaml
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    doc = yaml.safe_load(handle) or {}
for node in doc.get("nodes") or []:
    print("\t".join([
        str(node.get("node_id", "")),
        str(node.get("ssh_alias", "")),
        str(node.get("status", "")),
        str(node.get("agent_id") or ""),
        str(node.get("os", "")),
    ]))
PY
}

node_field() {
  local inventory="$1" node_id="$2" field="$3"
  require_python
  python3 - "$inventory" "$node_id" "$field" <<'PY'
import sys, yaml
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    doc = yaml.safe_load(handle) or {}
for node in doc.get("nodes") or []:
    if node.get("node_id") == sys.argv[2]:
        value = node.get(sys.argv[3])
        print("" if value is None else value)
        break
PY
}
