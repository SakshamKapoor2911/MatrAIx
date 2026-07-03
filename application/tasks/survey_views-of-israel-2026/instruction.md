# Views of Israel (Spring 2026 Global Attitudes Survey) — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is adapted from the Pew Research Center topline **"Views of Israel, Spring 2026 Global Attitudes Survey, April 7, 2026 Release"**
(source: https://www.pewresearch.org/wp-content/uploads/sites/20/2026/04/SR_04.07.26_views-of-israel_topline.pdf).

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Please tell me if you have a very favorable, somewhat favorable, somewhat unfavorable, or very unfavorable opinion of Israel.
- `a` — Very favorable
- `b` — Somewhat favorable
- `c` — Somewhat unfavorable
- `d` — Very unfavorable

### q1 — Tell me how much confidence you have in Israeli Prime Minister Benjamin Netanyahu to do the right thing regarding world affairs.
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all
- `e` — Never heard of this person

### q2 — Thinking about some foreign policy issues facing the country, how confident are you that Donald Trump can make good decisions when it comes to the relationship between the U.S. and Israel?
- `a` — Very confident
- `b` — Somewhat confident
- `c` — Not too confident
- `d` — Not at all confident

### q3 — How important would you say the conflict between Israel and Hamas is to you personally?
- `a` — Very important
- `b` — Somewhat important
- `c` — Not too important
- `d` — Not at all important
- `e` — Not sure

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
