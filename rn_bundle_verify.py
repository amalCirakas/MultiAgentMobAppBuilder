"""
Post-build Metro smoke: run `react-native bundle` so TransformError / bad cwd surface
before the user runs the app (Crew cannot reliably shell-test Metro).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def verify_rn_android_bundle_smoke(build_root: Path, *, timeout_s: int | None = None) -> None:
    """
    Run a one-off Android JS bundle from ``build_root``. Raises RuntimeError on failure.

    Catches many Metro/Babel issues early. ``uv_cwd`` / ENOENT cwd usually means Metro was
    started from a directory that was later deleted/renamed — not fixable by LLM codegen.
    """
    if os.getenv("SKIP_RN_BUNDLE_VERIFY", "").strip().lower() in ("1", "true", "yes", "on"):
        print("[BUILD] SKIP_RN_BUNDLE_VERIFY=1 — skipping Android Metro bundle smoke test.", flush=True)
        return

    if timeout_s is None:
        raw = os.getenv("RN_BUNDLE_VERIFY_TIMEOUT_SECONDS", "").strip()
        timeout_s = int(raw) if raw.isdigit() else 300

    root = build_root.resolve()
    if not root.is_dir():
        raise RuntimeError(f"[BUILD] BUILD_ROOT is not a directory: {root}")
    if not (root / "index.js").is_file():
        raise RuntimeError(f"[BUILD] Missing Metro entry {root / 'index.js'}; cannot bundle.")

    tmp = Path(tempfile.mkdtemp(prefix="rn-bundle-verify-"))
    try:
        bundle_out = tmp / "smoke.android.bundle"
        assets = tmp / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        cmd = [
            "npx",
            "react-native",
            "bundle",
            "--platform",
            "android",
            "--dev",
            "true",
            "--entry-file",
            "index.js",
            "--bundle-output",
            str(bundle_out),
            "--assets-dest",
            str(assets),
        ]
        env = dict(os.environ)
        env.setdefault("CI", "true")
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=timeout_s,
            env=env,
        )
        err = (proc.stderr or "") + "\n" + (proc.stdout or "")
        tail = err[-12000:] if len(err) > 12000 else err
        if proc.returncode != 0:
            hint = ""
            low = err.lower()
            if "uv_cwd" in err or ("enoent" in low and "cwd" in low):
                hint = (
                    "\nHint: ``uv_cwd`` / cwd ENOENT — stop every Metro window (`npm start`), "
                    "close terminals that were `cd`'d into a deleted/moved folder, then from a "
                    "**new** shell: `cd` into **this** project only and `npm start`. "
                    "Uninstall stale Android builds if the bundle URL still points at an old path.\n"
                )
            raise RuntimeError(
                "[BUILD] Metro `react-native bundle` (android dev smoke) failed — fix before "
                "`run-android`, or set SKIP_RN_BUNDLE_VERIFY=1 to opt out.\n"
                + hint
                + tail
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("[BUILD] Metro Android bundle smoke check OK.", flush=True)
