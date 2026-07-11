# Survey Product Feedback

Complete the survey using the provided context and structured questionnaire.

Requirements:

- Answer every required question in `input/questionnaire.yaml`.
- Use exact `questionId` values from the questionnaire.
- For choice questions, use the exact choice ids.
- For likert questions, use an integer within the declared range.
- Follow each question's `askRationale` / `askConfidence` flags when emitting answer metadata.

The platform writes `/app/output/survey_result.json` from your answers.
