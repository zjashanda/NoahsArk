"""Shared harness for the P5-W9 development-deployment checks.

Everything here is local and offline: temporary directories, shell scripts
from this checkout, fake ``pg_dump``/``pg_restore`` executables and a loopback
HTTP server bound to an ephemeral port. No credentials, external hosts or
production services are used.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
DEPLOY = ROOT / "deploy"


def base_env(**overrides: str) -> dict[str, str]:
    """Return a clean environment without ambient database/credential values."""

    env = dict(os.environ)
    for key in ("DATABASE_URL", "NAA_DATABASE_URL", "NAA_RESTORE_DSN"):
        env.pop(key, None)
    env.update(overrides)
    return env


def run(
    args: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env if env is not None else base_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.fixture
def repo_surface(tmp_path: Path) -> Path:
    """Copy only the deployment surface so mode damage stays in the sandbox."""

    surface = tmp_path / "surface"
    shutil.copytree(DEPLOY, surface / "deploy")
    shutil.copytree(SCRIPTS, surface / "scripts")
    return surface


@pytest.fixture
def fake_pg(tmp_path: Path) -> Path:
    """Install fake pg_dump/pg_restore that never contact a database."""

    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    pg_dump = bin_dir / "pg_dump"
    pg_dump.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ "${1:-}" == "--version" ]]; then\n'
        '  echo "pg_dump (PostgreSQL) 16.0 (fake)"\n'
        "  exit 0\n"
        "fi\n"
        "dest=''\n"
        "for arg in \"$@\"; do\n"
        '  case "$arg" in --file=*) dest="${arg#--file=}" ;; esac\n'
        "done\n"
        '[[ -n "$dest" ]] || { echo "fake pg_dump: missing --file" >&2; exit 1; }\n'
        'printf "PGDMP fake custom-format dump\\n" > "$dest"\n',
        encoding="utf-8",
    )
    pg_restore = bin_dir / "pg_restore"
    pg_restore.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ -n "${FAKE_PG_RESTORE_LOG:-}" ]]; then\n'
        '  printf "invoked %s\\n" "$*" >> "$FAKE_PG_RESTORE_LOG"\n'
        "fi\n"
        'for arg in "$@"; do\n'
        '  if [[ "$arg" == "--list" ]]; then\n'
        '    echo "; fake archive listing"\n'
        "    exit 0\n"
        "  fi\n"
        "done\n"
        "exit 0\n",
        encoding="utf-8",
    )
    for tool in (pg_dump, pg_restore):
        tool.chmod(0o755)
    return bin_dir


def with_path(bin_dir: Path) -> dict[str, str]:
    env = base_env()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    return env


@pytest.fixture
def backup_factory(tmp_path: Path, fake_pg: Path):
    """Create a real local backup using fake PostgreSQL tools."""

    def _make(relative_root: Path) -> Path:
        dest = relative_root / "backups"
        evidence = relative_root / "evidence"
        evidence.mkdir(parents=True)
        (evidence / "sample.json").write_text('{"sample": true}\n', encoding="utf-8")
        env = with_path(fake_pg)
        env.update(
            {
                "NAA_BACKUP_DIR": str(dest),
                "NAA_EVIDENCE_ROOT": str(evidence),
                "NAA_DATABASE_URL": "postgresql+asyncpg://noahsark:PLACEHOLDER@127.0.0.1:5432/noahsark",
            }
        )
        result = run([str(SCRIPTS / "backup.sh"), "--execute"], env=env)
        assert result.returncode == 0, result.stderr
        directories = sorted(path for path in dest.iterdir() if path.is_dir())
        assert len(directories) == 1
        return directories[0]

    return _make


@contextmanager
def health_server(*, ready_status: int) -> Iterator[str]:
    """Serve /healthz, /readyz and the UI on a loopback ephemeral port."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/healthz"):
                status, body, kind = 200, '{"status": "ok"}', "application/json"
            elif self.path.startswith("/readyz"):
                if ready_status == 200:
                    status, body = 200, '{"status": "ready"}'
                else:
                    status, body = ready_status, '{"status": "degraded", "reason": "test"}'
                kind = "application/json"
            else:
                status, body, kind = 200, "<html><body>ok</body></html>", "text/html"
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
