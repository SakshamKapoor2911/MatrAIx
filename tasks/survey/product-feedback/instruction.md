# Product concept survey (FocusLoop)

You are participating in a **product concept test** for a new app. Read the materials in `/app/input/`:

- `product_brief.md` — what FocusLoop is proposing
- `survey_questions.md` — questions to answer

Answer every question **as yourself** (your persona), based on how you would genuinely react to this concept. Do not invent product facts that are not in the brief.

Write your submission to `/app/output/survey_responses.json`:

```json
{
  "responses": [
    {"question_id": "q1", "answer": "<your answer>"},
    {"question_id": "q2", "answer": "<your answer>"}
  ],
  "overall_interest": 3,
  "would_try_beta": true,
  "summary": "<2–4 sentences explaining your overall stance>"
}
```

Rules:

- Include **every** `question_id` listed in `survey_questions.md`.
- `overall_interest` must be an integer from **1** (not interested) to **5** (very interested).
- `would_try_beta` must be `true` or `false`.
- `summary` must be at least **20 characters**.

**Suggested agent:** `persona-claude-code`. See `docs/applications/task-guide.md`.
