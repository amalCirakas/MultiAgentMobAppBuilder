"""Blueprint rendering and Human-in-the-Loop approval gate for generated apps."""

from __future__ import annotations

import html
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = PROJECT_ROOT / "docs" / "blueprints" / "templates"
APPROVAL_ENV = "APPROVE_BLUEPRINTS"
DEFAULT_REVIEW_HOST = "127.0.0.1"
DEFAULT_REVIEW_PORT = 8765
DEFAULT_REVIEW_TIMEOUT_SECONDS = 60 * 60


def _title_from_slug(slug: str) -> str:
    words = [part for part in slug.replace("_", "-").split("-") if part]
    if not words:
        return "Generated App"
    return " ".join(word[:1].upper() + word[1:] for word in words)


def _block_text(value: str) -> str:
    lines = (value.strip() or "No prompt supplied.").splitlines()
    return "\n    ".join(line.rstrip() or " " for line in lines)


def _render_template(
    template: str,
    *,
    slug: str,
    prompt: str,
    stack: str,
    backend_runtime: str | None,
) -> str:
    replacements = {
        "{{APP_TITLE}}": _title_from_slug(slug),
        "{{APP_SLUG}}": slug,
        "{{APP_PROMPT_BLOCK}}": _block_text(prompt),
        "{{BUILD_STACK}}": stack,
        "{{BACKEND_RUNTIME}}": backend_runtime or "none",
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def _env_bool(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _read_preview(path: Path, *, limit: int = 120_000) -> str:
    text = path.read_text(encoding="utf-8")
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n# ... truncated in HITL preview; open the file for full content."


def render_app_blueprints(
    build_root: Path,
    *,
    slug: str,
    prompt: str,
    stack: str,
    backend_runtime: str | None = None,
) -> tuple[Path, Path]:
    """Render reviewed OpenAPI and AsyncAPI starter blueprints into Project/<slug>/docs."""
    output_dir = build_root / "docs" / "blueprints"
    output_dir.mkdir(parents=True, exist_ok=True)

    openapi = _render_template(
        (TEMPLATE_DIR / "openapi.yaml").read_text(encoding="utf-8"),
        slug=slug,
        prompt=prompt,
        stack=stack,
        backend_runtime=backend_runtime,
    )
    asyncapi = _render_template(
        (TEMPLATE_DIR / "asyncapi.yaml").read_text(encoding="utf-8"),
        slug=slug,
        prompt=prompt,
        stack=stack,
        backend_runtime=backend_runtime,
    )

    openapi_path = output_dir / "openapi.yaml"
    asyncapi_path = output_dir / "asyncapi.yaml"
    openapi_path.write_text(openapi, encoding="utf-8")
    asyncapi_path.write_text(asyncapi, encoding="utf-8")

    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# Blueprint Review",
                "",
                "These files are the source of truth for this generated app:",
                "",
                "- `openapi.yaml` defines the REST/API contract.",
                "- `asyncapi.yaml` defines the event and service workflow contract.",
                "",
                "Review these contracts before approving code generation. If implementation needs",
                "change, update the blueprint first and rebuild.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return openapi_path, asyncapi_path


class _HitlState:
    def __init__(
        self,
        *,
        openapi_path: Path,
        asyncapi_path: Path,
        app_title: str,
        slug: str,
        prompt: str,
        stack: str,
        backend_runtime: str | None,
    ) -> None:
        self.openapi_path = openapi_path
        self.asyncapi_path = asyncapi_path
        self.app_title = app_title
        self.slug = slug
        self.prompt = prompt
        self.stack = stack
        self.backend_runtime = backend_runtime or "none"
        self.event = threading.Event()
        self.decision: str | None = None
        self.reason = ""


def _render_review_page(state: _HitlState, review_url: str) -> bytes:
    openapi = html.escape(_read_preview(state.openapi_path))
    asyncapi = html.escape(_read_preview(state.asyncapi_path))
    prompt = html.escape(state.prompt.strip() or "No prompt supplied.")
    app_title = html.escape(state.app_title)
    slug = html.escape(state.slug)
    stack = html.escape(state.stack)
    backend_runtime = html.escape(state.backend_runtime)
    openapi_path = html.escape(str(state.openapi_path))
    asyncapi_path = html.escape(str(state.asyncapi_path))
    review_url_esc = html.escape(review_url)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>HITL Contract Review - {app_title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body {{
      margin: 0;
      background: Canvas;
      color: CanvasText;
    }}
    header {{
      border-bottom: 1px solid color-mix(in srgb, CanvasText 20%, transparent);
      padding: 24px;
    }}
    main {{
      display: grid;
      gap: 20px;
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }}
    .card {{
      border: 1px solid color-mix(in srgb, CanvasText 20%, transparent);
      border-radius: 12px;
      padding: 16px;
      background: color-mix(in srgb, Canvas 94%, CanvasText 6%);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }}
    pre {{
      overflow: auto;
      max-height: 520px;
      border-radius: 10px;
      padding: 14px;
      background: color-mix(in srgb, Canvas 88%, CanvasText 12%);
      white-space: pre-wrap;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }}
    button {{
      border: 0;
      border-radius: 10px;
      cursor: pointer;
      font-size: 16px;
      font-weight: 700;
      padding: 14px 18px;
    }}
    .approve {{ background: #15803d; color: white; }}
    .reject {{ background: #b91c1c; color: white; }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      position: sticky;
      bottom: 0;
      padding: 16px 0;
      background: Canvas;
    }}
    a {{ color: LinkText; }}
  </style>
</head>
<body>
  <header>
    <h1>Shift-Left HITL Contract Review</h1>
    <p>Parallel agents and code generation are blocked until a human architect approves these contracts.</p>
  </header>
  <main>
    <section class="card">
      <h2>{app_title}</h2>
      <p><strong>Slug:</strong> {slug}</p>
      <p><strong>Stack:</strong> {stack}</p>
      <p><strong>Backend runtime:</strong> {backend_runtime}</p>
      <p><strong>Review URL:</strong> <code>{review_url_esc}</code></p>
      <p><strong>OpenAPI:</strong> <code>{openapi_path}</code> (<a href="/openapi.yaml">open raw</a>)</p>
      <p><strong>AsyncAPI:</strong> <code>{asyncapi_path}</code> (<a href="/asyncapi.yaml">open raw</a>)</p>
    </section>

    <section class="card">
      <h2>Original App Prompt</h2>
      <pre><code>{prompt}</code></pre>
    </section>

    <section class="grid">
      <article class="card">
        <h2>openapi.yaml</h2>
        <pre><code>{openapi}</code></pre>
      </article>
      <article class="card">
        <h2>asyncapi.yaml</h2>
        <pre><code>{asyncapi}</code></pre>
      </article>
    </section>

    <section class="actions" aria-label="Contract decision">
      <form method="post" action="/approve">
        <button class="approve" type="submit">APPROVE CONTRACT</button>
      </form>
      <form method="post" action="/reject">
        <button class="reject" type="submit">REJECT CONTRACT</button>
      </form>
    </section>
  </main>
</body>
</html>
""".encode("utf-8")


def _make_handler(state: _HitlState, review_url_getter: callable):
    class HitlHandler(BaseHTTPRequestHandler):
        server_version = "BlueprintHITL/1.0"

        def log_message(self, fmt: str, *args: object) -> None:
            print(f"[HITL] {self.address_string()} - {fmt % args}", flush=True)

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path in {"/", "/index.html"}:
                self._send(200, _render_review_page(state, review_url_getter()), "text/html; charset=utf-8")
                return
            if self.path == "/openapi.yaml":
                self._send(
                    200,
                    state.openapi_path.read_bytes(),
                    "application/yaml; charset=utf-8",
                )
                return
            if self.path == "/asyncapi.yaml":
                self._send(
                    200,
                    state.asyncapi_path.read_bytes(),
                    "application/yaml; charset=utf-8",
                )
                return
            self._send(404, b"Not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:
            if self.path == "/approve":
                state.decision = "approved"
                state.event.set()
                self._send(
                    200,
                    b"<h1>Contract approved</h1><p>You can close this page. The build is continuing.</p>",
                    "text/html; charset=utf-8",
                )
                return
            if self.path == "/reject":
                state.decision = "rejected"
                state.event.set()
                self._send(
                    200,
                    b"<h1>Contract rejected</h1><p>You can close this page. The build has stopped before agents.</p>",
                    "text/html; charset=utf-8",
                )
                return
            self._send(404, b"Not found", "text/plain; charset=utf-8")

    return HitlHandler


def _bind_hitl_server(host: str, port: int, state: _HitlState) -> tuple[HTTPServer, str]:
    review_url_holder = {"url": ""}

    def get_review_url() -> str:
        return review_url_holder["url"]

    handler = _make_handler(state, get_review_url)
    try:
        server = HTTPServer((host, port), handler)
    except OSError:
        if port == 0:
            raise
        print(f"[HITL] Port {port} unavailable; falling back to an ephemeral port.", flush=True)
        server = HTTPServer((host, 0), handler)

    actual_host, actual_port = server.server_address
    url_host = "127.0.0.1" if actual_host in {"", "0.0.0.0"} else actual_host
    review_url_holder["url"] = f"http://{url_host}:{actual_port}/"
    return server, review_url_holder["url"]


def _post_hitl_webhook(*, webhook_url: str, review_url: str, state: _HitlState) -> None:
    payload = {
        "event": "contract_review_requested",
        "reviewUrl": review_url,
        "slug": state.slug,
        "appTitle": state.app_title,
        "stack": state.stack,
        "backendRuntime": state.backend_runtime,
        "openapiPath": str(state.openapi_path),
        "asyncapiPath": str(state.asyncapi_path),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "multiAgentApp-HITL/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[HITL] Webhook delivered: HTTP {resp.status}", flush=True)
    except (OSError, urllib.error.URLError) as exc:
        print(f"[HITL] Webhook delivery failed: {exc}", flush=True)


def _serve_hitl_review(
    *,
    openapi_path: Path,
    asyncapi_path: Path,
    slug: str,
    prompt: str,
    stack: str,
    backend_runtime: str | None,
) -> None:
    host = os.getenv("HITL_REVIEW_HOST", DEFAULT_REVIEW_HOST).strip() or DEFAULT_REVIEW_HOST
    port = _env_int("HITL_REVIEW_PORT", DEFAULT_REVIEW_PORT)
    timeout_seconds = max(1, _env_int("HITL_REVIEW_TIMEOUT_SECONDS", DEFAULT_REVIEW_TIMEOUT_SECONDS))
    open_browser = _env_bool("HITL_OPEN_BROWSER", default=True)

    state = _HitlState(
        openapi_path=openapi_path,
        asyncapi_path=asyncapi_path,
        app_title=_title_from_slug(slug),
        slug=slug,
        prompt=prompt,
        stack=stack,
        backend_runtime=backend_runtime,
    )
    server, review_url = _bind_hitl_server(host, port, state)

    thread = threading.Thread(target=server.serve_forever, name="hitl-review-server", daemon=True)
    thread.start()

    print("\n[HITL] Contract review webpage is ready.", flush=True)
    print(f"[HITL] Review URL: {review_url}", flush=True)
    print("[HITL] Build is physically paused before backend scaffold and CrewAI.", flush=True)
    print("[HITL] Click APPROVE CONTRACT in the browser to continue.", flush=True)

    webhook_url = os.getenv("HITL_WEBHOOK_URL", "").strip()
    if webhook_url:
        _post_hitl_webhook(webhook_url=webhook_url, review_url=review_url, state=state)

    if open_browser:
        webbrowser.open(review_url)

    try:
        deadline = time.monotonic() + timeout_seconds
        while not state.event.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"HITL contract review timed out after {timeout_seconds} seconds."
                )
            state.event.wait(timeout=min(1.0, remaining))

        if state.decision == "approved":
            print("[HITL] Contract approved by human architect.", flush=True)
            return
        raise RuntimeError("Contract rejected by human architect; stopping before code generation.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def require_blueprint_approval(
    *,
    openapi_path: Path,
    asyncapi_path: Path,
    non_interactive: bool,
    approved_flag: bool,
    slug: str = "generated-app",
    prompt: str = "",
    stack: str = "frontend",
    backend_runtime: str | None = None,
) -> None:
    """Stop builds at the source-of-truth review point unless explicitly approved."""
    approved_env = os.getenv(APPROVAL_ENV, "").strip().lower() in {"1", "true", "yes", "y"}
    if approved_flag or approved_env:
        print("[BLUEPRINT] Approval supplied; continuing.", flush=True)
        return

    if non_interactive:
        print("[BLUEPRINT] Non-interactive build is waiting on HITL browser approval.", flush=True)

    _serve_hitl_review(
        openapi_path=openapi_path,
        asyncapi_path=asyncapi_path,
        slug=slug,
        prompt=prompt,
        stack=stack,
        backend_runtime=backend_runtime,
    )


def main() -> int:
    if len(sys.argv) < 5:
        print(
            "Usage: python3 blueprint_gate.py BUILD_ROOT SLUG STACK PROMPT [BACKEND_RUNTIME]",
            file=sys.stderr,
        )
        return 2
    build_root = Path(sys.argv[1]).resolve()
    slug = sys.argv[2]
    stack = sys.argv[3]
    prompt = sys.argv[4]
    backend_runtime = sys.argv[5] if len(sys.argv) > 5 else None
    openapi_path, asyncapi_path = render_app_blueprints(
        build_root,
        slug=slug,
        prompt=prompt,
        stack=stack,
        backend_runtime=backend_runtime,
    )
    print(openapi_path)
    print(asyncapi_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
