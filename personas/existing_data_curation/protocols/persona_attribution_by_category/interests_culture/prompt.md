You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Interests: Culture  (74 dimensions)

Return ONLY JSON with this shape (no markdown, no commentary):

{
  "fields": [
    {
      "field_id": "<one id from the DIMENSIONS list below>",
      "value": "<exactly one allowed value for that id, copied verbatim, or null>",
      "confidence": 0.0,
      "evidence": "<short quote copied from profile_text>",
      "assignment_type": "direct"
    }
  ],
  "reported_model": null,
  "model_source": "user_declared",
  "model_confidence": "user_declared"
}

Allowed assignment_type values:
- direct: explicitly stated in the text.
- structured_claim: derived from structured facts in the input.
- summary_inference: reasonable inference from the profile summary.
- unsupported: not supported by the input.

Rules:
- Emit exactly one object per dimension listed below, in the same order.
- value MUST be exactly one of that dimension's allowed values (copy it verbatim), OR null.
- If the profile does not support a dimension, set value to null and assignment_type to "unsupported".
- Every non-null value MUST include a short evidence quote copied from profile_text.
- Do not infer private, sensitive, or psychological traits unless directly stated; when unsure, prefer null/unsupported.
- Return valid JSON only, with no markdown.

DIMENSIONS (field_id — label — description — allowed values):
- cult_united_states — Culture: United States — Familiarity with United States culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_canada — Culture: Canada — Familiarity with Canada culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_mexico — Culture: Mexico — Familiarity with Mexico culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_brazil — Culture: Brazil — Familiarity with Brazil culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_argentina — Culture: Argentina — Familiarity with Argentina culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_united_kingdom — Culture: United Kingdom — Familiarity with United Kingdom culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_france — Culture: France — Familiarity with France culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_germany — Culture: Germany — Familiarity with Germany culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_italy — Culture: Italy — Familiarity with Italy culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_spain — Culture: Spain — Familiarity with Spain culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_netherlands — Culture: Netherlands — Familiarity with Netherlands culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_sweden — Culture: Sweden — Familiarity with Sweden culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_poland — Culture: Poland — Familiarity with Poland culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_russia — Culture: Russia — Familiarity with Russia culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_turkey — Culture: Turkey — Familiarity with Turkey culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_egypt — Culture: Egypt — Familiarity with Egypt culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_saudi_arabia — Culture: Saudi Arabia — Familiarity with Saudi Arabia culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_uae — Culture: UAE — Familiarity with UAE culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_israel — Culture: Israel — Familiarity with Israel culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_iran — Culture: Iran — Familiarity with Iran culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_nigeria — Culture: Nigeria — Familiarity with Nigeria culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_kenya — Culture: Kenya — Familiarity with Kenya culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_south_africa — Culture: South Africa — Familiarity with South Africa culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_ethiopia — Culture: Ethiopia — Familiarity with Ethiopia culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_india — Culture: India — Familiarity with India culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_pakistan — Culture: Pakistan — Familiarity with Pakistan culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_bangladesh — Culture: Bangladesh — Familiarity with Bangladesh culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_china — Culture: China — Familiarity with China culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_japan — Culture: Japan — Familiarity with Japan culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_south_korea — Culture: South Korea — Familiarity with South Korea culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_vietnam — Culture: Vietnam — Familiarity with Vietnam culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_thailand — Culture: Thailand — Familiarity with Thailand culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_indonesia — Culture: Indonesia — Familiarity with Indonesia culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_philippines — Culture: Philippines — Familiarity with Philippines culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_australia — Culture: Australia — Familiarity with Australia culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_new_zealand — Culture: New Zealand — Familiarity with New Zealand culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_singapore — Culture: Singapore — Familiarity with Singapore culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_malaysia — Culture: Malaysia — Familiarity with Malaysia culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_greece — Culture: Greece — Familiarity with Greece culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- cult_portugal — Culture: Portugal — Familiarity with Portugal culture. — [Native | Lived there | Visited | Studied | Unfamiliar]
- lstyle_smoking — Smoking / vaping — Smoking / vaping. — [Never | Former | Occasional | Regular]
- lstyle_caffeine — Caffeine intake — Caffeine intake. — [None | Low | Moderate | High]
- lstyle_cooking_freq — Cooking frequency — Cooking frequency. — [Daily | Weekly | Monthly | Rarely | Never]
- lstyle_shopping_style — Shopping style — Shopping style. — [Researcher | Impulse buyer | Bargain hunter | Brand loyal | Minimalist]
- lstyle_travel_freq — Travel frequency — Travel frequency. — [Frequent flyer | A few trips/yr | Occasional | Rare | Homebody]
- lstyle_commute_mode — Commute mode — Commute mode. — [Car | Public transit | Bike | Walk | Remote | Rideshare]
- lstyle_pet_ownership — Pet ownership — Pet ownership. — [Dog | Cat | Multiple pets | Other | None]
- lstyle_screen_time — Daily screen time — Daily screen time. — [<2 hrs | 2–4 hrs | 4–8 hrs | 8+ hrs]
- lstyle_social_battery — Social battery — Social battery. — [Strong introvert | Introvert | Ambivert | Extrovert | Strong extrovert]
- lstyle_planning_horizon — Planning horizon — Planning horizon. — [Day-to-day | Weekly | Monthly | Yearly | Multi-year]
- lstyle_punctuality — Punctuality — Punctuality. — [Always early | On time | Usually late | Unpredictable]
- lstyle_tidiness — Tidiness — Tidiness. — [Spotless | Tidy | Lived-in | Cluttered | Chaotic]
- lstyle_frugality — Spending vs saving — Spending vs saving. — [Frugal saver | Balanced | Spender | Splurger]
- lstyle_giving — Charitable giving — Charitable giving. — [Regular donor | Occasional | Rare | Never]
- lstyle_news_freq — News consumption — News consumption. — [Constant | Daily | Weekly | Rarely | Avoids news]
- lstyle_reading_freq — Reading frequency — Reading frequency. — [Daily | Weekly | Monthly | Rarely | Never]
- lstyle_gaming_freq — Gaming frequency — Gaming frequency. — [Daily | Weekly | Monthly | Rarely | Never]
- lstyle_streaming_hours — Streaming hours/week — Streaming hours/week. — [0–2 | 3–7 | 8–15 | 16+]
- lstyle_music_listening — Music listening — Music listening. — [All day | Daily | Sometimes | Rarely]
- lstyle_podcast_listening — Podcast listening — Podcast listening. — [Daily | Weekly | Monthly | Rarely | Never]
- lstyle_primary_social — Primary social platform — Primary social platform. — [Instagram | TikTok | X / Twitter | Facebook | LinkedIn | YouTube | Reddit | None]
- lstyle_primary_messenger — Primary messenger — Primary messenger. — [WhatsApp | iMessage | WeChat | Telegram | Signal | Messenger | SMS]
- lstyle_device_ecosystem — Device ecosystem — Device ecosystem. — [Apple | Android/Google | Windows | Mixed | Linux]
- lstyle_browser — Primary browser — Primary browser. — [Chrome | Safari | Firefox | Edge | Brave | Other]
- lstyle_payment_pref — Payment preference — Payment preference. — [Credit card | Debit card | Mobile wallet | Cash | BNPL | Crypto]
- lstyle_banking_style — Banking style — Banking style. — [Traditional bank | Neobank | Credit union | Mostly cash | Unbanked]
- lstyle_investment_style — Investment style — Investment style. — [Index investor | Active trader | Crypto-heavy | Real estate | Cash saver | None]
- lstyle_subscription_count — Active subscriptions — Active subscriptions. — [0–2 | 3–5 | 6–10 | 10+]
- lstyle_coffee_ritual — Coffee ritual — Coffee ritual. — [Home brew | Café regular | Office coffee | Tea instead | None]
- lstyle_fashion_sense — Fashion sense — Fashion sense. — [Trend-setter | Trend-follower | Classic | Practical | Indifferent]
- lstyle_hobby_intensity — Hobby intensity — Hobby intensity. — [Obsessive | Dedicated | Casual | Dabbler | None]
- lstyle_vacation_style — Vacation style — Vacation style. — [Adventure | Relaxation | Culture | Luxury | Budget backpacking | Staycation]
- lstyle_morning_routine — Morning routine — Morning routine. — [Highly structured | Loosely structured | Rushed | Slow | None]
- lstyle_volunteering — Volunteering — Volunteering. — [Daily | Weekly | Monthly | Rarely | Never]

INPUT:

{{input_json}}
