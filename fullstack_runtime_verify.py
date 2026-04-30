"""Build-time fullstack runtime smoke tests for generated Node notes APIs."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _http_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 2.0) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        if not raw:
            return None
        return json.loads(raw)


def _http_delete(url: str, timeout: float = 2.0) -> int:
    req = urllib.request.Request(url, method="DELETE")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return int(resp.status)


def _wait_for_health(base_url: str, proc: subprocess.Popen[str], timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    last_error = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            out = (proc.stdout.read() if proc.stdout else "") if proc.stdout else ""
            raise RuntimeError(
                "[FULLSTACK-QA] Generated Node server exited before /health responded "
                f"(exit {proc.returncode}).\n{out[-4000:]}"
            )
        try:
            health = _http_json("GET", f"{base_url}/health", timeout=1.0)
            if isinstance(health, dict) and health.get("status") == "ok":
                return
        except Exception as exc:  # noqa: BLE001 - keep last startup error for diagnostics.
            last_error = str(exc)
            time.sleep(0.25)
    raise RuntimeError(f"[FULLSTACK-QA] Timed out waiting for {base_url}/health. Last error: {last_error}")


def verify_fullstack_node_notes_api(build_root: Path, *, timeout_s: float | None = None) -> None:
    """Start generated server, exercise notes CRUD, then stop it."""
    if os.getenv("SKIP_FULLSTACK_API_VERIFY", "").strip().lower() in ("1", "true", "yes", "on"):
        print("[FULLSTACK-QA] SKIP_FULLSTACK_API_VERIFY=1 — skipping Node API smoke.", flush=True)
        return

    root = build_root.resolve()
    server = root / "server"
    package_json = server / "package.json"
    index_js = server / "src" / "index.js"
    if not package_json.is_file() or not index_js.is_file():
        raise RuntimeError(f"[FULLSTACK-QA] Missing generated Node server under {server}")

    if timeout_s is None:
        raw = os.getenv("FULLSTACK_API_VERIFY_TIMEOUT_SECONDS", "").strip()
        timeout_s = float(raw) if raw else 20.0

    if not (server / "node_modules").is_dir():
        print("[FULLSTACK-QA] Installing server dependencies...", flush=True)
        npm_i = subprocess.run(["npm", "install"], cwd=str(server), text=True)
        if npm_i.returncode != 0:
            raise RuntimeError(f"[FULLSTACK-QA] `npm install` failed in {server} ({npm_i.returncode})")

    base = "http://localhost:3090"
    proc: subprocess.Popen[str] | None = None
    try:
        try:
            health = _http_json("GET", f"{base}/health", timeout=1.0)
            already_running = isinstance(health, dict) and health.get("status") == "ok"
        except Exception:
            already_running = False

        if already_running:
            print("[FULLSTACK-QA] Using already-running Node API on http://localhost:3090.", flush=True)
        else:
            env = dict(os.environ)
            env["PORT"] = "3090"
            proc = subprocess.Popen(
                ["npm", "start"],
                cwd=str(server),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            _wait_for_health(base, proc, timeout_s)

        created = _http_json(
            "POST",
            f"{base}/api/v1/notes",
            {"title": "fullstack qa smoke", "body": "created during build verification"},
        )
        if not isinstance(created, dict) or not created.get("id"):
            raise RuntimeError(f"[FULLSTACK-QA] POST /api/v1/notes returned invalid payload: {created!r}")
        note_id = str(created["id"])

        listing = _http_json("GET", f"{base}/api/v1/notes")
        if not isinstance(listing, list) or not any(n.get("id") == note_id for n in listing if isinstance(n, dict)):
            raise RuntimeError("[FULLSTACK-QA] Created note was not returned by GET /api/v1/notes")

        status = _http_delete(f"{base}/api/v1/notes/{note_id}")
        if status not in (200, 202, 204):
            raise RuntimeError(f"[FULLSTACK-QA] DELETE returned unexpected status {status}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"[FULLSTACK-QA] API smoke failed: {exc}") from exc
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

    print("[FULLSTACK-QA] Node notes API smoke check OK.", flush=True)


def main() -> int:
    import sys

    if len(sys.argv) < 2:
        print("usage: python3 fullstack_runtime_verify.py BUILD_ROOT")
        return 1
    try:
        verify_fullstack_node_notes_api(Path(sys.argv[1]))
    except Exception as exc:  # noqa: BLE001 - CLI prints friendly error.
        print(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
