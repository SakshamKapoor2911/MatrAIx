# U.S. Image 2025 — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is **paraphrased and adapted** from the Pew Research Center topline
**"Spring 2025 Global Attitudes Survey (U.S. Image), June 11, 2025"**
(source: https://www.pewresearch.org/wp-content/uploads/sites/20/2025/06/gap_2025_06_11_us-image-2025_topline.pdf);
the question and answer wording here is original, and only the survey's topics and
constructs derive from that source.

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Overall, is your view of the United States strongly positive, mildly positive, mildly negative, or strongly negative?
- `a` — Strongly positive
- `b` — Mildly positive
- `c` — Mildly negative
- `d` — Strongly negative

### q1 — How much do you trust U.S. President Donald Trump to act appropriately when it comes to international affairs?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q2 — How much do you trust Chinese President Xi Jinping to act appropriately when it comes to international affairs?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q3 — How much do you trust Russian President Vladimir Putin to act appropriately when it comes to international affairs?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q4 — How much do you trust French President Emmanuel Macron to act appropriately when it comes to international affairs?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q5 — Would you describe U.S. President Donald Trump as well-suited for the presidency?
- `a` — Yes
- `b` — No

### q6 — Would you describe U.S. President Donald Trump as a forceful leader?
- `a` — Yes
- `b` — No

### q7 — Would you describe U.S. President Donald Trump as truthful?
- `a` — Yes
- `b` — No

### q8 — Would you describe U.S. President Donald Trump as a threat?
- `a` — Yes
- `b` — No

### q9 — Would you describe U.S. President Donald Trump as capable of grasping complicated issues?
- `a` — Yes
- `b` — No

### q10 — Would you describe U.S. President Donald Trump as diplomatic?
- `a` — Yes
- `b` — No

### q11 — Would you describe U.S. President Donald Trump as arrogant?
- `a` — Yes
- `b` — No

### q12 — How much do you trust U.S. President Donald Trump to deal with worldwide economic troubles?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q13 — How much do you trust U.S. President Donald Trump to deal with climate change?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q14 — How much do you trust U.S. President Donald Trump to manage the U.S.–China relationship?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q15 — How much do you trust U.S. President Donald Trump to manage the war between Russia and Ukraine?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q16 — How much do you trust U.S. President Donald Trump to manage the dispute between Israel and its neighbors?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q17 — How much do you trust U.S. President Donald Trump to manage immigration policy in the United States?
- `a` — A great deal of trust
- `b` — A fair amount of trust
- `c` — Not very much trust
- `d` — No trust whatsoever

### q18 — When you consider how democracy functions in the United States, would you say it performs very well, fairly well, fairly badly, or very badly?
- `a` — Very well
- `b` — Fairly well
- `c` — Fairly badly
- `d` — Very badly

### q19 — Within the United States, how intense are the tensions between backers of rival political parties — very intense, intense, not very intense, or nonexistent?
- `a` — Very intense conflicts
- `b` — Intense conflicts
- `c` — Not very intense conflicts
- `d` — No conflicts at all

### q20 — As of today, which SINGLE one of these do you regard as the top economic power in the world?
- `a` — The United States
- `b` — China
- `c` — Japan
- `d` — The nations of the European Union
- `e` — Some other country
- `f` — None; no single country leads economically

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
</output>
