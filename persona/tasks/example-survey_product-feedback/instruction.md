The ClearQueue team is running a quick pricing check before they ship.

Materials in `/app/input/`:

- `product_brief.md` — tiers and features
- `survey_questions.md` — the form and answer codes

Read both and submit responses that match how you actually see it.

Save your submission to `/app/output/survey_responses.json`:

```json
{
  "participation": "continued",
  "responses": [
    {"question_id": "q0", "choice_id": "..."},
    {"question_id": "q1", "choice_id": "..."},
    {"question_id": "q2", "choice_id": "..."}
  ],
  "overall_interest": 3,
  "would_try_beta": false
}
```

- `participation` is `"continued"` or `"declined"` (see the form for which questions to include).
- Each response needs `question_id` and `choice_id` exactly as listed in `survey_questions.md`.
- Replace `"..."` with the real `choice_id` for that question — pick options that fit **your** spending posture; do not copy placeholder values.
- If `participation` is `"continued"`, include one response for each of q0–q6.
- `overall_interest` is 1 (not interested) through 5 (very interested).
- `would_try_beta` is `true` or `false`.
