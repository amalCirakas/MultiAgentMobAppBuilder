import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

from crewai import Agent, Crew, LLM, Process, Task
from crewai_tools import FileWriterTool
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")
REQUIRED_FOLDERS = [
    "_contracts",
    "src/db",
    "src/screens",
    "src/validation",
    "src/navigation",
    "src/components",
    "src/store",
    "e2e",
    "docs",
]

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

MODULE_CONFIGS: Dict[str, Dict[str, object]] = {
    "patients": {
        "display_name": "Patient Registration and Profile",
        "feature_slug": "patient",
        "screen_name": "PatientRegistrationScreen",
        "contracts_path": "_contracts/patient.types.ts",
        "validation_path": "src/validation/patientValidation.ts",
        "service_path": "src/db/patientService.ts",
        "screen_path": "src/screens/PatientRegistrationScreen.tsx",
        "qa_path": "e2e/patient-registration.e2e.ts",
        "workflow_path": "docs/workflow-patients.mmd",
        "contracts_desc": "PatientProfile, EmergencyContact, InsuranceInfo, and PatientSyncIntent",
        "service_functions": "createPatient, updatePatient, queuePatientSync",
        "screen_focus": "patient registration form and profile update flow",
    },
    "appointments": {
        "display_name": "Appointments and Scheduling",
        "feature_slug": "appointment",
        "screen_name": "AppointmentSchedulingScreen",
        "contracts_path": "_contracts/appointment.types.ts",
        "validation_path": "src/validation/appointmentValidation.ts",
        "service_path": "src/db/appointmentService.ts",
        "screen_path": "src/screens/AppointmentSchedulingScreen.tsx",
        "qa_path": "e2e/appointment-scheduling.e2e.ts",
        "workflow_path": "docs/workflow-appointments.mmd",
        "contracts_desc": "Appointment, ProviderSlot, and AppointmentSyncIntent",
        "service_functions": "createAppointment, rescheduleAppointment, queueAppointmentSync",
        "screen_focus": "book and reschedule appointment flow",
    },
    "vitals": {
        "display_name": "Vitals and Nursing Notes",
        "feature_slug": "vitals",
        "screen_name": "VitalsEntryScreen",
        "contracts_path": "_contracts/vitals.types.ts",
        "validation_path": "src/validation/vitalsValidation.ts",
        "service_path": "src/db/vitalsService.ts",
        "screen_path": "src/screens/VitalsEntryScreen.tsx",
        "qa_path": "e2e/vitals-entry.e2e.ts",
        "workflow_path": "docs/workflow-vitals.mmd",
        "contracts_desc": "VitalsRecord, NursingNote, and VitalsSyncIntent",
        "service_functions": "createVitalsRecord, addNursingNote, queueVitalsSync",
        "screen_focus": "vitals capture and nursing note entry flow",
    },
    "admission": {
        "display_name": "Admission, Discharge, and Bed Management",
        "feature_slug": "admission",
        "screen_name": "AdmissionManagementScreen",
        "contracts_path": "_contracts/admission.types.ts",
        "validation_path": "src/validation/admissionValidation.ts",
        "service_path": "src/db/admissionService.ts",
        "screen_path": "src/screens/AdmissionManagementScreen.tsx",
        "qa_path": "e2e/admission-management.e2e.ts",
        "workflow_path": "docs/workflow-admission.mmd",
        "contracts_desc": "AdmissionRecord, DischargeSummary, BedAllocation, and AdmissionSyncIntent",
        "service_functions": "admitPatient, dischargePatient, queueAdmissionSync",
        "screen_focus": "admission and bed allocation workflow",
    },
    "billing": {
        "display_name": "Billing and Invoices",
        "feature_slug": "billing",
        "screen_name": "BillingScreen",
        "contracts_path": "_contracts/billing.types.ts",
        "validation_path": "src/validation/billingValidation.ts",
        "service_path": "src/db/billingService.ts",
        "screen_path": "src/screens/BillingScreen.tsx",
        "qa_path": "e2e/billing.e2e.ts",
        "workflow_path": "docs/workflow-billing.mmd",
        "contracts_desc": "Invoice, BillingLineItem, and BillingSyncIntent",
        "service_functions": "createInvoice, updateInvoiceStatus, queueBillingSync",
        "screen_focus": "invoice creation and payment status workflow",
    },
    "pharmacy": {
        "display_name": "Pharmacy and Prescriptions",
        "feature_slug": "pharmacy",
        "screen_name": "PharmacyScreen",
        "contracts_path": "_contracts/pharmacy.types.ts",
        "validation_path": "src/validation/pharmacyValidation.ts",
        "service_path": "src/db/pharmacyService.ts",
        "screen_path": "src/screens/PharmacyScreen.tsx",
        "qa_path": "e2e/pharmacy.e2e.ts",
        "workflow_path": "docs/workflow-pharmacy.mmd",
        "contracts_desc": "Prescription, Medication, and PharmacySyncIntent",
        "service_functions": "createPrescription, markMedicationDispensed, queuePharmacySync",
        "screen_focus": "prescription and dispensing workflow",
    },
    "labs": {
        "display_name": "Lab Orders and Results",
        "feature_slug": "lab",
        "screen_name": "LabOrdersScreen",
        "contracts_path": "_contracts/lab.types.ts",
        "validation_path": "src/validation/labValidation.ts",
        "service_path": "src/db/labService.ts",
        "screen_path": "src/screens/LabOrdersScreen.tsx",
        "qa_path": "e2e/lab-orders.e2e.ts",
        "workflow_path": "docs/workflow-labs.mmd",
        "contracts_desc": "LabOrder, LabResult, and LabSyncIntent",
        "service_functions": "createLabOrder, attachLabResult, queueLabSync",
        "screen_focus": "lab ordering and result entry workflow",
    },
    "auth": {
        "display_name": "Authentication and Role Based Access",
        "feature_slug": "auth",
        "screen_name": "AuthAndRoleScreen",
        "contracts_path": "_contracts/auth.types.ts",
        "validation_path": "src/validation/authValidation.ts",
        "service_path": "src/db/authService.ts",
        "screen_path": "src/screens/AuthAndRoleScreen.tsx",
        "qa_path": "e2e/auth-roles.e2e.ts",
        "workflow_path": "docs/workflow-auth.mmd",
        "contracts_desc": "UserSession, UserRole, PermissionSet, and AuthSyncIntent",
        "service_functions": "signInUser, assignRole, queueAuthSync",
        "screen_focus": "login and role assignment workflow",
    },
}


def ensure_folders_exist() -> None:
    for folder in REQUIRED_FOLDERS:
        (PROJECT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def get_target_module() -> str:
    module = os.getenv("MODULE", "patients").strip().lower()
    if module not in MODULE_CONFIGS:
        options = ", ".join(sorted(MODULE_CONFIGS.keys()))
        print(f"[CONFIG ERROR] Unsupported MODULE '{module}'.", file=sys.stderr)
        print(f"Use one of: {options}", file=sys.stderr)
        raise SystemExit(1)
    return module


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "gemini").strip().lower()


def require_provider_api_key(provider: str) -> str:
    if provider == "anthropic":
        env_key = "ANTHROPIC_API_KEY"
        key = os.getenv(env_key)
    elif provider == "gemini":
        env_key = "GOOGLE_API_KEY or GEMINI_API_KEY"
        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    elif provider == "groq":
        env_key = "GROQ_API_KEY"
        key = os.getenv(env_key)
    else:
        print("[CONFIG ERROR] Unsupported LLM_PROVIDER. Use 'gemini', 'anthropic', or 'groq'.", file=sys.stderr)
        raise SystemExit(1)

    if not key:
        print(f"[CONFIG ERROR] Missing API key for provider '{provider}'.", file=sys.stderr)
        print(f"Set {env_key} in your shell or .env loader before running.", file=sys.stderr)
        raise SystemExit(1)
    return key


def build_llm() -> LLM:
    provider = get_llm_provider()
    api_key = require_provider_api_key(provider)

    if provider == "anthropic":
        return LLM(model=f"anthropic/{ANTHROPIC_MODEL}", api_key=api_key, temperature=0)
    if provider == "groq":
        return LLM(model=f"groq/{GROQ_MODEL}", api_key=api_key, temperature=0)
    return LLM(model=f"gemini/{GEMINI_MODEL}", api_key=api_key, temperature=0)


def split_path_for_file_writer(relative_path: str) -> Tuple[str, str]:
    """Split a repo-relative path into FileWriterTool directory + filename."""
    p = Path(relative_path)
    directory = p.parent.as_posix() if p.parent.parts else "."
    if directory == "":
        directory = "."
    return directory, p.name


def write_contract_instructions(relative_path: str, language_hint: str) -> str:
    directory, filename = split_path_for_file_writer(relative_path)
    return f"""
Critical output contract:
- Write exactly one file at project-relative path: {relative_path}
- Call FileWriterTool with ALL of these keys in one tool call: filename, directory, content, overwrite.
- Use exactly: filename="{filename}", directory="{directory}" (forward slashes).
- overwrite MUST be the JSON boolean true (required by the tool schema — do not omit it).
- Write only valid {language_hint} to the file.
- Do not include markdown fences.
- Do not include explanations or extra files.
- Ensure exported symbols are named exactly as requested.
""".strip()


def agent_verbose() -> bool:
    return os.getenv("CREW_VERBOSE", "false").strip().lower() in ("1", "true", "yes", "on")


def parse_rate_limit_sleep_seconds(exc: Exception, default_seconds: float, cap_seconds: float) -> float:
    """Parse Groq-style hints: 'try again in 590ms' or 'try again in 12.5s'."""
    text = str(exc)
    ms_match = re.search(r"try again in ([0-9.]+)\s*ms", text, re.IGNORECASE)
    if ms_match:
        suggested_sec = float(ms_match.group(1)) / 1000.0
        jitter = random.uniform(0.05, 0.35)
        return min(cap_seconds, max(0.2, suggested_sec + jitter))
    # Match "... in 12.34s ..." inside JSON/strings (avoid requiring specific char after `s`).
    s_match = re.search(r"try again in ([0-9.]+)\s*s\b", text, re.IGNORECASE)
    if s_match:
        suggested_sec = float(s_match.group(1))
        jitter = random.uniform(0.15, 0.85)
        # Trust API when it gives seconds; do not force a high floor (that burns TPM).
        return min(cap_seconds, max(0.5, suggested_sec + jitter))
    return min(cap_seconds, default_seconds)


def kickoff_stage(crew: Crew, stage_name: str):
    max_retries = max(1, int(os.getenv("PIPELINE_MAX_RETRIES", "24")))
    default_delay = float(os.getenv("PIPELINE_RETRY_DELAY_SECONDS", "5"))
    cap = float(os.getenv("PIPELINE_RETRY_SLEEP_CAP_SECONDS", "90"))
    backoff_mult = float(os.getenv("PIPELINE_RATE_LIMIT_BACKOFF_MULT", "1.4"))
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return crew.kickoff()
        except Exception as exc:
            last_exc = exc
            message = str(exc).lower()
            is_rate_limited = (
                "rate_limit" in message
                or "resource_exhausted" in message
                or "429" in message
                or "rate limit" in message
            )
            is_tool_schema_retry = (
                "tool_use_failed" in message
                or ("invalid_request" in message and "failed to call" in message)
            )
            retryable = is_rate_limited or is_tool_schema_retry
            if not retryable or attempt >= max_retries:
                raise
            if is_rate_limited:
                base = parse_rate_limit_sleep_seconds(exc, default_delay, cap)
                sleep_s = min(cap, base * (backoff_mult ** max(0, attempt - 1)))
            else:
                sleep_s = max(default_delay, 3.0)
            print(
                f"[PIPELINE WARN] Stage '{stage_name}' transient error ({attempt}/{max_retries}). "
                f"Retrying in {sleep_s:.1f}s...",
                file=sys.stderr,
            )
            time.sleep(sleep_s)
    raise last_exc if last_exc else RuntimeError(f"Stage '{stage_name}' failed without an exception")


def run_staged_pipeline(module_key: str):
    """Run one CrewAI kickoff per pipeline stage; filesystem is the SSOT between stages."""
    llm = build_llm()
    file_writer = FileWriterTool()
    v = agent_verbose()
    config = MODULE_CONFIGS[module_key]
    workflow_mermaid = build_workflow_mermaid(module_key)

    contract_architect = Agent(
        role="ContractArchitectAgent",
        goal=f"Design strict TypeScript contracts for {config['display_name']}.",
        backstory="You design healthcare data contracts with deterministic strict typing.",
        verbose=v,
        allow_delegation=False,
        tools=[file_writer],
        llm=llm,
    )
    validation_engineer = Agent(
        role="ValidationAgent",
        goal=f"Implement robust validation rules for {config['display_name']}.",
        backstory="You create deterministic validation logic and explicit field-level error models.",
        verbose=v,
        allow_delegation=False,
        tools=[file_writer],
        llm=llm,
    )
    data_layer_engineer = Agent(
        role="DataLayerAgent",
        goal=f"Implement robust local data and sync services for {config['display_name']}.",
        backstory="You build offline-first service layers with explicit queue and retry handling.",
        verbose=v,
        allow_delegation=False,
        tools=[file_writer],
        llm=llm,
    )
    ui_engineer = Agent(
        role="UIScreenAgent",
        goal=f"Build React Native screen(s) for {config['display_name']} using provided contracts.",
        backstory="You write accessible RN components and strictly use provided interfaces and validators.",
        verbose=v,
        allow_delegation=False,
        tools=[file_writer],
        llm=llm,
    )
    qa_engineer = Agent(
        role="QATestAgent",
        goal=f"Write deterministic Detox end-to-end tests for {config['display_name']}.",
        backstory="You produce stable E2E coverage for success and validation-failure paths.",
        verbose=v,
        allow_delegation=False,
        tools=[file_writer],
        llm=llm,
    )
    workflow_reporter = Agent(
        role="WorkflowReporterAgent",
        goal="Persist workflow and module summary documentation artifacts.",
        backstory="You create concise workflow docs that mirror the pipeline execution.",
        verbose=v,
        allow_delegation=False,
        tools=[file_writer],
        llm=llm,
    )

    design_contracts_task = Task(
        description=(
            f"Design SSOT TypeScript contracts for {config['display_name']}.\n"
            f"Include: {config['contracts_desc']}.\n"
            f"{write_contract_instructions(str(config['contracts_path']), 'TypeScript')}"
        ),
        expected_output=f"A saved file at {config['contracts_path']} containing interfaces and types only.",
        agent=contract_architect,
    )
    build_validation_task = Task(
        description=(
            f"Read {config['contracts_path']} and implement the validation module.\n"
            "Export an error type and validate function with explicit field messages.\n"
            f"{write_contract_instructions(str(config['validation_path']), 'TypeScript')}"
        ),
        expected_output=f"A saved file at {config['validation_path']} containing validation helpers.",
        agent=validation_engineer,
    )
    build_data_task = Task(
        description=(
            f"Read {config['contracts_path']} and implement offline-first data services.\n"
            f"Export functions named: {config['service_functions']}.\n"
            f"{write_contract_instructions(str(config['service_path']), 'TypeScript')}"
        ),
        expected_output=f"A saved file at {config['service_path']} containing service functions.",
        agent=data_layer_engineer,
    )
    build_ui_task = Task(
        description=(
            f"Read {config['contracts_path']}, {config['validation_path']}, and {config['service_path']}.\n"
            f"Build {config['screen_focus']} in a screen exported as {config['screen_name']}.\n"
            f"{write_contract_instructions(str(config['screen_path']), 'TSX')}"
        ),
        expected_output=f"A saved file at {config['screen_path']} containing UI code only.",
        agent=ui_engineer,
    )
    build_qa_task = Task(
        description=(
            f"Read {config['screen_path']} and write Detox E2E tests.\n"
            "Cover field rendering, valid submission, and invalid validation feedback.\n"
            f"{write_contract_instructions(str(config['qa_path']), 'TypeScript (Detox)')}"
        ),
        expected_output=f"A saved file at {config['qa_path']} containing Detox tests only.",
        agent=qa_engineer,
    )
    build_workflow_task = Task(
        description=(
            f"Write this exact Mermaid graph to {config['workflow_path']}:\n{workflow_mermaid}\n"
            f"{write_contract_instructions(str(config['workflow_path']), 'Mermaid')}"
        ),
        expected_output=f"A saved file at {config['workflow_path']} with Mermaid workflow graph.",
        agent=workflow_reporter,
    )
    build_workflow_alias_task = Task(
        description=(
            f"Write the same exact Mermaid graph to docs/workflow.mmd for latest-run convenience:\n{workflow_mermaid}\n"
            f"{write_contract_instructions('docs/workflow.mmd', 'Mermaid')}"
        ),
        expected_output="A saved file at docs/workflow.mmd with Mermaid workflow graph.",
        agent=workflow_reporter,
    )
    build_summary_task = Task(
        description=(
            "Write docs/module-summary.md with plain markdown containing:\n"
            f"1) Module key: {module_key}\n"
            f"2) Module name: {config['display_name']}\n"
            f"3) Output files list: {config['contracts_path']}, {config['validation_path']}, {config['service_path']}, "
            f"{config['screen_path']}, {config['qa_path']}, {config['workflow_path']}\n"
            f"{write_contract_instructions('docs/module-summary.md', 'Markdown')}"
        ),
        expected_output="A saved file at docs/module-summary.md with module run summary.",
        agent=workflow_reporter,
    )

    stages: List[tuple[str, Agent, Task]] = [
        ("contracts", contract_architect, design_contracts_task),
        ("validation", validation_engineer, build_validation_task),
        ("data_layer", data_layer_engineer, build_data_task),
        ("ui", ui_engineer, build_ui_task),
        ("qa", qa_engineer, build_qa_task),
        ("workflow_mmd", workflow_reporter, build_workflow_task),
        ("workflow_alias", workflow_reporter, build_workflow_alias_task),
        ("summary", workflow_reporter, build_summary_task),
    ]

    raw_inter = os.getenv("PIPELINE_INTER_STAGE_SLEEP_SECONDS")
    if raw_inter is not None and raw_inter.strip() != "":
        inter_stage = float(raw_inter)
    elif get_llm_provider() == "groq":
        inter_stage = 12.0
    else:
        inter_stage = 0.0

    last_result = None
    for idx, (stage_name, agent, task) in enumerate(stages):
        print(f"\n[STAGE] Starting: {stage_name}", flush=True)
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=v,
            memory=False,
        )
        last_result = kickoff_stage(crew, stage_name)
        print(f"[STAGE] Done: {stage_name}", flush=True)
        if idx < len(stages) - 1 and inter_stage > 0:
            print(f"[STAGE] Pausing {inter_stage:.1f}s before next stage (spread TPM / quota)", flush=True)
            time.sleep(inter_stage)
    return last_result


def build_workflow_mermaid(module_key: str) -> str:
    return f"""flowchart TD
    ContractArchitectAgent["ContractArchitectAgent ({module_key})"] --> ValidationAgent["ValidationAgent ({module_key})"]
    ContractArchitectAgent --> DataLayerAgent["DataLayerAgent ({module_key})"]
    ValidationAgent --> UIScreenAgent["UIScreenAgent ({module_key})"]
    DataLayerAgent --> UIScreenAgent
    UIScreenAgent --> QATestAgent["QATestAgent ({module_key})"]
    QATestAgent --> WorkflowReporterAgent["WorkflowReporterAgent ({module_key})"]
"""


def get_expected_files(config: Dict[str, object], module_key: str) -> Dict[str, List[str]]:
    feature_slug = str(config["feature_slug"])
    screen_name = str(config["screen_name"])
    return {
        # Models may use plain `interface` or `export interface`; SSOT still has *SyncIntent.
        str(config["contracts_path"]): ["interface", "SyncIntent"],
        str(config["validation_path"]): ["export type", "export function validate"],
        # Services often use `export const fn = async ()` or `export async function`; require queue + naming.
        str(config["service_path"]): ["export", "queue", "Sync"],
        # Screens may use `const Screen = (...) =>` + `export default Screen` instead of single default-export function line.
        str(config["screen_path"]): ["export default", screen_name, "onPress"],
        str(config["qa_path"]): ["describe(", "it(", "expect("],
        str(config["workflow_path"]): ["flowchart TD", "ContractArchitectAgent", module_key],
        "docs/workflow.mmd": ["flowchart TD", "WorkflowReporterAgent", module_key],
        "docs/module-summary.md": [feature_slug, str(config["display_name"])],
    }


def verify_generated_files(expected_files: Dict[str, List[str]]) -> List[str]:
    errors: List[str] = []
    for relative_path, required_snippets in expected_files.items():
        file_path = PROJECT_ROOT / relative_path
        if not file_path.exists():
            errors.append(f"{relative_path}: missing file")
            continue

        content = file_path.read_text(encoding="utf-8")
        if "```" in content:
            errors.append(f"{relative_path}: contains markdown code fences")

        missing = [snippet for snippet in required_snippets if snippet not in content]
        if missing:
            errors.append(f"{relative_path}: missing required content -> {', '.join(missing)}")
    return errors


def print_workflow_banner(stage: str, module_key: str) -> None:
    print(f"\n[WORKFLOW] {stage} for MODULE={module_key}")
    print("[WORKFLOW] ContractArchitectAgent -> ValidationAgent")
    print("[WORKFLOW] ContractArchitectAgent -> DataLayerAgent")
    print("[WORKFLOW] ValidationAgent + DataLayerAgent -> UIScreenAgent")
    print("[WORKFLOW] UIScreenAgent -> QATestAgent -> WorkflowReporterAgent")


def main() -> int:
    ensure_folders_exist()
    module_key = get_target_module()
    config = MODULE_CONFIGS[module_key]
    expected_files = get_expected_files(config, module_key)

    print_workflow_banner("Planned Execution Graph", module_key)
    print(f"[INFO] Starting staged HospitalOS pipeline for MODULE={module_key}...")
    try:
        result = run_staged_pipeline(module_key)
    except Exception as exc:
        print("[PIPELINE ERROR] Staged pipeline failed.", file=sys.stderr)
        print(f"[PIPELINE ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print_workflow_banner("Execution Completed", module_key)
    print("\n[INFO] Pipeline finished. Verifying generated files...")
    validation_errors = verify_generated_files(expected_files)
    if validation_errors:
        print("[VALIDATION ERROR] Output did not meet expected contract:", file=sys.stderr)
        for err in validation_errors:
            print(f" - {err}", file=sys.stderr)
        return 2

    print("[SUCCESS] All expected files were generated and validated.")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
