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