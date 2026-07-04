Return strict JSON matching this shape.

```json
{
  "instrument": {
    "id": "product_feedback_v1",
    "title": "Survey Product Feedback"
  },
  "answers": [
    {
      "questionId": "q0",
      "value": "q0_pay_when_roi_clear",
      "rationale": "Brief answer-specific reason.",
      "confidence": 0.85
    }
  ]
}
```

Rules:

- Use exact `questionId` values from `questionnaire.yaml`.
- For choice questions, `value` must be the exact choice id.
- `overall_interest` uses a 1-5 integer.
- `would_try_beta` uses `"true"` or `"false"`.
