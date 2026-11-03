# B2 local accounts and development authentication

Date: 2026-10-30
Scope: `apps/control_plane/` only. No UI, contracts, `ssh.txt`, or git state
were modified. No credential value appears in source, tests, logs, this file,
or the terminal output used to produce it.

## Decision

- Password storage uses `pwdlib[argon2]` (Argon2id), following the FastAPI
  security guide and OWASP Password Storage guidance. Plain SHA-256 is not used
  for credentials.
- Accounts are created only by `python -m noahsark.bootstrap_accounts`, which
  reads `NOAHSARK_ADMIN_PASSWORD` and `NOAHSARK_OBSERVER_PASSWORD` from the
  environment (or a hidden prompt), never from source, argv, a file, or a log.
- `X-NoahsArk-Role` remains a development compatibility path only. It is not
  accepted as production authentication, and the development login endpoint is
  disabled when `DEV_SESSION_ENABLED=false` or `AUTH_MODE=oidc`.
- The existing capability map remains fail-closed: unknown roles raise `403`,
  `ADMIN` has every capability, and `OBSERVER` has `READ` only.

## Changes

| File | Purpose |
| --- | --- |
| `noahsark/models/identity.py` | `users.password_hash` (nullable, digest only); `ADMIN` allowed by the role check |
| `migrations/versions/b2f1a4c7d902_w4_accounts_auth.py` | Adds `password_hash`; widens `ck_roles_role_code_closed` to include `ADMIN` |
| `noahsark/services/passwords.py` | Argon2id hash/verify, dummy verification for unknown users, bootstrap secret policy |
| `noahsark/bootstrap_accounts.py` | Env-only, idempotent upsert of `bszheng` (ADMIN) and `test001` (OBSERVER) |
| `noahsark/api/auth.py` | `POST /api/v1/auth/dev-login`, `GET /api/v1/auth/session`, `POST /api/v1/auth/logout` |
| `noahsark/services/audit.py` | Login denials append `access_decision=DENY` / `result=DENIED` events |
| `noahsark/main.py` | Wires the auth router under `/api/v1` |
| `scripts/bootstrap-accounts.sh` | Hidden-input wrapper; clears the secrets on exit |
| `Makefile` | `make bootstrap-accounts` |
| `pyproject.toml`, `requirements.lock` | Pins `pwdlib==0.3.1` and Argon2 dependencies |
| `tests/test_b2_accounts_auth.py` | 17 B2 tests (unit + PostgreSQL) |
| `tests/test_api_batch1.py`, `test_api_batch2.py`, `test_api_batch3.py` | Explicitly allow the two new auth POST paths; role/user counts tolerate bootstrap rows |
| `.env.example` | Documents the two required bootstrap variable names without values |

Migration head: `b2f1a4c7d902` (`8a4e6c21d9f0` -> `b2f1a4c7d902`).

## Secure bootstrap command

The orchestrator supplies the two values separately. Locally, use hidden input
so no value enters shell history, a file, or terminal scrollback:

```bash
cd /home/bszheng/NoahsArk/apps/control_plane
read -r -s -p 'bszheng password: ' NOAHSARK_ADMIN_PASSWORD; echo
read -r -s -p 'test001 password: ' NOAHSARK_OBSERVER_PASSWORD; echo
export NOAHSARK_ADMIN_PASSWORD NOAHSARK_OBSERVER_PASSWORD
python -m noahsark.bootstrap_accounts
unset NOAHSARK_ADMIN_PASSWORD NOAHSARK_OBSERVER_PASSWORD
```

Equivalent wrapper: `make bootstrap-accounts`.

Observed output shape only (no digest or secret):

```text
bootstrap ok; Argon2id digests stored; secrets not printed
  bszheng: role=ADMIN status=ACTIVE action=created
  test001: role=OBSERVER status=ACTIVE action=created
```

The command refuses missing, empty, whitespace-padded, too-short, known-default,
and username-equal values. It writes only Argon2id digests and never prints the
database URL.

## Login behavior

`POST /api/v1/auth/dev-login` with `{"username": "...", "password": "..."}`
returns a one-time `nsk_...` server-side session token, role, capability list,
and expiry. Only a SHA-256 token hash is stored in `sessions`; the password
digest is never returned.

Fail-closed behavior:

| Case | Result |
| --- | --- |
| Valid `bszheng` | `200`, role `ADMIN`, all capabilities |
| Valid `test001` | `200`, role `OBSERVER`, `["READ"]` |
| Wrong password | `401 INVALID_CREDENTIALS` |
| Unknown user | `401 INVALID_CREDENTIALS`, same message; dummy Argon2 verify runs |
| Missing/expired/revoked session | `401 SESSION_*` |
| `AUTH_MODE=oidc` or dev login disabled | `403 DEV_LOGIN_DISABLED` |

Every login attempt appends a hash-chained `AUTH_LOGIN` audit event with
`ALLOW`/`SUCCESS` or `DENY`/`DENIED`; logout appends `AUTH_LOGOUT`.

## Verification

Run from `apps/control_plane` with the repository virtualenv:

```text
alembic current          -> b2f1a4c7d902 (head)
pytest --disable-warnings -> 104 passed, 1 warning
ruff check noahsark tests -> All checks passed!
mypy noahsark             -> Success: no issues found in 46 source files
alembic check             -> No new upgrade operations detected
```

B2-specific tests (17):

1. Argon2 digest differs from plaintext and verifies.
2. Per-hash salts are unique.
3. Empty/default/whitespace/username-equal bootstrap secrets are refused.
4. `ADMIN` holds every capability.
5. `OBSERVER` holds only `READ` and is denied every other capability.
6. Unknown role still fails closed.
7. Bootstrap stores only Argon2id digests with `source=bootstrap`.
8. Bootstrap is idempotent, preserves `user_id`, and rotates the digest.
9. Admin login returns a session with all capabilities.
10. `test001` reads tasks but is denied a write.
11. Wrong password and unknown user return the same `401`.
12. Both login success and denial append audit rows.
13. Expired session is rejected with `SESSION_EXPIRED`.
14. Logout revokes the session; reuse returns `SESSION_REVOKED`.
15. `password_hash`, `$argon2`, and both test secrets never appear in login,
    session, settings/access, tasks, or OpenAPI responses.
16. Bootstrap reads only `NOAHSARK_ADMIN_PASSWORD` and
    `NOAHSARK_OBSERVER_PASSWORD`; the values are neither echoed nor included
    in an error message.
17. A missing required environment secret is refused with the variable name
    only; the command does not fall back to a default or legacy name.

## Residual state

- The local database was migrated but intentionally not populated with real
  account credentials in this task; the orchestrator must run the secure
  bootstrap above with its separately supplied secrets.
- Production authentication still requires an OIDC/enterprise provider,
  issuer/audience/JWKS configuration, and a revocation policy. The header path
  and dev login are development-only.
