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
# or: MODULE=builder with BUILD_ROOT + APP_PROMPT + BUILD_STACK for the app builder
```

3. Run generator:

```bash
python3 crew.py
```

### Reliability and Groq TPM

Groq's **on_demand** tier enforces tokens-per-minute (TPM) limits. Long or chatty runs can hit `rate_limit_exceeded`. Mitigations:

- Set `CREW_VERBOSE=false` (default) to reduce noise.
- For **`build_app`** with **`BUILD_STACK=fullstack`** + **Node**, **`crew.py`** runs only the **`workflow_mmd`** stage by default (contracts through qa are superseded afterward by deterministic **`notes_stack_wire`**). Use **`BUILDER_RUN_ALL_CREW_STAGES=1`** to run every Crew stage anyway.
- If Groq prints **Requested … TPM … Limit**: shorten **`APP_PROMPT`**, tune **`PIPELINE_INTER_STAGE_SLEEP_SECONDS`** / backoff, raise tier, switch provider, set **`GROQ_BUILDER_PROMPT_MAX_CHARS`**, or rely on **fullstack + Node** default stage skipping once **`notes_stack_wire`** handles files.
- Increase waits: `PIPELINE_RETRY_DELAY_SECONDS`, `PIPELINE_MAX_RETRIES`, `PIPELINE_RETRY_SLEEP_CAP_SECONDS`. Groq often returns backoff in **milliseconds** (e.g. `try again in 590ms`) or seconds (`1.36s`); the runner parses both.

For **Groq** only (when unset), runs insert a ~**12 second** pause between stages to spread TPM across the quota window; set `PIPELINE_INTER_STAGE_SLEEP_SECONDS=0` to disable. Repeated rate limits inside one stage increase sleep using `PIPELINE_RATE_LIMIT_BACKOFF_MULT` (default 1.4). Raise **`PIPELINE_MAX_RETRIES`** in `.env` if you still hit limits (defaults in code assume up to ~24 retries per stage unless overridden).
- Use a Groq tier with higher TPM, or switch `LLM_PROVIDER` to `gemini` / `anthropic` if you have quota there.

When a rate limit occurs, the tool sleeps using the API's "try again in Xs" hint when present, capped by `PIPELINE_RETRY_SLEEP_CAP_SECONDS`.

## Terminal app builder (`Project/<slug>/`)

### Prerequisites

- **Python 3** with [`requirements.txt`](requirements.txt) installed.
- **Node.js 20+** (current **react-native** npm releases typically require Node ≥20; use **npm/npx** on your `PATH`) for React Native CLI. `build_app.py` runs `npx @react-native-community/cli@latest init` with **`react-native@latest`** resolved from **registry.npmjs.org** (no legacy tarball template).
- To run on simulators/devices: **Xcode** (iOS) and/or **Android Studio** — see [React Native environment setup](https://reactnative.dev/docs/set-up-your-environment).

### Pipeline order (`build_app.py`)

**Interactive mode** asks in order:

1. **App specs** — what you want built (stored as **`APP_PROMPT`** for Crew).
2. **Project folder name** — becomes **`Project/&lt;sanitized-name&gt;/`** (unless you pass **`--slug` / `--name`** on the command line, which skips this step).
3. **Stack surface** (**frontend** … **mobile**) — and backend runtime if relevant.

Pipeline steps:

1. **React Native CLI** creates **`Project/<slug>/`** with the **published latest `react-native`** ([`rn_init.py`](rn_init.py)).
2. **LangGraph** exports Mermaid (+ optional PNG) under **`Project/<slug>/docs/`**.
3. **Blueprints** render reviewed source-of-truth contracts under **`Project/<slug>/docs/blueprints/`** (`openapi.yaml`, `asyncapi.yaml`), then open a separate HITL review webpage. The build is blocked until a human clicks **APPROVE CONTRACT**.
4. If `--stack` is **backend** or **fullstack**: choose **Node** or **Java** (interactive or `--backend-runtime`). Scaffolds: **`server/`** (Express) or **`backend-java/`** (Spring Boot) ([`backend_scaffold.py`](backend_scaffold.py)).
5. Writes **`build-manifest.json`** (`rn_template`, resolved `react_native_version`, optional `backend_paths`).
6. **CrewAI** codegen writes `_contracts/`, `src/`, `e2e/`, `docs/` (`MODULE=builder`; agents intentionally do **not** replace root `App.tsx`).
7. **`build_app.py` finishes** by rewriting **`App.tsx`** to import **`src/screens/AppScreen.tsx`**, otherwise Metro would keep showing the RN CLI welcome template.

Interactive (omit `--slug` to be prompted for the folder name; or pass `--slug` / `--name` to prefill **`Project/&lt;folder&gt;/`**):

```bash
python3 build_app.py
# App specs prompt, then folder name prompt, then stack…

python3 build_app.py --slug my-notes --stack frontend "Notes app specs here"
```

Non-interactive **`-y`** must include **positional PROMPT**, **`--stack`**, and **`--slug`/`--name`** (folder). It still opens the HITL review webpage unless you explicitly pre-approve with **`--approve-blueprints`** or **`APPROVE_BLUEPRINTS=1`**. With backend/fullstack, add **`--backend-runtime node|java`**.

```bash
python3 build_app.py --yes --approve-blueprints --stack frontend --slug my-task-app "Minimal todo list"

python3 build_app.py -y --approve-blueprints --stack frontend --name my-notes "Same as --slug my-notes"

python3 build_app.py -y --approve-blueprints --stack fullstack --backend-runtime node \
  --slug task-tracker "Offline sync specs…"

python3 build_app.py -y --approve-blueprints --stack backend --backend-runtime java \
  --name api-heavy "Backend-focused specs…"
```

| Variable | Meaning |
|----------|---------|
| `BUILD_ROOT` | Path to generated RN tree (`Project/<slug>/`). |
| `MODULE` | `builder` for app-builder runs. |
| `APP_PROMPT` | User prompt for agents. |
| `BUILD_STACK` | `frontend`, `backend`, `fullstack`, or `mobile`. |
| `BACKEND_RUNTIME` | `node` or `java` when a backend scaffold exists. |
| `BUILDER_MODE` | When `1`, strict file verification is skipped. |
| `APPROVE_BLUEPRINTS` | Set to `1` to bypass the browser HITL gate for trusted automation. |
| `HITL_REVIEW_HOST` | Host for the local review webpage (default `127.0.0.1`). |
| `HITL_REVIEW_PORT` | Port for the local review webpage (default `8765`; falls back to a free port if busy). |
| `HITL_REVIEW_TIMEOUT_SECONDS` | How long the builder waits for approval before stopping (default `3600`). |
| `HITL_OPEN_BROWSER` | Set to `0` to print the review URL without opening a browser. |
| `HITL_WEBHOOK_URL` | Optional webhook that receives contract metadata and the review URL. |
| `SKIP_QUALITY_GUARDRAILS` | Set to `1` only for explicit debugging to skip TypeScript/ESLint guardrails. |
| `LIGHTRAG_URL` | LightRAG API URL (default `http://127.0.0.1:9621`). |
| `LIGHTRAG_API_KEY` | Optional API key sent as `X-API-Key` to LightRAG. |
| `SKIP_LIGHTRAG_MEMORY` | Set to `1` to skip contract ingestion into LightRAG. |
| `REQUIRE_LIGHTRAG_MEMORY` | Set to `1` to fail the build if LightRAG ingestion is unavailable. |

### Sovereign IDE / blueprint review

Continue.dev configuration lives in **`.continue/config.yaml`** and points to Groq-hosted Llama models. Set **`GROQ_API_KEY`** before using Continue in this repo.

Reusable contract templates live in **`docs/blueprints/templates/`**. Every build renders app-specific contracts into **`Project/<slug>/docs/blueprints/`** before codegen. The HITL pause node then serves those files on a local webpage with **APPROVE CONTRACT** and **REJECT CONTRACT** actions. Backend scaffold and CrewAI do not start until approval is recorded.

If `HITL_WEBHOOK_URL` is set, the builder sends a JSON payload to that endpoint with the review URL, slug, stack, backend runtime, and contract paths so a human lead can open the approval page.

### Topological memory with LightRAG

LightRAG stores the approved architecture contracts as graph-backed memory so agents can query the system map before implementing service interactions.

Start the local memory server:

```bash
cd docker/lightrag
cp .env.example .env
# Fill LIGHTRAG_API_KEY plus LLM/embedding provider keys in .env
docker compose up -d
```

Check health from the repo root:

```bash
python3 lightrag_memory.py health
```

Every build renders `openapi.yaml` and `asyncapi.yaml`, waits for HITL approval, then tries to ingest the approved contracts into LightRAG before backend scaffold and CrewAI. By default, LightRAG failures warn and continue. Set `REQUIRE_LIGHTRAG_MEMORY=1` when you want memory ingestion to be mandatory.

Manual commands:

```bash
python3 lightrag_memory.py build-packet --build-root Project/<slug>
python3 lightrag_memory.py ingest --build-root Project/<slug>
python3 lightrag_memory.py query "How should the mobile app create a note?" --mode hybrid
```

### Zero-hallucination quality guardrails

Root Node tooling runs deterministic checks against any generated `Project/<slug>` app that exists locally:

```bash
npm install
npm run quality
```

The guardrail runner discovers generated apps with `package.json` and `tsconfig.json`, then runs:

- `npx tsc --noEmit` inside each generated app.
- ESLint with `complexity: ["error", 10]` against generated `src/`, `_contracts/`, and `e2e/` TypeScript files.

Husky installs a pre-commit hook via `npm run prepare`; commits run `npm run quality` automatically. `build_app.py` also runs the same guardrail after the API and React Native bundle smoke checks, so agent output must pass type and complexity checks before the build succeeds.

### Full-stack expectations (honest baseline)

Choosing **`fullstack`** does **not** by itself imply a hardened production API or polished multi‑screen UX. **`build_app.py`** scaffolds RN plus a runnable backend stub next to it; codegen follows fixed paths (`AppScreen.tsx`, **`appService.ts`**, `_contracts`). For **Node**, the scaffold exposes **`GET /health`** and REST **`/api/v1/notes`** (deterministic MVP); **`build_app`** also drops **`src/config/api.ts`** with **`getApiBaseCandidates()`** so the app tries Metro’s host IP first, then Android emulator / USB reverse fallbacks. Detail and caveats: **[`docs/builder-limitations.md`](docs/builder-limitations.md)**.

### Run the scaffolded React Native app

```bash
cd Project/<slug>
npm start
# Other terminal — iOS or Android:
npx react-native run-ios
npx react-native run-android
```

Optional backend stubs:

```bash
cd Project/<slug>/server && npm install && npm start   # Express: `/health`; `/api/v1/notes` when `--stack fullstack` (server/README.md)
cd Project/<slug>/backend-java && mvn -q spring-boot:run  # http://localhost:8080/health
```

Java/Spring listens on **`http://localhost:8080/health`**; Node listens on **port 3090** (`PORT` env overrides unless changed).

### Full-stack Notes dev plumbing (Android / physical device)

- **Start the API first**: **`cd Project/<slug>/server && npm install && npm start`**. The app saves offline if this server is not reachable.
- **Android emulator → host**: the app falls back to **`http://10.0.2.2:3090`** automatically.
- **Physical Android device on same Wi-Fi**: the generated config derives the host from Metro’s **`scriptURL`** and tries **`http://<your-mac-lan-ip>:3090`** first.
- **Physical USB device**: run **`adb reverse tcp:3090 tcp:3090`** before launching the app; the generated config also tries **`127.0.0.1:3090`** / **`localhost:3090`**.
- **Slow first load / Save**: generated notes services use short request timeouts and then fall back to local pending notes, so unreachable API paths should not stall the UI for long.
- **Build-time API QA**: for **fullstack + Node**, **`build_app.py`** starts the generated server temporarily and verifies **`GET /health`**, **`POST /api/v1/notes`**, **`GET /api/v1/notes`**, and **`DELETE /api/v1/notes/:id`** before reporting success. Set **`SKIP_FULLSTACK_API_VERIFY=1`** only if you intentionally want to skip this runtime gate.
- **Runtime dev helper**: generated fullstack Notes apps include **`scripts/dev-fullstack.sh`**. It starts the Node API and prints the exact Metro / Android commands. The app also handles offline API state by saving a pending local note and showing a status banner instead of raw **`Network request failed`**.

For **alternate** pinning (explicit domain allow‑lists instead of **`usesCleartextTraffic`**), see **`docs/network_security_config.example.xml`**.

**`build_app.py`** merges **`android/app/src/debug/AndroidManifest.xml`** with **`android:usesCleartextTraffic="true"`** for **fullstack + Node** builds via **`rn_android_dev_network.ensure_android_http_debug_manifest`**, so plaintext HTTP is allowed alongside dev hosts.

### Metro and “InternalError / Fail…” toasts

A truncated red toast alone is not enough—read the **`npm start` / Metro** terminal:

- Restart Metro with **`npx react-native start --reset-cache`** (often fixes stale bundles after codegen).
- **`rm -rf node_modules`** then **`npm install`** if versions drifted.
- Errors often cite a **specific file**: fix the import/path/syntax shown (e.g. wrong relative import from **`src/db/`**).

If Metro prints **transform failed** or **`Unable to resolve module`**, use the literal path Metro reports (not only the simulator overlay).

- **`Unable to resolve module ./index` / 404 bundle**: run **`npm start`** from the **RN project folder** (**`Project/<slug>/`**), not from **`multiAgentApp/`**. Stale emulator installs pointing at another folder (**`Project/mybook`** vs **`mynotebook`**) yield the wrong Metro root—in that case reinstall the Android app or **`npx react-native run-android`** from the matching project directory.
- **`TransformError` / `ENOENT` / `uv_cwd`** (often under **`react-native-safe-area-context`**): Metro’s process has a **dead current working directory** (folder deleted/renamed while Metro ran, or Metro started from the wrong tree). Stop Metro (**Ctrl+C**), **`pkill -f "cli.js start"`** or Activity Monitor → **`node`**, open a **new** terminal, **`cd Project/<slug>`**, **`npm start`**, then **`run-android`** again. **`build_app.py`** now runs an Android **`react-native bundle`** smoke step after wiring so many bundler errors fail the build early (**`SKIP_RN_BUNDLE_VERIFY=1`** to opt out).
- **Stale Metro preflight:** **`build_app.py`** runs **`rn_metro_guard.py`** before scaffold. It fails if another **`Project/*`** Metro/devtools process is active, because that process can keep serving deleted roots. Set **`KILL_STALE_METRO=1`** for the builder to stop stale Metro processes automatically before creating the next app.

## Available modules


## Available modules
- `builder` (terminal app builder; use with `build_app.py` or set `BUILD_ROOT` + `APP_PROMPT` + `BUILD_STACK`)
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
