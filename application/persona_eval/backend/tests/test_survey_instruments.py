"""Tests for built-in PersonaEval survey instruments."""

from __future__ import annotations

import pytest

from backend.service.survey_instruments import (
    DEFAULT_SURVEY_INSTRUMENT_ID,
    get_survey_instrument,
    list_survey_instruments,
)


REAL_FEATURE_SURVEY_IDS = [
    "software_claude_code_vscode_checkpoints_v1",
    "finance_robinhood_cortex_digests_v1",
    "healthcare_cvs_app_prescription_ai_v1",
    "commerce_nike_air_max_dn_dynamic_air_v1",
]


def test_list_survey_instruments_includes_real_feature_surveys():
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


def test_get_survey_instrument_returns_real_feature_survey():
    instrument = get_survey_instrument("commerce_nike_air_max_dn_dynamic_air_v1")

    assert instrument.title == "Nike Air Max Dn Dynamic Air Purchase Survey"
    assert [question.id for question in instrument.questions] == [
        "dynamic_air_appeal",
        "comfort_price_tolerance",
        "purchase_driver",
        "proof_requirement",
    ]


def test_get_survey_instrument_unknown_id_raises_keyerror():
    with pytest.raises(KeyError, match="unknown survey instrument"):
        get_survey_instrument("missing_survey")
