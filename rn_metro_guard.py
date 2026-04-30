"""Detect and optionally stop stale React Native Metro processes under Project/*."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_DIR = PROJECT_ROOT / "Project"

METRO_MARKERS = (
    "node_modules/react-native/cli.js start",
    "node_modules/.generated/launchPackager.command",
    "react-native-devtools",
    "node_modules/jest-worker/build/workers/processChild.js",
)


@dataclass(frozen=True)
class MetroProcess:
    pid: int
    ppid: int
    project_root: Path
    command: str


def _ps_lines() -> list[str]:
    proc = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,command="],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return (proc.stdout or "").splitlines()


def _project_root_from_command(command: str) -> Path | None:
    escaped = re.escape(str(PROJECT_DIR))
    match = re.search(rf"({escaped}/[^/\s'\"]+)", command)
    if not match:
        return None
    return Path(match.group(1)).resolve()


def list_project_metro_processes() -> list[MetroProcess]:
    processes: list[MetroProcess] = []
    for line in _ps_lines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        command = parts[2]
        if not any(marker in command for marker in METRO_MARKERS):
            continue
        root = _project_root_from_command(command)
        if not root:
            continue
        processes.append(MetroProcess(pid=pid, ppid=ppid, project_root=root, command=command))
    return processes


def _format_processes(processes: list[MetroProcess]) -> str:
    rows = []
    for p in processes:
        exists = "exists" if p.project_root.is_dir() else "missing"
        rows.append(f"  - pid={p.pid} root={p.project_root} ({exists})")
    return "\n".join(rows)


def kill_processes(processes: list[MetroProcess]) -> None:
    # Children/workers should die with Metro, but killing all matched pids makes stale roots deterministic.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for p in processes:
            try:
                os.kill(p.pid, sig)
            except ProcessLookupError:
                pass
            except PermissionError:
                pass
        if sig == signal.SIGTERM:
            time.sleep(0.8)


def guard_stale_metro(active_build_root: Path) -> None:
    """
    Fail fast when Metro already serves another Project/* root.

    Set KILL_STALE_METRO=1 to terminate stale RN packagers automatically.
    """
    active = active_build_root.resolve()
    active_parent = active.parent.resolve()
    if active_parent != PROJECT_DIR.resolve():
        return

    processes = list_project_metro_processes()
    stale = [p for p in processes if p.project_root != active]
    if not stale:
        return

    if os.getenv("KILL_STALE_METRO", "").strip().lower() in ("1", "true", "yes", "on"):
        print("[METRO-GUARD] KILL_STALE_METRO=1: stopping stale Metro/devtools processes:")
        print(_format_processes(stale), flush=True)
        kill_processes(stale)
        remaining = [p for p in list_project_metro_processes() if p.project_root != active]
        if remaining:
            raise RuntimeError(
                "[METRO-GUARD] Some stale Metro processes are still running:\n"
                + _format_processes(remaining)
            )
        print("[METRO-GUARD] Stale Metro processes stopped.", flush=True)
        return

    raise RuntimeError(
        "[METRO-GUARD] Stale React Native Metro/devtools processes are running under Project/.\n"
        "They can serve deleted folders and cause red-screen errors like `Unable to resolve ./index`.\n"
        + _format_processes(stale)
        + "\n\nStop them, or rerun with KILL_STALE_METRO=1 to stop them automatically."
    )


def main() -> int:
    active = Path(os.environ.get("BUILD_ROOT", PROJECT_DIR / "__new_build__"))
    try:
        guard_stale_metro(active)
    except RuntimeError as exc:
        print(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
