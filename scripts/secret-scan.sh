#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
paths=(apps/control_plane/noahsark apps/control_plane/tests apps/control_plane/pyproject.toml .github design/ui-app/src)
pattern='PRIVATE KEY|password[[:space:]]*[:=]|api[_-]?key[[:space:]]*[:=]|Bearer[[:space:]]+[A-Za-z0-9._-]{20,}|(^|[^0-9])(10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3})([^0-9]|$)'
if grep -RInE "$pattern" "${paths[@]}" --exclude='*.lock' --exclude='.env' 2>/dev/null; then
  echo "secret scan: forbidden pattern found" >&2
  exit 1
fi
echo "secret scan: clean"
