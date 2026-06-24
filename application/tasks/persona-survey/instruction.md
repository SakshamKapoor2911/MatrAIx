# Persona survey task

You are a simulated survey respondent. Harbor has injected your assigned
persona through the Persona model API. Act according to that persona.

The application supplies the survey instrument and exact artifact contract as an
extra instruction. Complete the survey directly as the persona. Do not use a
separate persona simulator, do not call another model to simulate the
respondent, and do not invent a second persona layer.

## Required work

1. Read the appended survey instrument.
2. Answer every required question in character.
3. Save one valid JSON object to `/app/output/survey_result.json`.
4. Include answers, rationales when requested, confidence scores, and a
   telemetry-style trajectory.

## Output schema

`/app/output/survey_result.json`:

```json
{
  "instrument": {
    "id": "<instrument id>",
    "title": "<instrument title>"
  },
  "answers": [
    {
      "questionId": "<question id>",
      "value": "<likert number, choice string/list, or free text>",
      "rationale": "<short persona-grounded reason>",
      "confidence": 0.8
    }
  ],
  "trajectory": [
    {
      "timestamp": "2026-06-24T00:00:00Z",
      "actor": "user",
      "action": "answer_question",
      "context": {
        "questionId": "<question id>",
        "construct": "<construct label>"
      },
      "outcome": {
        "questionId": "<question id>",
        "value": 4,
        "rationale": "<short reason>",
        "confidence": 0.8
      }
    }
  ]
}
```

## Trajectory contract

The core trajectory is a timestamped sequence of actions/messages plus outcomes.
Every event must include:

- `timestamp`
- `actor`
- `action`
- `context`
- `outcome`

Use JSON objects for `context` and `outcome`, never strings. Include a
`system` / `survey_started` event, an `assistant` / `ask_question` event and a
`user` / `answer_question` event for every question, and a final `system` /
`survey_completed` event.

Make sure the JSON file is valid JSON.
