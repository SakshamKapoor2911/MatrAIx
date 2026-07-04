# Survey Product Feedback

Complete the survey using the provided context and structured questionnaire.

Return one JSON object that matches `input/output_schema.md`.

Requirements:

- Answer every required question in `input/questionnaire.yaml`.
- Use exact `questionId` values from the questionnaire.
- For choice questions, use the exact choice ids.
- For likert questions, use an integer within the declared range.
- Keep each `rationale` concise and specific to the selected answer.
- Return only the JSON object.

Write the final JSON artifact to `/app/output/survey_result.json`.
