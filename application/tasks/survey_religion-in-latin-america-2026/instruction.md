# Religion in Latin America 2026 — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is adapted from the Pew Research Center topline **"Spring 2024 Global
Attitudes Survey (Religion in Latin America), January 21, 2026"**
(source: https://www.pewresearch.org/wp-content/uploads/sites/20/2026/01/PR_2026.01.21_religion-in-latin-america_topline.pdf).

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — Would you describe yourself as Pentecostal, or not?
- `a` — Yes
- `b` — No

### q1 — Do you belong to …?
- `a` — A historical Protestant Church, for example, Baptist, Seventh Day Adventist, Methodist, Lutheran or Presbyterian
- `b` — A Pentecostal Church, for example, Assemblies of God or the Universal Church of the Kingdom of God
- `c` — Another Protestant Church
- `d` — Do not belong to a specific church

### q2 — How important is religion in your life: very important, somewhat important, not too important or not at all important?
- `a` — Very important
- `b` — Somewhat important
- `c` — Not too important
- `d` — Not at all important

### q3 — Aside from weddings and funerals, how often, if at all, do you attend religious services?
- `a` — Every day
- `b` — More than once a week
- `c` — Once a week
- `d` — Once or twice a month
- `e` — A few times a year
- `f` — Less often than that
- `g` — Never

### q4 — Outside of attending religious services, do you pray several times a day, once a day, a few times a week, once a week, a few times a month, less often than that, OR never?
- `a` — Several times a day
- `b` — Once a day
- `c` — A few times a week
- `d` — Once a week
- `e` — A few times a month
- `f` — Less often than that
- `g` — Never

### q5 — Do you believe in God, or not?
- `a` — Yes
- `b` — No

### q6 — Which of the following options comes closest to your views about life after death?
- `a` — There is definitely life after death
- `b` — There is probably life after death
- `c` — There is probably no life after death
- `d` — There is definitely no life after death

### q7 — Do you believe the following thing can have spirits or spiritual energies? Parts of nature, like mountains, rivers or trees
- `a` — Yes
- `b` — No

### q8 — Do you believe the following thing can have spirits or spiritual energies? Certain objects, like crystals, jewels or stones
- `a` — Yes
- `b` — No

### q9 — Do you believe the following thing can have spirits or spiritual energies? Animals
- `a` — Yes
- `b` — No

### q10 — Do you believe the following, or not? That spells, curses or other magic can influence people's lives
- `a` — Yes, believe
- `b` — No, do not believe

### q11 — Do you believe the following, or not? That the spirits of ancestors can help or harm you
- `a` — Yes, believe
- `b` — No, do not believe

### q12 — Do you believe the following, or not? In reincarnation – that people will be reborn in this world again and again
- `a` — Yes, believe
- `b` — No, do not believe

### q13 — Do you do the following practice, or not? Fast for certain periods during holy times
- `a` — Yes
- `b` — No

### q14 — Do you do the following practice, or not? Wear religious items or symbols, or carry them with you
- `a` — Yes
- `b` — No

### q15 — Do you do the following practice, or not? Consult a fortune teller, horoscope or other way to see the future
- `a` — Yes
- `b` — No

### q16 — Do you do the following practice, or not? Light incense or candles for spiritual or religious reasons
- `a` — Yes
- `b` — No

### q17 — Which statement comes closer to your view, even if neither is exactly right?
- `a` — There is something spiritual beyond the natural world, even if we cannot see it.
- `b` — The natural world is all there is.

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
