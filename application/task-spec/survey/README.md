# Survey Application Tasks

Survey tasks ask the simulated user to answer a defined form or questionnaire.
The active survey protocol uses a generic survey-form task. The application
runner supplies the survey instrument as task context, then maps the resulting
artifact into answers, metrics, and a telemetry-style trajectory.

**Canonical copy-from:** `application/tasks/example-survey_product-feedback`

### What you author (required vs optional)

```mermaid
flowchart TB
  subgraph folder ["YOUR task folder"]
    direction TB
    subgraph S_REQ ["REQUIRED"]
      direction LR
      s_inst["instruction.md"]
      s_toml["task.toml"]
      s_q["input/questionnaire.yaml"]
      s_out["input/output_schema.md"]
      s_test["tests/"]
      s_rep["reporting.json"]
    end
    subgraph S_OPT ["OPTIONAL"]
      direction LR
      s_ctx["input/context.md"]
      s_rep2["reporting.json contextRules"]
    end
  end
  subgraph S_PLAT ["PLATFORM"]
    direction LR
    s_rt["shared-survey-form runtime"]
    s_traj["survey trajectory"]
    s_agg["aggregation Layer 1"]
  end
  subgraph S_REF ["REFERENCE"]
    direction LR
    s_ex["survey/*.example.json"]
    s_cheat["structured-output-quick-reference"]
  end
  S_REQ --> S_PLAT
  s_test -->|"structured_output.json"| s_agg
  S_REF -.-> folder
```

| Verifier emits | Priority |
|---|---|
| `question_response` per question | **Required** |
| `trial_summary` | **Required** |
| Layer 2 summarize `reason` by `response` | Optional in `reporting.json` |

## Contract

- Task instruction: define the task steps, constraints, and submission requirements.
- Interaction protocol: answer a structured survey instrument.
- Shared runtime: the generic `shared-survey-form` environment plus a task-supplied instrument bundle.
- Stop conditions: `survey_result.json` exists and matches the schema.
- Artifacts: platform-owned survey result JSON with `answers` and `trajectory`.
- Evaluation contract: schema validation, answer coverage, type checks, and metrics.

## Authoring Bundle

Survey task content uses one task instruction at the task root and
supplementary materials under `input/`:

`application/tasks/<task-name>/`

- `instruction.md` — the single task instruction (steps, constraints, submission
  requirements)
- `input/context.md` — product brief, scenario, or other context shown before the
  questionnaire
- `input/questionnaire.yaml` — the canonical structured questionnaire source
- `input/output_schema.md` — the canonical response artifact contract shown to
  contributors and the UI

`questionnaire.yaml` is the source of truth for runtime question structure,
single-run UI rendering, and task detail panels. `output_schema.md` is the
source of truth for what the agent must write back. The platform may derive
display markdown from `questionnaire.yaml`, but contributors should not treat
question markdown as a canonical task asset.

Keep persona framing out of these task docs. The persona is injected separately
by the runtime; `instruction.md` should stay focused on what the task requires.

For the host-native / `auto` survey path, `output_schema.md` should describe only
the contributor-owned response payload. Do **not** specify survey `trajectory`
there; the backend/runtime appends the standardized survey trajectory after the
run.

## `questionnaire.yaml` Contract

The current contract is meant to cover the common 80-90% case:

```yaml
schemaVersion: "1.0"
id: example_survey_v1
title: Example Survey
description: Optional one-line summary.
questions:
  - id: q1
    prompt: How likely are you to try this product?
    type: likert
    construct: adoption_intent
    required: true
    minValue: 1
    maxValue: 5
  - id: q2
    prompt: Which choice best matches your default reaction?
    type: single_choice
    construct: price_stance
    required: true
    options:
      - id: avoid_paying
        label: I would avoid paying unless absolutely necessary.
      - id: pay_if_value_clear
        label: I would pay once the value is obvious.
```

Supported question types:

- `likert`
- `single_choice`
- `multi_choice`
- `free_text`

For choice questions:

- `options` should normally be a list of objects with at least `id` and `label`
- `id` is the machine-stable value that the agent must emit in `answers[].value`
- `label` is what the UI should show contributors and reviewers
- `description` is optional extra display/help text

Notes:

- `questionId` in runtime answers must match `questions[].id` exactly.
- Keep `id`, question ids, and option ids stable once data has been collected.
- Put long scenario prose in `context.md`, not inside `questionnaire.yaml`.
- Keep the artifact contract in `output_schema.md`, not inside `instruction.md`.

## Reporting contract

Survey tasks use the same generic `structured_output.json` / `reporting.json`
mechanism as other application tasks. The verifier reads `survey_result.json`
and emits normalized contexts for batch aggregation.

This contract should answer:

- what the persona answered for each question
- why they answered that way when a rationale is available
- how many answers and trajectory events the trial produced

Keep using the platform's existing artifact shape:

- verifier writes `verifier/structured_output.json`
- task root defines `reporting.json`
- both continue to use `contexts[]`, `facets[]`, `summaryDirectives[]`, and
  optional `judgeDirectives[]`

See the example templates in this folder:

- `survey_structured_output.example.json`
- `survey_reporting.example.json`

### Minimum Contexts

Survey verifiers should emit these contexts:

1. `question_response`
   Required. One context per answered question. Use a stable key such as
   `question.<questionId>`.
2. `trial_summary`
   Required. One context per trial, usually keyed as `survey.summary`.

If a survey task cannot produce stable per-question contexts, it is probably not
ready for shared batch reporting.

### Required Facets For `question_response`

Emit one `question_response` context for each entry in `survey_result.json`
`answers[]`. The question id in `answers[].questionId` must match
`questionnaire.yaml`.

| Facet key | Role | Kind | Required | Notes |
|---|---|---|---|---|
| `response` | `primary` | `numerical`, `categorical`, or `textual` | Yes | Use `numerical` for likert values, `categorical` for choice ids, `textual` for free-text answers |
| `reason` | `explanation` | `textual` | Prefer | Map from `answers[].rationale` when present |
| `confidence` | `score` | `numerical` | Optional | Map from `answers[].confidence` when present |

The context `label` should normally be the question prompt or a stable question
id. The context `key` should stay stable across trials, for example
`question.q1`.

### Required Facets For `trial_summary`

The `trial_summary` context summarizes the whole survey trial:

| Facet key | Role | Kind | Required | Notes |
|---|---|---|---|---|
| `answer_count` | `score` | `numerical` | Yes | Number of answers emitted |
| `trajectory_event_count` | `score` | `numerical` | Yes | Number of standardized trajectory events |
| `mean_numeric_answer` | `score` | `numerical` | Optional | Include when the survey has numeric answers |

### Default Reporting Pattern

For survey tasks, the default `reporting.json` should usually:

- summarize `reason` by `response` for every `question_response` context
- optionally judge `reason` for reusable signals such as price sensitivity,
  preference fit, or hesitation

Copy from:

- `survey_reporting.example.json`
- `application/tasks/example-survey_product-feedback/reporting.json`

### Contributor Extension Rules

- Keep the standard facet keys exactly as written above.
- Do not invent a different per-question context type; use `question_response`
  for every question.
- Put survey-specific additions behind a `task_` prefix or in a new
  scenario-specific context only when the shared contract is genuinely too
  narrow.
- Do not bake reporting policy into the verifier; use `reporting.json` for
  summaries and judges.

## Canonical Task

`application/tasks/example-survey_product-feedback`

The canonical shared runtime lives under:

`environment/task-environments/application/shared-survey-form`
