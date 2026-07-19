# Application Tasks

Task definitions for **application product research**. These were migrated from
MatrAIx and organized under the MatrAIx `application/` module.

This import contains application task folders, tests, and reference solutions.
Runtime build contexts live under `environment/task-environments/application/`.
Generated job recipes land under `configs/jobs/` (see [QUICKSTART.md](../QUICKSTART.md)).

## Naming

- **`example-*`** — reference tasks in the repo (copy from these). For surveys, only
  **`example-survey_product-feedback`** is the reference; other `survey_*` folders are
  real application benchmark tasks. Chat references are
  **`example-chat-api_*`** / **`example-chat-mcp_*`**.
- **`survey_*`** — application survey tasks.
- **`chat_*`** — application chatbot tasks, named after the SUT chatbot
  (e.g. `chat_recai`, `chat_openbb`, `chat_multi-agent-medical-assistant`).
  Match `[environment].local_compose` sidecars `chatbot-*-sidecar_<sut>` when present.
- **`example-web-*`** — reference web tasks for Playwright, browser-use, Cocoa,
  and CUA style browsing flows.
- **`example-computer-use-*`** — reference os-app / computer-use tasks.
- **`os-app-ios_*` / `os-app-macos_*` / `os-app-linux_*`** — real application
  os-app tasks (e.g. `os-app-ios_news-subscription-decision`).
- **Your task** — `application/tasks/<your-task-name>/` (use `survey_*` / `chat_*`
  / `web-*` / `os-app-*` conventions above when it is a real benchmark task).

## New Task

Copy the closest `example-*` sibling with the same interaction type, then edit
the scenario, task metadata, and verifier.

1. `cp -R application/tasks/example-survey_product-feedback application/tasks/<your-task-name>`
2. Set `[task].name` to `application/{slug}`.
3. Update `[metadata]` with `type`, `domain`, `difficulty`, and task-specific `tags`.
4. For survey tasks, keep `[environment].definition = "application/shared-survey-form"`
   and put task-owned docs under `application/tasks/<your-task-name>/input/`.
5. For chat tasks, set `[environment].definition = "application/shared-chat-persona"`.
   Choose the sidecar by the **persona-facing protocol** (what UserSim / the agent
   actually calls), not by every backend the product uses internally:
   - persona talks HTTP chat → `chatbot-api-sidecar_<sut>` + `transport: sidecar_http`
   - persona talks MCP chat tools → `chatbot-mcp-sidecar_<sut>` + `transport: mcp`
   Reference the folder with `[environment].local_compose`, or point at an external
   URL in `input/chatbot.yaml`. Example of HTTP adapter wrapping an MCP data
   layer: `chat_openbb` → `chatbot-api-sidecar_openbb` (`finance-chatbot` + `openbb-mcp`).
   For browser tasks, prefer an existing `shared-web-*` runtime.
   Only create a task-specific environment when the agent image or browser stack is
   genuinely new.
6. Keep verifier entry points under `tests/`.
7. Define batch reporting policy in `reporting.json` at the task root. Use this
   file for context-level summaries, grouping rules, and later judge prompts.
   Do not hardcode reporting policy into the verifier unless you are prototyping
   a brand-new schema feature.
8. Add `persona_strategy.json` at the task root with a target cohort
   (`dimensionFilters` and/or `cohortId`; default mode, optional `sampleSize`).
   See
   [`../task-spec/authoring-bundle.md`](../task-spec/authoring-bundle.md#persona_strategyjson).
9. If those filters are narrower than `bench-dev-sample` (~200 personas),
   generate a local coverage pool **before** Playground / CLI sampling fails.
   The production persona dataset is not ready yet — synthetic pools exist so
   you can ship and exercise **task design** plus the **persona reporting /
   analysis** path, not as a stand-in for the final population:

   ```bash
   uv run python persona/scripts/generate_dev_personas.py \
     --strategy application/tasks/<your-task-name>/persona_strategy.json
   ```

   Playground will also auto top-up `_generated/` when coverage is too thin;
   the CLI is the preferred contributor path. Details:
   [Ensuring pool coverage](../task-spec/authoring-bundle.md#ensuring-pool-coverage).
10. Use `persona/datasets/bench-dev-sample/persona_0042.yaml` for lightweight
   smoke examples until a larger persona dataset is restored externally.

For survey tasks, create a canonical task-local bundle under:

`application/tasks/<your-task-name>/input/`

with:

- `instruction.md`
- `context.md`
- `questionnaire.yaml` (include `askRationale` / `askConfidence` as needed)

Do **not** add `output_schema.md` for surveys — the platform derives the answer
envelope from `questionnaire.yaml` and writes `survey_result.json`.

For chatbot tasks, keep contributor-facing docs under `input/`:

- `context.md`
- `protocol.md` (when the API/MCP contract should stay separate)
- `chatbot.yaml`
- `self_report_schema.yaml` (persona self-report for `user_feedback.json`)

Platform-managed chat artifacts (`transcript.json`, `application_result.json`) are
documented in [`../task-spec/chatbot/eval_artifacts.md`](../task-spec/chatbot/eval_artifacts.md),
not in per-task `output_schema.md`.

For web and OS/app tasks, keep the task-result JSON schema inline in
`instruction.md`, put optional scenario or product background in
`input/context.md`, and optional persona self-report in
`input/self_report_schema.yaml`. These tasks do not use `input/output_schema.md`.

Do not create `application/tasks/<your-task-name>/environment/` for surveys.
Harbor treats a task-local `environment/` as the full runtime environment, which
would shadow the shared `application/shared-survey-form` runtime instead of
extending it.

See [`../task-spec/survey/README.md`](../task-spec/survey/README.md) for the structured
questionnaire contract.

## Reporting Policy

### PR batch evidence (required)

For multi-persona validation on a new or substantially changed task, attach the
**Playground UI** batch PDF in the PR:

1. Open the completed job in Playground **Runs**.
2. On the persona-task batch report card, click **Download PDF**.
3. Upload that file to the PR (filename typically ends in
   `persona-task-batch-report.pdf`).

That UI export is the reviewer-facing artifact. Do **not** attach the server
text report from `GET /api/harbor/jobs/<job>/report.pdf` (or an equivalent
FPDF/script export) as a substitute — layout and content differ from the UI
report.

Each task folder should include a `reporting.json` file, even if it currently
contains only:

```json
{
  "schemaVersion": "1.0",
  "contextRules": []
}
```

The verifier should extract structured runtime facts into
`verifier/structured_output.json`. Reporting semantics belong in
`reporting.json`, where task contributors can define:

- which context(s) should be summarized
- which textual facet is the summary target
- which categorical or numeric facet should bucket that summary
- which judge prompts, rubrics, and signals should be used later in reporting

This keeps the platform generic while letting each task define its own signals.

When the backend is started with `PLAYGROUND_REPORTING_ENABLE_LLM=1`, completed
jobs will queue a background reporting pass for `llm_*` directives and persist
the results into the job's `aggregation.json`. These LLM results are cached by
input fingerprint, so reopening the same job detail does not rerun unchanged
directives; the UI can surface `queued` / `running` / `completed` style
reporting states from the job aggregation view.

For web / computer-use tasks, prefer the shared contracts in
[`../task-spec/os-app/README.md`](../task-spec/os-app/README.md) and
[`../task-spec/web/README.md`](../task-spec/web/README.md) rather than inventing new
metrics from scratch.

- `../task-spec/os-app/README.md` is the main app benchmark contract for
  native desktop/mobile and cross-app operating tasks.
- `../task-spec/web/README.md` is the web-task contract for browser-mediated tasks,
  including its own web-specific metrics and browser-specific persona decision
  contract.

For persona-sensitive chatbot tasks, prefer the shared semantic contract in
[`../task-spec/chatbot/README.md`](../task-spec/chatbot/README.md) rather than
inventing new outcome / feedback keys per task. That contract standardizes the
minimum `task_outcome` / `conversation_summary` contexts, shared facet keys
like `outcome_status`, `resolution_basis`, `feedback_reason`, and
`conversation_path`, plus example templates for `structured_output.json` and
`reporting.json`.

Default survey `reporting.json` is Layer 1 only (`contextRules: []`). The
shape below is an **opt-in** Layer 2 example when `askRationale` is true:

```json
{
  "schemaVersion": "1.0",
  "contextRules": [
    {
      "match": {
        "contextType": "question_response"
      },
      "summaryDirectives": [
        {
          "id": "question.reason_by_response",
          "targetFacetKey": "reason",
          "groupByFacetKey": "response",
          "groupByMode": "categorical",
          "summaryKind": "llm_bucket_summary"
        }
      ],
      "judgeDirectives": [
        {
          "id": "question.reason_signal_scan",
          "targetFacetKey": "reason",
          "groupByFacetKey": "response",
          "groupByMode": "categorical",
          "judgeKind": "llm_signal_judge",
          "prompt": "Read each reason and extract the configured signals.",
          "rubric": "Mark a signal true only when it is clearly expressed.",
          "signals": [
            {
              "key": "hesitation",
              "label": "Hesitation",
              "valueType": "boolean"
            }
          ]
        }
      ]
    }
  ]
}
```

## Metadata

| Field | Meaning |
|-------|---------|
| **type** | Interaction form (`survey`, `chat`, `web`, `desktop`, `mobile`, …) |
| **domain** | Vertical: `software` · `finance` · `healthcare` · `commerce-retail` |
| **tags** | Task-specific labels; do not repeat `type` or `domain`. |

Persona benchmark and grounding tasks should live under `persona/tasks/`, not
in this module.

## Task spec

[`../task-spec/`](../task-spec/) records the shared application-task spec for
survey, chatbot, and web/computer-use tasks. Use it to decide where a new task
belongs and which artifacts its verifier should expect.

## Task environment

Harbor resolves `[environment].definition` to a folder under
`environment/task-environments/application/`.

Keep **persona-side** vs **SUT-side** folders distinct:

**Persona agent / interaction surface** (`shared-*` → `[environment].definition`):

- survey form: `shared-survey-form`
- chatbot persona: `shared-chat-persona`
- browser agent stacks: `shared-web-*`
- os-app use.computer (macOS / iOS): `shared-os-app-mac-ios`
- os-app Linux desktop Docker: `shared-os-app-linux`

**System under test** (`*-sidecar_<sut-name>` → `[environment].local_compose`):

- chatbot API hosts: `chatbot-api-sidecar_<sut>` (e.g. `chatbot-api-sidecar_recai`,
  `chatbot-api-sidecar_openbb`) — used when the persona-facing surface is HTTP
  `/v1/messages` (even if a product data layer underneath is MCP)
- chatbot MCP hosts: `chatbot-mcp-sidecar_<sut>` (e.g. `chatbot-mcp-sidecar_acme-support`) —
  used when the persona talks MCP chat tools directly
- task-hosted web apps: `web-sidecar_<sut>` (e.g. a task-hosted storefront package)

Do not put the persona agent image inside a `*-sidecar_*` package.
See also [`../../environment/task-environments/application/CHAT_ENVS.md`](../../environment/task-environments/application/CHAT_ENVS.md).

Create a task-specific environment folder only when you need a genuinely new
runtime or sidecar topology. Survey tasks stay task-local only for `input/`
content; they still reuse `environment/task-environments/application/shared-survey-form/`.

Survey and chat reference tasks run in **auto** mode without building a task image
(see [QUICKSTART.md](../QUICKSTART.md)). Web and computer-use tasks need a
Dockerfile in the task environment directory.
