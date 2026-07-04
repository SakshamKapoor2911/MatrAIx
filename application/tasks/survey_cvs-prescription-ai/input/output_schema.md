Return strict JSON matching this shape.

```json
{
  "instrument": {
    "id": "healthcare_cvs_app_prescription_ai_v1",
    "title": "CVS Health App Prescription AI Survey"
  },
  "answers": [
    {
      "questionId": "pharmacy_convenience",
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
