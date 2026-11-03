#!/usr/bin/env bash
# Repository secret scan for the development baseline.
#
# Scans source, tests, deployment templates, scripts and node-inventory
# configuration for credential-shaped strings and private address literals.
# It deliberately excludes the scanner itself, lockfiles and any local `.env`.
#
# Usage:
#   scripts/secret-scan.sh                 # scan the default surface
#   scripts/secret-scan.sh PATH [PATH...]  # scan explicit paths (used by tests)
set -euo pipefail
cd "$(dirname "$0")/.."

if (($#)); then
  paths=("$@")
else
  paths=(
    apps/control_plane/noahsark
    apps/control_plane/tests
    apps/control_plane/pyproject.toml
    apps/node_agent
    deploy
    scripts
    config
    .github
    design/ui-app/src
  )
fi

pattern='PRIVATE KEY|password[[:space:]]*[:=]|api[_-]?key[[:space:]]*[:=]|secret[_-]?key[[:space:]]*[:=]|access[_-]?token[[:space:]]*[:=]|Bearer[[:space:]]+[A-Za-z0-9._-]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AGE-SECRET-KEY-1[0-9A-Z]{20,}|(^|[^0-9])(10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3})([^0-9]|$)'

existing=()
for path in "${paths[@]}"; do
  [[ -e "$path" ]] && existing+=("$path")
done

if ((${#existing[@]} == 0)); then
  echo "secret scan: no existing paths to scan" >&2
  exit 2
fi

matches=()
while IFS= read -r file; do
  [[ -n "$file" ]] && matches+=("$file")
done < <(grep -RIlE "$pattern" "${existing[@]}" \
  --binary-files=without-match \
  --exclude='*.lock' \
  --exclude='.env' \
  --exclude='secret-scan.sh' \
  --exclude='validate-inventory.py' 2>/dev/null || true)

if ((${#matches[@]} > 0)); then
  # Report only file paths: printing the matching line would echo the secret.
  echo "secret scan: forbidden pattern found in:" >&2
  printf '  %s\n' "${matches[@]}" >&2
  exit 1
fi
echo "secret scan: clean"
