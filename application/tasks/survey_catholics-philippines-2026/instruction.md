# Religion in the Philippines — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is **paraphrased and adapted** from the Pew Research Center topline
**"Spring 2026 Global Attitudes Survey (Philippines), June 30, 2026 release"**
(source:
https://www.pewresearch.org/wp-content/uploads/sites/20/2026/06/SR_26.06.30_CatholicsPhilippines_topline.pdf);
the question and answer wording here is original, and only the survey's topics
and constructs derive from that source.

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Which faith, if any, do you identify with at present?
- `a` — Roman Catholic
- `b` — Protestant
- `c` — Iglesia ni Cristo
- `d` — Muslim
- `e` — Atheist
- `f` — Agnostic
- `g` — Some other religion
- `h` — No religion in particular
- `i` — Christian with no specific denomination
- `j` — Mormon (Church of Jesus Christ of Latter-day Saints/LDS)
- `k` — Buddhist
- `l` — Chinese traditional religion (for example Taoism, Confucianism or animism)
- `m` — Hindu
- `n` — Sikh

### q1 — Overall, how would you describe your view of Pope Leo — strongly positive, mildly positive, mildly negative or strongly negative?
- `a` — Strongly positive
- `b` — Mildly positive
- `c` — Mildly negative
- `d` — Strongly negative

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
