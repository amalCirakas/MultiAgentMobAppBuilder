import os
from pathlib import Path
from typing import Dict, TypedDict

from langgraph.graph import END, START, StateGraph

PROJECT_ROOT = Path(__file__).resolve().parent
DOCS_DIR = PROJECT_ROOT / "docs"

MODULE_CONFIGS: Dict[str, Dict[str, str]] = {
    "patients": {"display_name": "Patient Registration and Profile"},
    "appointments": {"display_name": "Appointments and Scheduling"},
    "vitals": {"display_name": "Vitals and Nursing Notes"},
    "admission": {"display_name": "Admission, Discharge, and Bed Management"},
    "billing": {"display_name": "Billing and Invoices"},
    "pharmacy": {"display_name": "Pharmacy and Prescriptions"},
    "labs": {"display_name": "Lab Orders and Results"},
    "auth": {"display_name": "Authentication and Role Based Access"},
}


class WorkflowState(TypedDict):
    module: str


def _pass_through(state: WorkflowState) -> WorkflowState:
    return state


def get_module() -> str:
    module = os.getenv("MODULE", "patients").strip().lower()
    if module not in MODULE_CONFIGS:
        options = ", ".join(sorted(MODULE_CONFIGS.keys()))
        raise SystemExit(f"Unsupported MODULE '{module}'. Use one of: {options}")
    return module


def build_graph():
    builder = StateGraph(WorkflowState)
    builder.add_node("contract_architect", _pass_through)
    builder.add_node("validation", _pass_through)
    builder.add_node("data_layer", _pass_through)
    builder.add_node("ui", _pass_through)
    builder.add_node("qa", _pass_through)
    builder.add_node("workflow_reporter", _pass_through)

    builder.add_edge(START, "contract_architect")
    builder.add_edge("contract_architect", "validation")
    builder.add_edge("contract_architect", "data_layer")
    builder.add_edge("validation", "ui")
    builder.add_edge("data_layer", "ui")
    builder.add_edge("ui", "qa")
    builder.add_edge("qa", "workflow_reporter")
    builder.add_edge("workflow_reporter", END)
    return builder.compile()


def main() -> int:
    module = get_module()
    display_name = MODULE_CONFIGS[module]["display_name"]
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    graph = build_graph()
    drawable = graph.get_graph()
    mermaid_text = drawable.draw_mermaid()

    module_mermaid_path = DOCS_DIR / f"langgraph-workflow-{module}.mmd"
    latest_mermaid_path = DOCS_DIR / "langgraph-workflow.mmd"
    module_mermaid_path.write_text(mermaid_text, encoding="utf-8")
    latest_mermaid_path.write_text(mermaid_text, encoding="utf-8")
    print(f"[LANGGRAPH] Mermaid saved: {module_mermaid_path}")
    print(f"[LANGGRAPH] Mermaid alias saved: {latest_mermaid_path}")

    # PNG generation may fail if rendering dependencies are unavailable.
    try:
        png_bytes = drawable.draw_mermaid_png()
        module_png_path = DOCS_DIR / f"langgraph-workflow-{module}.png"
        latest_png_path = DOCS_DIR / "langgraph-workflow.png"
        module_png_path.write_bytes(png_bytes)
        latest_png_path.write_bytes(png_bytes)
        print(f"[LANGGRAPH] PNG saved: {module_png_path}")
        print(f"[LANGGRAPH] PNG alias saved: {latest_png_path}")
    except Exception as exc:
        print(f"[LANGGRAPH] PNG generation skipped: {type(exc).__name__}: {exc}")

    summary_path = DOCS_DIR / "langgraph-summary.md"
    summary_path.write_text(
        "\n".join(
            [
                "# LangGraph Workflow Summary",
                "",
                f"- Module: `{module}`",
                f"- Name: {display_name}",
                "- Nodes: contract_architect, validation, data_layer, ui, qa, workflow_reporter",
                f"- Mermaid: `{module_mermaid_path.relative_to(PROJECT_ROOT)}`",
            ]
        ),
        encoding="utf-8",
    )
    print(f"[LANGGRAPH] Summary saved: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
