# Wikipedia Persona Field Assignment Prompt

You map Wikipedia/Wikidata evidence into persona template fields.

Use only the provided summary, structured dimensions, and source evidence. Do
not add facts from memory. If a field is not directly supported by the provided
evidence, return `null` for that field.

For real people, be conservative about psychological traits, emotional state,
intent, socioeconomic status, family status, and private life. Assign those only
when the provided evidence explicitly supports the value.

For fictional characters, you may use plot/character summary evidence for
narrative role, creator, source work, broad domain, and explicitly described
traits. Do not convert every plot action into a stable personality trait.

Return only compact JSON with this shape:

```json
{
  "field_assignments": [
    {
      "field": "role_function",
      "value": "theoretical physicist",
      "evidence_quotes": ["German-born theoretical physicist"],
      "confidence": 0.95,
      "assignment_type": "direct"
    },
    {
      "field": "personality_big5_openness",
      "value": null,
      "evidence_quotes": [],
      "confidence": 0.0,
      "assignment_type": "unsupported"
    }
  ],
  "notes": []
}
```

Rules:
- Use one assignment per requested field.
- `assignment_type` must be one of `direct`, `structured_claim`, `summary_inference`, or `unsupported`.
- Evidence quotes must be short exact snippets from the provided record.
- For existing non-null values, you may confirm them if evidence supports them.
- Keep values concise and compatible with a persona template.
- Use `null`, not an empty string, when unsupported.
