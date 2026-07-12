# Census Household Pulse Survey

PersonaBench **survey** task: read the topic context and a structured questionnaire,
then submit persona-aligned answers.

Task-owned content:

- `instruction.md` — persona-facing scenario
- `input/context.md` — topic background
- `input/questionnaire.yaml` — the 111 questions

Reuses the shared `application/shared-survey-form` runtime environment. The platform
derives runtime prompts and the answer envelope from `input/questionnaire.yaml` and
writes `survey_result.json`; the verifier emits `question_response` + `trial_summary`
contexts per the survey task contract.

## Source

This task adapts a real, publicly released survey instrument (questions only; all original results/frequencies removed).

- **Original survey:** Census Household Pulse Survey Phase 4.1 (2024)
- **Source:** https://www2.census.gov/programs-surveys/demo/technical-documentation/hhp/Phase_4-1_HPS_Questionnaire_English.pdf
- **License:** U.S. federal government (U.S. Census Bureau) — public domain.

