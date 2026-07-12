# CPS Food Security Supplement Survey

PersonaBench **survey** task: read the topic context and a structured questionnaire,
then submit persona-aligned answers.

Task-owned content:

- `instruction.md` — persona-facing scenario
- `input/context.md` — topic background
- `input/questionnaire.yaml` — the 77 questions

Reuses the shared `application/shared-survey-form` runtime environment. The platform
derives runtime prompts and the answer envelope from `input/questionnaire.yaml` and
writes `survey_result.json`; the verifier emits `question_response` + `trial_summary`
contexts per the survey task contract.

## Source

This task adapts a real, publicly released survey instrument (questions only; all original results/frequencies removed).

- **Original survey:** U.S. Census Bureau for USDA Economic Research Service, Current Population Survey, December 2023 Food Security Supplement.
- **Source:** https://www.census.gov/ (CPS December 2023 Food Security Supplement technical documentation; questionnaire facsimile = Attachment 8).
- **License:** U.S. federal government (USDA / U.S. Census Bureau) — public domain.

