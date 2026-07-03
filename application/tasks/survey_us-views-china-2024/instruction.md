# U.S. Views of China (2024) — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is adapted from the Pew Research Center topline **"Spring 2024 Global Attitudes Survey, May 1, 2024 Release"**
(source: https://www.pewresearch.org/wp-content/uploads/sites/20/2024/04/pg_2024.05.01_us-views-china_topline.pdf).

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Please tell me if you have a very favorable, somewhat favorable, somewhat unfavorable, or very unfavorable opinion of China?
- `a` — Very favorable
- `b` — Somewhat favorable
- `c` — Somewhat unfavorable
- `d` — Very unfavorable

### q1 — Tell me how much confidence you have in Chinese President Xi Jinping to do the right thing regarding world affairs – a lot of confidence, some confidence, not too much confidence, or no confidence at all.
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all
- `e` — Never heard of this person

### q2 — Thinking about China, would you say its influence in the world in recent years has been getting stronger, getting weaker or staying about the same?
- `a` — Getting stronger
- `b` — Getting weaker
- `c` — Staying about the same

### q3 — On balance, do you think of China as a partner of the U.S., a competitor of the U.S. or an enemy of the U.S.?
- `a` — Partner
- `b` — Competitor
- `c` — Enemy

### q4 — How much influence do you think China is having on economic conditions in (survey country) – a great deal of influence, a fair amount of influence, not too much influence, or no influence at all?
- `a` — Great deal
- `b` — Fair amount
- `c` — Not too much
- `d` — No influence at all

### q5 — Right now, is China having a positive or negative impact on economic conditions in (survey country)?
- `a` — Positive
- `b` — Negative

### q6 — How concerned are you, if at all, about territorial disputes between China and neighboring countries – very concerned, somewhat concerned, not too concerned or not at all concerned?
- `a` — Very concerned
- `b` — Somewhat concerned
- `c` — Not too concerned
- `d` — Not at all concerned
- `e` — Not sure

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
