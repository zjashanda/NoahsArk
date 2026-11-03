"""Allow-listed node tool registry.

The platform sends a tool id, never a command line.  Each entry owns its
executable, its fixed argument vector (or, for ``test.run``, a strictly
validated argument schema), its working directory, its timeout and its output
cap, so there is no user-controlled string for a shell to interpret.

Tools
-----
``usb.scan``
    Runs ``usbTree-cli.cmd`` from ``NOAHSARK_USBTREE_DIR`` (default
    ``C:\\Temp\\usb-tree``) with the fixed arguments ``--all --format csv`` and
    returns its stdout as CSV.

``test.run``
    Runs the TCL ``wake-recognition`` runner from ``NOAHSARK_TCL_DIR`` (default
    ``D:\\zhsh\\workspace\\tcl-r5\\tcl-lstest-debug``) as::

        python -u scripts/tcl_test_sub.py run <scenario> --rounds <rounds> \
            --bench config/benches/<bench> --runtime compat -- \
            --commands-file <commands-file> --cycle-commands

    Only ``scenario="wake-recognition"``, an integer ``rounds`` in ``1..1000``,
    a plain ``.json`` bench filename under ``config/benches/`` and a
    ``command_set`` of ``single`` (default) or ``full`` are accepted.
    ``single`` keeps the historical one-command pool
    (``config/entry_gate_offline_commands.txt``); ``full`` selects the campaign
    command pool (``config/full_commands.txt``).  The command is assembled as an
    argv list with ``shell=False``; no user string ever reaches a command
    interpreter.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # POSIX
    import fcntl
except ImportError:  # pragma: no cover - Windows node
    fcntl = None  # type: ignore[assignment]

try:  # Windows
    import msvcrt
except ImportError:  # pragma: no cover - Linux test host
    msvcrt = None  # type: ignore[assignment]

from .protocol import utc_now_iso

DEFAULT_USBTREE_DIR = r"C:\Temp\usb-tree"
USBTREE_CLI = "usbTree-cli.cmd"
MAX_OUTPUT_BYTES = 1_000_000
MAX_ROUND_ROWS = 1000
DEFAULT_TIMEOUT_SECONDS = 30

DEFAULT_TCL_DIR = r"C:\ProgramData\NoahsArk\Node\tests\tcl-r5\tcl-lstest-debug"
TCL_PYTHON_ENV = "NOAHSARK_TCL_PYTHON"
DEFAULT_TCL_PYTHON = r"C:\Program Files\Python310\python.exe"
TCL_RUNNER_SCRIPT = "scripts/tcl_test_sub.py"
TCL_BENCH_SUBDIR = "config/benches"
TCL_DEFAULT_RESULT_ROOT = "result"
TEST_RUN_TIMEOUT_SECONDS = 28800
TEST_RUN_SCENARIOS = frozenset({"wake-recognition"})
TEST_RUN_COMMAND_SETS = frozenset({"single", "full"})
TEST_RUN_DEFAULT_COMMAND_SET = "single"
# The command pool is chosen by name only; these paths are registry-owned, so no
# caller-supplied string can redirect the runner at an arbitrary file.
TCL_COMMAND_FILES: dict[str, str] = {
    "single": "config/entry_gate_offline_commands.txt",
    "full": "config/full_commands.txt",
}
TEST_RUN_ARGUMENTS = frozenset(
    {"scenario", "rounds", "bench", "result_root", "command_set"}
)
MIN_TEST_ROUNDS = 1
MAX_TEST_ROUNDS = 1000

_BENCH_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json$", re.ASCII)
_RELATIVE_DIR_PART = re.compile(r"^[A-Za-z0-9._-]{1,64}$", re.ASCII)
_PATH_SEPARATORS = re.compile(r"[\\/]")

TOOL_KIND_FIXED = "fixed"
TOOL_KIND_TCL_TEST_RUN = "tcl_test_run"

STATUS_SUCCEEDED = "SUCCEEDED"
STATUS_FAILED = "FAILED"
STATUS_TIMEOUT = "TIMEOUT"

ERROR_TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
ERROR_TOOL_TIMEOUT = "TOOL_TIMEOUT"
ERROR_TOOL_EXIT_NONZERO = "TOOL_EXIT_NONZERO"
ERROR_UNKNOWN_TOOL = "UNKNOWN_TOOL"
ERROR_INVALID_TOOL_ARGS = "INVALID_TOOL_ARGS"
ERROR_DEVICE_BUSY = "DEVICE_BUSY"

# Local second line of defence: one ``test.run`` at a time per node.  The OS
# releases the advisory lock when the process exits (including a crash), so a
# stale lock file can never wedge the agent after a restart.
DEVICE_LOCK_DIR_ENV = "NOAHSARK_DEVICE_LOCK_DIR"
DEFAULT_DEVICE_LOCK_DIR = r"C:\ProgramData\NoahsArk\Node\locks"


class DeviceBusyError(RuntimeError):
    """Another process on this node already holds the test-run lock."""


class UnknownToolError(ValueError):
    """The platform asked for a tool this agent does not implement."""


class InvalidToolArgsError(ValueError):
    """The platform sent arguments the tool does not accept."""


@dataclass(frozen=True, slots=True)
class ToolSpec:
    tool_id: str
    executable_name: str
    args: tuple[str, ...]
    timeout_seconds: int
    max_output_bytes: int
    env_dir_var: str
    default_dir: str = DEFAULT_USBTREE_DIR
    kind: str = TOOL_KIND_FIXED


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "usb.scan": ToolSpec(
        tool_id="usb.scan",
        executable_name=USBTREE_CLI,
        args=("--all", "--format", "csv"),
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        max_output_bytes=MAX_OUTPUT_BYTES,
        env_dir_var="NOAHSARK_USBTREE_DIR",
        default_dir=DEFAULT_USBTREE_DIR,
        kind=TOOL_KIND_FIXED,
    ),
    "test.run": ToolSpec(
        tool_id="test.run",
        executable_name=TCL_RUNNER_SCRIPT,
        args=(),
        timeout_seconds=TEST_RUN_TIMEOUT_SECONDS,
        max_output_bytes=MAX_OUTPUT_BYTES,
        env_dir_var="NOAHSARK_TCL_DIR",
        default_dir=DEFAULT_TCL_DIR,
        kind=TOOL_KIND_TCL_TEST_RUN,
    ),
}


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_id: str
    status: str
    exit_code: int | None
    stdout: str | None
    stderr: str | None
    truncated: bool
    error_code: str | None
    started_at: str
    finished_at: str
    duration_ms: int
    details: Mapping[str, Any] | None = None

    def to_payload(self, *, node_id: str, command_id: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "node_id": node_id,
            "command_id": command_id,
            "status": self.status,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "truncated": self.truncated,
            "error_code": self.error_code,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
        }
        if self.details:
            # Extra structured fields (e.g. ``result_dir``) stay additive: the
            # control-plane schema ignores unknown keys, and existing fields win.
            for key, value in self.details.items():
                payload.setdefault(key, value)
        return payload


@dataclass(frozen=True, slots=True)
class TestRunArgs:
    """Validated ``test.run`` arguments; no raw user string survives this type."""

    scenario: str
    rounds: int
    bench: str
    result_root: str
    command_set: str


def rejected_result(tool_id: str, error_code: str, message: str) -> ToolResult:
    """A FAILED result for a request the registry refused before execution."""

    now = utc_now_iso()
    return ToolResult(
        tool_id=tool_id,
        status=STATUS_FAILED,
        exit_code=None,
        stdout=None,
        stderr=message,
        truncated=False,
        error_code=error_code,
        started_at=now,
        finished_at=now,
        duration_ms=0,
    )


def _failure(
    spec: ToolSpec,
    *,
    status: str,
    error_code: str,
    message: str,
    started_at: str,
    started_perf: float,
    details: Mapping[str, Any] | None = None,
) -> ToolResult:
    return ToolResult(
        tool_id=spec.tool_id,
        status=status,
        exit_code=None,
        stdout=None,
        stderr=message,
        truncated=False,
        error_code=error_code,
        started_at=started_at,
        finished_at=utc_now_iso(),
        duration_ms=int((time.monotonic() - started_perf) * 1000),
        details=details,
    )


def _as_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8", errors="replace")


def _truncate(raw: bytes | str | None, max_bytes: int) -> tuple[str, bool]:
    data = _as_bytes(raw)
    return data[:max_bytes].decode("utf-8", errors="replace"), len(data) > max_bytes


def _build_argv(spec: ToolSpec, executable: Path) -> list[str]:
    """Explicit ``cmd.exe /c`` for batch wrappers; never ``shell=True``.

    ``CreateProcess`` cannot launch a ``.cmd`` directly, so the fixed wrapper is
    invoked through the system command interpreter with the already-validated
    path and the registry-owned argument vector.
    """

    if os.name == "nt" and executable.suffix.lower() in {".cmd", ".bat"}:
        interpreter = os.environ.get("COMSPEC", "cmd.exe")
        return [interpreter, "/c", str(executable), *spec.args]
    return [str(executable), *spec.args]


def _tool_dir(spec: ToolSpec, env: dict[str, str] | None = None) -> Path:
    source = os.environ if env is None else env
    return Path(source.get(spec.env_dir_var, spec.default_dir))


def _device_lock_dir(env: dict[str, str] | None = None) -> Path:
    source = os.environ if env is None else env
    configured = source.get(DEVICE_LOCK_DIR_ENV)
    if configured:
        return Path(configured)
    if os.name == "nt":
        return Path(DEFAULT_DEVICE_LOCK_DIR)
    return Path(tempfile.gettempdir()) / "noahsark-node-locks"


def _device_lock_name(env: dict[str, str] | None = None) -> str:
    """One lock per node agent, so two agents never share a lock accidentally."""

    source = os.environ if env is None else env
    node_id = source.get("NOAHSARK_NODE_ID", "")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", node_id)[:80] or "default"
    return f"test-run-{safe}.lock"


def _lock_handle(handle: Any) -> None:
    if msvcrt is not None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
        return
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return
    raise OSError("no advisory file locking available on this platform")


def _unlock_handle(handle: Any) -> None:
    if msvcrt is not None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        return
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class _DeviceFileLock:
    """Non-blocking exclusive lock backed by the OS advisory lock."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: Any | None = None

    def acquire(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = self.path.open("a+", encoding="utf-8")
        except OSError as exc:
            raise DeviceBusyError(f"device lock unavailable: {exc}") from exc
        try:
            # Windows locks bytes from the current offset; make sure byte 0
            # exists before taking the lock.
            handle.seek(0)
            if handle.read(1) == "":
                handle.seek(0)
                handle.write("0")
                handle.flush()
            _lock_handle(handle)
        except OSError as exc:
            handle.close()
            raise DeviceBusyError(
                f"another test.run is already active on this node ({self.path.name})"
            ) from exc
        # Keep the locked byte at offset 0 intact: Windows drops byte-range
        # locks when the locked region is truncated away.  Metadata lives after
        # it and is replaced on every acquisition.
        metadata = json.dumps(
            {
                "pid": os.getpid(),
                "acquired_at": utc_now_iso(),
                "node_id": os.environ.get("NOAHSARK_NODE_ID"),
            },
            sort_keys=True,
        )
        handle.seek(1)
        handle.write(metadata)
        handle.truncate(1 + len(metadata.encode("utf-8")))
        handle.flush()
        self._handle = handle

    def release(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is None:
            return
        try:
            _unlock_handle(handle)
        except OSError:
            pass
        finally:
            handle.close()

    def __enter__(self) -> _DeviceFileLock:
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


def _device_lock(env: dict[str, str] | None = None) -> _DeviceFileLock:
    return _DeviceFileLock(_device_lock_dir(env) / _device_lock_name(env))



def _resolve_tcl_python(env: dict[str, str] | None = None) -> str | None:
    """Pick the TCL interpreter: explicit override, WIN009 default, then us.

    Returns ``None`` only when the override is set but does not exist, so the
    caller can fail loudly instead of silently running the wrong interpreter.
    """

    source = os.environ if env is None else env
    configured = source.get(TCL_PYTHON_ENV)
    if configured:
        return configured if Path(configured).is_file() else None
    if Path(DEFAULT_TCL_PYTHON).is_file():
        return DEFAULT_TCL_PYTHON
    return sys.executable or "python"


def resolve_executable(
    spec: ToolSpec, env: dict[str, str] | None = None
) -> Path:
    return _tool_dir(spec, env) / spec.executable_name


def _effective_timeout(spec: ToolSpec, requested: int | None) -> int:
    if requested is None:
        return spec.timeout_seconds
    return max(1, min(int(requested), spec.timeout_seconds))


def _valid_relative_dir(value: str) -> bool:
    """A plain relative directory with no drive, absolute root or ``..`` part."""

    if not value or value.startswith(("/", "\\")):
        return False
    if len(value) >= 2 and value[1] == ":":
        return False
    parts = _PATH_SEPARATORS.split(value)
    if not parts:
        return False
    return all(part not in {".", ".."} and _RELATIVE_DIR_PART.match(part) for part in parts)


def validate_test_run_args(args: Mapping[str, Any] | None) -> TestRunArgs:
    """Normalize ``test.run`` args or raise ``InvalidToolArgsError``.

    Exactly ``{scenario, rounds, bench, result_root, command_set}`` (the last
    two optional) are accepted. Values are checked against closed sets, not
    merely sanitized, so a caller becomes an argv element only after it matches
    an allow-list.
    """

    if args is None:
        args = {}
    if not isinstance(args, Mapping):
        raise InvalidToolArgsError("test.run args must be an object")
    unknown = sorted(set(args) - TEST_RUN_ARGUMENTS)
    if unknown:
        raise InvalidToolArgsError(
            f"test.run does not accept arguments: {', '.join(unknown)}"
        )

    scenario = args.get("scenario")
    if not isinstance(scenario, str) or scenario not in TEST_RUN_SCENARIOS:
        raise InvalidToolArgsError(
            "test.run scenario must be one of: "
            + ", ".join(sorted(TEST_RUN_SCENARIOS))
        )

    rounds = args.get("rounds")
    if (
        isinstance(rounds, bool)
        or not isinstance(rounds, int)
        or not MIN_TEST_ROUNDS <= rounds <= MAX_TEST_ROUNDS
    ):
        raise InvalidToolArgsError(
            f"test.run rounds must be an integer in "
            f"{MIN_TEST_ROUNDS}..{MAX_TEST_ROUNDS}"
        )

    bench = args.get("bench")
    if (
        not isinstance(bench, str)
        or ".." in bench
        or _PATH_SEPARATORS.search(bench)
        or not _BENCH_NAME.match(bench)
    ):
        raise InvalidToolArgsError(
            "test.run bench must be a plain .json filename under config/benches"
        )

    result_root = args.get("result_root", TCL_DEFAULT_RESULT_ROOT)
    if not isinstance(result_root, str) or not _valid_relative_dir(result_root):
        raise InvalidToolArgsError(
            "test.run result_root must be a relative directory inside the project"
        )

    command_set = args.get("command_set", TEST_RUN_DEFAULT_COMMAND_SET)
    if not isinstance(command_set, str) or command_set not in TEST_RUN_COMMAND_SETS:
        raise InvalidToolArgsError(
            "test.run command_set must be one of: "
            + ", ".join(sorted(TEST_RUN_COMMAND_SETS))
        )

    return TestRunArgs(
        scenario=scenario,
        rounds=rounds,
        bench=bench,
        result_root=result_root,
        command_set=command_set,
    )


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if len(raw) > 2_000_000:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _read_csv_rows(path: Path) -> list[dict[str, str]] | None:
    """Parse a runner CSV into at most ``MAX_ROUND_ROWS`` row mappings.

    The CSV is machine output from the runner, but it is still a file on the
    node: malformed rows and oversized files degrade to "no rows" instead of
    failing the tool call.
    """

    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return None
            rows: list[dict[str, str]] = []
            for raw in reader:
                row = {
                    key: value
                    for key, value in raw.items()
                    if isinstance(key, str) and key and isinstance(value, str)
                }
                if not any(value.strip() for value in row.values()):
                    continue
                rows.append(row)
                if len(rows) >= MAX_ROUND_ROWS:
                    break
    except (OSError, csv.Error):
        return None
    return rows


def _round_rows(result_dir: Path) -> tuple[list[dict[str, str]], str | None]:
    """Return parsed per-round rows and the CSV that supplied them."""

    first_existing: str | None = None
    for name in ("results.csv", "rounds.csv"):
        candidate = result_dir / name
        if not candidate.is_file():
            continue
        if first_existing is None:
            first_existing = str(candidate)
        rows = _read_csv_rows(candidate)
        if rows:
            return rows, str(candidate)
    return [], first_existing


def _newest_result_dir(base: Path, scenario: str) -> Path | None:
    if not base.is_dir():
        return None
    suffix = "_" + scenario.replace("-", "_")
    candidates: list[Path] = []
    try:
        entries = list(base.iterdir())
    except OSError:
        return None
    for entry in entries:
        try:
            if entry.is_dir():
                candidates.append(entry)
        except OSError:
            continue
    matching = [entry for entry in candidates if entry.name.endswith(suffix)]
    pool = matching or candidates
    if not pool:
        return None

    def _mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    return max(pool, key=lambda path: (_mtime(path), path.name))


def _collect_test_details(
    project_dir: Path, result_root: str, scenario: str
) -> dict[str, Any]:
    """Describe the newest result directory; never fail the tool call here."""

    details: dict[str, Any] = {
        "result_dir": None,
        "summary_path": None,
        "rounds_path": None,
    }
    result_dir = _newest_result_dir(project_dir / result_root, scenario)
    if result_dir is None:
        return details
    details["result_dir"] = str(result_dir)

    summary = result_dir / "summary_final.json"
    if summary.is_file():
        details["summary_path"] = str(summary)
        parsed = _read_json_object(summary)
        if parsed is not None:
            details["summary"] = parsed

    rounds, rounds_path = _round_rows(result_dir)
    if rounds_path is not None:
        details["rounds_path"] = rounds_path
    if rounds:
        details["rounds"] = rounds
    return details


def _run_fixed(
    spec: ToolSpec,
    *,
    timeout_seconds: int | None,
    env: dict[str, str] | None,
) -> ToolResult:
    executable = resolve_executable(spec, env)
    started_at = utc_now_iso()
    started_perf = time.monotonic()
    if not executable.is_file():
        return _failure(
            spec,
            status=STATUS_FAILED,
            error_code=ERROR_TOOL_UNAVAILABLE,
            message=f"tool executable not found: {executable}",
            started_at=started_at,
            started_perf=started_perf,
        )

    try:
        completed = subprocess.run(
            _build_argv(spec, executable),
            cwd=str(executable.parent),
            capture_output=True,
            timeout=_effective_timeout(spec, timeout_seconds),
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout, stdout_truncated = _truncate(exc.stdout, spec.max_output_bytes)
        stderr, stderr_truncated = _truncate(exc.stderr, spec.max_output_bytes)
        return ToolResult(
            tool_id=spec.tool_id,
            status=STATUS_TIMEOUT,
            exit_code=None,
            stdout=stdout,
            stderr=stderr,
            truncated=stdout_truncated or stderr_truncated,
            error_code=ERROR_TOOL_TIMEOUT,
            started_at=started_at,
            finished_at=utc_now_iso(),
            duration_ms=int((time.monotonic() - started_perf) * 1000),
        )
    except OSError as exc:
        return _failure(
            spec,
            status=STATUS_FAILED,
            error_code=ERROR_TOOL_UNAVAILABLE,
            message=f"tool could not start: {exc}",
            started_at=started_at,
            started_perf=started_perf,
        )

    stdout, stdout_truncated = _truncate(completed.stdout, spec.max_output_bytes)
    stderr, stderr_truncated = _truncate(completed.stderr, spec.max_output_bytes)
    succeeded = completed.returncode == 0
    return ToolResult(
        tool_id=spec.tool_id,
        status=STATUS_SUCCEEDED if succeeded else STATUS_FAILED,
        exit_code=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        truncated=stdout_truncated or stderr_truncated,
        error_code=None if succeeded else ERROR_TOOL_EXIT_NONZERO,
        started_at=started_at,
        finished_at=utc_now_iso(),
        duration_ms=int((time.monotonic() - started_perf) * 1000),
    )


def _run_tcl_test(
    spec: ToolSpec,
    args: Mapping[str, Any] | None,
    *,
    timeout_seconds: int | None,
    env: dict[str, str] | None,
) -> ToolResult:
    """Take the per-node test-run lock, then execute the runner.

    The lock is acquired non-blocking: a second ``test.run`` while one is live
    returns ``FAILED / DEVICE_BUSY`` instead of touching the same COM ports and
    sound card.  ``finally`` releases it on success, failure, timeout and
    exception; the OS releases it if the process crashes.
    """

    started_at = utc_now_iso()
    started_perf = time.monotonic()
    lock = _device_lock(env)
    try:
        lock.acquire()
    except DeviceBusyError as exc:
        return _failure(
            spec,
            status=STATUS_FAILED,
            error_code=ERROR_DEVICE_BUSY,
            message=str(exc),
            started_at=started_at,
            started_perf=started_perf,
        )
    try:
        return _run_tcl_test_locked(
            spec,
            args,
            timeout_seconds=timeout_seconds,
            env=env,
        )
    finally:
        lock.release()


def _run_tcl_test_locked(
    spec: ToolSpec,
    args: Mapping[str, Any] | None,
    *,
    timeout_seconds: int | None,
    env: dict[str, str] | None,
) -> ToolResult:
    parsed = validate_test_run_args(args)
    started_at = utc_now_iso()
    started_perf = time.monotonic()
    project_dir = _tool_dir(spec, env)

    runner = project_dir / TCL_RUNNER_SCRIPT
    if not runner.is_file():
        return _failure(
            spec,
            status=STATUS_FAILED,
            error_code=ERROR_TOOL_UNAVAILABLE,
            message=f"test runner not found: {runner}",
            started_at=started_at,
            started_perf=started_perf,
        )

    bench_dir = project_dir / TCL_BENCH_SUBDIR
    bench_path = bench_dir / parsed.bench
    try:
        resolved_bench = bench_path.resolve()
        resolved_bench.relative_to(bench_dir.resolve())
    except (OSError, ValueError) as exc:
        raise InvalidToolArgsError(
            "test.run bench must stay inside config/benches"
        ) from exc
    if not resolved_bench.is_file():
        return _failure(
            spec,
            status=STATUS_FAILED,
            error_code=ERROR_INVALID_TOOL_ARGS,
            message=f"bench file not found: {bench_path}",
            started_at=started_at,
            started_perf=started_perf,
        )

    interpreter = _resolve_tcl_python(env)
    if interpreter is None:
        source = os.environ if env is None else env
        return _failure(
            spec,
            status=STATUS_FAILED,
            error_code=ERROR_TOOL_UNAVAILABLE,
            message=f"test interpreter not found: {source.get(TCL_PYTHON_ENV)}",
            started_at=started_at,
            started_perf=started_perf,
        )

    commands_file = TCL_COMMAND_FILES[parsed.command_set]
    commands_path = project_dir / commands_file
    if not commands_path.is_file():
        return _failure(
            spec,
            status=STATUS_FAILED,
            error_code=ERROR_INVALID_TOOL_ARGS,
            message=f"commands file not found: {commands_path}",
            started_at=started_at,
            started_perf=started_perf,
        )

    argv = [
        interpreter,
        "-u",
        TCL_RUNNER_SCRIPT,
        "run",
        parsed.scenario,
        "--rounds",
        str(parsed.rounds),
        "--bench",
        f"{TCL_BENCH_SUBDIR}/{parsed.bench}",
        "--runtime",
        "compat",
        "--",
        "--commands-file",
        commands_file,
        "--cycle-commands",
    ]

    try:
        completed = subprocess.run(
            argv,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=_effective_timeout(spec, timeout_seconds),
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        details = _collect_test_details(project_dir, parsed.result_root, parsed.scenario)
        stdout, stdout_truncated = _truncate(exc.stdout, spec.max_output_bytes)
        stderr, stderr_truncated = _truncate(exc.stderr, spec.max_output_bytes)
        return ToolResult(
            tool_id=spec.tool_id,
            status=STATUS_TIMEOUT,
            exit_code=None,
            stdout=stdout,
            stderr=stderr,
            truncated=stdout_truncated or stderr_truncated,
            error_code=ERROR_TOOL_TIMEOUT,
            started_at=started_at,
            finished_at=utc_now_iso(),
            duration_ms=int((time.monotonic() - started_perf) * 1000),
            details=details,
        )
    except OSError as exc:
        return _failure(
            spec,
            status=STATUS_FAILED,
            error_code=ERROR_TOOL_UNAVAILABLE,
            message=f"test runner could not start: {exc}",
            started_at=started_at,
            started_perf=started_perf,
        )

    details = _collect_test_details(project_dir, parsed.result_root, parsed.scenario)
    stdout, stdout_truncated = _truncate(completed.stdout, spec.max_output_bytes)
    stderr, stderr_truncated = _truncate(completed.stderr, spec.max_output_bytes)
    succeeded = completed.returncode == 0
    return ToolResult(
        tool_id=spec.tool_id,
        status=STATUS_SUCCEEDED if succeeded else STATUS_FAILED,
        exit_code=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        truncated=stdout_truncated or stderr_truncated,
        error_code=None if succeeded else ERROR_TOOL_EXIT_NONZERO,
        started_at=started_at,
        finished_at=utc_now_iso(),
        duration_ms=int((time.monotonic() - started_perf) * 1000),
        details=details,
    )


def run_tool(
    tool_id: str,
    args: dict[str, Any] | None = None,
    *,
    timeout_seconds: int | None = None,
    env: dict[str, str] | None = None,
) -> ToolResult:
    """Execute one allow-listed tool and capture a bounded result.

    Raises ``UnknownToolError`` / ``InvalidToolArgsError`` for a request the
    registry cannot honour; all execution failures come back as ``ToolResult``
    so the caller always has something to report to the platform.
    """

    spec = TOOL_REGISTRY.get(tool_id)
    if spec is None:
        raise UnknownToolError(f"unknown tool: {tool_id}")

    if spec.kind == TOOL_KIND_TCL_TEST_RUN:
        return _run_tcl_test(
            spec, args, timeout_seconds=timeout_seconds, env=env
        )

    if args:
        raise InvalidToolArgsError(f"tool {tool_id} takes no arguments")
    return _run_fixed(spec, timeout_seconds=timeout_seconds, env=env)
