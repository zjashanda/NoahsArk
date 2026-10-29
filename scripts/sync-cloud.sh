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

# Push is best-effort: retry HTTPS and SSH-over-443, then record a pending
# marker and exit 0 so phase execution is never blocked by network failure.
SSH_KEY="${NAA_SSH_KEY:-$HOME/.ssh/id_ed25519_zjashanda_skills}"
SSH_REMOTE="ssh-origin"
SSH_URL="ssh://git@ssh.github.com:443/zjashanda/NoahsArk.git"

try_push() {
  local i
  for i in 1 2; do
    if timeout 30 git push origin main; then
      echo "sync: pushed to origin/main"
      return 0
    fi
    sleep 3
  done
  if [ -f "$SSH_KEY" ]; then
    if ! git remote get-url "$SSH_REMOTE" >/dev/null 2>&1; then
      git remote add "$SSH_REMOTE" "$SSH_URL"
    fi
    for i in 1 2; do
      if timeout 60 env GIT_SSH_COMMAND="ssh -i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -p 443" git push "$SSH_REMOTE" main; then
        echo "sync: pushed via ssh.github.com:443"
        return 0
      fi
      sleep 3
    done
  fi
  return 1
}

if try_push; then
  rm -f .omo/sync-pending.log
  exit 0
fi

mkdir -p .omo
printf '%s commit=%s reason=push_unreachable\n' "$(date -Iseconds)" "$(git rev-parse --short HEAD)" >> .omo/sync-pending.log
echo "sync: push pending (network). Local commit kept; implementation continues."
echo "sync: retry later: cd $(pwd) && git push origin main"
exit 0
