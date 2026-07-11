# Authoring bundle

Per-type file layouts for tasks under `application/tasks/<task-name>/`.
Part of [README.md](README.md) **Step 2**. Per-type **diagrams** are in each
type README ([survey](survey/README.md), [chatbot](chatbot/README.md),
[web](web/README.md), [os-app](os-app/README.md)).

Each runnable task lives under `application/tasks/<task-name>/` and always
includes `instruction.md`, `task.toml`, `tests/`, and `reporting.json`.
Supplementary files differ by application type:

### Survey

```text
instruction.md                 # short scenario / requirements
reporting.json                 # batch aggregation policy (contextRules)
input/
  context.md                   # product concept (optional)
  questionnaire.yaml           # questions + askRationale / askConfidence
```

Do **not** add `input/output_schema.md`. The platform derives the answer
envelope from `questionnaire.yaml` and writes `survey_result.json`.

### Chatbot

```text
instruction.md                 # conversation goal
reporting.json                 # batch aggregation policy (contextRules)
input/
  context.md                   # application background (optional)
  protocol.md                  # chat API / MCP contract (optional)
  chatbot.yaml                 # runtime connection metadata
  self_report_schema.yaml      # user_feedback.json
```

Platform-managed harness artifacts (`transcript.json`,
`application_result.json`) are documented in
[`chatbot/eval_artifacts.md`](chatbot/eval_artifacts.md), not in per-task files.

### Web / OS-app

```text
instruction.md                 # task goal, steps, optional submission JSON schema
reporting.json                 # batch aggregation policy (contextRules)
input/
  context.md                   # scenario / product background (optional)
  self_report_schema.yaml      # user_feedback.json (optional)
```

Prefer verifying from browser/OS traces and final state. When state is hard to
read, an agent submission schema may still live inline in `instruction.md`.
Persona self-report uses the same `input/self_report_schema.yaml` convention as
chatbot tasks.

### Quick reference

| Concern | survey | chatbot | web / os-app |
|---|---|---|---|
| Scenario | `instruction.md` | `instruction.md` | `instruction.md` |
| Background context | `input/context.md` | `input/context.md` | `input/context.md` (optional) |
| Structured input | `input/questionnaire.yaml` | `input/chatbot.yaml`, optional `protocol.md` | — |
| Objective evidence | platform `survey_result.json` | platform harness artifacts | trace/state (optional agent submission) |
| Persona self-report | — | `input/self_report_schema.yaml` | `input/self_report_schema.yaml` |
| Batch reporting policy | `reporting.json` | `reporting.json` | `reporting.json` |
