#!/usr/bin/env bash
# NoahsArk healthcheck: loopback API liveness/readiness + candidate UI.
#
# Usage: scripts/healthcheck.sh
# Env:   NAA_API_BASE (default http://127.0.0.1:8000)
#        NAA_UI_BASE  (default http://127.0.0.1:8100)
#        NAA_HEALTH_TIMEOUT (seconds, default 3)
#
# This checks the local processes, not Caddy or the public hostname. A 503
# from /readyz is reported as FAIL because it means DATABASE_URL is missing
# or the database is unreachable.

set -euo pipefail

API_BASE="${NAA_API_BASE:-http://127.0.0.1:8000}"
UI_BASE="${NAA_UI_BASE:-http://127.0.0.1:8100}"
TIMEOUT="${NAA_HEALTH_TIMEOUT:-3}"
FAILURES=0

command -v curl >/dev/null 2>&1 || {
  printf 'healthcheck: ERROR: curl not found\n' >&2
  exit 2
}

probe() {
  local name="$1" url="$2"
  local out body meta code elapsed
  if ! out="$(curl -sS -m "$TIMEOUT" -w $'\n%{http_code} %{time_total}' "$url" 2>&1)"; then
    printf 'FAIL  %-8s %s (unreachable)\n' "$name" "$url"
    FAILURES=$((FAILURES + 1))
    return 1
  fi
  body="${out%$'\n'*}"
  meta="${out##*$'\n'}"
  code="${meta%% *}"
  elapsed="${meta##* }"
  PROBE_BODY="$body"
  PROBE_CODE="$code"
  PROBE_ELAPSED="$elapsed"
  return 0
}

check_api_health() {
  local url="$API_BASE/healthz"
  if probe "healthz" "$url"; then
    if [[ "$PROBE_CODE" == "200" ]] && grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' <<<"$PROBE_BODY"; then
      printf 'PASS  %-8s %s (%ss)\n' "healthz" "$url" "$PROBE_ELAPSED"
      return 0
    fi
    printf 'FAIL  %-8s %s (http=%s body=%s)\n' "healthz" "$url" "$PROBE_CODE" "$PROBE_BODY"
  fi
  FAILURES=$((FAILURES + 1))
}

check_api_ready() {
  local url="$API_BASE/readyz"
  if probe "readyz" "$url"; then
    if [[ "$PROBE_CODE" == "200" ]] && grep -q '"status"[[:space:]]*:[[:space:]]*"ready"' <<<"$PROBE_BODY"; then
      printf 'PASS  %-8s %s (%ss)\n' "readyz" "$url" "$PROBE_ELAPSED"
      return 0
    fi
    printf 'FAIL  %-8s %s (http=%s body=%s)\n' "readyz" "$url" "$PROBE_CODE" "$PROBE_BODY"
  fi
  FAILURES=$((FAILURES + 1))
}

check_ui() {
  local url="$UI_BASE/"
  if probe "ui" "$url"; then
    if [[ "$PROBE_CODE" == "200" ]] && grep -qi '<html' <<<"$PROBE_BODY"; then
      printf 'PASS  %-8s %s (%ss)\n' "ui" "$url" "$PROBE_ELAPSED"
      return 0
    fi
    printf 'FAIL  %-8s %s (http=%s, expected 200 HTML)\n' "ui" "$url" "$PROBE_CODE"
  fi
  FAILURES=$((FAILURES + 1))
}

printf 'healthcheck: api=%s ui=%s timeout=%ss\n' "$API_BASE" "$UI_BASE" "$TIMEOUT"
check_api_health
check_api_ready
check_ui

if ((FAILURES > 0)); then
  printf 'healthcheck: %s check(s) failed\n' "$FAILURES" >&2
  exit 1
fi
printf 'healthcheck: all checks passed\n'
