"""Entry point: ``python -m noahsark.supervisor``.

The worker is intentionally disabled unless ``NOAHSARK_SUPERVISOR_ENABLED`` is
explicitly true, so importing or launching it cannot start remote side effects
by accident.
"""

from __future__ import annotations

import logging
import sys

import anyio

from .config import SupervisorSettings
from .runtime import run_worker


def main(argv: list[str] | None = None) -> int:
    del argv
    settings = SupervisorSettings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if not settings.enabled:
        logging.getLogger("noahsark.supervisor").info(
            "supervisor worker is disabled (NOAHSARK_SUPERVISOR_ENABLED=false)"
        )
        return 0
    try:
        anyio.run(run_worker, settings)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
