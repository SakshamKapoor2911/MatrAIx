You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: State: Emotional  (5 dimensions)

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
- emotional_state — Emotional state — Mood at the moment of interaction. — [Calm | Curious | Frustrated | Anxious | Excited | Skeptical | Urgent]
- intent — Intent — What they want from the agent. — [Learn / explain | Get task done | Brainstorm | Debug / troubleshoot | Decide | Vent / support | Probe / red-team | Verify a claim]
- query_complexity — Query complexity — Shape of the request. — [Simple factual | Multi-step | Ambiguous / underspecified | Adversarial | Open-ended creative]
- prior_context — Prior context — History with the agent. — [Cold start | Returning user | Long ongoing project | Frustrated re-ask]
- device_context — Device context — Where/how they're interacting. — [Desktop, focused | Mobile, on-the-go | Voice assistant | Accessibility tool | Low-bandwidth]

INPUT:

{{input_json}}
