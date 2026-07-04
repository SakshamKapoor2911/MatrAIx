Return strict JSON matching this shape.

```json
{
  "instrument": {
    "id": "finance_robinhood_cortex_digests_v1",
    "title": "Robinhood Cortex Digests Survey"
  },
  "answers": [
    {
      "questionId": "market_summary_utility",
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
