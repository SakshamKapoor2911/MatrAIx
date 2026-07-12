# CPS Tobacco Use Supplement Survey

PersonaBench **survey** task: read the topic context and a structured questionnaire,
then submit persona-aligned answers.

Task-owned content:

- `instruction.md` — persona-facing scenario
- `input/context.md` — topic background
- `input/questionnaire.yaml` — the 61 questions

Reuses the shared `application/shared-survey-form` runtime environment. The platform
derives runtime prompts and the answer envelope from `input/questionnaire.yaml` and
writes `survey_result.json`; the verifier emits `question_response` + `trial_summary`
contexts per the survey task contract.

## Source

This task adapts a real, publicly released survey instrument (questions only; all original results/frequencies removed).

- **Original survey:** National Cancer Institute / U.S. Census Bureau, Tobacco Use Supplement to the Current Population Survey (2022-2023 wave, September 2022 fielding).
- **Source:** https://cancercontrol.cancer.gov/brp/tcrb/tus-cps (TUS-CPS September 2022 questionnaire/data dictionary; questionnaire facsimile = Attachment 8).
- **License:** U.S. federal government (NCI / U.S. Census Bureau) — public domain.

