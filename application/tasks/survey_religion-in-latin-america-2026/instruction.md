# Religion in Latin America 2026 — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is **paraphrased and adapted** from the Pew Research Center topline
**"Spring 2024 Global Attitudes Survey (Religion in Latin America), January 21, 2026"**
(source: https://www.pewresearch.org/wp-content/uploads/sites/20/2026/01/PR_2026.01.21_religion-in-latin-america_topline.pdf);
the question and answer wording here is original, and only the survey's topics and
constructs derive from that source.

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Do you think of yourself as Pentecostal, or would you say you are not?
- `a` — Yes
- `b` — No

### q1 — Which of these describes the church you are part of?
- `a` — A traditional Protestant denomination — such as Baptist, Seventh Day Adventist, Methodist, Lutheran or Presbyterian
- `b` — A Pentecostal congregation — such as the Assemblies of God or the Universal Church of the Kingdom of God
- `c` — Some other Protestant church
- `d` — I am not affiliated with any particular church

### q2 — How much does religion matter in your life — would you say very important, somewhat important, not too important, or not at all important?
- `a` — Very important
- `b` — Somewhat important
- `c` — Not too important
- `d` — Not at all important

### q3 — Setting aside weddings and funerals, how frequently do you go to religious services, if you do at all?
- `a` — Every day
- `b` — More than once a week
- `c` — Once a week
- `d` — Once or twice a month
- `e` — A few times a year
- `f` — Less frequently than that
- `g` — Never

### q4 — Apart from religious services, how often do you pray — several times daily, once daily, a few times weekly, once a week, a few times monthly, less often than that, or not at all?
- `a` — Several times a day
- `b` — Once a day
- `c` — A few times a week
- `d` — Once a week
- `e` — A few times a month
- `f` — Less frequently than that
- `g` — Never

### q5 — Would you say you believe in God, or that you do not?
- `a` — Yes
- `b` — No

### q6 — Which of these statements best matches what you think about an afterlife?
- `a` — Life after death is certain
- `b` — Life after death is likely
- `c` — Life after death is unlikely
- `d` — There is certainly no life after death

### q7 — Do you think the following can hold spirits or spiritual energy? Elements of nature, such as mountains, rivers or trees
- `a` — Yes
- `b` — No

### q8 — Do you think the following can hold spirits or spiritual energy? Particular objects, such as crystals, gems or stones
- `a` — Yes
- `b` — No

### q9 — Do you think the following can hold spirits or spiritual energy? Animals
- `a` — Yes
- `b` — No

### q10 — Do you hold the following belief, or not? That spells, curses or other magic are able to shape people's lives
- `a` — Yes, believe
- `b` — No, do not believe

### q11 — Do you hold the following belief, or not? That the spirits of your ancestors are able to help or harm you
- `a` — Yes, believe
- `b` — No, do not believe

### q12 — Do you hold the following belief, or not? In reincarnation — that a person is born again into this world repeatedly
- `a` — Yes, believe
- `b` — No, do not believe

### q13 — Is this something you do, or not? Go without food during sacred periods
- `a` — Yes
- `b` — No

### q14 — Is this something you do, or not? Put on religious items or symbols, or keep them on you
- `a` — Yes
- `b` — No

### q15 — Is this something you do, or not? Turn to a fortune teller, horoscope or another method for glimpsing the future
- `a` — Yes
- `b` — No

### q16 — Is this something you do, or not? Burn incense or candles for spiritual or religious purposes
- `a` — Yes
- `b` — No

### q17 — Which of these views is closer to yours, even if neither captures it perfectly?
- `a` — Something spiritual exists beyond the physical world, even if it is invisible to us.
- `b` — Nothing exists beyond the physical world.

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

- Include one response object for every question q0…q17 listed above.
- `choice_id` must be one of the option letters listed under that question.
- Pick the option that best fits **your** persona; do not copy the `"..."` placeholder.
