You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Personality: Relationships  (4 dimensions)

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
- attachment_anxiety — Attachment Anxiety — Adult attachment dimension: fear of rejection, abandonment, or partner unavailability. — [Very high | High | Average | Low | Very low]
- attachment_avoidance — Attachment Avoidance — Adult attachment dimension: discomfort with closeness, dependence, or intimacy. — [Very high | High | Average | Low | Very low]
- interpersonal_agency_dominance — Interpersonal Agency/Dominance — Interpersonal circumplex axis: agency, dominance, status, control, and assertive interpersonal stance. — [Very high | High | Average | Low | Very low]
- interpersonal_communion_warmth — Interpersonal Communion/Warmth — Interpersonal circumplex axis: communion, warmth, affiliation, friendliness, and care. — [Very high | High | Average | Low | Very low]

INPUT:

{{input_json}}
