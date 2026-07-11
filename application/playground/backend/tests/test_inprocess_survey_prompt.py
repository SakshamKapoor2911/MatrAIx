from backend.service.example_task_catalog import repo_root
from backend.service.survey_questionnaire_catalog import get_survey_questionnaire
from backend.service.survey_types import SurveyInstrument, SurveyQuestion
from playground.inprocess.survey_eval import build_survey_task_prompt


def test_repo_backed_local_survey_prompt_is_only_document_bundle():
    instrument = get_survey_questionnaire("product_attitudes_v1", repo_root=repo_root())

    prompt = build_survey_task_prompt(instrument=instrument)

    assert "You are completing a market research survey" not in prompt
    assert "The persona is provided separately in the system prompt." not in prompt
    assert "Additional answer rule:" not in prompt
    assert "## Task instruction" in prompt
    assert "## Context" in prompt
    assert "## Questionnaire" in prompt
    assert "## Answer envelope" in prompt
    assert "## Output schema" not in prompt
    assert "input/output_schema.md" not in prompt


def test_unmapped_local_survey_prompt_falls_back_to_rendered_docs_only():
    instrument = SurveyInstrument(
        id="survey1",
        title="Survey",
        description="A survey about a concrete feature.",
        questions=[SurveyQuestion(id="fit", prompt="This fits me.")],
    )

    prompt = build_survey_task_prompt(instrument=instrument)

    assert "You are completing a market research survey" not in prompt
    assert "The persona is provided separately in the system prompt." not in prompt
    assert "## Task instruction" in prompt
    assert "## Context" in prompt
    assert "## Questionnaire" in prompt
    assert "## Answer envelope" in prompt
    assert "## Output schema" not in prompt
    assert "A survey about a concrete feature." in prompt
    assert "Ask rationale:" not in prompt
    assert "Ask confidence:" not in prompt
    assert "selected value only" in prompt
    assert "questionId` + `value` only" in prompt
