#!/usr/bin/env bash
# Batch read-only SSH verification for every node in the public inventory.
#
# Guarantees:
#   - BatchMode=yes, no password prompt, no host-key auto-accept
#   - per-node timeout, so one dead node cannot stall the batch
#   - stdout contains only node_id / status / error_class / checked_at
#   - host, user, IP, banner, and raw stderr are never printed or logged
#   - no status is updated unless --update-status is explicitly passed
#
# Usage:
#   scripts/node-inventory/verify-nodes.sh [--node-id ID] [--dry-run]
#       [--timeout 12] [--json] [--update-status] [--fail-on-unreachable]
#       [--inventory PATH]

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

NODE_ID=""
INVENTORY="$PUBLIC_INVENTORY"
TIMEOUT=12
DRY_RUN=0
JSON_OUT=0
UPDATE_STATUS=0
FAIL_ON_UNREACHABLE=0
KNOWN_HOSTS="${NOAHSARK_KNOWN_HOSTS:-$HOME/.ssh/known_hosts}"

usage() { sed -n '2,17p' "${BASH_SOURCE[0]}"; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --node-id) NODE_ID="${2:-}"; shift 2 ;;
    --inventory) INVENTORY="${2:-}"; shift 2 ;;
    --timeout) TIMEOUT="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --json) JSON_OUT=1; shift ;;
    --update-status) UPDATE_STATUS=1; shift ;;
    --fail-on-unreachable) FAIL_ON_UNREACHABLE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown_argument=$1" ;;
  esac
done

case "$TIMEOUT" in
  ''|*[!0-9]*) die "invalid_timeout" ;;
esac
[ "$TIMEOUT" -ge 1 ] && [ "$TIMEOUT" -le 120 ] || die "invalid_timeout"

require_python
require_file "$INVENTORY"
validate_inventory public "$INVENTORY" >/dev/null || die "inventory_invalid"

if [ "$DRY_RUN" -eq 0 ]; then
  require_cmd ssh
  require_cmd timeout
  [ -f "$KNOWN_HOSTS" ] || warn "known_hosts_absent=$KNOWN_HOSTS nodes_will_not_be_trusted"
fi

ensure_local_dirs
STAMP="$(date -u +%Y%m%d)"
RESULT_LOG="$LOG_DIR/verify-$STAMP.jsonl"
SUMMARY_LOG="$LOG_DIR/verify-$STAMP.summary.json"
: >"$RESULT_LOG"
chmod 600 "$RESULT_LOG"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/noahsark-verify.XXXXXX")"
chmod 700 "$TMP_DIR"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

count_total=0
count_reachable=0
count_timeout=0
count_denied=0
count_error=0
count_skipped=0

if [ "$JSON_OUT" -eq 0 ]; then
  printf '%-24s %-16s %-22s %s\n' "NODE_ID" "STATUS" "ERROR_CLASS" "CHECKED_AT"
fi

while IFS=$'\t' read -r node_id ssh_alias node_status agent_id node_os; do
  [ -n "$node_id" ] || continue
  if [ -n "$NODE_ID" ] && [ "$node_id" != "$NODE_ID" ]; then
    continue
  fi
  is_safe_node_id "$node_id" || die "unsafe_node_id=$node_id"
  is_safe_ssh_alias "$ssh_alias" || die "unsafe_ssh_alias_for_node=$node_id"
  count_total=$((count_total + 1))
  checked_at="$(iso_now)"

  if [ "$node_status" = "retired" ]; then
    status="skipped"
    error_class="retired"
    count_skipped=$((count_skipped + 1))
  elif [ "$DRY_RUN" -eq 1 ]; then
    status="planned"
    error_class="none"
  else
    err_file="$TMP_DIR/$node_id.err"
    timeout "$TIMEOUT" ssh \
      -o BatchMode=yes \
      -o ConnectTimeout=5 \
      -o ConnectionAttempts=1 \
      -o ServerAliveInterval=5 \
      -o ServerAliveCountMax=1 \
      -o StrictHostKeyChecking=yes \
      -o UserKnownHostsFile="$KNOWN_HOSTS" \
      -o LogLevel=ERROR \
      -o PreferredAuthentications=publickey \
      -o PasswordAuthentication=no \
      -o KbdInteractiveAuthentication=no \
      "$ssh_alias" -- 'exit 0' >/dev/null 2>"$err_file"
    rc=$?
    case "$rc" in
      0)
        status="reachable"
        error_class="none"
        count_reachable=$((count_reachable + 1))
        ;;
      124|137)
        status="timeout"
        error_class="timeout"
        count_timeout=$((count_timeout + 1))
        ;;
      255)
        if grep -qi 'permission denied' "$err_file"; then
          status="permission_denied"
          error_class="permission_denied"
          count_denied=$((count_denied + 1))
        elif grep -qi 'host key verification failed' "$err_file"; then
          status="error"
          error_class="host_key_unverified"
          count_error=$((count_error + 1))
        elif grep -qi 'connection refused' "$err_file"; then
          status="error"
          error_class="connection_refused"
          count_error=$((count_error + 1))
        elif grep -qi 'could not resolve hostname' "$err_file"; then
          status="error"
          error_class="dns_failure"
          count_error=$((count_error + 1))
        elif grep -qiE 'no route to host|network is unreachable' "$err_file"; then
          status="error"
          error_class="network_unreachable"
          count_error=$((count_error + 1))
        else
          status="error"
          error_class="unknown"
          count_error=$((count_error + 1))
        fi
        ;;
      *)
        status="error"
        error_class="unknown"
        count_error=$((count_error + 1))
        ;;
    esac
    rm -f "$err_file"
  fi

  record="$(NODE_ID="$node_id" STATUS="$status" ERROR_CLASS="$error_class" CHECKED_AT="$checked_at" \
    python3 -c 'import json,os;print(json.dumps({"node_id":os.environ["NODE_ID"],"status":os.environ["STATUS"],"error_class":os.environ["ERROR_CLASS"],"checked_at":os.environ["CHECKED_AT"]},separators=(",",":")))')"
  printf '%s\n' "$record" >>"$RESULT_LOG"
  if [ "$JSON_OUT" -eq 1 ]; then
    printf '%s\n' "$record"
  else
    printf '%-24s %-16s %-22s %s\n' "$node_id" "$status" "$error_class" "$checked_at"
  fi
done < <(inventory_rows "$INVENTORY")

if [ -n "$NODE_ID" ] && [ "$count_total" -eq 0 ]; then
  die "node_id_not_found=$NODE_ID"
fi

python3 - "$SUMMARY_LOG" "$count_total" "$count_reachable" "$count_timeout" \
  "$count_denied" "$count_error" "$count_skipped" <<'PY'
import json, sys, datetime
path, total, reachable, timed_out, denied, errored, skipped = sys.argv[1:8]
payload = {
    "checked_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "total": int(total),
    "reachable": int(reachable),
    "timeout": int(timed_out),
    "permission_denied": int(denied),
    "error": int(errored),
    "skipped": int(skipped),
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, separators=(",", ":"))
    handle.write("\n")
PY
[ "$?" -eq 0 ] || die "summary_write_failed"
chmod 600 "$SUMMARY_LOG"
info "SUMMARY total=$count_total reachable=$count_reachable timeout=$count_timeout permission_denied=$count_denied error=$count_error skipped=$count_skipped"
info "RECEIPT=$RESULT_LOG"
audit_event "verify_run" "ok" "" "$count_total"

if [ "$UPDATE_STATUS" -eq 1 ]; then
  [ "$DRY_RUN" -eq 0 ] || die "update_status_requires_real_run"
  RESULTS="$RESULT_LOG" INVENTORY="$INVENTORY" python3 - <<'PY'
import os, yaml, pathlib
inventory = pathlib.Path(os.environ["INVENTORY"])
with open(inventory, encoding="utf-8") as handle:
    document = yaml.safe_load(handle) or {}
latest = {}
with open(os.environ["RESULTS"], encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if not line:
            continue
        row = __import__("json").loads(line)
        if row["status"] in {"reachable", "timeout", "permission_denied", "error"}:
            latest[row["node_id"]] = row
for node in document.get("nodes") or []:
    row = latest.get(node.get("node_id"))
    if not row:
        continue
    node["last_verified_at"] = row["checked_at"]
    node["last_verified_result"] = row["status"]
inventory.write_text(yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8")
PY
  [ "$?" -eq 0 ] || die "status_update_failed"
  info "STATUS_UPDATED=last_verified_only"
fi

if [ "$FAIL_ON_UNREACHABLE" -eq 1 ]; then
  [ "$count_error" -eq 0 ] && [ "$count_timeout" -eq 0 ] && [ "$count_denied" -eq 0 ] \
    || exit 4
fi
exit 0
