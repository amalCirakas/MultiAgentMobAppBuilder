# HospitalOS Multi-Agent Generator

This project uses CrewAI to generate React Native module code for a hospital management app.

The generator runs as a **staged pipeline**: each step (contracts, validation, services, UI, QA, docs) executes in its own short `Crew` run. Outputs are written under the repo; the next step reads those files from disk. If a provider rate-limits you, retries apply **only to the failing stage** (not restarting the whole workflow from scratch).

## Python generator setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

Groq (and several other providers) rely on LiteLLM inside CrewAI. If you omit `litellm` from the install you may see provider connection errors.

2. Configure environment variables (either export in your shell or create a `.env` file beside `crew.py`; see [`.env.example`](.env.example)):

```bash
export LLM_PROVIDER=gemini
export GEMINI_API_KEY='your_key'
export MODULE=patients
```

3. Run generator:

```bash
python3 crew.py
```

### Reliability and Groq TPM

Groq’s **on_demand** tier enforces tokens-per-minute (TPM) limits. Long or chatty runs can hit `rate_limit_exceeded`. Mitigations:

- Set `CREW_VERBOSE=false` (default) to reduce noise.
- Increase waits: `PIPELINE_RETRY_DELAY_SECONDS`, `PIPELINE_MAX_RETRIES`, `PIPELINE_RETRY_SLEEP_CAP_SECONDS`. Groq often returns backoff in **milliseconds** (e.g. `try again in 590ms`) or seconds (`1.36s`); the runner parses both.

For **Groq** only (when unset), runs insert a ~**12 second** pause between stages to spread TPM across the quota window; set `PIPELINE_INTER_STAGE_SLEEP_SECONDS=0` to disable. Repeated rate limits inside one stage increase sleep using `PIPELINE_RATE_LIMIT_BACKOFF_MULT` (default 1.4). Raise **`PIPELINE_MAX_RETRIES`** in `.env` if you still hit limits (defaults in code assume up to ~24 retries per stage unless overridden).
- Use a Groq tier with higher TPM, or switch `LLM_PROVIDER` to `gemini` / `anthropic` if you have quota there.

When a rate limit occurs, the tool sleeps using the API’s “try again in Xs” hint when present, capped by `PIPELINE_RETRY_SLEEP_CAP_SECONDS`.

## Available modules

- `patients`
- `appointments`
- `vitals`
- `admission`
- `billing`
- `pharmacy`
- `labs`
- `auth`

## Output pattern per module

- `_contracts/<module>.types.ts`
- `src/validation/<module>Validation.ts`
- `src/db/<module>Service.ts`
- `src/screens/<ModuleScreen>.tsx`
- `e2e/<module>.e2e.ts`
- `docs/workflow-<module>.mmd`
- `docs/workflow.mmd` (latest run alias)
- `docs/module-summary.md`

## Graphical overview

For diagrams of the logical agent graph, the staged Crew execution order, and where LangGraph PNG/Mermaid files live, see **[`docs/multi-agent-architecture.md`](docs/multi-agent-architecture.md)**.

## LangGraph visualization

Generate a LangGraph workflow diagram for the same module pipeline:

```bash
export MODULE=patients
python3 langgraph_visualize.py
```

Generated artifacts:

- `docs/langgraph-workflow-<module>.mmd`
- `docs/langgraph-workflow.mmd` (latest run alias)
- `docs/langgraph-workflow-<module>.png` (if PNG rendering works)
- `docs/langgraph-workflow.png` (latest run alias, if available)
- `docs/langgraph-summary.md`
