# U.S. Image Abroad 2024 — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is adapted from the Pew Research Center topline **"Spring 2024 Global
Attitudes Survey (U.S. Image Abroad), June 11, 2024"**
(source: https://www.pewresearch.org/wp-content/uploads/sites/20/2024/06/gap_2024.06.11_us-image-2024_topline.pdf).

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Please tell me if you have a very favorable, somewhat favorable, somewhat unfavorable, or very unfavorable opinion of the United States.
- `a` — Very favorable
- `b` — Somewhat favorable
- `c` — Somewhat unfavorable
- `d` — Very unfavorable

### q1 — Tell me how much confidence you have in U.S. President Joe Biden to do the right thing regarding world affairs.
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q2 — Tell me how much confidence you have in Former U.S. President Donald Trump to do the right thing regarding world affairs.
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q3 — Tell me how much confidence you have in Chinese President Xi Jinping to do the right thing regarding world affairs.
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q4 — Tell me how much confidence you have in Russian President Vladimir Putin to do the right thing regarding world affairs.
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q5 — Tell me how much confidence you have in French President Emmanuel Macron to do the right thing regarding world affairs.
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q6 — Thinking about U.S. president Joe Biden, do you strongly approve, somewhat approve, somewhat disapprove or strongly disapprove of the way he is dealing with global economic problems?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q7 — Thinking about U.S. president Joe Biden, do you strongly approve, somewhat approve, somewhat disapprove or strongly disapprove of the way he is dealing with climate change?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q8 — Thinking about U.S. president Joe Biden, do you strongly approve, somewhat approve, somewhat disapprove or strongly disapprove of the way he is dealing with China?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q9 — Thinking about U.S. president Joe Biden, do you strongly approve, somewhat approve, somewhat disapprove or strongly disapprove of the way he is dealing with the conflict between Russia and Ukraine?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q10 — Thinking about U.S. president Joe Biden, do you strongly approve, somewhat approve, somewhat disapprove or strongly disapprove of the way he is dealing with the conflict between Israel and Hamas?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q11 — Which statement comes closest to your view, even if none are exactly right? Democracy in the United States …
- `a` — Is a good example for other countries to follow
- `b` — Used to be a good example, but has not been in recent years
- `c` — Has never been a good example for other countries to follow

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

- Include one response object for every question q0…q11 listed above.
- `choice_id` must be one of the option letters listed under that question.
- Pick the option that best fits **your** persona; do not copy the `"..."` placeholder.
