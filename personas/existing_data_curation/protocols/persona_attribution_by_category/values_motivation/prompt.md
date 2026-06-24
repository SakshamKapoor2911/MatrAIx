You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Values & Motivation  (46 dimensions)

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
- values_priority — Core value — Top personal value. — [Achievement | Security | Autonomy | Community | Novelty | Tradition]
- religiosity — Religiosity — Relationship to religion. — [Secular | Spiritual | Observant | Devout | Prefer not to say]
- economic_motivation — Economic motivation — Spending posture. — [Cost-sensitive | Value-driven | Premium-seeking | Indifferent]
- val_family — Value: Family — How strongly the persona prioritizes family. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_career_success — Value: Career success — How strongly the persona prioritizes career success. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_wealth — Value: Wealth — How strongly the persona prioritizes wealth. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_health — Value: Health — How strongly the persona prioritizes health. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_personal_freedom — Value: Personal freedom — How strongly the persona prioritizes personal freedom. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_security_stability — Value: Security & stability — How strongly the persona prioritizes security & stability. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_adventure — Value: Adventure — How strongly the persona prioritizes adventure. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_tradition — Value: Tradition — How strongly the persona prioritizes tradition. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_power_influence — Value: Power & influence — How strongly the persona prioritizes power & influence. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_achievement — Value: Achievement — How strongly the persona prioritizes achievement. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_creativity_self_expression — Value: Creativity & self-expression — How strongly the persona prioritizes creativity & self-expression. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_community — Value: Community — How strongly the persona prioritizes community. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_spirituality_faith — Value: Spirituality / faith — How strongly the persona prioritizes spirituality / faith. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_knowledge_truth — Value: Knowledge & truth — How strongly the persona prioritizes knowledge & truth. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_social_status — Value: Social status — How strongly the persona prioritizes social status. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_independence — Value: Independence — How strongly the persona prioritizes independence. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_justice_fairness — Value: Justice & fairness — How strongly the persona prioritizes justice & fairness. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_loyalty — Value: Loyalty — How strongly the persona prioritizes loyalty. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_sustainability — Value: Sustainability — How strongly the persona prioritizes sustainability. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_recognition — Value: Recognition — How strongly the persona prioritizes recognition. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_helping_others — Value: Helping others — How strongly the persona prioritizes helping others. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_personal_growth — Value: Personal growth — How strongly the persona prioritizes personal growth. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_fun_enjoyment — Value: Fun & enjoyment — How strongly the persona prioritizes fun & enjoyment. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_integrity_honesty — Value: Integrity & honesty — How strongly the persona prioritizes integrity & honesty. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_beauty_aesthetics — Value: Beauty & aesthetics — How strongly the persona prioritizes beauty & aesthetics. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_order_structure — Value: Order & structure — How strongly the persona prioritizes order & structure. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_patriotism — Value: Patriotism — How strongly the persona prioritizes patriotism. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_equality — Value: Equality — How strongly the persona prioritizes equality. — [Core value | Important | Moderate | Minor | Irrelevant]
- val_privacy — Value: Privacy — How strongly the persona prioritizes privacy. — [Core value | Important | Moderate | Minor | Irrelevant]
- schwartz_value_self_direction — Schwartz Self-Direction — Schwartz basic value construct: independent thought and action. — [Very high | High | Average | Low | Very low]
- schwartz_value_stimulation — Schwartz Stimulation — Schwartz basic value construct: excitement, novelty, and challenge. — [Very high | High | Average | Low | Very low]
- schwartz_value_hedonism — Schwartz Hedonism — Schwartz basic value construct: pleasure and sensuous gratification. — [Very high | High | Average | Low | Very low]
- schwartz_value_achievement — Schwartz Achievement — Schwartz basic value construct: personal success through demonstrated competence. — [Very high | High | Average | Low | Very low]
- schwartz_value_power — Schwartz Power — Schwartz basic value construct: social status, prestige, and control over resources or people. — [Very high | High | Average | Low | Very low]
- schwartz_value_security — Schwartz Security — Schwartz basic value construct: safety, harmony, and stability. — [Very high | High | Average | Low | Very low]
- schwartz_value_conformity — Schwartz Conformity — Schwartz basic value construct: restraint of actions likely to upset others or violate expectations. — [Very high | High | Average | Low | Very low]
- schwartz_value_tradition — Schwartz Tradition — Schwartz basic value construct: respect and commitment to cultural, religious, or family customs. — [Very high | High | Average | Low | Very low]
- schwartz_value_benevolence — Schwartz Benevolence — Schwartz basic value construct: preserving and enhancing the welfare of close others. — [Very high | High | Average | Low | Very low]
- schwartz_value_universalism — Schwartz Universalism — Schwartz basic value construct: understanding, tolerance, and protection for all people and nature. — [Very high | High | Average | Low | Very low]
- sdt_need_autonomy — SDT Autonomy Need — Self-Determination Theory basic psychological need: autonomy. — [Very high | High | Average | Low | Very low]
- sdt_need_competence — SDT Competence Need — Self-Determination Theory basic psychological need: competence. — [Very high | High | Average | Low | Very low]
- sdt_need_relatedness — SDT Relatedness Need — Self-Determination Theory basic psychological need: relatedness. — [Very high | High | Average | Low | Very low]
- need_for_cognition — Need for Cognition — Preference for engaging in and enjoying effortful thinking. — [Very high | High | Average | Low | Very low]

INPUT:

{{input_json}}
