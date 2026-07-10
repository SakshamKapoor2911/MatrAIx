# Structured output quick reference

Cheat sheet for verifier output and `reporting.json` across all task types.
Start from [README.md](README.md) **Step 3** for the onboarding context.

Every application task uses the same shape:

```text
structured_output.json
  contexts[]
    key: "task_outcome.primary"     ← stable instance id (you choose the suffix)
    contextType: "task_outcome"     ← type label used by reporting.json match rules
    facets[]
      key: "outcome_status"         ← standard field name from the contract
      kind: numerical | categorical | textual
      value: ...
```

Three responsibilities:

| Piece | Who owns it | What it does |
|---|---|---|
| Verifier facts | Task contributor in `tests/` | Emit `contexts[]` + `facets[]` for one trial |
| Layer 1 automatic aggregation | Platform | Always aggregates every facet (`numerical` stats, `categorical` counts, `textual` samples) |
| Layer 2 extra batch analysis | Task contributor in `reporting.json` | Optional LLM bucket summaries and judge scans |

Extension rule for all types:

- keep shared `contextType` and facet keys exactly as written
- add task-specific details in new scenario contexts or behind a `task_` prefix
- do not rename shared fields to fit one task

### Survey

Full guide: [`survey/README.md`](survey/README.md)

Canonical task: `application/tasks/example-survey_product-feedback`

| Context type | Required | How many | Standard facet keys |
|---|---|---|---|
| `question_response` | Yes | one per answered question (`question.<questionId>`) | `response` (required), `reason`, `confidence` |
| `trial_summary` | Yes | one per trial (`survey.summary`) | `answer_count`, `trajectory_event_count`, `mean_numeric_answer` |

`response` kind depends on question type:

- likert → `numerical`
- single/multi choice → `categorical` (option id)
- free text → `textual`

Default reporting: summarize `reason` by `response` for each `question_response`.

Templates:

- `survey/survey_structured_output.example.json`
- `survey/survey_reporting.example.json`

### Chatbot

Full guide: [`chatbot/README.md`](chatbot/README.md)

Canonical task: `application/tasks/recommender-agent_chat_api`

| Context type | Required | Standard facet keys |
|---|---|---|
| `task_outcome` | Yes | `outcome_status`, `resolution_basis`, `outcome_reason`, `next_step_owner`, `task_goal_label` |
| `conversation_summary` | Recommended | `conversation_path`, `user_turn_count`, `assistant_turn_count`, `message_count`, `process_notes`, `clarification_question_count` |
| `user_feedback` | Recommended when self-report exists | `overall_experience_rating`, `feedback_reason`, `need_constraint_satisfaction`, `personal_preference_satisfaction`, `clarification_questions_useful`, `trust_level`, `effort_rating`, `felt_understood` |
| `policy_and_trust` | Optional | `policy_compliance`, `groundedness_primary`, `policy_notes`, `handoff_appropriateness` |
| `coordination` | Optional | `coordination_mode`, `state_change_achieved`, `user_action_required`, `guidance_quality`, `coordination_notes` |

Note: chatbot uses `outcome_reason` in `task_outcome`. Web and OS/app use
`outcome_explanation` for the same role.

Default reporting: summarize `outcome_reason` by `outcome_status`, `process_notes`
by `conversation_path`, and `feedback_reason` by satisfaction-style facets.

Templates:

- `chatbot/chatbot_structured_output.example.json`
- `chatbot/chatbot_reporting.example.json`

### Web

Full guide: [`web/README.md`](web/README.md)

Canonical task: `application/tasks/example-web-playwright_quote-choice`

Web tasks use **two layers**:

1. **Shared core** — same contexts and facet keys as OS/app (see
   [Shared core metrics](shared-core-metrics.md#shared-core-for-web-and-os-app) below)
2. **Web-specific layer** — persona-sensitive browse/choose semantics

| Context type | Required | Standard facet keys |
|---|---|---|
| `decision` | Yes for browse/choose tasks | `decision_outcome`, `basis_primary`, `reason`, `decision_subject_label`, `decision_subject_id`, `basis_secondary`, `decision_confidence` |
| `decision_process` | Recommended | `exploration_style`, `options_considered_count`, `used_search`, `used_filter_or_sort`, `comparison_notes` |
| `web_interaction` | Optional | task-specific navigation/interaction facets |
| `web_artifact` | Optional | artifact validation facets |
| `experience` | Optional | web-only subjective friction/UI facets |

Default reporting: shared core rules plus decision/process summaries. Merge
templates when needed:

- `web/web_metric_reporting.example.json`
- `web/persona_sensitive_reporting.example.json`

Templates:

- `web/web_metric_structured_output.example.json`
- `web/persona_sensitive_structured_output.example.json`

### OS / app

Full guide: [`os-app/README.md`](os-app/README.md)

Canonical task: `application/tasks/example-computer-use-ios_photo-access-review`

OS/app tasks reuse the **same shared core** as web (see [shared core metrics](shared-core-metrics.md)). Add
scenario-specific contexts such as local artifact checks or cross-app handoff
slices on top of that core rather than replacing it.

Templates:

- `os-app/os_app_metric_structured_output.example.json`
- `os-app/os_app_persona_structured_output.example.json`
- `os-app/os_app_metric_reporting.example.json`
- `os-app/os_app_persona_reporting.example.json`

Machine-readable shared core: `shared_core_metric_contract.example.json`

### Example template index

| Type | Structured output | Reporting |
|---|---|---|
| Survey | `survey/survey_structured_output.example.json` | `survey/survey_reporting.example.json` |
| Chatbot | `chatbot/chatbot_structured_output.example.json` | `chatbot/chatbot_reporting.example.json` |
| Web | `web/web_metric_structured_output.example.json`, `web/persona_sensitive_structured_output.example.json` | `web/web_metric_reporting.example.json`, `web/persona_sensitive_reporting.example.json` |
| OS / app | `os-app/os_app_metric_structured_output.example.json`, `os-app/os_app_persona_structured_output.example.json` | `os-app/os_app_metric_reporting.example.json`, `os-app/os_app_persona_reporting.example.json` |
| Web + OS shared core | `shared_core_metric_contract.example.json` | covered by the web/os templates above |

