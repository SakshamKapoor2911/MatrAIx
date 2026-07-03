# U.S. Image Abroad 2024 — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This survey
is **paraphrased and adapted** from the Pew Research Center topline **"Spring 2024
Global Attitudes Survey (U.S. Image Abroad), June 11, 2024"**
(source: https://www.pewresearch.org/wp-content/uploads/sites/20/2024/06/gap_2024.06.11_us-image-2024_topline.pdf);
the question and answer wording here is original, and only the survey's topics and
constructs derive from that source.

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Overall, how do you regard the United States — would you say your view is strongly positive, mildly positive, mildly negative, or strongly negative?
- `a` — Strongly positive
- `b` — Mildly positive
- `c` — Mildly negative
- `d` — Strongly negative

### q1 — When it comes to handling international matters wisely, how much trust do you place in U.S. President Joe Biden?
- `a` — A great deal of trust
- `b` — A fair amount
- `c` — Not much
- `d` — None at all

### q2 — When it comes to handling international matters wisely, how much trust do you place in Former U.S. President Donald Trump?
- `a` — A great deal of trust
- `b` — A fair amount
- `c` — Not much
- `d` — None at all

### q3 — When it comes to handling international matters wisely, how much trust do you place in Chinese President Xi Jinping?
- `a` — A great deal of trust
- `b` — A fair amount
- `c` — Not much
- `d` — None at all

### q4 — When it comes to handling international matters wisely, how much trust do you place in Russian President Vladimir Putin?
- `a` — A great deal of trust
- `b` — A fair amount
- `c` — Not much
- `d` — None at all

### q5 — When it comes to handling international matters wisely, how much trust do you place in French President Emmanuel Macron?
- `a` — A great deal of trust
- `b` — A fair amount
- `c` — Not much
- `d` — None at all

### q6 — Considering U.S. President Joe Biden, how do you rate his handling of problems in the world economy — do you strongly approve, somewhat approve, somewhat disapprove, or strongly disapprove?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q7 — Considering U.S. President Joe Biden, how do you rate his handling of climate change — do you strongly approve, somewhat approve, somewhat disapprove, or strongly disapprove?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q8 — Considering U.S. President Joe Biden, how do you rate his handling of relations with China — do you strongly approve, somewhat approve, somewhat disapprove, or strongly disapprove?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q9 — Considering U.S. President Joe Biden, how do you rate his handling of the war between Russia and Ukraine — do you strongly approve, somewhat approve, somewhat disapprove, or strongly disapprove?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q10 — Considering U.S. President Joe Biden, how do you rate his handling of the war between Israel and Hamas — do you strongly approve, somewhat approve, somewhat disapprove, or strongly disapprove?
- `a` — Strongly approve
- `b` — Somewhat approve
- `c` — Somewhat disapprove
- `d` — Strongly disapprove

### q11 — Even if none fits perfectly, which of these best matches how you see it? American democracy …
- `a` — Sets a model that other nations would do well to imitate
- `b` — Once set a good model, though it has fallen short of that lately
- `c` — Has never offered a model worth other nations imitating

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
