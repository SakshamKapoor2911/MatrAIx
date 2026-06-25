# Application task prompt: survey form

Harbor supplies the persona system prompt through the Persona model API. Use
that persona as the respondent identity, values, constraints, communication
style, and decision-making style. This application supplies only the survey
instrument and artifact contract.

Survey instrument:

```json
{
  "id": "product_attitudes_v1",
  "title": "Product Attitudes",
  "description": "A short product concept survey.",
  "questions": [
    {
      "id": "concept_fit",
      "prompt": "This product would fit my needs.",
      "type": "likert",
      "minValue": 1,
      "maxValue": 5,
      "construct": "product_need_fit",
      "required": true
    },
    {
      "id": "adoption_barrier",
      "prompt": "What would be your biggest barrier?",
      "type": "single_choice",
      "options": ["price", "privacy", "complexity"],
      "construct": "adoption_barrier",
      "required": true
    }
  ]
}
```

Write exactly one valid JSON object to `/app/output/survey_result.json`.

Required top-level schema:

```json
{
  "instrument": {"id": "product_attitudes_v1", "title": "Product Attitudes"},
  "answers": [
    {
      "questionId": "concept_fit",
      "value": 4,
      "rationale": "short persona-grounded reason",
      "confidence": 0.8
    }
  ],
  "trajectory": [
    {
      "timestamp": "2026-06-24T00:00:00Z",
      "actor": "user",
      "action": "answer_question",
      "context": {"questionId": "concept_fit", "construct": "product_need_fit"},
      "outcome": {"questionId": "concept_fit", "value": 4}
    }
  ]
}
```

Answer every required question. For `likert`, use a number within `minValue`
and `maxValue`. For `single_choice`, use exactly one string from `options`.
Every answer must include a concise persona-grounded rationale. Every trajectory
event must include `timestamp`, `actor`, `action`, `context`, and `outcome`, with
`context` and `outcome` as JSON objects.
