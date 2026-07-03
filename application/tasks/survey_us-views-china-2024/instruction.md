# U.S. Views of China (2024) — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is **paraphrased and adapted** from the Pew Research Center topline **"Spring 2024 Global Attitudes Survey, May 1, 2024 Release"**
(source: https://www.pewresearch.org/wp-content/uploads/sites/20/2024/04/pg_2024.05.01_us-views-china_topline.pdf); the question and answer wording here is original, and only the survey's topics and constructs derive from that source.

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Overall, how would you rate your view of China — strongly positive, mildly positive, mildly negative, or strongly negative?
- `a` — Strongly positive
- `b` — Mildly positive
- `c` — Mildly negative
- `d` — Strongly negative

### q1 — When it comes to handling global matters wisely, how much trust do you place in Chinese President Xi Jinping — a great deal, a fair amount, not much, or none at all?
- `a` — A great deal of trust
- `b` — A fair amount
- `c` — Not much
- `d` — None at all
- `e` — Have never heard of this person

### q2 — Over the past few years, do you see China's sway around the world as rising, declining, or holding roughly steady?
- `a` — Rising
- `b` — Declining
- `c` — Holding roughly steady

### q3 — All things considered, do you regard China mainly as an ally of the U.S., a rival of the U.S., or a foe of the U.S.?
- `a` — Ally
- `b` — Rival
- `c` — Foe

### q4 — To what extent do you believe China shapes the economy of (survey country) — a great deal, a fair amount, not much, or none at all?
- `a` — A great deal
- `b` — A fair amount
- `c` — Not much
- `d` — None at all

### q5 — At present, is China's effect on the economy of (survey country) helpful or harmful?
- `a` — Helpful
- `b` — Harmful

### q6 — To what degree, if any, do border and territorial conflicts between China and its neighbors worry you — greatly, somewhat, only slightly, or not in the least?
- `a` — Greatly worried
- `b` — Somewhat worried
- `c` — Only slightly worried
- `d` — Not worried in the least
- `e` — Unsure

## Output

Save your submission to `/app/output/survey_responses.json`:

```json
{
  "responses": [
    {"question_id": "q0", "choice_id": "..."},
    {"question_id": "q1", "choice_id": "..."},
    {"question_id": "q2", "choice_id": "..."},
    {"question_id": "q3", "choice_id": "..."},
    {"question_id": "q4", "choice_id": "..."},
    {"question_id": "q5", "choice_id": "..."},
    {"question_id": "q6", "choice_id": "..."}
  ]
}
```

- Include one response object for every question q0…q6 listed above.
- `choice_id` must be one of the option letters listed under that question.
- Pick the option that best fits **your** persona; do not copy the `"..."` placeholder.
