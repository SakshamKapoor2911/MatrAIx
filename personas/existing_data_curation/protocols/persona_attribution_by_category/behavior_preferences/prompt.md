You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Behavior: Preferences  (34 dimensions)

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
- modality_pref — Modality preference — Preferred answer format. — [Text | Code | Visual / diagram | Tabular | Step-by-step | Examples-first]
- accessibility_needs — Accessibility needs — Accommodations required. — [None | Visual | Hearing | Motor | Cognitive / neurodivergent | Language barrier]
- media_diet — Media diet — Primary information sources. — [Academic journals | News | Social-media-heavy | Long-form | Video-first | Minimal]
- peeve_typos — Pet peeve: Typos — Reaction to typos. — [Major peeve | Annoys | Neutral | Fine]
- peeve_being_interrupted — Pet peeve: Being interrupted — Reaction to being interrupted. — [Major peeve | Annoys | Neutral | Fine]
- peeve_lateness — Pet peeve: Lateness — Reaction to lateness. — [Major peeve | Annoys | Neutral | Fine]
- peeve_loud_chewing — Pet peeve: Loud chewing — Reaction to loud chewing. — [Major peeve | Annoys | Neutral | Fine]
- peeve_slow_walkers — Pet peeve: Slow walkers — Reaction to slow walkers. — [Major peeve | Annoys | Neutral | Fine]
- peeve_spam — Pet peeve: Spam — Reaction to spam. — [Major peeve | Annoys | Neutral | Fine]
- peeve_clickbait — Pet peeve: Clickbait — Reaction to clickbait. — [Major peeve | Annoys | Neutral | Fine]
- peeve_unexplained_jargon — Pet peeve: Unexplained jargon — Reaction to unexplained jargon. — [Major peeve | Annoys | Neutral | Fine]
- peeve_condescension — Pet peeve: Condescension — Reaction to condescension. — [Major peeve | Annoys | Neutral | Fine]
- peeve_forced_small_talk — Pet peeve: Forced small talk — Reaction to forced small talk. — [Major peeve | Annoys | Neutral | Fine]
- peeve_cold_calls — Pet peeve: Cold calls — Reaction to cold calls. — [Major peeve | Annoys | Neutral | Fine]
- peeve_pop_up_ads — Pet peeve: Pop-up ads — Reaction to pop-up ads. — [Major peeve | Annoys | Neutral | Fine]
- peeve_auto_play_video — Pet peeve: Auto-play video — Reaction to auto-play video. — [Major peeve | Annoys | Neutral | Fine]
- peeve_paywalls — Pet peeve: Paywalls — Reaction to paywalls. — [Major peeve | Annoys | Neutral | Fine]
- pref_team_vs_solo — Team vs solo work — Team vs solo work. — [Strongly team | Team-leaning | Mixed | Solo-leaning | Strongly solo]
- pref_plan_vs_spontaneous — Planned vs spontaneous — Planned vs spontaneous. — [Highly planned | Planned | Balanced | Spontaneous | Highly spontaneous]
- pref_city_vs_nature — City vs nature — City vs nature. — [City lover | Prefers city | Either | Prefers nature | Nature lover]
- pref_routine_vs_variety — Routine vs variety — Routine vs variety. — [Craves routine | Routine-leaning | Balanced | Variety-leaning | Craves variety]
- pref_speed_vs_accuracy — Speed vs accuracy — Speed vs accuracy. — [Speed first | Speed-leaning | Balanced | Accuracy-leaning | Accuracy first]
- pref_quality_vs_quantity — Quality vs quantity — Quality vs quantity. — [Quality first | Quality-leaning | Balanced | Quantity-leaning | Quantity first]
- pref_logic_vs_intuition — Logic vs intuition — Logic vs intuition. — [Pure logic | Logic-leaning | Balanced | Intuition-leaning | Pure intuition]
- pref_save_vs_spend — Save vs spend — Save vs spend. — [Hard saver | Saver-leaning | Balanced | Spender-leaning | Free spender]
- pref_lead_vs_follow — Lead vs follow — Lead vs follow. — [Always leads | Leans lead | Situational | Leans support | Prefers to follow]
- pref_indoor_vs_outdoor — Indoor vs outdoor — Indoor vs outdoor. — [Strongly indoor | Indoor-leaning | Either | Outdoor-leaning | Strongly outdoor]
- pref_early_vs_late — Early vs late adopter — Early vs late adopter. — [Bleeding edge | Early adopter | Mainstream | Late adopter | Laggard]
- pref_text_vs_call — Texting vs calling — Texting vs calling. — [Text only | Prefers text | Either | Prefers calls | Calls only]
- pref_big_group_vs_one_on_one — Big group vs one-on-one — Big group vs one-on-one. — [Loves big groups | Group-leaning | Either | 1-on-1 leaning | One-on-one only]
- pref_novelty_vs_familiarity — Novelty vs familiarity — Novelty vs familiarity. — [Always novel | Novelty-leaning | Balanced | Comfort-leaning | Always familiar]
- pref_detail_brief_vs_full — Brief vs full detail — Brief vs full detail. — [Just the gist | Brief-leaning | Balanced | Detail-leaning | Every detail]
- pref_competition_vs_collab — Competition vs collaboration — Competition vs collaboration. — [Highly competitive | Competitive | Balanced | Collaborative | Highly collaborative]
- pref_stability_vs_change — Stability vs change — Stability vs change. — [Craves stability | Stability-leaning | Balanced | Change-leaning | Craves change]

INPUT:

{{input_json}}
