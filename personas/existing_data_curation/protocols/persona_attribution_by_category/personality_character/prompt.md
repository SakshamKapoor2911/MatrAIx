You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Personality: Character  (34 dimensions)

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
- domain_characteristics — Domain stance — Relationship to their field. — [Cutting-edge researcher | Practitioner | Educator | Student | Hobbyist | Skeptic / critic | Cross-disciplinary]
- dominant_trait — Dominant trait — Most pronounced Big-Five-style trait. — [High openness | High conscientiousness | High extraversion | High agreeableness | High neuroticism | Balanced]
- trait_curiosity — Character: Curiosity — How present curiosity is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_creativity — Character: Creativity — How present creativity is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_love_of_learning — Character: Love of learning — How present love of learning is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_open_mindedness — Character: Open-mindedness — How present open-mindedness is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_perspective — Character: Perspective — How present perspective is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_bravery — Character: Bravery — How present bravery is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_perseverance — Character: Perseverance — How present perseverance is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_honesty — Character: Honesty — How present honesty is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_zest — Character: Zest — How present zest is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_capacity_for_love — Character: Capacity for love — How present capacity for love is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_kindness — Character: Kindness — How present kindness is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_social_intelligence — Character: Social intelligence — How present social intelligence is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_teamwork — Character: Teamwork — How present teamwork is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_fairness — Character: Fairness — How present fairness is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_leadership — Character: Leadership — How present leadership is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_forgiveness — Character: Forgiveness — How present forgiveness is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_humility — Character: Humility — How present humility is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_prudence — Character: Prudence — How present prudence is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_self_regulation — Character: Self-regulation — How present self-regulation is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_appreciation_of_beauty — Character: Appreciation of beauty — How present appreciation of beauty is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_gratitude — Character: Gratitude — How present gratitude is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_hope_optimism — Character: Hope / optimism — How present hope / optimism is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_playfulness — Character: Playfulness — How present playfulness is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_spirituality — Character: Spirituality — How present spirituality is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_ambition — Character: Ambition — How present ambition is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_empathy — Character: Empathy — How present empathy is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_resilience — Character: Resilience — How present resilience is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_discipline — Character: Discipline — How present discipline is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_generosity — Character: Generosity — How present generosity is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_loyalty — Character: Loyalty — How present loyalty is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_competitiveness — Character: Competitiveness — How present competitiveness is in the persona. — [Signature | Strong | Moderate | Slight | Absent]
- trait_adaptability — Character: Adaptability — How present adaptability is in the persona. — [Signature | Strong | Moderate | Slight | Absent]

INPUT:

{{input_json}}
