# Persona survey task

Read the survey context, task instruction, questionnaire, and output schema
provided at runtime, then produce one JSON response that matches the schema.
Answer every required question and use the exact `questionId` values and choice
ids defined by the questionnaire.

The platform owns the response artifact contract, trajectory generation, and
runtime plumbing. Do not invent another persona layer, do not describe file
paths or platform internals, and do not call a second model to simulate the
respondent.
