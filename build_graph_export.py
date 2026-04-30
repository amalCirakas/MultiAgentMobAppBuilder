"""
Export a stack-specific LangGraph (Mermaid + optional PNG) for a terminal-driven build.

This does not execute LLMs; it only compiles a graph model and renders artifacts,
matching the existing langgraph_visualize.py behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph


class StackBuildState(TypedDict):
    """Minimal state for visualization-only graphs."""

    stack: str
    slug: str


def _pass_through(state: StackBuildState) -> StackBuildState:
    return state


def _linear_chain(
    node_names: list[str],
) -> Callable[[StateGraph[StackBuildState, StackBuildState, StackBuildState]], None]:
    def _wire(builder: StateGraph[StackBuildState, StackBuildState, StackBuildState]) -> None:
        for name in node_names:
            builder.add_node(name, _pass_through)
        builder.add_edge(START, node_names[0])
        for a, b in zip(node_names, node_names[1:]):
            builder.add_edge(a, b)
        builder.add_edge(node_names[-1], END)

    return _wire


def build_compiled_graph_for_stack(stack: str) -> object:
    """Return a compiled LangGraph whose structure depends on stack surface."""
    stack_l = stack.strip().lower()
    builder = StateGraph(StackBuildState)

    if stack_l == "frontend":
        _linear_chain(["spec", "scaffold", "blueprints", "human_contract_review", "ui", "tests"])(builder)
    elif stack_l == "backend":
        _linear_chain(["spec", "scaffold", "blueprints", "human_contract_review", "api", "data", "tests"])(builder)
    elif stack_l == "fullstack":
        _linear_chain(
            ["spec", "scaffold", "blueprints", "human_contract_review", "backend", "frontend", "integration", "tests"]
        )(builder)
    elif stack_l == "mobile":
        _linear_chain(["spec", "scaffold", "blueprints", "human_contract_review", "rn_ui", "tests"])(builder)
    else:
        raise ValueError(f"Unsupported stack '{stack}' for LangGraph export")

    return builder.compile()


def _export_crew_codegen_graph_mermaid(docs_dir: Path) -> tuple[Path, Path | None]:
    """
    Same DAG as `langgraph_visualize.py` (contract_architect → … → workflow_reporter).
    """
    from langgraph_visualize import build_graph

    graph = build_graph()
    drawable = graph.get_graph()
    mermaid_text = drawable.draw_mermaid()
    crew_path = docs_dir / "langgraph-crew-codegen.mmd"
    crew_path.write_text(mermaid_text, encoding="utf-8")
    crew_png: Path | None = None
    try:
        png_bytes = drawable.draw_mermaid_png()
        crew_png = docs_dir / "langgraph-crew-codegen.png"
        crew_png.write_bytes(png_bytes)
    except Exception:
        crew_png = None
    return crew_path, crew_png


def export_build_graph_docs(
    docs_dir: Path,
    *,
    stack: str,
    slug: str,
) -> tuple[Path, Path | None]:
    """
    Write stack pipeline Mermaid/PNG, crew-codegen LangGraph Mermaid/PNG, and summary under docs_dir.

    Stack artifacts: langgraph-build.mmd, langgraph-workflow.mmd (alias), matching PNGs when rendering works.
    Crew artifacts: langgraph-crew-codegen.mmd (+ optional PNG), same structure as repo `langgraph_visualize.py`.

    Returns (stack_mermaid_path, stack_png_path_or_none).
    """
    docs_dir = docs_dir.resolve()
    docs_dir.mkdir(parents=True, exist_ok=True)

    graph = build_compiled_graph_for_stack(stack)
    drawable = graph.get_graph()
    mermaid_text = drawable.draw_mermaid()

    build_path = docs_dir / "langgraph-build.mmd"
    alias_path = docs_dir / "langgraph-workflow.mmd"
    build_path.write_text(mermaid_text, encoding="utf-8")
    alias_path.write_text(mermaid_text, encoding="utf-8")

    png_path: Path | None = None
    try:
        png_bytes = drawable.draw_mermaid_png()
        png_path = docs_dir / "langgraph-build.png"
        png_path.write_bytes(png_bytes)
        (docs_dir / "langgraph-workflow.png").write_bytes(png_bytes)
    except Exception:
        png_path = None

    crew_mmd, crew_png = _export_crew_codegen_graph_mermaid(docs_dir)

    summary = docs_dir / "langgraph-summary.md"
    summary_lines = [
        "# LangGraph (build output)",
        "",
        f"- Slug: `{slug}`",
        f"- Stack: `{stack}`",
        "",
        "## Stack pipeline",
        f"- Mermaid: `{build_path.name}`",
        f"- Alias: `{alias_path.name}`",
        f"- PNG: `{png_path.name}`" if png_path else "- PNG: (skipped — renderer unavailable)",
        "",
        "## Crew codegen workflow",
        f"- Mermaid: `{crew_mmd.name}`",
        f"- PNG: `{crew_png.name}`" if crew_png else "- PNG: (skipped — renderer unavailable)",
        "",
        "Exported at the start of the app folder lifecycle. The `human_contract_review` node is a blocking HITL pause before backend scaffold and CrewAI.",
    ]
    summary.write_text("\n".join(summary_lines), encoding="utf-8")

    return build_path, png_path
