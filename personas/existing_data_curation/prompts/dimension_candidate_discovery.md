# Dimension Candidate Discovery Prompt

You are discovering raw persona dimensions from user-language evidence.

Input: a batch of PRISM conversation records. Each record may include user prompts,
conversation type, ratings, choice/performance attributes, and open feedback.

Task: identify persona dimension candidates that are supported by the user's
language or feedback. Do not restrict yourself to dataset-provided fields. Do not
map candidates to any canonical schema. Do not deduplicate against previous
batches.

A valid candidate describes a stable or semi-stable user attribute, preference,
concern, communication style, decision criterion, topic interest, value, or
interaction tendency.

Return only compact JSON with this shape:

```json
{
  "dimension_candidates": [
    {
      "dimension_label": "preferred_answer_length",
      "definition": "Whether the user prefers concise, balanced, or detailed responses.",
      "supported_by": "The user explicitly comments on response length and information density.",
      "source_fields": ["open_feedback"],
      "evidence_quotes": ["Shorter blocks would be nice. but has to have enough info."],
      "possible_values": ["very concise", "balanced", "detailed"],
      "value_type": "categorical",
      "granularity": "response-preference-level",
      "confidence": 0.95
    }
  ]
}
```

Rules:
- Keep useful dataset-provided dimensions, and also discover additional dimensions from natural-language evidence instead of limiting the output to preset rating names.
- Evidence must be quoted from a provided field.
- Keep evidence quotes short.
- Do not infer sensitive attributes beyond explicit text.
- It is fine to output a topic-interest dimension when the topic seems salient,
  but avoid turning every one-off wording detail into a persona dimension.
- Use snake_case labels.
- Use confidence from 0 to 1.
