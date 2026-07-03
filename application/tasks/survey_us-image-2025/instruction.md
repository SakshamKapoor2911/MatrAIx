# U.S. Image 2025 — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is adapted from the Pew Research Center topline **"Spring 2025 Global
Attitudes Survey (U.S. Image), June 11, 2025"**
(source: https://www.pewresearch.org/wp-content/uploads/sites/20/2025/06/gap_2025_06_11_us-image-2025_topline.pdf).

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Do you have a very favorable, somewhat favorable, somewhat unfavorable, or very unfavorable opinion of the United States?
- `a` — Very favorable
- `b` — Somewhat favorable
- `c` — Somewhat unfavorable
- `d` — Very unfavorable

### q1 — How much confidence do you have in U.S. President Donald Trump to do the right thing regarding world affairs?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q2 — How much confidence do you have in Chinese President Xi Jinping to do the right thing regarding world affairs?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q3 — How much confidence do you have in Russian President Vladimir Putin to do the right thing regarding world affairs?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q4 — How much confidence do you have in French President Emmanuel Macron to do the right thing regarding world affairs?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q5 — Do you think of U.S. President Donald Trump as well-qualified to be president?
- `a` — Yes
- `b` — No

### q6 — Do you think of U.S. President Donald Trump as a strong leader?
- `a` — Yes
- `b` — No

### q7 — Do you think of U.S. President Donald Trump as honest?
- `a` — Yes
- `b` — No

### q8 — Do you think of U.S. President Donald Trump as dangerous?
- `a` — Yes
- `b` — No

### q9 — Do you think of U.S. President Donald Trump as able to understand complex problems?
- `a` — Yes
- `b` — No

### q10 — Do you think of U.S. President Donald Trump as diplomatic?
- `a` — Yes
- `b` — No

### q11 — Do you think of U.S. President Donald Trump as arrogant?
- `a` — Yes
- `b` — No

### q12 — How much confidence do you have in U.S. President Donald Trump to handle global economic problems?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q13 — How much confidence do you have in U.S. President Donald Trump to handle climate change?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q14 — How much confidence do you have in U.S. President Donald Trump to handle relations between China and the United States?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q15 — How much confidence do you have in U.S. President Donald Trump to handle the conflict between Russia and Ukraine?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q16 — How much confidence do you have in U.S. President Donald Trump to handle the conflict between Israel and its neighbors?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q17 — How much confidence do you have in U.S. President Donald Trump to handle United States' immigration policies?
- `a` — A lot of confidence
- `b` — Some confidence
- `c` — Not too much confidence
- `d` — No confidence at all

### q18 — Thinking about democracy in the United States, would you say it works very well, somewhat well, somewhat poorly or very poorly?
- `a` — Very well
- `b` — Somewhat well
- `c` — Somewhat poorly
- `d` — Very poorly

### q19 — In the United States, are the conflicts between people who support different political parties very strong, strong, not very strong or are there no conflicts at all?
- `a` — Very strong conflicts
- `b` — Strong conflicts
- `c` — Not very strong conflicts
- `d` — There are no conflicts at all

### q20 — Today, which ONE of the following do you think is the world's leading economic power?
- `a` — The United States
- `b` — China
- `c` — Japan
- `d` — The countries of the European Union
- `e` — Other
- `f` — None; there is no leading economic power

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

- Include one response object for every question q0…q20 listed above.
- `choice_id` must be one of the option letters listed under that question.
- Pick the option that best fits **your** persona; do not copy the `"..."` placeholder.
