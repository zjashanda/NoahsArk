#!/usr/bin/env bash
# Sync the current worktree to the cloud remote after a completed substage.
# Usage: scripts/sync-cloud.sh "feat: message"
# Exit codes: 0 = pushed or nothing to do; 2 = committed locally but push failed.

set -euo pipefail
cd "$(dirname "$0")/.."

MSG="${1:-chore: sync $(date +%Y-%m-%dT%H:%M:%S)}"

# Never commit local secrets or tool state.
FORBIDDEN='(^|/)ssh\.txt$|(^|/)\.env$|(^|/)\.venv/|(^|/)\.playwright-mcp/|(^|/)__pycache__/|\.pyc$|(^|/)\.pytest_cache/|(^|/)\.ruff_cache/|(^|/)\.egg-info/'

git add -A

if git diff --cached --quiet; then
  echo "sync: no staged changes"
  exit 0
fi

if git diff --cached --name-only | grep -Eq "$FORBIDDEN"; then
  echo "sync: refusing to commit forbidden files:"
  git diff --cached --name-only | grep -E "$FORBIDDEN"
  exit 1
fi

# Repo-local identity is required for non-interactive commits.
if ! git config user.email >/dev/null; then
  git config user.name "zjashanda"
  git config user.email "zjashanda@users.noreply.github.com"
fi

git commit -m "$MSG"
echo "sync: local commit $(git rev-parse --short HEAD)"

if timeout 180 git push origin main; then
  echo "sync: pushed to origin/main"
  exit 0
fi

echo "sync: push failed (network/proxy/credentials). Commit kept locally."
echo "sync: retry with: cd $(pwd) && git push origin main"
exit 2
