You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: External: Datasets  (94 dimensions)

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
- personahub_dimension_1 — PersonaHub_Dimension1 — Placeholder imported dimension 1 from PersonaHub. — [Absent | Minimal | Moderate | Significant | Dominant]
- personahub_dimension_2 — PersonaHub_Dimension2 — Placeholder imported dimension 2 from PersonaHub. — [Absent | Minimal | Moderate | Significant | Dominant]
- oasis_dimension_1 — OASIS_Dimension1 — Placeholder imported dimension 1 from OASIS. — [Never | Rarely | Sometimes | Often | Always]
- oasis_dimension_2 — OASIS_Dimension2 — Placeholder imported dimension 2 from OASIS. — [Never | Rarely | Sometimes | Often | Always]
- oasis_dimension_3 — OASIS_Dimension3 — Placeholder imported dimension 3 from OASIS. — [Never | Rarely | Sometimes | Often | Always]
- oasis_dimension_4 — OASIS_Dimension4 — Placeholder imported dimension 4 from OASIS. — [Never | Rarely | Sometimes | Often | Always]
- oasis_dimension_5 — OASIS_Dimension5 — Placeholder imported dimension 5 from OASIS. — [Never | Rarely | Sometimes | Often | Always]
- oasis_dimension_6 — OASIS_Dimension6 — Placeholder imported dimension 6 from OASIS. — [Never | Rarely | Sometimes | Often | Always]
- apple_primex_dimension_1 — ApplePRIMEX_Dimension1 — Placeholder imported dimension 1 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_2 — ApplePRIMEX_Dimension2 — Placeholder imported dimension 2 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_3 — ApplePRIMEX_Dimension3 — Placeholder imported dimension 3 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_4 — ApplePRIMEX_Dimension4 — Placeholder imported dimension 4 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_5 — ApplePRIMEX_Dimension5 — Placeholder imported dimension 5 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_6 — ApplePRIMEX_Dimension6 — Placeholder imported dimension 6 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_7 — ApplePRIMEX_Dimension7 — Placeholder imported dimension 7 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_8 — ApplePRIMEX_Dimension8 — Placeholder imported dimension 8 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_9 — ApplePRIMEX_Dimension9 — Placeholder imported dimension 9 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_10 — ApplePRIMEX_Dimension10 — Placeholder imported dimension 10 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_11 — ApplePRIMEX_Dimension11 — Placeholder imported dimension 11 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_12 — ApplePRIMEX_Dimension12 — Placeholder imported dimension 12 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_13 — ApplePRIMEX_Dimension13 — Placeholder imported dimension 13 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_14 — ApplePRIMEX_Dimension14 — Placeholder imported dimension 14 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_15 — ApplePRIMEX_Dimension15 — Placeholder imported dimension 15 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_16 — ApplePRIMEX_Dimension16 — Placeholder imported dimension 16 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_17 — ApplePRIMEX_Dimension17 — Placeholder imported dimension 17 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_18 — ApplePRIMEX_Dimension18 — Placeholder imported dimension 18 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_19 — ApplePRIMEX_Dimension19 — Placeholder imported dimension 19 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_20 — ApplePRIMEX_Dimension20 — Placeholder imported dimension 20 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_21 — ApplePRIMEX_Dimension21 — Placeholder imported dimension 21 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_22 — ApplePRIMEX_Dimension22 — Placeholder imported dimension 22 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_23 — ApplePRIMEX_Dimension23 — Placeholder imported dimension 23 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_24 — ApplePRIMEX_Dimension24 — Placeholder imported dimension 24 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_25 — ApplePRIMEX_Dimension25 — Placeholder imported dimension 25 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_26 — ApplePRIMEX_Dimension26 — Placeholder imported dimension 26 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_27 — ApplePRIMEX_Dimension27 — Placeholder imported dimension 27 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_28 — ApplePRIMEX_Dimension28 — Placeholder imported dimension 28 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_29 — ApplePRIMEX_Dimension29 — Placeholder imported dimension 29 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_30 — ApplePRIMEX_Dimension30 — Placeholder imported dimension 30 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_31 — ApplePRIMEX_Dimension31 — Placeholder imported dimension 31 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_32 — ApplePRIMEX_Dimension32 — Placeholder imported dimension 32 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_33 — ApplePRIMEX_Dimension33 — Placeholder imported dimension 33 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_34 — ApplePRIMEX_Dimension34 — Placeholder imported dimension 34 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_35 — ApplePRIMEX_Dimension35 — Placeholder imported dimension 35 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_36 — ApplePRIMEX_Dimension36 — Placeholder imported dimension 36 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_37 — ApplePRIMEX_Dimension37 — Placeholder imported dimension 37 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_38 — ApplePRIMEX_Dimension38 — Placeholder imported dimension 38 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_39 — ApplePRIMEX_Dimension39 — Placeholder imported dimension 39 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_40 — ApplePRIMEX_Dimension40 — Placeholder imported dimension 40 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_41 — ApplePRIMEX_Dimension41 — Placeholder imported dimension 41 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_42 — ApplePRIMEX_Dimension42 — Placeholder imported dimension 42 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- apple_primex_dimension_43 — ApplePRIMEX_Dimension43 — Placeholder imported dimension 43 from ApplePRIMEX. — [Very Low | Low | Medium | High | Very High]
- pandora_dimension_1 — PANDORA_Dimension1 — Placeholder imported dimension 1 from PANDORA. — [Very Low | Low | Average | High | Very High]
- pandora_dimension_2 — PANDORA_Dimension2 — Placeholder imported dimension 2 from PANDORA. — [Very Low | Low | Average | High | Very High]
- pandora_dimension_3 — PANDORA_Dimension3 — Placeholder imported dimension 3 from PANDORA. — [Very Low | Low | Average | High | Very High]
- pandora_dimension_4 — PANDORA_Dimension4 — Placeholder imported dimension 4 from PANDORA. — [Very Low | Low | Average | High | Very High]
- pandora_dimension_5 — PANDORA_Dimension5 — Placeholder imported dimension 5 from PANDORA. — [Very Low | Low | Average | High | Very High]
- pandora_dimension_6 — PANDORA_Dimension6 — Placeholder imported dimension 6 from PANDORA. — [Very Low | Low | Average | High | Very High]
- synthetic_persona_chat_dimension_1 — SyntheticPersonaChat_Dimension1 — Placeholder imported dimension 1 from SyntheticPersonaChat. — [Not Applicable | Minor | Moderate | Notable | Central]
- synthetic_persona_chat_dimension_2 — SyntheticPersonaChat_Dimension2 — Placeholder imported dimension 2 from SyntheticPersonaChat. — [Not Applicable | Minor | Moderate | Notable | Central]
- synthetic_persona_chat_dimension_3 — SyntheticPersonaChat_Dimension3 — Placeholder imported dimension 3 from SyntheticPersonaChat. — [Not Applicable | Minor | Moderate | Notable | Central]
- personachat_persona — PersonaChat_PersonaDescription — Free-text persona profile sentences describing interests, habits, and traits from PersonaChat dataset. — [Not Described | Mentioned Once | Occasionally Mentioned | Frequently Mentioned | Central to Profile]
- horizonbench_dimension_1 — HorizonBench_Advice_Delivery_Preferences — Preference evolution domain 'advice_delivery_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_2 — HorizonBench_Analytical_Approach — Preference evolution domain 'analytical_approach' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_3 — HorizonBench_Apology_Style_Preferences — Preference evolution domain 'apology_style_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_4 — HorizonBench_Communication_Intimacy — Preference evolution domain 'communication_intimacy' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_5 — HorizonBench_Communication_Medium_Preferences — Preference evolution domain 'communication_medium_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_6 — HorizonBench_Conflict_Resolution_Style_Preferences — Preference evolution domain 'conflict_resolution_style_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_7 — HorizonBench_Content_Length_Preferences — Preference evolution domain 'content_length_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_8 — HorizonBench_Creative_Collaboration — Preference evolution domain 'creative_collaboration' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_9 — HorizonBench_Emotional_Support_Style — Preference evolution domain 'emotional_support_style' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_10 — HorizonBench_Empirical_Evidence_Integration_Preferences — Preference evolution domain 'empirical_evidence_integration_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_11 — HorizonBench_Entertainment_Preferences — Preference evolution domain 'entertainment_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_12 — HorizonBench_Ethical_Review_Preferences — Preference evolution domain 'ethical_review_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_13 — HorizonBench_Event_Planning_Detail_Preferences — Preference evolution domain 'event_planning_detail_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_14 — HorizonBench_Facilitation_Style_Preferences — Preference evolution domain 'facilitation_style_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_15 — HorizonBench_Follow_Up_Strategy_Preferences — Preference evolution domain 'follow_up_strategy_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_16 — HorizonBench_Interfaith_Engagement_Preferences — Preference evolution domain 'interfaith_engagement_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_17 — HorizonBench_Intergenerational_Engagement_Preferences — Preference evolution domain 'intergenerational_engagement_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_18 — HorizonBench_Language_Preferences — Preference evolution domain 'language_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_19 — HorizonBench_Motivation_Strategy_Preferences — Preference evolution domain 'motivation_strategy_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_20 — HorizonBench_Philosophical_Engagement — Preference evolution domain 'philosophical_engagement' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_21 — HorizonBench_Productivity_Style — Preference evolution domain 'productivity_style' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_22 — HorizonBench_Public_Speaking_Coaching_Preferences — Preference evolution domain 'public_speaking_coaching_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_23 — HorizonBench_Self_Esteem_Rebuilding_Preferences — Preference evolution domain 'self_esteem_rebuilding_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_24 — HorizonBench_Social_Engagement_Style_Preferences — Preference evolution domain 'social_engagement_style_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_25 — HorizonBench_Stakeholder_Consultation_Preferences — Preference evolution domain 'stakeholder_consultation_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_26 — HorizonBench_Support_Technique_Preferences — Preference evolution domain 'support_technique_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_27 — HorizonBench_Technology_Assistance_Style_Preferences — Preference evolution domain 'technology_assistance_style_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_28 — HorizonBench_Therapy_Discussion_Preferences — Preference evolution domain 'therapy_discussion_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_29 — HorizonBench_Tone_Guideline_Preferences — Preference evolution domain 'tone_guideline_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- horizonbench_dimension_30 — HorizonBench_Writing_Style_Preferences — Preference evolution domain 'writing_style_preferences' from HorizonBench long-horizon personalization dataset. — [Not Active | Minimally Active | Moderately Active | Highly Active | Dominant]
- wildchat_state — WildChat_State — U.S. state where user accessed WildChat (geographic dimension from IP geolocation). — [Unknown | Unlikely | Possible | Likely | Confirmed]
- wildchat_country — WildChat_Country — Country where user accessed WildChat (geographic dimension from IP geolocation). — [Unknown | Unlikely | Possible | Likely | Confirmed]
- wildchat_hashed_ip — WildChat_HashedIP — Privacy-preserving hashed IP address from WildChat (technical/geographic dimension). — [Unknown | Unlikely | Possible | Likely | Confirmed]

INPUT:

{{input_json}}
