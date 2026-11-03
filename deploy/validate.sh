#!/usr/bin/env bash
# Static validation for the development deployment baseline.
#
# This does not start services, connect to PostgreSQL, or print secrets. It
# validates shell syntax, the secret scan, systemd unit syntax, file modes and
# (when installed) the Caddyfile.
set -euo pipefail
cd "$(dirname "$0")/.."

FAILURES=0
pass() { printf 'PASS  %s\n' "$*"; }
skip() { printf 'SKIP  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*" >&2; FAILURES=$((FAILURES + 1)); }

check_unit_hardening() {
  local unit="$1"
  local name
  name="$(basename "$unit")"
  local required_rules=(
    'NoNewPrivileges=true'
    'PrivateTmp=true'
    'PrivateDevices=true'
    'ProtectSystem=strict'
    'ProtectHome=true'
    'ProtectKernelTunables=true'
    'ProtectKernelModules=true'
    'ProtectControlGroups=true'
    'RestrictSUIDSGID=true'
    'RestrictRealtime=true'
    'RestrictNamespaces=true'
    'LockPersonality=true'
    'SystemCallArchitectures=native'
    'UMask=0077'
  )
  local rule
  local missing=()
  for rule in "${required_rules[@]}"; do
    grep -qxF "$rule" "$unit" || missing+=("$rule")
  done
  if ((${#missing[@]})); then
    fail "$name missing hardening: ${missing[*]}"
  else
    pass "$name hardening baseline"
  fi

  local user
  user="$(sed -n 's/^User=//p' "$unit" | head -n 1)"
  if [[ -n "$user" && "$user" != "root" ]]; then
    pass "$name runs as non-root user"
  else
    fail "$name has no non-root User="
  fi

  if grep -qE '^(CapabilityBoundingSet|AmbientCapabilities)=.+' "$unit"; then
    fail "$name grants Linux capabilities"
  else
    pass "$name drops all Linux capabilities"
  fi
}

check_caddy_static() {
  local file=deploy/Caddyfile
  local rule
  local missing=()
  for rule in \
    'reverse_proxy 127.0.0.1:8000' \
    'reverse_proxy 127.0.0.1:8100' \
    'Strict-Transport-Security' \
    'X-Content-Type-Options' \
    'X-Frame-Options' \
    'Referrer-Policy' \
    'Permissions-Policy' \
    'tls internal'; do
    grep -qF "$rule" "$file" || missing+=("$rule")
  done
  if ((${#missing[@]})); then
    fail "Caddyfile missing: ${missing[*]}"
  else
    pass "Caddyfile security headers and loopback upstreams"
  fi

  if grep -qE '^[[:space:]]*(http://|0\.0\.0\.0|\[::\]|:80[[:space:]]*\{)' "$file"; then
    fail "Caddyfile exposes a plaintext or wildcard listener"
  else
    pass "Caddyfile has no plaintext/wildcard listener"
  fi

  if grep -qE '^[a-z0-9.-]+\.example\.internal[[:space:]]*\{' "$file"; then
    pass "Caddyfile uses a placeholder internal hostname"
  else
    fail "Caddyfile has no .example.internal placeholder site"
  fi
}

check_env_template() {
  local file=deploy/env/control-plane.env.example
  if grep -qxF 'AUTH_MODE=oidc' "$file" \
    && grep -qxF 'DEV_SESSION_ENABLED=false' "$file" \
    && grep -qE '^DATABASE_URL=.*CHANGE_ME' "$file"; then
    pass "env template fails closed and has no real credential"
  else
    fail "env template does not fail closed or contains a real credential"
  fi
}

required=(
  deploy/Caddyfile
  deploy/systemd/noahsark-control-plane.service
  deploy/systemd/noahsark-node.service
  deploy/env/control-plane.env.example
  deploy/perf-smoke.py
  scripts/backup.sh
  scripts/restore-drill.sh
  scripts/healthcheck.sh
  scripts/secret-scan.sh
)
for file in "${required[@]}"; do
  [[ -f "$file" ]] && pass "present $file" || fail "missing $file"
done

for script in deploy/validate.sh scripts/backup.sh scripts/restore-drill.sh scripts/healthcheck.sh scripts/secret-scan.sh; do
  if [[ ! -f "$script" ]]; then
    continue
  fi
  if bash -n "$script"; then
    pass "bash -n $script"
  else
    fail "bash -n $script"
  fi
done

if ./scripts/secret-scan.sh; then
  pass "secret scan"
else
  fail "secret scan"
fi

for script in scripts/backup.sh scripts/restore-drill.sh scripts/healthcheck.sh scripts/secret-scan.sh scripts/sync-cloud.sh deploy/validate.sh deploy/perf-smoke.py; do
  [[ -f "$script" ]] || continue
  mode="$(stat -c '%a' "$script")"
  if (( (8#$mode & 8#022) == 0 )); then
    pass "not group/world-writable $script ($mode)"
  else
    fail "group/world-writable $script ($mode)"
  fi
  if (( (8#$mode & 8#111) != 0 )); then
    pass "executable $script ($mode)"
  else
    fail "not executable $script ($mode)"
  fi
done

for file in deploy/Caddyfile deploy/systemd/*.service deploy/env/control-plane.env.example; do
  [[ -f "$file" ]] || continue
  mode="$(stat -c '%a' "$file")"
  if (( (8#$mode & 8#022) == 0 )); then
    pass "not group/world-writable $file ($mode)"
  else
    fail "group/world-writable $file ($mode)"
  fi
done

if find deploy -type f -name '*.env' -not -name '*.example' | grep -q .; then
  fail "deploy contains a non-example .env file"
else
  pass "no filled deploy .env file"
fi

if [[ -e /etc/noahsark/control-plane.env ]]; then
  mode="$(stat -c '%a' /etc/noahsark/control-plane.env)"
  if (( (8#$mode & 8#077) == 0 )); then
    pass "installed env file is owner-only ($mode)"
  else
    fail "installed env file is readable by group/world ($mode)"
  fi
else
  skip "installed env permission check (/etc/noahsark/control-plane.env absent)"
fi

if command -v systemd-analyze >/dev/null 2>&1; then
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  for unit in deploy/systemd/*.service; do
    # Replace the host-specific ExecStart so syntax can be checked on a
    # development host where /opt/noahsark does not exist.
    sed 's|^ExecStart=.*|ExecStart=/bin/true|' "$unit" > "$tmp/$(basename "$unit")"
  done
  if systemd-analyze verify "$tmp"/*.service; then
    pass "systemd-analyze verify (sanitized ExecStart)"
  else
    fail "systemd-analyze verify (sanitized ExecStart)"
  fi
else
  skip "systemd-analyze not installed"
fi

for unit in deploy/systemd/*.service; do
  [[ -f "$unit" ]] && check_unit_hardening "$unit"
done
check_caddy_static
check_env_template

if command -v caddy >/dev/null 2>&1; then
  if caddy validate --config deploy/Caddyfile --adapter caddyfile; then
    pass "caddy validate"
  else
    fail "caddy validate"
  fi
else
  skip "caddy not installed; run caddy validate on the deployment host"
fi

if ((FAILURES > 0)); then
  printf 'deploy validation: %s failure(s)\n' "$FAILURES" >&2
  exit 1
fi
printf 'deploy validation: all available checks passed\n'
