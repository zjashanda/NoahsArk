"""P5-W9 secret scanning and least-privilege deployment checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import DEPLOY, ROOT, SCRIPTS, run

SECRET_SCAN = SCRIPTS / "secret-scan.sh"


def test_secret_scan_flags_credential_without_echoing_the_value(tmp_path: Path):
    # Given a file containing a credential-shaped assignment
    secret = "S3cr3t-Value-Must-Not-Be-Echoed"
    target = tmp_path / "leak.txt"
    target.write_text(f'db_password = "{secret}"\n', encoding="utf-8")

    # When the scan runs over that file
    result = run([str(SECRET_SCAN), str(tmp_path)])

    # Then it fails, names the file, and never prints the value
    assert result.returncode == 1
    assert "leak.txt" in result.stderr
    assert secret not in result.stdout
    assert secret not in result.stderr


def test_secret_scan_flags_private_key_block(tmp_path: Path):
    # Given a private key header
    target = tmp_path / "key.pem"
    target.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n", encoding="utf-8")

    # When the scan runs
    result = run([str(SECRET_SCAN), str(tmp_path)])

    # Then the key material is reported by path only
    assert result.returncode == 1
    assert "key.pem" in result.stderr


def test_secret_scan_is_clean_on_the_repository_surface():
    # Given the real deployment/application surface
    # When the repository scan runs
    result = run([str(SECRET_SCAN)])

    # Then it reports clean and exits zero
    assert result.returncode == 0, result.stderr
    assert "secret scan: clean" in result.stdout


def test_validate_rejects_group_writable_deployment_script(repo_surface: Path):
    # Given a copied deployment surface whose backup script is unsafe
    target = repo_surface / "scripts" / "backup.sh"
    target.chmod(0o666)

    # When static validation runs
    result = run([str(repo_surface / "deploy" / "validate.sh")], cwd=repo_surface)

    # Then the permission regression is named and validation fails
    assert result.returncode == 1
    assert "group/world-writable scripts/backup.sh" in result.stderr


def test_validate_passes_on_the_repository_baseline():
    # Given the repository as checked in
    # When static validation runs
    result = run([str(DEPLOY / "validate.sh")], cwd=ROOT)

    # Then every available check passes
    assert result.returncode == 0, result.stdout + result.stderr
    assert "deploy validation: all available checks passed" in result.stdout
    assert "FAIL" not in result.stdout


@pytest.mark.parametrize(
    "unit_name",
    ["noahsark-control-plane.service", "noahsark-node.service"],
)
def test_systemd_units_run_unprivileged_without_capabilities(unit_name: str):
    # Given a shipped systemd unit
    text = (DEPLOY / "systemd" / unit_name).read_text(encoding="utf-8")
    directives = {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in text.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }

    # When its privilege directives are inspected
    # Then it must not run as root and must not retain capabilities
    assert directives["User"] not in {"root", ""}
    assert directives["Group"] not in {"root", ""}
    assert directives["CapabilityBoundingSet"] == ""
    assert directives["AmbientCapabilities"] == ""
    assert directives["NoNewPrivileges"] == "true"
    assert directives["ProtectSystem"] == "strict"
    assert directives["UMask"] == "0077"


def test_caddy_template_only_proxies_loopback_and_hides_health():
    # Given the Caddy template
    text = (DEPLOY / "Caddyfile").read_text(encoding="utf-8")

    # When its listeners and routes are inspected
    # Then upstreams stay on loopback, no plaintext/wildcard listener exists,
    # and liveness endpoints are not published through the proxy.
    assert "reverse_proxy 127.0.0.1:8000" in text
    assert "reverse_proxy 127.0.0.1:8100" in text
    assert "http://" not in text
    assert "0.0.0.0" not in text
    assert ":80 {" not in text
    assert "/healthz" not in text
    assert "/readyz" not in text
    assert "tls internal" in text
