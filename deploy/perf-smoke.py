#!/usr/bin/env python3
"""Bounded, local in-process latency smoke for the control-plane health route.

This is a development sanity check, not a capacity test, load test or SLO
proof. It sends a hard-capped number of requests through the real FastAPI
application with Starlette's in-process TestClient and reports p50/p95/max
latency. It never prints configuration values, database URLs or headers.

Exit codes: 0 pass; 1 unhealthy route or latency above threshold; 2 bad usage
or missing test dependencies.
"""

from __future__ import annotations

import argparse
import math
import platform
import sys
import time
from pathlib import Path

MAX_ITERATIONS = 200
MAX_WARMUP = 50
DEFAULT_ITERATIONS = 30
DEFAULT_WARMUP = 5
DEFAULT_P95_MS = 250.0
PATH = "/healthz"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_app():
    """Import the control-plane app from this checkout, not an arbitrary install."""

    try:
        from noahsark.main import app
    except ImportError:
        sys.path.insert(0, str(_repo_root() / "apps" / "control_plane"))
        from noahsark.main import app
    return app


def _percentile(samples: list[float], fraction: float) -> float:
    ordered = sorted(samples)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bounded in-process latency smoke for the NoahsArk control plane."
    )
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--max-p95-ms", type=float, default=DEFAULT_P95_MS)
    args = parser.parse_args(argv)

    if not 1 <= args.iterations <= MAX_ITERATIONS:
        parser.error(f"--iterations must be between 1 and {MAX_ITERATIONS}")
    if not 0 <= args.warmup <= MAX_WARMUP:
        parser.error(f"--warmup must be between 0 and {MAX_WARMUP}")
    if args.max_p95_ms < 0:
        parser.error("--max-p95-ms must be >= 0")

    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print(
            "perf-smoke: ERROR: fastapi TestClient dependencies are not installed",
            file=sys.stderr,
        )
        return 2

    app = _load_app()

    try:
        with TestClient(app) as client:
            for _ in range(args.warmup):
                warmup = client.get(PATH)
                if warmup.status_code != 200:
                    print(
                        f"perf-smoke: FAIL warmup returned HTTP {warmup.status_code}",
                        file=sys.stderr,
                    )
                    return 1

            samples: list[float] = []
            statuses: set[int] = set()
            for _ in range(args.iterations):
                started = time.perf_counter()
                response = client.get(PATH)
                samples.append((time.perf_counter() - started) * 1000.0)
                statuses.add(response.status_code)
    except Exception as exc:  # noqa: BLE001 - CLI boundary; report type only, never values
        print(f"perf-smoke: FAIL application startup error ({type(exc).__name__})", file=sys.stderr)
        return 1

    if statuses != {200}:
        print(f"perf-smoke: FAIL unexpected status set {sorted(statuses)}", file=sys.stderr)
        return 1

    p50 = _percentile(samples, 0.50)
    p95 = _percentile(samples, 0.95)
    maximum = max(samples)
    verdict = "PASS" if p95 <= args.max_p95_ms else "FAIL"

    print(
        "perf-smoke: "
        f"python={platform.python_version()} target=in-process {PATH} "
        f"iterations={args.iterations} warmup={args.warmup}"
    )
    print(
        "perf-smoke: "
        f"p50_ms={p50:.3f} p95_ms={p95:.3f} max_ms={maximum:.3f} "
        f"threshold_p95_ms={args.max_p95_ms:.3f}"
    )
    print("perf-smoke: bounded local smoke; not a capacity test or SLO claim")

    if verdict != "PASS":
        print(
            f"perf-smoke: FAIL p95 {p95:.3f}ms exceeds {args.max_p95_ms:.3f}ms",
            file=sys.stderr,
        )
        return 1

    print("perf-smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
