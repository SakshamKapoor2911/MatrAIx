# News and Social Media — Persona Survey

You are a survey respondent. Answer every question below exactly as your assigned
persona would — based on their demographics, values, and circumstances. This
survey is adapted from the Pew Research Center topline **"News and Social Media
(American Trends Panel Wave 73, fielded August 31–September 7, 2020; released
January 2021)"** (source: https://www.pewresearch.org/journalism/wp-content/uploads/sites/8/2021/01/PJ_2021.01.12_News-and-Social-Media_TOPLINE.pdf).

Choose exactly one option (its `choice_id`) per question. Do not leave any question
blank and do not copy placeholder values.

## Questions

### q0 — How often do you get news from television?
- `a` — Often
- `b` — Sometimes
- `c` — Rarely
- `d` — Never

### q1 — How often do you get news from radio?
- `a` — Often
- `b` — Sometimes
- `c` — Rarely
- `d` — Never

### q2 — How often do you get news from print publications?
- `a` — Often
- `b` — Sometimes
- `c` — Rarely
- `d` — Never

### q3 — How often do you get news from a smartphone, computer or tablet?
- `a` — Often
- `b` — Sometimes
- `c` — Rarely
- `d` — Never

### q4 — Now thinking about the news you get on a smartphone, computer, or tablet, how often do you get news from news websites or apps?
- `a` — Often
- `b` — Sometimes
- `c` — Rarely
- `d` — Never

### q5 — Now thinking about the news you get on a smartphone, computer, or tablet, how often do you get news from social media such as Facebook, Twitter, or Instagram?
- `a` — Often
- `b` — Sometimes
- `c` — Rarely
- `d` — Never

### q6 — Now thinking about the news you get on a smartphone, computer, or tablet, how often do you get news from search through Google or other search engines?
- `a` — Often
- `b` — Sometimes
- `c` — Rarely
- `d` — Never

### q7 — Now thinking about the news you get on a smartphone, computer, or tablet, how often do you get news from podcasts?
- `a` — Often
- `b` — Sometimes
- `c` — Rarely
- `d` — Never

### q8 — Which do you prefer for getting news?
- `a` — Television
- `b` — Radio
- `c` — Print publications
- `d` — News websites or apps
- `e` — Social media such as Facebook, Twitter, or Instagram
- `f` — Search through Google or other search engines
- `g` — Podcasts

### q9 — Do you use Twitter?
- `a` — Yes, use this
- `b` — No, do not use this

### q10 — Do you use Instagram?
- `a` — Yes, use this
- `b` — No, do not use this

### q11 — Do you use Facebook?
- `a` — Yes, use this
- `b` — No, do not use this

### q12 — Do you use Snapchat?
- `a` — Yes, use this
- `b` — No, do not use this

### q13 — Do you use YouTube?
- `a` — Yes, use this
- `b` — No, do not use this

### q14 — Do you use LinkedIn?
- `a` — Yes, use this
- `b` — No, do not use this

### q15 — Do you use Reddit?
- `a` — Yes, use this
- `b` — No, do not use this

### q16 — Do you use Tumblr?
- `a` — Yes, use this
- `b` — No, do not use this

### q17 — Do you use WhatsApp?
- `a` — Yes, use this
- `b` — No, do not use this

### q18 — Do you use TikTok?
- `a` — Yes, use this
- `b` — No, do not use this

### q19 — Do you use Twitch?
- `a` — Yes, use this
- `b` — No, do not use this

### q20 — Do you REGULARLY get news or news headlines on Twitter? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q21 — Do you REGULARLY get news or news headlines on Instagram? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q22 — Do you REGULARLY get news or news headlines on Facebook? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q23 — Do you REGULARLY get news or news headlines on Snapchat? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q24 — Do you REGULARLY get news or news headlines on YouTube? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q25 — Do you REGULARLY get news or news headlines on LinkedIn? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q26 — Do you REGULARLY get news or news headlines on Reddit? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q27 — Do you REGULARLY get news or news headlines on Tumblr? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q28 — Do you REGULARLY get news or news headlines on WhatsApp? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q29 — Do you REGULARLY get news or news headlines on TikTok? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q30 — Do you REGULARLY get news or news headlines on Twitch? (By news we mean information about events and issues that involve more than just your friends or family.)
- `a` — Yes, regularly get news on this
- `b` — No, don't regularly get news on this

### q31 — Which of the following best describes how you approach news stories from social media sites, even if neither is exactly right? I expect the news I see on social media will…
- `a` — Largely be accurate
- `b` — Largely be inaccurate

### q32 — Overall, would you say news on social media has…
- `a` — Helped you better understand current events
- `b` — Made you more confused about current events
- `c` — Not made much of a difference

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

- Include one response object for every question q0…q32 listed above.
- `choice_id` must be one of the option letters listed under that question.
- Pick the option that best fits **your** persona; do not copy the `"..."` placeholder.
