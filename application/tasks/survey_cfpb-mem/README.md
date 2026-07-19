# CFPB Making Ends Meet Survey

PersonaBench **survey** task: read the topic context and a structured questionnaire,
then submit persona-aligned answers.

Task-owned content:

- `instruction.md` — persona-facing scenario
- `input/context.md` — topic background
- `input/questionnaire.yaml` — the 180 questions

Reuses the shared `application/shared-survey-form` runtime environment. The platform
derives runtime prompts and the answer envelope from `input/questionnaire.yaml` and
writes `survey_result.json`; the verifier emits `question_response` + `trial_summary`
contexts per the survey task contract.

## Source

This task adapts a real, publicly released survey instrument (questions only; all original results/frequencies removed).

- **Original survey:** CFPB Making Ends Meet Survey, Sample 6 Wave 1 (January 2025)
- **Source:** https://files.consumerfinance.gov/f/documents/cfpb_making-ends-meet_data-sample-6.zip
- **License:** U.S. federal government (Consumer Financial Protection Bureau) public use file — no registration; terms prohibit re-identification of individuals; suggested citation applies.

