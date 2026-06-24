You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Health: Physical  (25 dimensions)

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
- health_general_health — General health — General health. — [Excellent | Good | Fair | Poor]
- health_chronic_condition — Chronic condition — Chronic condition. — [None | Managed | Multiple | Undiagnosed concerns]
- health_mobility — Mobility — Mobility. — [Full | Mild limitation | Moderate limitation | Uses mobility aid]
- health_vision — Vision — Vision. — [Normal | Corrected | Low vision | Blind]
- health_hearing — Hearing — Hearing. — [Normal | Mild loss | Moderate loss | Deaf / hard of hearing]
- health_color_vision — Color vision — Color vision. — [Typical | Color-blind]
- health_dexterity — Manual dexterity — Manual dexterity. — [Full | Reduced | Limited | Assistive needed]
- health_mental_health — Mental health — Mental health. — [Thriving | Stable | Struggling | In crisis]
- health_stress_level — Stress level — Stress level. — [Very high | High | Moderate | Low | None]
- health_energy_level — Energy level — Energy level. — [Very high | High | Moderate | Low | None]
- health_sleep_quality — Sleep quality — Sleep quality. — [Excellent | Good | Fair | Poor]
- health_pain_level — Chronic pain — Chronic pain. — [None | Mild | Moderate | Severe]
- health_medication_use — Medication use — Medication use. — [None | Occasional | Daily | Multiple daily]
- health_dietary_restriction — Dietary restriction — Dietary restriction. — [None | Allergy | Religious | Medical | Ethical]
- health_neurodivergence — Neurodivergence — Neurodivergence. — [Neurotypical | ADHD | Autistic | Dyslexic | Other]
- health_caregiver_status — Caregiver status — Caregiver status. — [Not a caregiver | Child caregiver | Elder caregiver | Both]
- health_health_literacy — Health literacy — Health literacy. — [Very high | High | Moderate | Low | None]
- health_insurance_status — Insurance status — Insurance status. — [Comprehensive | Basic | Minimal | Uninsured]
- health_fitness_level — Fitness level — Fitness level. — [Athlete | Fit | Average | Sedentary]
- health_cognitive_load_capacity — Cognitive load capacity — Cognitive load capacity. — [Very high | High | Moderate | Low | None]
- health_contrast_need — High-contrast need — High-contrast need. — [No | Prefers | Requires]
- health_text_size_need — Large-text need — Large-text need. — [No | Prefers | Requires]
- health_assistive_tech — Assistive technology — Assistive technology. — [None | Screen reader | Switch control | Voice control | Magnifier]
- health_motion_sensitivity — Motion sensitivity — Motion sensitivity. — [None | Mild | Strong (reduced motion)]
- health_attention_condition — Attention condition — Attention condition. — [None | Mild | Diagnosed]

INPUT:

{{input_json}}
