# National Identity 2024 — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is **paraphrased and adapted** from the Pew Research Center topline
**"Spring 2023 Global Attitudes Survey, January 18, 2024 Release"** (source:
https://www.pewresearch.org/global/wp-content/uploads/sites/2/2024/01/gap_2024.01.18_national-identity_topline.pdf);
the question and answer wording here is original, and only the survey's topics and
constructs derive from that source.

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — In your view, how essential is having been born within your country for someone to genuinely count as one of its nationals?
- `a` — Extremely important
- `b` — Fairly important
- `c` — Only slightly important
- `d` — Not important at all

### q1 — In your view, how essential is being able to speak your country's national language for someone to genuinely count as one of its nationals?
- `a` — Extremely important
- `b` — Fairly important
- `c` — Only slightly important
- `d` — Not important at all

### q2 — In your view, how essential is belonging to your country's main religious denomination for someone to genuinely count as one of its nationals?
- `a` — Extremely important
- `b` — Fairly important
- `c` — Only slightly important
- `d` — Not important at all

### q3 — In your view, how essential is sharing your country's customs and traditions for someone to genuinely count as one of its nationals?
- `a` — Extremely important
- `b` — Fairly important
- `c` — Only slightly important
- `d` — Not important at all

### q4 — In your view, how essential is being a Muslim for someone to genuinely count as one of its nationals?
- `a` — Extremely important
- `b` — Fairly important
- `c` — Only slightly important
- `d` — Not important at all

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
