#!/usr/bin/env bash
# NoahsArk platform stack helper.
#
# Safe, read-only by default. Mutating actions (start/stop/restart) require an
# explicit component name or "all". This script uses systemd --user and curl
# only. It never kills processes by PID, never reads secrets, and never runs
# database commands.
#
# Usage:
#   scripts/ops/noahsark-stack.sh status
#   scripts/ops/noahsark-stack.sh health
#   scripts/ops/noahsark-stack.sh logs [component|all]
#   scripts/ops/noahsark-stack.sh start    <component|all> [...]
#   scripts/ops/noahsark-stack.sh stop     <component|all> [...]
#   scripts/ops/noahsark-stack.sh restart  <component|all> [...]
#
# Components:
#   platform-opencode  noahsark-platform-opencode.service  (127.0.0.1:4097)
#   supervisor         noahsark-supervisor.service
#   control-plane      noahsark-control-plane.service      (127.0.0.1:8000)
#   ui                 noahsark-ui.service                 (0.0.0.0:8200)
#   local-opencode     noahsark-opencode.service           (127.0.0.1:4096)
#   all                every component in dependency order
#
# Environment:
#   NAA_LINES    journal tail line count for "logs" (default 100)
#   NAA_TIMEOUT  curl timeout seconds for "health" (default 3)

set -euo pipefail

readonly SCRIPT_NAME="${0##*/}"
readonly LINES="${NAA_LINES:-100}"
readonly TIMEOUT="${NAA_TIMEOUT:-3}"

# Component to unit mapping. Keep names user-facing and short.
declare -A UNIT_MAP=(
  [platform-opencode]="noahsark-platform-opencode.service"
  [supervisor]="noahsark-supervisor.service"
  [control-plane]="noahsark-control-plane.service"
  [ui]="noahsark-ui.service"
  [local-opencode]="noahsark-opencode.service"
)

readonly START_ORDER=(platform-opencode supervisor control-plane ui local-opencode)
readonly STOP_ORDER=(ui control-plane supervisor platform-opencode local-opencode)
readonly ALL_ORDER=(platform-opencode supervisor control-plane ui local-opencode)

info() { printf '[noahsark-stack] %s\n' "$*"; }
warn() { printf '[noahsark-stack] WARN: %s\n' "$*" >&2; }
die() { printf '[noahsark-stack] ERROR: %s\n' "$*" >&2; exit 2; }

usage() {
  cat <<'EOF'
Usage:
  scripts/ops/noahsark-stack.sh status
  scripts/ops/noahsark-stack.sh health
  scripts/ops/noahsark-stack.sh logs [component|all]
  scripts/ops/noahsark-stack.sh start    <component|all> [...]
  scripts/ops/noahsark-stack.sh stop     <component|all> [...]
  scripts/ops/noahsark-stack.sh restart  <component|all> [...]

Components:
  platform-opencode  noahsark-platform-opencode.service  (127.0.0.1:4097)
  supervisor         noahsark-supervisor.service
  control-plane      noahsark-control-plane.service      (127.0.0.1:8000)
  ui                 noahsark-ui.service                 (0.0.0.0:8200)
  local-opencode     noahsark-opencode.service           (127.0.0.1:4096)
  all                every component in dependency order

Read-only: status, health, logs. Mutating actions require an explicit
component or "all"; restart never defaults to all.
EOF
}

require_systemctl() {
  command -v systemctl >/dev/null 2>&1 || die "systemctl not found; this host must use systemd --user"
}

unit_for() {
  local component="$1"
  [[ -n "${UNIT_MAP[$component]:-}" ]] || die "unknown component '$component'; run '$SCRIPT_NAME status' for the component list"
  printf '%s\n' "${UNIT_MAP[$component]}"
}

# Resolve user arguments into a component list. "all" expands in dependency
# order and cannot be mixed with explicit components.
RESOLVED=()
resolve_components() {
  local -a raw=("$@")
  local arg

  RESOLVED=()
  ((${#raw[@]} > 0)) || die "this action needs an explicit component or 'all'"

  for arg in "${raw[@]}"; do
    case "$arg" in
      all)
        ((${#raw[@]} == 1)) || die "'all' cannot be combined with other components"
        RESOLVED=("${ALL_ORDER[@]}")
        ;;
      *)
        [[ -n "${UNIT_MAP[$arg]:-}" ]] || die "unknown component '$arg'"
        RESOLVED+=("$arg")
        ;;
    esac
  done
}

print_unit_state() {
  local component="$1"
  local unit active enabled sub
  unit="$(unit_for "$component")"

  if ! systemctl --user cat "$unit" >/dev/null 2>&1; then
    printf '  %-18s %-40s missing\n' "$component" "$unit"
    return 0
  fi

  active="$(systemctl --user is-active "$unit" 2>/dev/null || true)"
  enabled="$(systemctl --user is-enabled "$unit" 2>/dev/null || true)"
  sub="$(systemctl --user show -p SubState --value "$unit" 2>/dev/null || true)"
  printf '  %-18s %-40s active=%-8s sub=%-10s enabled=%s\n' \
    "$component" "$unit" "${active:-unknown}" "${sub:-unknown}" "${enabled:-unknown}"
}

cmd_status() {
  require_systemctl
  info "服务栈状态 / service status"
  local component
  for component in "${ALL_ORDER[@]}"; do
    print_unit_state "$component"
  done
  cat <<'EOF'

提示: status 只读取 systemd 状态。使用 health 检查 HTTP 端点。
Hint: status is read-only. Use health for HTTP checks.
EOF
}

probe_http() {
  local label="$1" url="$2"
  local code
  if code="$(curl -sS -m "$TIMEOUT" -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)"; then
    if [[ "$code" == "200" ]]; then
      printf '  PASS  %-20s %s (HTTP %s)\n' "$label" "$url" "$code"
    else
      printf '  WARN  %-20s %s (HTTP %s)\n' "$label" "$url" "$code"
      return 1
    fi
  else
    printf '  FAIL  %-20s %s (unreachable)\n' "$label" "$url"
    return 1
  fi
}

cmd_health() {
  command -v curl >/dev/null 2>&1 || die "curl not found"
  info "HTTP 健康检查 / HTTP health checks"
  local failures=0
  probe_http "control-plane healthz" "http://127.0.0.1:8000/healthz" || failures=$((failures + 1))
  probe_http "control-plane readyz" "http://127.0.0.1:8000/readyz" || failures=$((failures + 1))
  probe_http "ui" "http://127.0.0.1:8200/" || failures=$((failures + 1))
  probe_http "platform-opencode" "http://127.0.0.1:4097/" || failures=$((failures + 1))
  # The local 4096 provider is intentionally separate and may be stopped; it is
  # advisory only and must not fail a platform health check.
  probe_http "local-opencode" "http://127.0.0.1:4096/" \
    || warn "local-opencode 未运行（可选）/ local provider not running (advisory)"

  if ((failures > 0)); then
    warn "$failures 个端点未通过 / $failures endpoint check(s) failed"
    return 1
  fi
  info "全部端点通过 / all endpoint checks passed"
}

cmd_logs() {
  require_systemctl
  command -v journalctl >/dev/null 2>&1 || die "journalctl not found"

  local -a components=()
  if (($# == 0)); then
    components=("${ALL_ORDER[@]}")
    warn "未指定组件，读取全部组件日志 / no component given, reading all components"
  else
    resolve_components "$@"
    components=("${RESOLVED[@]}")
  fi

  local component unit
  for component in "${components[@]}"; do
    unit="$(unit_for "$component")"
    printf '\n===== %s (%s), last %s lines =====\n' "$component" "$unit" "$LINES"
    journalctl --user -u "$unit" -n "$LINES" --no-pager || warn "no journal entries for $unit"
  done
}

run_action() {
  local action="$1"
  shift
  require_systemctl

  local first_arg="${1:-}"
  resolve_components "$@"
  local -a requested=("${RESOLVED[@]}")

  local -a ordered=()
  local component
  case "$action" in
    start|restart)
      # "all" follows dependency order; explicit components keep caller order.
      if [[ "$first_arg" == "all" ]]; then
        ordered=("${START_ORDER[@]}")
      else
        ordered=("${requested[@]}")
      fi
      ;;
    stop)
      if [[ "$first_arg" == "all" ]]; then
        ordered=("${STOP_ORDER[@]}")
      else
        ordered=("${requested[@]}")
      fi
      ;;
    *) die "internal error: unknown action $action" ;;
  esac

  if [[ "$action" == "restart" ]]; then
    info "即将重启: ${ordered[*]} / restarting: ${ordered[*]}"
  else
    info "即将执行 $action: ${ordered[*]}"
  fi

  for component in "${ordered[@]}"; do
    local unit
    unit="$(unit_for "$component")"
    info "$action $component ($unit)"
    case "$action" in
      start)
        systemctl --user start "$unit" || die "failed to start $unit"
        ;;
      stop)
        systemctl --user stop "$unit" || die "failed to stop $unit"
        ;;
      restart)
        systemctl --user restart "$unit" || die "failed to restart $unit"
        ;;
    esac
    print_unit_state "$component"
  done

  info "完成。用 '$SCRIPT_NAME status' 和 '$SCRIPT_NAME health' 核验 / done"
}

main() {
  local action="${1:-}"
  case "$action" in
    status)
      (($# == 1)) || die "status takes no arguments"
      cmd_status
      ;;
    health)
      (($# == 1)) || die "health takes no arguments"
      cmd_health
      ;;
    logs)
      shift
      cmd_logs "$@"
      ;;
    start|stop|restart)
      shift
      run_action "$action" "$@"
      ;;
    ""|-h|--help|help)
      usage
      ;;
    *)
      die "unknown subcommand '$action'; run '$SCRIPT_NAME --help'"
      ;;
  esac
}

main "$@"
