# Claude Code IDE Autonomy Survey

You are the assigned persona. Read the context below and answer every question as that person would.

Harbor runs this survey via **json_survey** (one-shot JSON completion). Your answers are saved to `/app/output/survey_result.json`.

---

## Context

Survey reactions to Claude Code's native VS Code extension and checkpoint feature, where a coding agent can edit code in the IDE, show inline diffs, and let developers roll back autonomous changes.

---

## Survey questions

Use exact `questionId` values and valid `value` strings from the instrument JSON schema.
Every answer needs a short **rationale** in the persona's voice and a **confidence** between 0 and 1.

### reviewable_edits

I would use Claude Code inside VS Code to make multi-file code edits if I could review inline diffs before accepting changes.

*Construct: coding_agent_reviewability*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### checkpoint_control

Checkpoint rollback would make me more comfortable letting a coding agent work autonomously on a complex task.

*Construct: agentic_coding_control_trust*

**Type:** Likert scale — set `value` to an integer **1**–**5**.

### adoption_concern

What would be your biggest concern before using this feature on a real codebase?

*Construct: coding_agent_adoption_barrier*

**Type:** Single choice — set `value` to one **choice_id**:
- `incorrect_code_changes`
- `hard_to_review_diffs`
- `security_or_secret_exposure`
- `too_much_autonomy`

### safe_first_task

What coding task would you feel safest delegating to Claude Code first?

*Construct: safe_initial_coding_agent_use_case*

**Type:** Free text — set `value` to a short string in the persona's voice.

---

## Output artifact

Save to `/app/output/survey_result.json`:

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
      "rationale": "Brief persona-grounded reason.",
      "confidence": 0.85
    }
  ],
  "trajectory": []
}
```

- Include one entry in `answers` for each question you answer.
- The runtime fills `trajectory` automatically if you leave it empty.