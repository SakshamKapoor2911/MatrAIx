Return strict JSON matching this shape.

```json
{
  "instrument": {
    "id": "commerce_nike_air_max_dn_dynamic_air_v1",
    "title": "Nike Air Max Dn Dynamic Air Purchase Survey"
  },
  "answers": [
    {
      "questionId": "dynamic_air_appeal",
      "value": "<answer>",
      "rationale": "Brief answer-specific reason.",
      "confidence": 0.85
    }
  ]
}
```

Rules:

- Include one answer entry for every required question.
- Use exact `questionId` values from `questionnaire.yaml`.
- For choice questions, `value` must be the exact choice id.
- For likert questions, `value` must be an integer from 1 to 5.
