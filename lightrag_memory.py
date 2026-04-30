#!/usr/bin/env python3
"""LightRAG topological memory tooling for generated app contracts."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_LIGHTRAG_URL = "http://127.0.0.1:9621"


def _base_url() -> str:
    return os.getenv("LIGHTRAG_URL", DEFAULT_LIGHTRAG_URL).rstrip("/")


def _api_key() -> str:
    return os.getenv("LIGHTRAG_API_KEY", "").strip()


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    key = _api_key()
    if key:
        headers["X-API-Key"] = key
    return headers


def _request_json(method: str, path: str, payload: dict[str, Any] | None = None, *, timeout: float = 30.0) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{_base_url()}{path}",
        data=data,
        headers=_headers(),
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw


def health() -> bool:
    try:
        _request_json("GET", "/health", timeout=5.0)
        return True
    except Exception:
        return False


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _extract_openapi_operations(text: str) -> list[str]:
    operations: list[str] = []
    current_path = ""
    for line in text.splitlines():
        path_match = re.match(r"^  (/[^:]+):\s*$", line)
        if path_match:
            current_path = path_match.group(1)
            continue
        method_match = re.match(r"^    (get|post|put|patch|delete|options|head):\s*$", line)
        if current_path and method_match:
            operations.append(f"{method_match.group(1).upper()} {current_path}")
    return operations


def _extract_openapi_schemas(text: str) -> list[str]:
    schemas: list[str] = []
    in_schemas = False
    for line in text.splitlines():
        if line.strip() == "schemas:":
            in_schemas = True
            continue
        if in_schemas:
            match = re.match(r"^    ([A-Za-z0-9_.-]+):\s*$", line)
            if match:
                schemas.append(match.group(1))
            elif line and not line.startswith(" "):
                break
    return schemas


def _extract_asyncapi_channels(text: str) -> list[str]:
    channels: list[str] = []
    in_channels = False
    for line in text.splitlines():
        if line.strip() == "channels:":
            in_channels = True
            continue
        if in_channels:
            match = re.match(r"^  ([A-Za-z0-9_.-]+):\s*$", line)
            if match:
                channels.append(match.group(1))
            elif line and not line.startswith(" "):
                break
    return channels


def _extract_asyncapi_messages(text: str) -> list[str]:
    messages: list[str] = []
    in_messages = False
    for line in text.splitlines():
        if line.strip() == "messages:":
            in_messages = True
            continue
        if in_messages:
            match = re.match(r"^    ([A-Za-z0-9_.-]+):\s*$", line)
            if match:
                messages.append(match.group(1))
            elif line and not line.startswith(" "):
                in_messages = False
    return messages


def build_memory_packet(build_root: Path) -> str:
    root = build_root.resolve()
    manifest = _json_optional(root / "build-manifest.json")
    openapi_path = root / "docs" / "blueprints" / "openapi.yaml"
    asyncapi_path = root / "docs" / "blueprints" / "asyncapi.yaml"
    langgraph_summary = _read_optional(root / "docs" / "langgraph-summary.md")
    openapi = _read_optional(openapi_path)
    asyncapi = _read_optional(asyncapi_path)

    slug = str(manifest.get("slug") or root.name)
    stack = str(manifest.get("stack") or "unknown")
    backend_runtime = str(manifest.get("backend_runtime") or "none")
    prompt = str(manifest.get("prompt") or "")

    operations = _extract_openapi_operations(openapi)
    schemas = _extract_openapi_schemas(openapi)
    channels = _extract_asyncapi_channels(asyncapi)
    messages = _extract_asyncapi_messages(asyncapi)

    lines = [
        "# Topological System Memory Packet",
        "",
        f"- App slug: `{slug}`",
        f"- Build root: `{root}`",
        f"- Stack: `{stack}`",
        f"- Backend runtime: `{backend_runtime}`",
        f"- Source OpenAPI: `{openapi_path}`",
        f"- Source AsyncAPI: `{asyncapi_path}`",
        "",
        "## App Prompt",
        prompt or "(no prompt recorded)",
        "",
        "## REST Surface",
        *(f"- `{op}`" for op in operations),
        "",
        "## REST Schemas",
        *(f"- `{schema}`" for schema in schemas),
        "",
        "## Async Channels",
        *(f"- `{channel}`" for channel in channels),
        "",
        "## Async Messages",
        *(f"- `{message}`" for message in messages),
        "",
        "## LangGraph / HITL Summary",
        langgraph_summary.strip() or "(no LangGraph summary found)",
        "",
        "## Full OpenAPI Contract",
        "```yaml",
        openapi.strip() or "# missing openapi.yaml",
        "```",
        "",
        "## Full AsyncAPI Contract",
        "```yaml",
        asyncapi.strip() or "# missing asyncapi.yaml",
        "```",
    ]
    return "\n".join(lines) + "\n"


def ingest_build_root(build_root: Path) -> Any:
    packet = build_memory_packet(build_root)
    description = f"Day 1 contracts for {build_root.resolve().name}"
    return _request_json(
        "POST",
        "/documents/text",
        {"text": packet, "description": description},
        timeout=float(os.getenv("LIGHTRAG_INGEST_TIMEOUT_SECONDS", "120")),
    )


def query_memory(question: str, *, mode: str = "hybrid", only_need_context: bool = True) -> Any:
    return _request_json(
        "POST",
        "/query",
        {"query": question, "mode": mode, "only_need_context": only_need_context},
        timeout=float(os.getenv("LIGHTRAG_QUERY_TIMEOUT_SECONDS", "45")),
    )


def try_ingest_build_root(build_root: Path, *, require: bool = False) -> bool:
    if os.getenv("SKIP_LIGHTRAG_MEMORY", "").strip().lower() in {"1", "true", "yes", "on"}:
        print("[LIGHTRAG] SKIP_LIGHTRAG_MEMORY=1 - skipping topological memory ingest.", flush=True)
        return True
    try:
        ingest_build_root(build_root)
        print(f"[LIGHTRAG] Ingested approved contracts for {build_root}.", flush=True)
        return True
    except Exception as exc:
        msg = f"[LIGHTRAG] Memory ingest failed: {exc}"
        if require:
            raise RuntimeError(msg) from exc
        print(msg, flush=True)
        print("[LIGHTRAG] Continuing build. Set REQUIRE_LIGHTRAG_MEMORY=1 to make this fatal.", flush=True)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="LightRAG topological memory for generated contracts.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="Check LightRAG server health.")

    packet_parser = sub.add_parser("build-packet", help="Render a memory packet without ingesting it.")
    packet_parser.add_argument("--build-root", required=True)

    ingest_parser = sub.add_parser("ingest", help="Ingest generated app contracts into LightRAG.")
    ingest_parser.add_argument("--build-root", required=True)

    query_parser = sub.add_parser("query", help="Query LightRAG memory.")
    query_parser.add_argument("question")
    query_parser.add_argument("--mode", default="hybrid", choices=["naive", "local", "global", "hybrid", "mix"])
    query_parser.add_argument("--full-response", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "health":
            ok = health()
            print("ok" if ok else "unreachable")
            return 0 if ok else 1
        if args.command == "build-packet":
            print(build_memory_packet(Path(args.build_root)), end="")
            return 0
        if args.command == "ingest":
            result = ingest_build_root(Path(args.build_root))
            print(json.dumps(result, indent=2) if not isinstance(result, str) else result)
            return 0
        if args.command == "query":
            result = query_memory(args.question, mode=args.mode, only_need_context=not args.full_response)
            if isinstance(result, dict):
                print(result.get("response") or result.get("data") or json.dumps(result, indent=2))
            else:
                print(result)
            return 0
    except (OSError, urllib.error.URLError, RuntimeError) as exc:
        print(f"[LIGHTRAG] {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
