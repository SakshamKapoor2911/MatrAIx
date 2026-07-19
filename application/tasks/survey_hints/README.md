# NCI Health Information National Trends Survey

PersonaBench **survey** task: read the topic context and a structured questionnaire,
then submit persona-aligned answers.

Task-owned content:

- `instruction.md` — persona-facing scenario
- `input/context.md` — topic background
- `input/questionnaire.yaml` — the 196 questions

Reuses the shared `application/shared-survey-form` runtime environment. The platform
derives runtime prompts and the answer envelope from `input/questionnaire.yaml` and
writes `survey_result.json`; the verifier emits `question_response` + `trial_summary`
contexts per the survey task contract.

## Source

This task adapts a real, publicly released survey instrument (questions only; all original results/frequencies removed).

- **Original survey:** Health Information National Trends Survey (HINTS 7), 2024 — National Cancer Institute (NCI), National Institutes of Health.
- **Source:** https://hints.cancer.gov/data/download-data.aspx
- **License:** U.S. federal government (NCI/NIH) — public domain.

