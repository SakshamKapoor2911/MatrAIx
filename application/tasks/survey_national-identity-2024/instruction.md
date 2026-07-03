# National Identity 2024 — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is adapted from the Pew Research Center topline **"Spring 2023 Global
Attitudes Survey, January 18, 2024 Release"** (source:
https://www.pewresearch.org/global/wp-content/uploads/sites/2/2024/01/gap_2024.01.18_national-identity_topline.pdf).

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — How important do you think it is for being truly a national of your country to have been born in your country?
- `a` — Very important
- `b` — Somewhat important
- `c` — Not too important
- `d` — Not at all important

### q1 — How important do you think it is for being truly a national of your country to be able to speak your country's national language?
- `a` — Very important
- `b` — Somewhat important
- `c` — Not too important
- `d` — Not at all important

### q2 — How important do you think it is for being truly a national of your country to be a member of your country's dominant religious denomination?
- `a` — Very important
- `b` — Somewhat important
- `c` — Not too important
- `d` — Not at all important

### q3 — How important do you think it is for being truly a national of your country to share your country's customs and traditions?
- `a` — Very important
- `b` — Somewhat important
- `c` — Not too important
- `d` — Not at all important

### q4 — How important do you think it is for being truly a national of your country to be a Muslim?
- `a` — Very important
- `b` — Somewhat important
- `c` — Not too important
- `d` — Not at all important

## Output

Save your submission to `/app/output/survey_responses.json`:

```json
{
  "responses": [
    {"question_id": "q0", "choice_id": "..."},
    {"question_id": "q1", "choice_id": "..."},
    {"question_id": "q2", "choice_id": "..."},
    {"question_id": "q3", "choice_id": "..."},
    {"question_id": "q4", "choice_id": "..."}
  ]
}
```

- Include one response object for every question q0…q4 listed above.
- `choice_id` must be one of the option letters listed under that question.
- Pick the option that best fits **your** persona; do not copy the `"..."` placeholder.
