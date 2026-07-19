# Shared core metrics

Shared contracts for `web/` and `os-app/` tasks, plus the cross-family subjective
channel. Read [README.md](README.md) **Step 1** (web vs os-app) and **Step 3**
(shared contexts) first.

## Choosing `web` vs `os-app`

Use `web/` when the benchmark target is primarily one website or web product:

- the core task is search, browse, compare, filter, fill, submit, cart, checkout,
  booking, or account management on web pages
- the main observable errors are wrong page navigation, broken form filling,
  search/filter misuse, or live-site brittleness
- success is mainly judged from web-visible state or a site-backed submission

Use `os-app/` when the benchmark target is primarily native app operation or a
workflow that spans apps and local artifacts:

- the core task is settings changes, file transforms, local document edits,
  email/calendar/file-manager workflows, or mobile/desktop app operation
- the main observable errors are wrong edits, destructive side effects, broken
  cross-app handoff, or task completion with the wrong artifact
- success is mainly judged from local app state, exported files, or cross-app
  side effects

If a task starts in a browser but the real benchmark target is a broader
operating workflow, prefer `os-app/`. If the browser is the product under test,
prefer `web/`.

## Shared core for `web` and `os-app`

If you author **web** or **OS/app** tasks, read
[Structured output quick reference](structured-output-quick-reference.md)
first, then use this section for the shared context names and facet keys that
both families reuse. For full metric templates and reporting patterns, use
[`web/README.md`](web/README.md) and [`os-app/README.md`](os-app/README.md).

For a machine-readable companion to this section, see
`shared_core_metric_contract.example.json`.

### Shared Core Contexts

Both `web` and `os-app` should reuse these context types with the same names
and semantics:

1. `task_outcome`
   Required. The benchmark-facing result for the whole task.
2. `goal_component`
   Recommended. One context per major required subgoal or assertion group.
3. `side_effects`
   Recommended. Unexpected edits, destructive changes, duplicates, privacy
   leaks, or other collateral damage.
4. `execution_profile`
   Recommended. Runtime and operating-shape diagnostics.
5. `infeasibility`
   Optional but strongly recommended when some tasks are intentionally blocked,
   unsupported, or impossible.
6. `user_feedback`
   Recommended whenever the task collects post-run self-report.
7. `persona_alignment`
   Recommended when persona alignment is part of the evaluation target.
8. `persona_constraint`
   Recommended when the task has explicit or inferable persona constraints.

Scenario-specific contexts such as `web_interaction`, `web_artifact`,
`decision`, or `decision_process` should layer on top of this shared core, not
replace it.

### Shared Core Facet Keys

These facet keys should stay identical across `web` and `os-app` so that
reporting code can aggregate them without task-family-specific branching.

For `task_outcome`:

- `outcome_status`
- `goal_completion_ratio`
- `goal_completion_bucket`
- `verifier_mode`
- `primary_failure_reason`
- `outcome_explanation`
- `completion_evidence`

For `goal_component`:

- `goal_component_key`
- `goal_component_label`
- `goal_component_status`
- `goal_component_weight`
- `goal_component_required`
- `goal_component_evidence`

For `side_effects`:

- `collateral_damage_present`
- `blocking_side_effect_present`
- `damage_severity`
- `damage_type_primary`
- `unsafe_action_present`
- `side_effect_notes`

For `execution_profile`:

- `task_archetype`
- `used_gui_primary`
- `used_terminal_or_script`
- `apps_touched_count`
- `step_count`
- `wall_clock_seconds`
- `recovery_count`

For `infeasibility`:

- `infeasible_expected`
- `agent_declared_infeasible`
- `infeasibility_reason_match`
- `declared_before_side_effects`
- `infeasibility_notes`

For `user_feedback`:

- `overall_experience_rating`
- `feedback_reason`
- `need_constraint_satisfaction`
- `personal_preference_satisfaction`
- `trust_level`
- `effort_rating`
- `clarity_of_next_step`

For persona-aware tasks:

- `persona_alignment_status`
- `persona_alignment_score`
- `persona_preference_axis_primary`
- `persona_signal_source`
- `persona_alignment_explanation`
- `persona_constraint_key`
- `persona_constraint_type`
- `persona_constraint_priority`
- `persona_constraint_status`
- `persona_constraint_evidence`

### Shared Core Rules

- Keep the shared context names and facet keys exactly as written.
- Do not rename shared fields to fit one task family; add task-specific fields
  behind a `task_` prefix or in scenario-specific contexts instead.
- Keep `user_feedback` as the shared post-run subjective channel across
  interactive tasks. Family-specific process contexts may add richer slices, but
  they should not replace the shared feedback context.
- Keep binary success outcome-based. Do not derive success from action-sequence
  matching.
- Use the same shared enums for common fields whenever possible so batch reports
  can compare `web` and `os-app` runs directly.

## Shared subjective channel (interactive tasks)

When a task collects post-run persona feedback (`chatbot`, `web`, `os-app`):

- write the raw artifact to `user_feedback.json`
- define task-owned questions in `input/self_report_schema.yaml`
- map the feedback into a `user_feedback` context in
  `verifier/structured_output.json`

The shared `user_feedback` context is the default reporting home for subjective
signals such as satisfaction, effort, trust, or clarity. Family-specific
contexts can still add narrower slices when that improves analysis:

- chatbot may additionally emphasize conversation-only signals such as whether
  clarification questions were useful or whether the user felt understood
- web may optionally add an `experience` context for web-specific friction or UI
  journey analysis
- os-app may additionally surface persona alignment or archetype-specific
  summaries when local workflow tradeoffs matter

Recommended shared `user_feedback` facets:

- `overall_experience_rating`
- `feedback_reason`
- `need_constraint_satisfaction`
- `personal_preference_satisfaction`
- `trust_level`
- `effort_rating`
- `clarity_of_next_step`

Task families can extend this shared feedback contract with extra `task_*`
fields or family-specific fields when needed, but `user_feedback` should remain
the common subjective reporting entry point.

Across application tasks, prefer `shared-*` environment folders when the runtime
is reusable across multiple tasks. Reserve task-named environment folders for
truly task-specific app hosts or sidecar topologies.
