# NoahsArk V0.0.1 development deployment baseline

This directory contains a **development baseline** for a single Linux host.
It is not a production release, does not contain real hostnames, certificates,
tokens or credentials, and has not been accepted by Phase 6. Production
topology, TLS/domain ownership and recovery objectives remain owner decisions
(`G-DEPLOY`, `G-AUTH`, `G-EVIDENCE`, `G-NODE`).

## Components

| File | Purpose |
| --- | --- |
| `Caddyfile` | Template reverse proxy: browser -> Caddy -> UI `127.0.0.1:8100` / API `127.0.0.1:8000`. Uses `tls internal` and a placeholder hostname. |
| `systemd/noahsark-control-plane.service` | Control-plane API on loopback, unprivileged user, hardened sandbox, no capability set. |
| `systemd/noahsark-node.service` | Disabled-by-default Linux simulator unit. It does not perform device actions and produces no acceptance evidence. |
| `env/control-plane.env.example` | Placeholder environment file. Install with mode `0600`; never commit a filled copy. |
| `validate.sh` | Static validation: shell syntax, secret scan, unit-file syntax, permission checks, optional Caddy parse. |
| `perf-smoke.py` | Bounded, local in-process latency smoke. Not a capacity or SLO test. |

## Least privilege and secrets

- The API and node units run as dedicated system users (`noahsark`,
  `noahsark-node`), never as root.
- `CapabilityBoundingSet=` and `AmbientCapabilities=` are empty. The API needs
  no Linux capabilities. A future device adapter that needs hardware access
  must document a narrow exception instead of re-enabling the full set.
- Both units set `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`,
  `PrivateTmp`, `PrivateDevices`, `ProtectKernel*`, `RestrictSUIDSGID` and
  `UMask=0077`.
- The control plane only listens on `127.0.0.1:8000`; Caddy is the only
  network-facing process. Uvicorn access logging is disabled because the
  application access log records method/path/status/correlation id and never
  query strings, headers or bodies.
- Install the environment file as `root:noahsark 0640` (or `0600` read by
  root+unit) and verify it has no group/world write bits:

  ```bash
  install -d -m 0750 /etc/noahsark
  install -m 0600 deploy/env/control-plane.env.example /etc/noahsark/control-plane.env
  stat -c '%a %U:%G %n' /etc/noahsark/control-plane.env
  ```

- Credentials belong only in the operator-managed environment file or the
  SOPS-encrypted node inventory. `scripts/secret-scan.sh` scans `deploy/`,
  `scripts/`, `config/`, application source and CI for credential-shaped
  strings and private address literals.

## Logging and health

- `GET /healthz` is liveness and never includes the database URL.
- `GET /readyz` returns `503` with a fixed reason when `DATABASE_URL` is not
  configured. It never echoes the URL.
- `scripts/healthcheck.sh` probes loopback health, readiness and the UI. A
  `503` readiness response is a failure.
- Metrics and distributed tracing are **not implemented** in this baseline.
  Journald/Caddy logs plus the correlation id are the available observability.
  `/metrics` must not be published until the observability contract is frozen.

## Backup and restore drill

`scripts/backup.sh` is read-only without `--execute`; with `--execute` it
writes a PostgreSQL custom-format dump, an evidence archive, `SHA256SUMS` and
`manifest.json` under `NAA_BACKUP_DIR`. `scripts/restore-drill.sh` verifies the
checksums first and refuses to write unless the target database ends in
`_drill`, differs from the source database, and `--execute --confirm` is
given.

These scripts prove local backup/restore mechanics only. They do not prove
RPO/RTO, off-host durability, encryption at rest, or production recovery.

## Static validation

```bash
./deploy/validate.sh
```

The script runs `bash -n` on deployment scripts, the repository secret scan,
`sytemd-analyze verify` on a sanitized copy of each unit (the real `ExecStart`
paths do not exist on a development host), mode checks, and `caddy validate`
when Caddy is installed. Caddy is not installed in the development
environment, so Caddy parsing is reported as `SKIP` there and must be repeated
on the deployment host.

## Explicit limitations

- No public domain, public IP, certificate, ACME account or DNS proof.
- No production Windows Session 0/NSSM installation, TCL device, or hardware
  acceptance.
- No production backup, replication, failover or RPO/RTO proof.
- No capacity SLO. `perf-smoke.py` is an in-process latency sanity check with
  the environment printed alongside the numbers.
