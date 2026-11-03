"""Windows service wrapper stub (pywin32 primary, NSSM documented fallback).

This module must be importable on Linux. pywin32 is imported only behind a guard;
``run_service`` refuses to run unless the real Windows service APIs are present.
No service is installed or started by tests or the Linux development environment.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Any

from .agent import NodeAgent
from .config import NodeAgentSettings
from .runtime import build_agent

LOGGER = logging.getLogger("noahsark_node.service")

SERVICE_NAME = "NoahsArkNodeAgent"
SERVICE_DISPLAY_NAME = "NoahsArk Node Agent"
SERVICE_DESCRIPTION = (
    "NoahsArk Windows Node Agent (outbound-only, facts-only development skeleton)"
)

NSSM_FALLBACK = (
    'nssm install NoahsArkNodeAgent "C:\\path\\to\\python.exe" '
    '"-m noahsark_node --interval 15"'
)

try:  # pragma: no cover - exercised only on Windows
    import win32event as _win32event
    import win32service as _win32service
    import win32serviceutil as _win32serviceutil

    PYWIN32_AVAILABLE = True
except ImportError:  # pragma: no cover - Linux development path
    _win32event = None  # type: ignore[assignment]
    _win32service = None  # type: ignore[assignment]
    _win32serviceutil = None  # type: ignore[assignment]
    PYWIN32_AVAILABLE = False


_ServiceBase: Any = (
    _win32serviceutil.ServiceFramework if PYWIN32_AVAILABLE else object
)


class NodeAgentWindowsService(_ServiceBase):  # type: ignore[misc, valid-type]
    """Minimal SCM lifecycle: start the outbound loop, stop on SvcStop.

    Session 0 / interactive-helper separation and real device adapters are PENDING
    (G-NODE / A-0). This stub only proves the packaging hook is present.
    """

    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args: list[str]) -> None:
        if PYWIN32_AVAILABLE:
            _win32serviceutil.ServiceFramework.__init__(self, args)
            self._stop_event = _win32event.CreateEvent(None, 0, 0, None)
        else:
            self._stop_event = None
        self._thread: threading.Thread | None = None
        self._agent: NodeAgent | None = None

    def SvcStop(self) -> None:
        self.ReportServiceStatus(_win32service.SERVICE_STOP_PENDING)
        if self._stop_event is not None:
            _win32event.SetEvent(self._stop_event)

    def SvcDoRun(self) -> None:
        settings = NodeAgentSettings.from_env()
        self._agent = build_agent(settings)
        LOGGER.info("node agent service starting: %s", settings.node_id)
        self._thread = threading.Thread(target=self._run_loop, name="node-agent-loop")
        self._thread.start()
        self._wait(stop_event=self._stop_event)
        if self._thread is not None:
            self._thread.join(timeout=10)

    def _run_loop(self) -> None:
        settings = NodeAgentSettings.from_env()
        agent = self._agent or build_agent(settings)
        try:
            while not self._stop_requested():
                try:
                    report = agent.run_cycle()
                except Exception:  # service boundary must not die
                    LOGGER.exception("node agent cycle crashed; retrying next interval")
                else:
                    LOGGER.info("cycle: %s", report.to_dict())
                self._sleep(settings.heartbeat_interval_seconds)
        finally:
            agent.spool.close()

    def _stop_requested(self) -> bool:
        if self._stop_event is None:
            return False
        result = _win32event.WaitForSingleObject(self._stop_event, 0)
        return result == _win32event.WAIT_OBJECT_0

    def _wait(self, *, stop_event: object | None) -> None:
        if stop_event is None:
            while not self._stop_requested():
                time.sleep(0.5)
            return
        _win32event.WaitForSingleObject(stop_event, _win32event.INFINITE)

    def _sleep(self, seconds: float) -> None:
        if self._stop_event is not None:
            _win32event.WaitForSingleObject(self._stop_event, int(seconds * 1000))
        else:
            time.sleep(seconds)


def install_service() -> None:
    _require_windows()
    _win32serviceutil.HandleCommandLine(NodeAgentWindowsService)


def run_service() -> None:
    if not PYWIN32_AVAILABLE:
        raise RuntimeError(
            "pywin32 service APIs are unavailable on this platform. "
            f"Use the documented NSSM fallback instead: {NSSM_FALLBACK}"
        )
    _win32serviceutil.HandleCommandLine(NodeAgentWindowsService)


def _require_windows() -> None:
    if sys.platform != "win32" or not PYWIN32_AVAILABLE:
        raise RuntimeError(
            "Windows service install requires Windows and pywin32. "
            f"NSSM fallback: {NSSM_FALLBACK}"
        )
