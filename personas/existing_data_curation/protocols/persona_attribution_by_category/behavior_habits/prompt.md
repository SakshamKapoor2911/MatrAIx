You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Behavior: Habits  (30 dimensions)

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
- habit_journaling — Habit: Journaling — How often the persona engages in journaling. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_meditation — Habit: Meditation — How often the persona engages in meditation. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_to_do_lists — Habit: To-do lists — How often the persona engages in to-do lists. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_goal_setting — Habit: Goal setting — How often the persona engages in goal setting. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_daily_reflection — Habit: Daily reflection — How often the persona engages in daily reflection. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_budget_tracking — Habit: Budget tracking — How often the persona engages in budget tracking. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_meal_prepping — Habit: Meal prepping — How often the persona engages in meal prepping. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_stretching_mobility — Habit: Stretching / mobility — How often the persona engages in stretching / mobility. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_morning_walk — Habit: Morning walk — How often the persona engages in morning walk. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_phone_free_downtime — Habit: Phone-free downtime — How often the persona engages in phone-free downtime. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_gratitude_practice — Habit: Gratitude practice — How often the persona engages in gratitude practice. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_reading_before_bed — Habit: Reading before bed — How often the persona engages in reading before bed. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_naps — Habit: Naps — How often the persona engages in naps. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_power_snoozing_alarm — Habit: Power-snoozing alarm — How often the persona engages in power-snoozing alarm. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_skipping_breakfast — Habit: Skipping breakfast — How often the persona engages in skipping breakfast. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_late_night_snacking — Habit: Late-night snacking — How often the persona engages in late-night snacking. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_nail_biting_fidgeting — Habit: Nail-biting / fidgeting — How often the persona engages in nail-biting / fidgeting. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_doomscrolling — Habit: Doomscrolling — How often the persona engages in doomscrolling. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_multitab_browsing — Habit: Multitab browsing — How often the persona engages in multitab browsing. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_inbox_zero_discipline — Habit: Inbox-zero discipline — How often the persona engages in inbox-zero discipline. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_saving_receipts — Habit: Saving receipts — How often the persona engages in saving receipts. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_pre_trip_overpacking — Habit: Pre-trip overpacking — How often the persona engages in pre-trip overpacking. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_talking_to_oneself — Habit: Talking to oneself — How often the persona engages in talking to oneself. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_humming_whistling — Habit: Humming / whistling — How often the persona engages in humming / whistling. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_cold_showers — Habit: Cold showers — How often the persona engages in cold showers. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_step_counting — Habit: Step counting — How often the persona engages in step counting. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_hydration_tracking — Habit: Hydration tracking — How often the persona engages in hydration tracking. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_backing_up_files — Habit: Backing up files — How often the persona engages in backing up files. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_re_reading_texts_before_sending — Habit: Re-reading texts before sending — How often the persona engages in re-reading texts before sending. — [Daily | Weekly | Monthly | Rarely | Never]
- habit_procrasti_cleaning — Habit: Procrasti-cleaning — How often the persona engages in procrasti-cleaning. — [Daily | Weekly | Monthly | Rarely | Never]

INPUT:

{{input_json}}
