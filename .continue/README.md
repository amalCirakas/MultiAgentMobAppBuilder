# Continue.dev Setup

This repo uses Continue.dev as the blueprint-review layer before generated code is accepted.

## Configure

1. Install the Continue extension in Cursor or VS Code.
2. Set `GROQ_API_KEY` in your shell or environment manager.
3. Open this workspace so Continue picks up `.continue/config.yaml`.

The default chat/edit model is `llama-3.3-70b-versatile` through Groq. Autocomplete uses the smaller `llama-3.1-8b-instant` model for speed.

## Review Workflow

Each generated app writes reviewed contracts to:

- `Project/<slug>/docs/blueprints/openapi.yaml`
- `Project/<slug>/docs/blueprints/asyncapi.yaml`

Use those files as the source of truth when asking Continue to review or change the generated app. The intended workflow is:

1. Generate LangGraph and blueprint contracts.
2. Review the OpenAPI/AsyncAPI files.
3. Approve the shift-left gate.
4. Let CrewAI and deterministic wiring generate code from the approved blueprint.

For non-interactive builds, pass the explicit approval flag or set `APPROVE_BLUEPRINTS=1`.
