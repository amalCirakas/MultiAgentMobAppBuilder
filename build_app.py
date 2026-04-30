#!/usr/bin/env python3
"""
Terminal entrypoint: scaffold React Native (TypeScript), export LangGraph (stack + crew)
into Project/<slug>/docs immediately after init, optionally scaffold backend, write manifest,
run CrewAI codegen into BUILD_ROOT.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from backend_scaffold import scaffold_java_spring_boot, scaffold_node_server
from rn_init import (
    TEMPLATE,
    patch_android_gradle_properties,
    patch_android_sdk_versions,
    patch_org_gradle_java_home,
    react_native_init,
    read_rn_version,
)

PROJECT_DIR = Path(__file__).resolve().parent / "Project"

STACK_CHOICES = ("frontend", "backend", "fullstack", "mobile")
BACKEND_RUNTIME_CHOICES = ("node", "java")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return "app-build"
    return text[:48].strip("-")


def slug_to_rn_app_name(slug: str) -> str:
    """Convert kebab slug to PascalCase for `react-native init` app name."""
    parts = [p for p in re.split(r"[-_\s]+", slug.strip()) if p]
    if not parts:
        return "GeneratedApp"
    return "".join(p[:1].upper() + p[1:].lower() for p in parts)


def pick_unique_slug(base: str) -> str:
    candidate = base
    n = 2
    while (PROJECT_DIR / candidate).exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def prompt_for_text(message: str, default: str | None = None) -> str:
    if default:
        raw = input(f"{message} [{default}]: ").strip()
        return raw or default
    return input(f"{message}: ").strip()


SPECS_PROMPT = (
    "Describe your app (features, audiences, offline/sync, backends, platforms, anything relevant)"
)


def prompt_for_specs() -> str:
    return prompt_for_text(SPECS_PROMPT).strip()


def prompt_project_folder_name() -> str:
    """Return raw user input; caller runs slugify + pick_unique_slug."""
    return prompt_for_text(
        "Project folder name (stored as Project/<name>/ — sanitized to a safe folder name)"
    )


def prompt_for_stack() -> str:
    print("\nSelect target stack surface:")
    for i, name in enumerate(STACK_CHOICES, start=1):
        print(f"  {i}) {name}")
    while True:
        raw = input("Enter number (1-4): ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(STACK_CHOICES):
                return STACK_CHOICES[idx - 1]
        print("Please enter 1, 2, 3, or 4.")


def prompt_backend_runtime() -> str:
    print("\nBackend runtime (REST scaffold):")
    for i, name in enumerate(BACKEND_RUNTIME_CHOICES, start=1):
        print(f"  {i}) {name}")
    while True:
        raw = input("Enter number (1-2): ").strip()
        if raw == "1":
            return "node"
        if raw == "2":
            return "java"
        print("Please enter 1 or 2.")


def needs_backend_scaffold(stack: str) -> bool:
    return stack in ("backend", "fullstack")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold React Native (TS) under Project/<slug>/, LangGraph, optional backend, then Crew codegen."
        )
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="App specs for agents (positional). With -y, required alongside --slug/--name and --stack.",
    )
    parser.add_argument(
        "--stack",
        choices=STACK_CHOICES,
        default=None,
        help="Target stack (skip interactive prompt when set)",
    )
    parser.add_argument(
        "--slug",
        "--name",
        dest="slug",
        metavar="folder",
        default=None,
        help="Folder under Project/ (sanitize to kebab-case). Alias: --name. Required with -y.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Non-interactive: require PROMPT positional, --stack, --slug|--name (and --backend-runtime if backend/fullstack).",
    )
    parser.add_argument(
        "--backend-runtime",
        choices=BACKEND_RUNTIME_CHOICES,
        default=None,
        help="Backend scaffold: node (Express) or java (Spring Boot); required with -y when --stack is backend or fullstack",
    )
    parser.add_argument(
        "--approve-blueprints",
        action="store_true",
        help="Approve generated OpenAPI/AsyncAPI source-of-truth contracts and continue past the shift-left gate.",
    )
    args = parser.parse_args()

    os.environ.pop("BACKEND_RUNTIME", None)

    cli_slug = (args.slug or "").strip()

    prompt = (args.prompt or "").strip()
    if not prompt:
        if args.yes:
            print(
                "[ERROR] Non-interactive mode requires PROMPT positional (app specs for agents).",
                file=sys.stderr,
            )
            return 1
        prompt = prompt_for_specs().strip()

    if not prompt:
        print("[ERROR] App specs prompt is empty.", file=sys.stderr)
        return 1

    # Non-interactive must name the folder explicitly (no prompt-derived slug)
    if args.yes and not cli_slug:
        print("[ERROR] Non-interactive mode requires --slug FOLDERNAME (folder under Project/) or --name.", file=sys.stderr)
        return 1

    # Resolve slug: CLI override or interactive project-folder prompt
    if cli_slug:
        slug = slugify(cli_slug)
        if (PROJECT_DIR / slug).exists():
            print(
                f"[ERROR] Project/{slug} already exists. Choose a different --slug / --name.",
                file=sys.stderr,
            )
            return 1
    else:
        raw_name = prompt_project_folder_name().strip()
        base = slugify(raw_name) if raw_name else "app-build"
        slug = pick_unique_slug(base)

    stack = args.stack
    if not stack:
        if args.yes:
            print("[ERROR] Non-interactive mode requires --stack.", file=sys.stderr)
            return 1
        stack = prompt_for_stack()

    backend_runtime: str | None = None
    if needs_backend_scaffold(stack):
        if args.yes:
            if not args.backend_runtime:
                print(
                    "[ERROR] Non-interactive mode with backend/fullstack requires --backend-runtime node|java.",
                    file=sys.stderr,
                )
                return 1
            backend_runtime = args.backend_runtime
        else:
            backend_runtime = args.backend_runtime or prompt_backend_runtime()

    build_root = (PROJECT_DIR / slug).resolve()
    rn_app_name = slug_to_rn_app_name(slug)

    try:
        from rn_metro_guard import guard_stale_metro

        guard_stale_metro(build_root)
    except Exception as exc:
        print(f"[METRO-GUARD] {exc}", file=sys.stderr)
        return 1

    # 1) React Native CLI — creates build_root directory
    try:
        react_native_init(app_name_display=rn_app_name, target_dir=build_root)
    except Exception as exc:
        print(f"[RN] Failed: {exc}", file=sys.stderr)
        return 1

    # LangGraph first in the new tree (stack + crew codegen DAG) so docs exist even if later steps fail.
    from build_graph_export import export_build_graph_docs

    docs_dir = build_root / "docs"
    try:
        mmd_path, png_path = export_build_graph_docs(docs_dir, stack=stack, slug=slug)
    except Exception as exc:
        print(f"[LANGGRAPH] Failed: {exc}", file=sys.stderr)
        return 1
    print(f"[LANGGRAPH] Stack Mermaid: {mmd_path}")
    if png_path:
        print(f"[LANGGRAPH] Stack PNG: {png_path}")
    crew_mmd = docs_dir / "langgraph-crew-codegen.mmd"
    if crew_mmd.is_file():
        print(f"[LANGGRAPH] Crew codegen Mermaid: {crew_mmd}")

    from blueprint_gate import render_app_blueprints, require_blueprint_approval

    try:
        openapi_path, asyncapi_path = render_app_blueprints(
            build_root,
            slug=slug,
            prompt=prompt,
            stack=stack,
            backend_runtime=backend_runtime,
        )
        print(f"[BLUEPRINT] OpenAPI: {openapi_path}")
        print(f"[BLUEPRINT] AsyncAPI: {asyncapi_path}")
        require_blueprint_approval(
            openapi_path=openapi_path,
            asyncapi_path=asyncapi_path,
            non_interactive=args.yes,
            approved_flag=args.approve_blueprints,
            slug=slug,
            prompt=prompt,
            stack=stack,
            backend_runtime=backend_runtime,
        )
    except Exception as exc:
        print(f"[BLUEPRINT] {exc}", file=sys.stderr)
        return 1

    rn_hint = read_rn_version(build_root)
    patch_android_gradle_properties(build_root)
    patch_android_sdk_versions(build_root)
    patch_org_gradle_java_home(build_root)

    if stack == "fullstack" and backend_runtime == "node":
        from rn_api_config import write_builder_api_config
        from rn_android_dev_network import ensure_android_http_debug_manifest

        write_builder_api_config(build_root)
        dbg = ensure_android_http_debug_manifest(build_root)
        if dbg:
            print(f"[BUILD] Android dev HTTP manifest merge: {dbg}")

    backend_paths: dict[str, str] = {}

    # 2) Backend scaffold (node or java alongside RN)
    if backend_runtime == "node":
        p = scaffold_node_server(build_root, notes_api=(stack == "fullstack"))
        backend_paths["node_server"] = str(p.relative_to(build_root))
    elif backend_runtime == "java":
        p = scaffold_java_spring_boot(build_root)
        backend_paths["java_backend"] = str(p.relative_to(build_root))

    # 3) Manifest — after scaffolding
    manifest: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "slug": slug,
        "prompt": prompt,
        "stack": stack,
        "build_root": str(build_root),
        "rn_app_name": rn_app_name,
        "rn_template": TEMPLATE,
        "react_native_version": rn_hint,
    }
    if backend_runtime:
        manifest["backend_runtime"] = backend_runtime
        manifest["backend_paths"] = backend_paths

    manifest_path = build_root / "build-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[BUILD] Manifest: {manifest_path}")

    os.environ["BUILD_ROOT"] = str(build_root)
    os.environ["APP_PROMPT"] = prompt
    os.environ["BUILD_STACK"] = stack
    os.environ["MODULE"] = "builder"
    os.environ["BUILDER_MODE"] = "1"
    if backend_runtime:
        os.environ["BACKEND_RUNTIME"] = backend_runtime

    print(f"[BUILD] Starting CrewAI pipeline in BUILD_ROOT={build_root}")

    import crew as crew_module

    code = int(crew_module.main())
    if code != 0:
        return code

    from notes_stack_wire import wire_fullstack_notes_stack
    from notes_template_verify import verify_notes_templates
    from rn_wire_app import sanitize_generated_accessibility, wire_builder_app_tsx

    wire_fullstack_notes_stack(build_root)
    if stack == "fullstack" and backend_runtime == "node":
        try:
            verify_notes_templates(build_root)
        except Exception as exc:
            print(f"[BUILD ERROR] {exc}", file=sys.stderr)
            return 1
    sanitize_generated_accessibility(build_root)

    if wire_builder_app_tsx(build_root):
        docs_sum = build_root / "docs" / "module-summary.md"
        if docs_sum.is_file():
            sep = docs_sum.read_text(encoding="utf-8").rstrip()
            marker = "**Wired:** root `App.tsx`"
            if marker not in sep:
                docs_sum.write_text(
                    sep
                    + "\n\n- "
                    + marker
                    + " imports `./src/screens/AppScreen` after codegen.\n",
                    encoding="utf-8",
                )

    if stack == "fullstack" and backend_runtime == "node":
        try:
            from fullstack_runtime_verify import verify_fullstack_node_notes_api

            verify_fullstack_node_notes_api(build_root)
        except Exception as exc:
            print(f"[BUILD ERROR] {exc}", file=sys.stderr)
            return 1

    try:
        from rn_bundle_verify import verify_rn_android_bundle_smoke

        verify_rn_android_bundle_smoke(build_root)
    except Exception as exc:
        print(f"[BUILD ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
