# NEA Survey of Public Participation in the Arts Survey

PersonaBench **survey** task: read the topic context and a structured questionnaire,
then submit persona-aligned answers.

Task-owned content:

- `instruction.md` — persona-facing scenario
- `input/context.md` — topic background
- `input/questionnaire.yaml` — the 157 questions

Reuses the shared `application/shared-survey-form` runtime environment. The platform
derives runtime prompts and the answer envelope from `input/questionnaire.yaml` and
writes `survey_result.json`; the verifier emits `question_response` + `trial_summary`
contexts per the survey task contract.

## Source

This task adapts a real, publicly released survey instrument (questions only; all original results/frequencies removed).

- **Original survey:** National Endowment for the Arts / U.S. Census Bureau, Current Population Survey, July 2022 Public Participation in the Arts (SPPA) Supplement.
- **Source:** https://www.arts.gov/impact/research/arts-data-profile-series (CPS July 2022 PPA Supplement technical documentation; questionnaire facsimile = Attachment 8).
- **License:** U.S. federal government (NEA / U.S. Census Bureau) — public domain.

