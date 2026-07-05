"""Tests for task-backed PersonaEval survey questionnaires."""

from __future__ import annotations

import pytest

from backend.service.example_task_catalog import repo_root
from backend.service.survey_questionnaire_catalog import (
    DEFAULT_SURVEY_QUESTIONNAIRE_ID,
    get_survey_questionnaire,
    list_survey_questionnaires,
)
from persona_eval.survey_task_content import (
    load_survey_task_content_for_questionnaire_id,
)


REAL_FEATURE_SURVEY_IDS = [
    "product_feedback_v1",
    "software_claude_code_vscode_checkpoints_v1",
    "finance_robinhood_cortex_digests_v1",
    "healthcare_cvs_app_prescription_ai_v1",
    "commerce_nike_air_max_dn_dynamic_air_v1",
]


def test_list_survey_questionnaires_includes_real_feature_surveys():
    questionnaires = list_survey_questionnaires()
    ids = [questionnaire.id for questionnaire in questionnaires]

    assert ids == [DEFAULT_SURVEY_QUESTIONNAIRE_ID] + REAL_FEATURE_SURVEY_IDS
    assert len(ids) == 6

    for questionnaire in questionnaires:
        assert questionnaire.title
        assert questionnaire.description
        assert len(questionnaire.questions) >= 4
        assert all(question.id for question in questionnaire.questions)
        assert all(question.prompt for question in questionnaire.questions)
        assert all(question.construct for question in questionnaire.questions)


def test_get_survey_questionnaire_returns_real_feature_survey():
    questionnaire = get_survey_questionnaire("commerce_nike_air_max_dn_dynamic_air_v1")

    assert questionnaire.title == "Nike Air Max Dn Dynamic Air Purchase Survey"
    assert [question.id for question in questionnaire.questions] == [
        "dynamic_air_appeal",
        "comfort_price_tolerance",
        "purchase_driver",
        "proof_requirement",
    ]


def test_get_survey_questionnaire_unknown_id_raises_keyerror():
    with pytest.raises(KeyError, match="unknown survey questionnaire"):
        get_survey_questionnaire("missing_survey")


def test_repo_backed_survey_questionnaire_loads_structured_option_labels():
    questionnaire = get_survey_questionnaire("product_feedback_v1", repo_root=repo_root())

    first = questionnaire.questions[0]
    assert first.id == "q0"
    assert first.options[0] == "q0_use_free_wont_pay"
    assert first.option_details
    assert first.option_details[0].label.startswith("Keep using free.")


def test_repo_backed_survey_task_content_uses_task_input_without_infra_copy():
    questionnaire = get_survey_questionnaire("product_attitudes_v1", repo_root=repo_root())
    content = load_survey_task_content_for_questionnaire_id(
        questionnaire.id,
        repo_root=repo_root(),
        fallback_questionnaire=questionnaire,
    )

    assert content is not None
    assert "Complete the survey using the provided context" in content.instruction_markdown
    assert "input/output_schema.md" in content.instruction_markdown
    assert "backend/runtime" not in content.instruction_markdown
    assert "backend/runtime" not in content.output_schema_markdown
    assert '"trajectory"' not in content.output_schema_markdown
