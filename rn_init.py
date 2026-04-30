"""Run React Native CLI init — uses npm dist-tags.latest for react-native."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

TEMPLATE = (
    "@react-native-community/cli init — npm dist-tags react-native@latest (no legacy tarball)"
)


def npm_dist_tags_latest(package: str = "react-native") -> str | None:
    req = urllib.request.Request(
        f"https://registry.npmjs.org/{package}",
        headers={"Accept": "application/json", "User-Agent": "multiAgentAppRNInit/2.1"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        payload = json.loads(resp.read().decode())
    latest = payload.get("dist-tags", {}).get("latest")
    return str(latest).strip() if latest else None


def parse_rn_major_minor(dep: str | None) -> tuple[int, int] | None:
    if not dep:
        return None
    token = dep.strip().split(",")[0].strip().strip("^~=<> ").split(":")[0]
    m = re.match(r"^(\d+)\.(\d+)", token)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def gradle_major_from_wrapper(build_root: Path) -> int | None:
    gw = build_root / "android" / "gradle" / "wrapper" / "gradle-wrapper.properties"
    if not gw.is_file():
        return None
    m = re.search(r"distributions/gradle-(\d+)", gw.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else None


def _darwin_java_home(version_switch: str) -> str | None:
    if sys.platform != "darwin":
        return None
    try:
        proc = subprocess.run(
            ["/usr/libexec/java_home", "-v", version_switch],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if proc.returncode != 0:
            return None
        line = (proc.stdout or "").strip().splitlines()[0].strip()
        return line if line and Path(line).is_dir() else None
    except OSError:
        return None


def _jdk_major_from_java_exe(java_exe: Path) -> int | None:
    if not java_exe.is_file():
        return None
    try:
        proc = subprocess.run(
            [str(java_exe), "-version"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        merged = ((proc.stderr or "") + (proc.stdout or "")).strip()
        m = re.search(r'version "?(\d+)', merged)
        return int(m.group(1)) if m else None
    except OSError:
        return None


def select_java_home_for_gradle(build_root: Path) -> str | None:
    java_bin_name = "java.exe" if sys.platform == "win32" else "java"
    gm = gradle_major_from_wrapper(build_root)

    prefers_newer_first = gm is not None and gm >= 9
    probe_order = ("21", "23", "22", "17") if prefers_newer_first else ("17", "21", "23")

    for lbl in probe_order:
        mj = _darwin_java_home(lbl)
        if mj:
            return mj

    jh = os.environ.get("JAVA_HOME", "").strip()
    if jh:
        home = Path(jh).expanduser().resolve()
        maj = _jdk_major_from_java_exe(home / "bin" / java_bin_name)
        if maj is not None and maj >= 17:
            return str(home)
    return None


def android_root_gradle_legacy_layout(build_root: Path) -> bool:
    bg = build_root / "android" / "build.gradle"
    if not bg.is_file():
        return False
    return "compileSdkVersion" in bg.read_text(encoding="utf-8")


def patch_org_gradle_java_home(build_root: Path) -> None:
    gp = build_root / "android" / "gradle.properties"
    if not gp.is_file():
        return
    text = gp.read_text(encoding="utf-8")
    if re.search(r"(?m)^\s*org\.gradle\.java\.home\s*=", text):
        return

    jdk = select_java_home_for_gradle(build_root)
    if not jdk:
        print(
            "[RN] JDK not auto-selected — install Temurin 17 or 21 and set JAVA_HOME, "
            "or set org.gradle.java.home in android/gradle.properties.",
            flush=True,
        )
        return

    gm = gradle_major_from_wrapper(build_root)
    note = ""
    if gm is not None and gm >= 9:
        note = "# multiAgentApp: pin JVM for repeatable Gradle/Kotlin toolchain (Gradle ≥9 favors JDK 21).\n"

    gp.write_text(
        text.rstrip()
        + "\n\n"
        + (note or "# multiAgentApp: pin JVM used by `./gradlew` from `npx react-native run-android`.\n")
        + "org.gradle.java.home="
        + jdk.replace("\\", "/")
        + "\n",
        encoding="utf-8",
    )
    print(f"[RN] Patched android/gradle.properties (org.gradle.java.home={jdk})", flush=True)


def patch_android_gradle_properties(build_root: Path) -> None:
    mm = parse_rn_major_minor(read_rn_version(build_root))
    if mm and mm[0] == 0 and mm[1] > 71:
        print("[RN] Skipping android.enableDexingArtifactTransform (RN > 0.71 template).", flush=True)
        return
    if not android_root_gradle_legacy_layout(build_root):
        print("[RN] Skipping dexing workaround (modern Gradle layout).", flush=True)
        return
    gp = build_root / "android" / "gradle.properties"
    if not gp.is_file():
        return
    text = gp.read_text(encoding="utf-8")
    if "android.enableDexingArtifactTransform" in text:
        return
    gp.write_text(
        text.rstrip()
        + "\n\n# multiAgentApp: D8/R8 dexing stability (legacy RN 0.70 + JDK 17 + AGP 7.x)\n"
        + "android.enableDexingArtifactTransform=false\n",
        encoding="utf-8",
    )
    print("[RN] Patched android/gradle.properties (android.enableDexingArtifactTransform=false)", flush=True)


def patch_android_sdk_versions(
    build_root: Path,
    *,
    compile_sdk: int = 34,
    target_sdk: int = 32,
    build_tools: str = "34.0.0",
) -> None:
    mm = parse_rn_major_minor(read_rn_version(build_root))
    if mm and mm[0] == 0 and mm[1] > 71:
        print("[RN] Skipping manual compile/target shim (modern RN manages SDK versions).", flush=True)
        return
    if not android_root_gradle_legacy_layout(build_root):
        print("[RN] Skipping manual SDK bump regex (Gradle KTS plugin DSL).", flush=True)
        return

    bg = build_root / "android" / "build.gradle"
    text = bg.read_text(encoding="utf-8")
    out = text
    out = re.sub(
        r'buildToolsVersion\s*=\s*"[^"]*"',
        f'buildToolsVersion = "{build_tools}"',
        out,
        count=1,
    )
    out = re.sub(r"compileSdkVersion\s*=\s*\d+", f"compileSdkVersion = {compile_sdk}", out, count=1)
    out = re.sub(r"targetSdkVersion\s*=\s*\d+", f"targetSdkVersion = {target_sdk}", out, count=1)
    if compile_sdk >= 34:
        out = re.sub(
            r'classpath\("com\.android\.tools\.build:gradle:[^"]+"\)',
            'classpath("com.android.tools.build:gradle:7.4.2")',
            out,
            count=1,
        )
    if out == text:
        return

    lines = out.splitlines(keepends=True)
    patched_lines: list[str] = []
    injected = False
    inject_sdk_comment = "multiAgentApp: compileSdk" not in out
    for line in lines:
        if not injected and "ext {" in line:
            patched_lines.append(line)
            if inject_sdk_comment:
                patched_lines.append(
                    "        // multiAgentApp: compileSdk "
                    + str(compile_sdk)
                    + "; targetSdk "
                    + str(target_sdk)
                    + " — RN 0.70 DevSupport crashes if target ≥33 (registerReceiver)\n"
                )
            injected = True
            continue
        patched_lines.append(line)

    if injected:
        bg.write_text("".join(patched_lines), encoding="utf-8")
    else:
        bg.write_text(out, encoding="utf-8")

    print(
        f"[RN] Patched legacy android/build.gradle (compileSdk={compile_sdk}, targetSdk={target_sdk})",
        flush=True,
    )
    gp = build_root / "android" / "gradle.properties"
    if compile_sdk >= 34 and gp.is_file():
        gtxt = gp.read_text(encoding="utf-8")
        if "android.suppressUnsupportedCompileSdk" not in gtxt:
            gp.write_text(
                gtxt.rstrip()
                + "\n\n# multiAgentApp: suppress AGP warning when compileSdk > tested default\n"
                + f"android.suppressUnsupportedCompileSdk={compile_sdk}\n",
                encoding="utf-8",
            )
            print("[RN] Patched android/gradle.properties (android.suppressUnsupportedCompileSdk)", flush=True)


def read_rn_version(build_root: Path) -> str | None:
    pkg = build_root / "package.json"
    if not pkg.is_file():
        return None
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    deps = data.get("dependencies") or {}
    dev = data.get("devDependencies") or {}
    rn = deps.get("react-native") or dev.get("react-native")
    return str(rn).strip() if rn else None


def _warn_node_if_old() -> None:
    try:
        proc = subprocess.run(
            ["node", "-v"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        raw = ((proc.stdout or "") + (proc.stderr or "")).strip()
        mv = parse_rn_major_minor(raw.lstrip("v"))
        if mv and mv[0] < 20:
            print(
                f"[RN] WARNING: `{raw}` detected. Latest react-native expects Node ≥20 "
                "(see npm package engines). Prefer Node 22 LTS.",
                flush=True,
            )
    except OSError:
        pass


def react_native_init(
    *,
    app_name_display: str,
    target_dir: Path,
    npm_exec: str = "npm",
) -> None:
    if target_dir.exists():
        raise FileExistsError(
            f"Refusing RN init: {target_dir} already exists (remove or pick another slug)."
        )
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    rn_latest = npm_dist_tags_latest("react-native")
    if not rn_latest:
        raise RuntimeError(
            "Could not read react-native latest version from https://registry.npmjs.org — check network.",
        )

    print(
        f"[RN] Scaffold with react-native@{rn_latest} (npm dist-tags.latest)…",
        flush=True,
    )
    _warn_node_if_old()

    cmd = [
        "npx",
        "--yes",
        "@react-native-community/cli@latest",
        "init",
        app_name_display,
        "--directory",
        str(target_dir.resolve()),
        "--pm",
        "npm",
        "--skip-git-init",
        "--skip-install",
        "--version",
        rn_latest,
    ]

    env = dict(os.environ)
    env.setdefault("CI", "true")
    env.setdefault("GIT_TERMINAL_PROMPT", "0")

    print(f"[RN] Running: {' '.join(cmd)}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(target_dir.parent),
        env=env,
        text=True,
        capture_output=False,
    )
    if proc.returncode != 0:
        print(
            f"[RN] react-native init failed with exit code {proc.returncode}.\n"
            "Ensure Node 20+, npm/npx OK, SDK licenses installed for Android builds.",
            file=sys.stderr,
            flush=True,
        )
        raise RuntimeError(f"react-native init exited {proc.returncode}")

    print("[RN] Running npm install in project…", flush=True)
    npm_i = subprocess.run(
        [npm_exec, "install"],
        cwd=str(target_dir.resolve()),
        env=env,
    )
    if npm_i.returncode != 0:
        raise RuntimeError(f"npm install failed with exit code {npm_i.returncode}")

    verify_rn_project_entrypoints(target_dir)


def verify_rn_project_entrypoints(build_root: Path) -> None:
    """Fail fast when Metro can't resolve `./index` (404 / UnableToResolveError on device)."""
    root = build_root.resolve()
    has_entry = (
        (root / "index.js").is_file()
        or (root / "index.tsx").is_file()
        or (root / "index.ts").is_file()
    )
    if not has_entry:
        raise RuntimeError(
            f"[RN] Missing Metro registry entry — expected index.js (or index.ts/x) under {root}. "
            "Folder looks incomplete; remove it and re-run build_app.py, then "
            "`cd Project/<slug> && npm start` from that project root (not parent folders)."
        )
    has_app = (root / "App.tsx").is_file() or (root / "App.js").is_file()
    if not has_app:
        raise RuntimeError(
            f"[RN] Missing App root — expected App.tsx or App.js under {root}. "
            "React Native CLI init appears incomplete."
        )
