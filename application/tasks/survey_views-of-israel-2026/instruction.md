# Views of Israel (Spring 2026 Global Attitudes Survey) — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This survey is **paraphrased and adapted** from the Pew Research Center topline **"Views of Israel, Spring 2026 Global Attitudes Survey, April 7, 2026 Release"** (source: https://www.pewresearch.org/wp-content/uploads/sites/20/2026/04/SR_04.07.26_views-of-israel_topline.pdf); the question and answer wording here is original, and only the survey's topics and constructs derive from that source.

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Overall, how would you describe the way you view Israel — strongly positive, mildly positive, mildly negative, or strongly negative?
- `a` — Strongly positive view
- `b` — Mildly positive view
- `c` — Mildly negative view
- `d` — Strongly negative view

### q1 — When it comes to handling international matters wisely, how much do you trust Israeli Prime Minister Benjamin Netanyahu to act appropriately?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not much trust
- `d` — No trust whatsoever
- `e` — I'm not familiar with this person

### q2 — Turning to foreign policy challenges the country faces, how much faith do you have that Donald Trump will handle U.S.–Israel relations well?
- `a` — A great deal of faith
- `b` — A moderate amount of faith
- `c` — Only a little faith
- `d` — No faith at all

### q3 — For you personally, how much does the fighting between Israel and Hamas matter?
- `a` — Matters a great deal
- `b` — Matters somewhat
- `c` — Matters only a little
- `d` — Does not matter at all
- `e` — Uncertain

## Output

Save your submission to `/app/output/survey_responses.json`:

```json
{
  "responses": [
    {"question_id": "q0", "choice_id": "..."},
    {"question_id": "q1", "choice_id": "..."},
    {"question_id": "q2", "choice_id": "..."},
    {"question_id": "q3", "choice_id": "..."}
  ]
}
```

- Include one response object for every question q0…q3 listed above.
- `choice_id` must be one of the option letters listed under that question.
- Pick the option that best fits **your** persona; do not copy the `"..."` placeholder.
