You are extracting persona attribution fields from a Wikipedia-derived profile.

Return only JSON with this shape:

{
  "fields": [
    {
      "field_id": "domain",
      "value": "short normalized value",
      "confidence": 0.0,
      "evidence": "short quote copied from the input profile_text",
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
- Do not infer private, sensitive, or psychological traits unless directly stated.
- Every non-null value must include evidence from the input.
- Use null value with assignment_type "unsupported" when the profile does not support a field.
- Keep evidence short and copied from the input text.
- Return valid JSON only, with no markdown.

Extract these fields when supported:
- source_entity_type
- domain
- subject_specialty
- role_function
- known_for_or_source_work
- creator
- highest_education
- intent
- personality_big5_openness

INPUT:

{{input_json}}

