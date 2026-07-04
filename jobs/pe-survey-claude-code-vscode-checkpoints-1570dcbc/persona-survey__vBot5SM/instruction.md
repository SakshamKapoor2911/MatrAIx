# Claude Code IDE Autonomy Survey

## Task instruction

Complete the survey using the provided context and structured questionnaire.

Return one JSON object that matches `input/output_schema.md`.

Requirements:

- Answer every required question in `input/questionnaire.yaml`.
- Use exact `questionId` values from the questionnaire.
- For choice questions, use the exact choice ids.
- For likert questions, use an integer within the declared range.
- Keep each `rationale` concise and specific to the selected answer.
- Return only the JSON object.

## Context

Survey reactions to Claude Code's native VS Code extension and checkpoint
feature, where a coding agent can edit code in the IDE, show inline diffs, and
let developers roll back autonomous changes.

## Questionnaire

# Claude Code IDE Autonomy Survey

Use exact `questionId` and valid choice ids.

## reviewable_edits

Prompt: I would use Claude Code inside VS Code to make multi-file code edits if I could review inline diffs before accepting changes.

- Construct: `coding_agent_reviewability`
- Type: `likert`
- Required: `true`
- Scale: `1`-`5`

Rate with an integer between **1** and **5**.


## checkpoint_control

Prompt: Checkpoint rollback would make me more comfortable letting a coding agent work autonomously on a complex task.

- Construct: `agentic_coding_control_trust`
- Type: `likert`
- Required: `true`
- Scale: `1`-`5`

Rate with an integer between **1** and **5**.


## adoption_concern

Prompt: What would be your biggest concern before using this feature on a real codebase?

- Construct: `coding_agent_adoption_barrier`
- Type: `single_choice`
- Required: `true`

| choice_id | label |
|-----------|-------|
| `incorrect_code_changes` | Incorrect code changes |
| `hard_to_review_diffs` | Hard to review diffs |
| `security_or_secret_exposure` | Security or secret exposure |
| `too_much_autonomy` | Too much autonomy |

## safe_first_task

Prompt: What coding task would you feel safest delegating to Claude Code first?

- Construct: `safe_initial_coding_agent_use_case`
- Type: `free_text`
- Required: `true`

Respond in a short free-text answer.

## Output schema

Return strict JSON matching this shape.

```json
{
  "instrument": {
    "id": "software_claude_code_vscode_checkpoints_v1",
    "title": "Claude Code IDE Autonomy Survey"
  },
  "answers": [
    {
      "questionId": "reviewable_edits",
      "value": "<answer>",
      "rationale": "Brief answer-specific reason.",
      "confidence": 0.85
    }
  ]
}
```

Rules:

- Include one answer entry for every required question.
- Use exact `questionId` values from `questionnaire.yaml`.
- For choice questions, `value` must be the exact choice id.
- For likert questions, `value` must be an integer from 1 to 5.