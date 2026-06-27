"""Tests for built-in PersonaEval survey instruments."""

from __future__ import annotations

import pytest

from application.persona_eval.backend.service.survey_instruments import (
    DEFAULT_SURVEY_INSTRUMENT_ID,
    get_survey_instrument,
    list_survey_instruments,
)
from application.persona_eval.backend.service.survey_types import (
    SurveyInstrument,
    SurveyQuestion,
)


REAL_FEATURE_SURVEY_IDS = [
    "software_claude_code_vscode_checkpoints_v1",
    "finance_robinhood_cortex_digests_v1",
    "healthcare_cvs_app_prescription_ai_v1",
    "commerce_nike_air_max_dn_dynamic_air_v1",
]


def test_list_survey_instruments_includes_real_feature_surveys() -> None:
    instruments = list_survey_instruments()
    ids = [instrument.id for instrument in instruments]

    assert ids == [DEFAULT_SURVEY_INSTRUMENT_ID] + REAL_FEATURE_SURVEY_IDS
    assert len(ids) == len(set(ids))

    for instrument in instruments:
        assert instrument.title
        assert instrument.description
        assert len(instrument.questions) >= 4
        assert all(question.id for question in instrument.questions)
        assert all(question.prompt for question in instrument.questions)
        assert all(question.construct for question in instrument.questions)


def test_get_survey_instrument_returns_real_feature_survey() -> None:
    instrument = get_survey_instrument("finance_robinhood_cortex_digests_v1")

    assert instrument.title == "Robinhood Cortex Digests Survey"
    assert [question.id for question in instrument.questions] == [
        "market_summary_utility",
        "source_transparency",
        "ai_investing_concern",
        "safety_requirement",
    ]


def test_get_survey_instrument_unknown_id_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="unknown survey instrument"):
        get_survey_instrument("missing_survey")


def test_survey_types_round_trip_dict_payload() -> None:
    instrument = SurveyInstrument(
        id="example",
        title="Example",
        description="Fixture",
        questions=[
            SurveyQuestion(
                id="q1",
                prompt="Rate the concept.",
                construct="concept_fit",
            ),
            SurveyQuestion(
                id="q2",
                prompt="Pick one.",
                type="single_choice",
                options=["a", "b"],
                construct="choice",
            ),
        ],
    )

    assert SurveyInstrument.from_dict(instrument.to_dict()) == instrument


def test_survey_question_rejects_invalid_choice_question() -> None:
    with pytest.raises(ValueError, match="single_choice questions require options"):
        SurveyQuestion(
            id="missing_options",
            prompt="Pick one.",
            type="single_choice",
        )
