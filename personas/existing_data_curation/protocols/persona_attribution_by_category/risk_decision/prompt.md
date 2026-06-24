You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Risk & Decision  (7 dimensions)

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
- risk_tolerance — Risk tolerance — Appetite for risk. — [Risk-averse | Cautious | Balanced | Risk-tolerant | Risk-seeking]
- decision_style — Decision style — How they reach decisions. — [Analytical | Intuitive | Consensus-driven | Directive | Deliberative]
- need_for_closure — Need for Closure — Preference for firm answers, certainty, and closure under ambiguity. — [Very high | High | Average | Low | Very low]
- dospert_ethical_risk_tolerance — DOSPERT Ethical Risk Tolerance — Domain-specific risk orientation for ethical risks. — [Very high | High | Average | Low | Very low]
- dospert_financial_risk_tolerance — DOSPERT Financial Risk Tolerance — Domain-specific risk orientation for financial risks. — [Very high | High | Average | Low | Very low]
- dospert_recreational_risk_tolerance — DOSPERT Recreational Risk Tolerance — Domain-specific risk orientation for recreational risks. — [Very high | High | Average | Low | Very low]
- dospert_social_risk_tolerance — DOSPERT Social Risk Tolerance — Domain-specific risk orientation for social risks. — [Very high | High | Average | Low | Very low]

INPUT:

{{input_json}}
