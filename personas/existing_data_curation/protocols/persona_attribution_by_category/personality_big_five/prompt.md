You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Personality: Big Five  (56 dimensions)

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
- big5_imagination — Imagination — Openness facet — imagination. — [Very high | High | Average | Low | Very low]
- big5_artistic_interest — Artistic interest — Openness facet — artistic interest. — [Very high | High | Average | Low | Very low]
- big5_emotionality — Emotionality — Openness facet — emotionality. — [Very high | High | Average | Low | Very low]
- big5_adventurousness — Adventurousness — Openness facet — adventurousness. — [Very high | High | Average | Low | Very low]
- big5_intellect — Intellect — Openness facet — intellect. — [Very high | High | Average | Low | Very low]
- big5_liberalism — Liberalism — Openness facet — liberalism. — [Very high | High | Average | Low | Very low]
- big5_self_efficacy — Self-efficacy — Conscientiousness facet — self-efficacy. — [Very high | High | Average | Low | Very low]
- big5_orderliness — Orderliness — Conscientiousness facet — orderliness. — [Very high | High | Average | Low | Very low]
- big5_dutifulness — Dutifulness — Conscientiousness facet — dutifulness. — [Very high | High | Average | Low | Very low]
- big5_achievement_striving — Achievement-striving — Conscientiousness facet — achievement-striving. — [Very high | High | Average | Low | Very low]
- big5_self_discipline — Self-discipline — Conscientiousness facet — self-discipline. — [Very high | High | Average | Low | Very low]
- big5_cautiousness — Cautiousness — Conscientiousness facet — cautiousness. — [Very high | High | Average | Low | Very low]
- big5_friendliness — Friendliness — Extraversion facet — friendliness. — [Very high | High | Average | Low | Very low]
- big5_gregariousness — Gregariousness — Extraversion facet — gregariousness. — [Very high | High | Average | Low | Very low]
- big5_assertiveness — Assertiveness — Extraversion facet — assertiveness. — [Very high | High | Average | Low | Very low]
- big5_activity_level — Activity level — Extraversion facet — activity level. — [Very high | High | Average | Low | Very low]
- big5_excitement_seeking — Excitement-seeking — Extraversion facet — excitement-seeking. — [Very high | High | Average | Low | Very low]
- big5_cheerfulness — Cheerfulness — Extraversion facet — cheerfulness. — [Very high | High | Average | Low | Very low]
- big5_trust — Trust — Agreeableness facet — trust. — [Very high | High | Average | Low | Very low]
- big5_morality — Morality — Agreeableness facet — morality. — [Very high | High | Average | Low | Very low]
- big5_altruism — Altruism — Agreeableness facet — altruism. — [Very high | High | Average | Low | Very low]
- big5_cooperation — Cooperation — Agreeableness facet — cooperation. — [Very high | High | Average | Low | Very low]
- big5_modesty — Modesty — Agreeableness facet — modesty. — [Very high | High | Average | Low | Very low]
- big5_sympathy — Sympathy — Agreeableness facet — sympathy. — [Very high | High | Average | Low | Very low]
- big5_anxiety — Anxiety — Neuroticism facet — anxiety. — [Very high | High | Average | Low | Very low]
- big5_anger — Anger — Neuroticism facet — anger. — [Very high | High | Average | Low | Very low]
- big5_depression — Depression — Neuroticism facet — depression. — [Very high | High | Average | Low | Very low]
- big5_self_consciousness — Self-consciousness — Neuroticism facet — self-consciousness. — [Very high | High | Average | Low | Very low]
- big5_immoderation — Immoderation — Neuroticism facet — immoderation. — [Very high | High | Average | Low | Very low]
- big5_vulnerability — Vulnerability — Neuroticism facet — vulnerability. — [Very high | High | Average | Low | Very low]
- pandora_big5_dimension_1 — PANDORA_Openness — Big Five personality trait: Openness from PANDORA Big5 subset. — [Very Low | Low | Average | High | Very High]
- pandora_big5_dimension_2 — PANDORA_Conscientiousness — Big Five personality trait: Conscientiousness from PANDORA Big5 subset. — [Very Low | Low | Average | High | Very High]
- pandora_big5_dimension_3 — PANDORA_Extraversion — Big Five personality trait: Extraversion from PANDORA Big5 subset. — [Very Low | Low | Average | High | Very High]
- pandora_big5_dimension_4 — PANDORA_Agreeableness — Big Five personality trait: Agreeableness from PANDORA Big5 subset. — [Very Low | Low | Average | High | Very High]
- pandora_big5_dimension_5 — PANDORA_Neuroticism — Big Five personality trait: Neuroticism from PANDORA Big5 subset. — [Very Low | Low | Average | High | Very High]
- pandora_big5_dimension_6 — PANDORA_PersonalityType — Personality type classification (0-31) from PANDORA Big5 subset. — [Very Low | Low | Average | High | Very High]
- bfi2_domain_extraversion — BFI-2 Extraversion — BFI-2 Big Five domain construct: Extraversion. — [Very high | High | Average | Low | Very low]
- bfi2_domain_agreeableness — BFI-2 Agreeableness — BFI-2 Big Five domain construct: Agreeableness. — [Very high | High | Average | Low | Very low]
- bfi2_domain_conscientiousness — BFI-2 Conscientiousness — BFI-2 Big Five domain construct: Conscientiousness. — [Very high | High | Average | Low | Very low]
- bfi2_domain_negative_emotionality — BFI-2 Negative Emotionality — BFI-2 Big Five domain construct: Negative Emotionality. — [Very high | High | Average | Low | Very low]
- bfi2_domain_open_mindedness — BFI-2 Open-Mindedness — BFI-2 Big Five domain construct: Open-Mindedness. — [Very high | High | Average | Low | Very low]
- bfi2_facet_sociability — BFI-2 Sociability — BFI-2 Extraversion facet construct: Sociability. — [Very high | High | Average | Low | Very low]
- bfi2_facet_assertiveness — BFI-2 Assertiveness — BFI-2 Extraversion facet construct: Assertiveness. — [Very high | High | Average | Low | Very low]
- bfi2_facet_energy_level — BFI-2 Energy Level — BFI-2 Extraversion facet construct: Energy Level. — [Very high | High | Average | Low | Very low]
- bfi2_facet_compassion — BFI-2 Compassion — BFI-2 Agreeableness facet construct: Compassion. — [Very high | High | Average | Low | Very low]
- bfi2_facet_respectfulness — BFI-2 Respectfulness — BFI-2 Agreeableness facet construct: Respectfulness. — [Very high | High | Average | Low | Very low]
- bfi2_facet_trust — BFI-2 Trust — BFI-2 Agreeableness facet construct: Trust. — [Very high | High | Average | Low | Very low]
- bfi2_facet_organization — BFI-2 Organization — BFI-2 Conscientiousness facet construct: Organization. — [Very high | High | Average | Low | Very low]
- bfi2_facet_productiveness — BFI-2 Productiveness — BFI-2 Conscientiousness facet construct: Productiveness. — [Very high | High | Average | Low | Very low]
- bfi2_facet_responsibility — BFI-2 Responsibility — BFI-2 Conscientiousness facet construct: Responsibility. — [Very high | High | Average | Low | Very low]
- bfi2_facet_anxiety — BFI-2 Anxiety — BFI-2 Negative Emotionality facet construct: Anxiety. — [Very high | High | Average | Low | Very low]
- bfi2_facet_depression — BFI-2 Depression — BFI-2 Negative Emotionality facet construct: Depression. — [Very high | High | Average | Low | Very low]
- bfi2_facet_emotional_volatility — BFI-2 Emotional Volatility — BFI-2 Negative Emotionality facet construct: Emotional Volatility. — [Very high | High | Average | Low | Very low]
- bfi2_facet_intellectual_curiosity — BFI-2 Intellectual Curiosity — BFI-2 Open-Mindedness facet construct: Intellectual Curiosity. — [Very high | High | Average | Low | Very low]
- bfi2_facet_aesthetic_sensitivity — BFI-2 Aesthetic Sensitivity — BFI-2 Open-Mindedness facet construct: Aesthetic Sensitivity. — [Very high | High | Average | Low | Very low]
- bfi2_facet_creative_imagination — BFI-2 Creative Imagination — BFI-2 Open-Mindedness facet construct: Creative Imagination. — [Very high | High | Average | Low | Very low]

INPUT:

{{input_json}}
