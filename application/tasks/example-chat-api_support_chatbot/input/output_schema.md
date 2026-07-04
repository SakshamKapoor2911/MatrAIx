# Output schema

Document **task-owned** artifacts here. Platform-managed eval files
(`transcript.json`, `application_result.json`) are described in
[`application/tasks/interface/chatbot/eval_artifacts.md`](../../interface/chatbot/eval_artifacts.md).

## `user_feedback.json`

Recommended when the task collects post-run persona self-report via
`input/self_report_schema.yaml`. Object with:

- `needConstraintSatisfaction`: short label such as `yes`, `partially`, or `no`
- `personalPreferenceSatisfaction`: short label such as `yes`, `partially`, or `no`
- `overallExperienceRating`: integer 1-10
- `reason`: concise explanation
- `askedUsefulClarificationQuestions`: boolean
- `clarifyingNotes`: concise note about which clarification questions helped
