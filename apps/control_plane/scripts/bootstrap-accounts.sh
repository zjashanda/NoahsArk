#!/usr/bin/env bash
# Local-only account bootstrap.
#
# Secrets are read from the environment when provided, otherwise from hidden
# prompts.  Nothing is written to shell history, a file, or the terminal, and
# the variables are cleared when the script exits.
set -euo pipefail

if [[ -z "${NOAHSARK_ADMIN_PASSWORD:-}" ]]; then
  read -r -s -p "bszheng password: " NOAHSARK_ADMIN_PASSWORD
  printf '\n'
fi
if [[ -z "${NOAHSARK_OBSERVER_PASSWORD:-}" ]]; then
  read -r -s -p "test001 password: " NOAHSARK_OBSERVER_PASSWORD
  printf '\n'
fi
export NOAHSARK_ADMIN_PASSWORD NOAHSARK_OBSERVER_PASSWORD
trap 'unset NOAHSARK_ADMIN_PASSWORD NOAHSARK_OBSERVER_PASSWORD' EXIT

cd "$(dirname "$0")/.."
exec python -m noahsark.bootstrap_accounts
