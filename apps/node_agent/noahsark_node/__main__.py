"""Command-line entry point for the development Node Agent.

The agent only makes outbound requests. It never binds a port or opens an
inbound listener, so it is safe to run as a Session 0 service or in a terminal.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Sequence

from . import __version__
from .agent import NodeAgent
from .config import NodeAgentSettings
from .runtime import build_agent


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="noahsark-node",
        description="NoahsArk outbound-only, facts-only Node Agent (simulator)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--once",
        action="store_true",
        help="run exactly one cycle and exit (useful for smoke tests)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        metavar="SECONDS",
        help="loop interval; defaults to NOAHSARK_HEARTBEAT_INTERVAL_SECONDS",
    )
    return parser


def run(agent: NodeAgent, *, interval: float, once: bool) -> int:
    try:
        while True:
            report = agent.run_cycle()
            print(json.dumps(report.to_dict(), sort_keys=True), flush=True)
            if once:
                return 0
            time.sleep(interval)
    except KeyboardInterrupt:
        return 0
    finally:
        agent.spool.close()


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = NodeAgentSettings.from_env()
    interval = settings.heartbeat_interval_seconds if args.interval is None else args.interval
    agent = build_agent(settings)
    return run(agent, interval=interval, once=bool(args.once))


if __name__ == "__main__":
    raise SystemExit(main())
