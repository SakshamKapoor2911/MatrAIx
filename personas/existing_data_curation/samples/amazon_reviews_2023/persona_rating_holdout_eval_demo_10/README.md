# Persona Rating Holdout Demo Outputs

Small tracked demo artifact bundle for the V1 Amazon persona rating holdout
evaluation flow. These files were copied out of the ignored `raw/` workspace so
the PR can show an end-to-end example without committing full raw histories.

Contents:

- `prediction_targets_demo_5_per_user.jsonl`: 50 blind prediction targets, 5
  holdout reviews for each of 10 users.
- `persona_prediction_prompts_demo_5_per_user.jsonl`: dry-run prompt payloads
  used for the LLM prediction pass.
- `persona_predictions_demo_5_per_user.jsonl`: OpenAI API persona rating
  predictions for the 50 demo targets.
- `scored_5_per_user/`: evaluator outputs for the same 50-target demo subset,
  including labeled targets, blind targets, selected users, `summary.json`, and
  `report.md`.

The demo prediction input uses sanitized persona YAML features and excludes
product metadata, heldout review text/title, true ratings, cohort labels, and
explicit historical rating/star summaries.
