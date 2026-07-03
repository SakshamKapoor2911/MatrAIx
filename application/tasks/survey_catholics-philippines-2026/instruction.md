# Religion in the Philippines — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is adapted from the Pew Research Center topline **"Spring 2026 Global
Attitudes Survey (Philippines), June 30, 2026 release"** (source:
https://www.pewresearch.org/wp-content/uploads/sites/20/2026/06/SR_26.06.30_CatholicsPhilippines_topline.pdf).

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — What is your current religion, if any?
- `a` — Roman Catholic
- `b` — Protestant
- `c` — Iglesia ni Cristo
- `d` — Muslim
- `e` — Atheist
- `f` — Agnostic
- `g` — Something else
- `h` — Nothing in particular
- `i` — Just a Christian
- `j` — Mormon (Church of Jesus Christ of Latter-day Saints/LDS)
- `k` — Buddhist
- `l` — Chinese traditional religion (for example Taoism, Confucianism or animism)
- `m` — Hindu
- `n` — Sikh

### q1 — Is your overall opinion of Pope Leo very favorable, somewhat favorable, somewhat unfavorable or very unfavorable?
- `a` — Very favorable
- `b` — Somewhat favorable
- `c` — Somewhat unfavorable
- `d` — Very unfavorable

## Output

Save your submission to `/app/output/survey_responses.json`:

```json
{
  "responses": [
    {"question_id": "q0", "choice_id": "..."},
    {"question_id": "q1", "choice_id": "..."}
  ]
}
```

- Include one response object for every question q0…q1 listed above.
- `choice_id` must be one of the option letters listed under that question.
- Pick the option that best fits **your** persona; do not copy the `"..."` placeholder.
