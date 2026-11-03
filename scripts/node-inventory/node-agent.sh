#!/usr/bin/env bash
# Read-only Node Agent troubleshooting by node_id.
#
# The NoahsArk Node Agent is outbound long-poll only, so there is no inbound
# health port to probe. This script reaches the node over the existing SSH
# alias and runs a small allowlist of read-only service-state commands.
# Arbitrary remote commands are intentionally not supported.
#
# Usage:
#   scripts/node-inventory/node-agent.sh --node-id win009 --status
#   scripts/node-inventory/node-agent.sh --node-id win009 --log-tail --allow-log-output
#
# Output is limited to node_id / agent_state / error_class / checked_at.
# --log-tail prints remote log lines only with an explicit opt-in because logs
# may contain non-public control-plane URLs.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

NODE_ID=""
INVENTORY="$PUBLIC_INVENTORY"
MODE="status"
TIMEOUT=15
ALLOW_LOG=0
SERVICE_NAME="${NOAHSARK_AGENT_SERVICE_NAME:-}"

usage() { sed -n '2,16p' "${BASH_SOURCE[0]}"; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --node-id) NODE_ID="${2:-}"; shift 2 ;;
    --inventory) INVENTORY="${2:-}"; shift 2 ;;
    --status) MODE="status"; shift ;;
    --log-tail) MODE="log"; shift ;;
    --allow-log-output) ALLOW_LOG=1; shift ;;
    --service-name) SERVICE_NAME="${2:-}"; shift 2 ;;
    --timeout) TIMEOUT="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown_argument=$1" ;;
  esac
done

[ -n "$NODE_ID" ] || die "missing_argument=--node-id"
is_safe_node_id "$NODE_ID" || die "unsafe_node_id"
case "$TIMEOUT" in ''|*[!0-9]*) die "invalid_timeout" ;; esac
[ "$TIMEOUT" -ge 1 ] && [ "$TIMEOUT" -le 120 ] || die "invalid_timeout"

require_python
require_file "$INVENTORY"
validate_inventory public "$INVENTORY" >/dev/null || die "inventory_invalid"

node_os="$(node_field "$INVENTORY" "$NODE_ID" os)"
ssh_alias="$(node_field "$INVENTORY" "$NODE_ID" ssh_alias)"
[ -n "$ssh_alias" ] || die "node_id_not_found=$NODE_ID"
is_safe_ssh_alias "$ssh_alias" || die "unsafe_ssh_alias_for_node=$NODE_ID"

case "$node_os" in
  windows-11|windows-server-2022)
    platform="windows"
    : "${SERVICE_NAME:=NoahsArkNodeAgent}"
    [[ "$SERVICE_NAME" =~ ^[A-Za-z0-9_.-]{1,64}$ ]] || die "unsafe_service_name"
    LOG_PATH='C:\ProgramData\NoahsArk\logs\node-agent.log'
    if [ "$MODE" = "status" ]; then
      remote_cmd="powershell -NoProfile -NonInteractive -Command \"try { (Get-Service -Name '$SERVICE_NAME' -ErrorAction Stop).Status } catch { 'not-installed' }\""
    else
      remote_cmd="powershell -NoProfile -NonInteractive -Command \"if (Test-Path '$LOG_PATH') { Get-Content -Path '$LOG_PATH' -Tail 40 } else { 'log-not-found' }\""
    fi
    ;;
  linux)
    platform="linux"
    : "${SERVICE_NAME:=noahsark-node-agent}"
    [[ "$SERVICE_NAME" =~ ^[A-Za-z0-9_.@-]{1,64}$ ]] || die "unsafe_service_name"
    if [ "$MODE" = "status" ]; then
      remote_cmd="systemctl is-active '$SERVICE_NAME' 2>/dev/null || true"
    else
      remote_cmd="journalctl -u '$SERVICE_NAME' -n 40 --no-pager 2>/dev/null || true"
    fi
    ;;
  *)
    die "unsupported_os_for_agent_probe value=$node_os"
    ;;
esac

if [ "$MODE" = "log" ] && [ "$ALLOW_LOG" -ne 1 ]; then
  die "log_output_requires=--allow-log-output"
fi

require_cmd ssh
require_cmd timeout
KNOWN_HOSTS="${NOAHSARK_KNOWN_HOSTS:-$HOME/.ssh/known_hosts}"
ensure_local_dirs
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/noahsark-agent.XXXXXX")"
chmod 700 "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

checked_at="$(iso_now)"
status="unknown"
error_class="none"

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
  "$ssh_alias" -- "$remote_cmd" >"$TMP_DIR/out" 2>"$TMP_DIR/err"
rc=$?

if [ "$rc" -eq 0 ] && [ "$MODE" = "status" ]; then
  first_line="$(head -n 1 "$TMP_DIR/out" | tr -d '\r' | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  case "$first_line" in
    running|active) status="active" ;;
    stopped|inactive|failed|dead) status="inactive" ;;
    not-installed|log-not-found|'') status="not_installed" ;;
    *) status="unknown" ;;
  esac
elif [ "$rc" -eq 0 ]; then
  status="log_retrieved"
else
  case "$rc" in
    124|137) status="timeout"; error_class="timeout" ;;
    255)
      if grep -qi 'permission denied' "$TMP_DIR/err"; then
        status="permission_denied"; error_class="permission_denied"
      elif grep -qi 'host key verification failed' "$TMP_DIR/err"; then
        status="ssh_error"; error_class="host_key_unverified"
      else
        status="ssh_error"; error_class="ssh_error"
      fi
      ;;
    *) status="ssh_error"; error_class="unknown" ;;
  esac
fi

info "NODE_ID=$NODE_ID PLATFORM=$platform AGENT_SERVICE=$SERVICE_NAME AGENT_STATE=$status ERROR_CLASS=$error_class CHECKED_AT=$checked_at"

if [ "$MODE" = "log" ] && [ "$status" = "log_retrieved" ]; then
  info "LOG_BEGIN may_contain_non_public_metadata"
  sed -n '1,40p' "$TMP_DIR/out"
  info "LOG_END"
fi

audit_event "agent_check" "$status" "$NODE_ID"
[ "$error_class" = "none" ] || exit 4
exit 0
