# Stack Overflow Developer Survey

PersonaBench **survey** task: read the topic context and a structured questionnaire,
then submit persona-aligned answers.

Task-owned content:

- `instruction.md` — persona-facing scenario
- `input/context.md` — topic background
- `input/questionnaire.yaml` — the 108 questions

Reuses the shared `application/shared-survey-form` runtime environment. The platform
derives runtime prompts and the answer envelope from `input/questionnaire.yaml` and
writes `survey_result.json`; the verifier emits `question_response` + `trial_summary`
contexts per the survey task contract.

## Source

This task adapts a real, publicly released survey instrument (questions only; all original results/frequencies removed).

- **Original survey:** Stack Overflow Developer Survey 2025
- **Source:** https://survey.stackoverflow.co/2025/
- **License:** Open Database License (ODbL 1.0) for the database + Database Contents License (DbCL 1.0) for contents — attribution + share-alike.

