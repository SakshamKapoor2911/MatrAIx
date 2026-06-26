"""Tests for built-in PersonaEval survey instruments."""

from __future__ import annotations

import pytest

from backend.service.survey_instruments import (
    DEFAULT_SURVEY_INSTRUMENT_ID,
    get_survey_instrument,
    list_survey_instruments,
)


REAL_FEATURE_SURVEY_IDS = [
    "instagram_reels_market_research_v1",
    "nike_air_max_dn_market_research_v1",
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
    instrument = get_survey_instrument("nike_air_max_dn_market_research_v1")

    assert instrument.title == "Nike Air Max Dn Market Research Survey"
    assert [question.id for question in instrument.questions] == [
        "try_on_intent",
        "purchase_driver",
        "adoption_barrier",
        "proof_needed",
    ]


def test_get_survey_instrument_unknown_id_raises_keyerror():
    with pytest.raises(KeyError, match="unknown survey instrument"):
        get_survey_instrument("missing_survey")
