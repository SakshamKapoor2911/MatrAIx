# Survey Application Tasks

Survey tasks ask the simulated user to answer a defined form or questionnaire.
The active survey protocol uses a generic survey-form task. The application
runner supplies the survey instrument as task context, then maps the resulting
artifact into answers, metrics, and a telemetry-style trajectory.

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

## Canonical Task

`application/tasks/example-survey_product-feedback`

The canonical shared runtime lives under:

`environment/task-environments/application/shared-survey-form`
