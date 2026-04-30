#!/usr/bin/env python3
"""Deterministic quality guardrails for generated Project/<slug> apps."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_DIR = PROJECT_ROOT / "Project"
ESLINT_CONFIG = PROJECT_ROOT / "eslint.config.cjs"


def _run(cmd: list[str], *, cwd: Path) -> None:
    print(f"[QUALITY] $ {' '.join(cmd)} (cwd={cwd})", flush=True)
    proc = subprocess.run(cmd, cwd=str(cwd), text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"[QUALITY] Command failed with exit code {proc.returncode}: {' '.join(cmd)}")


def _generated_apps() -> list[Path]:
    if not PROJECT_DIR.is_dir():
        return []
    apps: list[Path] = []
    for child in sorted(PROJECT_DIR.iterdir()):
        if not child.is_dir():
            continue
        if (child / "package.json").is_file() and (child / "tsconfig.json").is_file():
            apps.append(child)
    return apps


def _eslint_targets(app: Path) -> list[str]:
    candidates = [
        app / "src",
        app / "_contracts",
        app / "e2e",
        app / "App.tsx",
        app / "index.js",
    ]
    targets: list[str] = []
    for path in candidates:
        if path.is_dir():
            targets.append(str(path.relative_to(PROJECT_ROOT) / "**" / "*.{ts,tsx}"))
        elif path.is_file() and path.suffix in {".ts", ".tsx"}:
            targets.append(str(path.relative_to(PROJECT_ROOT)))
    return targets


def _ensure_project_dependencies(app: Path) -> None:
    if (app / "node_modules").is_dir():
        return
    print(f"[QUALITY] Installing dependencies for {app.relative_to(PROJECT_ROOT)}", flush=True)
    _run(["npm", "install"], cwd=app)


def validate_app(app: Path, *, install: bool) -> None:
    rel = app.relative_to(PROJECT_ROOT)
    print(f"[QUALITY] Validating generated app: {rel}", flush=True)
    if install:
        _ensure_project_dependencies(app)
    elif not (app / "node_modules").is_dir():
        raise RuntimeError(
            f"[QUALITY] {rel} has no node_modules. Run npm install there, or rerun with --install."
        )

    _run(["npx", "tsc", "--noEmit"], cwd=app)

    targets = _eslint_targets(app)
    if not targets:
        print(f"[QUALITY] No TS/TSX lint targets found in {rel}; skipping ESLint.", flush=True)
        return

    _run(
        [
            "npx",
            "eslint",
            "--config",
            str(ESLINT_CONFIG),
            "--max-warnings=0",
            *targets,
        ],
        cwd=PROJECT_ROOT,
    )


def run_quality(*, install: bool) -> None:
    if os.getenv("SKIP_QUALITY_GUARDRAILS", "").strip().lower() in {"1", "true", "yes", "on"}:
        print("[QUALITY] SKIP_QUALITY_GUARDRAILS=1 - skipping deterministic checks.", flush=True)
        return

    apps = _generated_apps()
    if not apps:
        print("[QUALITY] No generated Project/<slug> apps found; nothing to validate.", flush=True)
        return

    for app in apps:
        validate_app(app, install=install)
    print("[QUALITY] TypeScript and complexity guardrails passed.", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic quality checks for generated apps.")
    parser.add_argument(
        "--projects",
        action="store_true",
        help="Alias for the default behavior: validate generated Project/<slug> apps.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Run npm install inside generated apps when node_modules is missing.",
    )
    args = parser.parse_args()

    try:
        run_quality(install=args.install)
    except Exception as exc:  # noqa: BLE001 - CLI should report concise actionable failures.
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
