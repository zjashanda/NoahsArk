"""P5-W9 health probing, log redaction and bounded performance checks."""

from __future__ import annotations

import logging
import sys

import pytest
from conftest import ROOT, SCRIPTS, base_env, health_server, run
from fastapi.testclient import TestClient
from noahsark.config import settings
from noahsark.main import app

HEALTHCHECK = SCRIPTS / "healthcheck.sh"
PERF_SMOKE = ROOT / "deploy" / "perf-smoke.py"
DATABASE_URL = "postgresql+asyncpg://noahsark:SuperSecretValue@127.0.0.1:5432/noahsark"


def _health_env(base: str) -> dict[str, str]:
    return base_env(
        NAA_API_BASE=base,
        NAA_UI_BASE=base,
        NAA_HEALTH_TIMEOUT="5",
    )


def test_healthcheck_fails_when_readiness_degrades():
    # Given a loopback API whose /readyz returns 503
    with health_server(ready_status=503) as base:
        # When the healthcheck probes liveness, readiness and the UI
        result = run([str(HEALTHCHECK)], env=_health_env(base))

    # Then degraded readiness is a failure even though /healthz is healthy
    assert result.returncode == 1
    assert "PASS  healthz" in result.stdout
    assert "FAIL  readyz" in result.stdout
    assert "all checks passed" not in result.stdout


def test_healthcheck_passes_when_all_loopback_probes_are_healthy():
    # Given a loopback API and UI that are healthy
    with health_server(ready_status=200) as base:
        # When the healthcheck runs
        result = run([str(HEALTHCHECK)], env=_health_env(base))

    # Then all three probes pass
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS  healthz" in result.stdout
    assert "PASS  readyz" in result.stdout
    assert "PASS  ui" in result.stdout


def test_health_responses_never_echo_the_database_url(monkeypatch):
    # Given a configured database URL containing a credential
    monkeypatch.setattr(settings, "database_url", DATABASE_URL)
    client = TestClient(app)

    # When liveness and readiness are requested
    health = client.get("/healthz")
    ready = client.get("/readyz")

    # Then both answer without echoing the URL, user or password
    assert health.status_code == 200
    assert ready.status_code == 200
    for response in (health, ready):
        body = response.text.lower()
        assert "supersecretvalue" not in body
        assert "database_url" not in body
        assert "postgresql" not in body
        assert "noahsark:super" not in body


def test_access_log_omits_query_string_and_authorization(caplog: pytest.LogCaptureFixture):
    # Given a request carrying a query token and an Authorization header
    client = TestClient(app)
    caplog.set_level(logging.INFO, logger="noahsark.access")

    # When the request is served
    response = client.get(
        "/healthz?token=QuerySecretToken",
        headers={"Authorization": "Bearer HeaderSecretToken"},
    )

    # Then the access log keeps the path only and leaks neither value
    assert response.status_code == 200
    log_text = caplog.text
    assert "request method=GET path=/healthz" in log_text
    assert "QuerySecretToken" not in log_text
    assert "HeaderSecretToken" not in log_text
    assert "?token" not in log_text


@pytest.mark.parametrize("iterations", ["999", "0"])
def test_perf_smoke_rejects_unbounded_or_empty_runs(iterations: str):
    # Given an out-of-range iteration count
    # When the smoke is asked to run it
    result = run([sys.executable, str(PERF_SMOKE), "--iterations", iterations])

    # Then argument validation refuses before importing the application
    assert result.returncode == 2
    assert "must be between" in result.stderr


def test_perf_smoke_is_bounded_and_repeatable():
    # Given the in-process latency smoke
    args = [sys.executable, str(PERF_SMOKE), "--iterations", "5", "--warmup", "1"]

    # When it runs twice with the same bound
    first = run(args)
    second = run(args)

    # Then both runs pass, stay within the cap and report the same shape
    for result in (first, second):
        assert result.returncode == 0, result.stderr
        assert "perf-smoke: PASS" in result.stdout
        assert "iterations=5 warmup=1" in result.stdout
        assert "bounded local smoke; not a capacity test or SLO claim" in result.stdout
        assert "p95_ms=" in result.stdout
