You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Professional: Career  (6 dimensions)

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
- research_output — Research output — Scholarly/published footprint. — [Prolific publisher | Occasional author | Industry whitepapers | Thesis only | None]
- seniority — Seniority — Career level (LinkedIn-style). — [Student / intern | Entry | Mid | Senior | Lead / Principal | Manager | Director | VP | C-suite | Founder | Retired]
- years_experience — Years experience — Tenure in their field. — [0–2 | 3–5 | 6–10 | 11–20 | 20+]
- linkedin_activity — LinkedIn activity — Professional-network behavior. — [Thought leader | Active networker | Lurker | Job seeker | Recruiter | Inactive]
- wiki_position_held — Notable Positions/Titles — Official roles and positions occupied by the person. — [CEO | President | Minister | Governor | Mayor | Archbishop | Chancellor | General | Ambassador | None]
- wiki_awards_recognition — Awards and Honors — Major prizes and distinctions received. — [Nobel Prize | Academy Award | Pulitzer Prize | Emmy Award | Olympic Medal | Grammy Award | Other major award | None]

INPUT:

{{input_json}}
