"""Tests for Harbor user_sim_chat artifact mapping."""

from __future__ import annotations

from environment.integrations.persona_eval.harbor.chat_artifacts import (
    harbor_artifacts_from_result,
    harbor_chat_config_from_env,
)
from environment.integrations.persona_eval.harbor.chat_sidecar_io import parse_json_stdout
from persona_eval.types import (
    MetricScores,
    Persona,
    PersonaEvalConfig,
    PersonaEvalResult,
    PersonaEvalTurn,
    Questionnaire,
)


def test_harbor_artifacts_from_result_maps_chat_contract(monkeypatch):
    monkeypatch.delenv("MATRIX_CHATBOT_DOMAIN", raising=False)
    config = harbor_chat_config_from_env()
    assert config.domain == "movie"
    assert config.application_id == "recai"

    persona = Persona(id="0042", name="Test", context="A movie fan.")
    result = PersonaEvalResult(
        config=PersonaEvalConfig(domain="movie", max_turns=5),
        persona=persona,
        sut_description="Movie recommender.",
        transcript=[
            PersonaEvalTurn(
                turn_index=1,
                user_message="Hi",
                assistant_message="Hello",
                recommended_items=[],
                decision="continue",
            ),
            PersonaEvalTurn(
                turn_index=2,
                user_message="Something warm",
                assistant_message="Try Past Lives",
                recommended_items=[{"id": "movie-past-lives", "title": "Past Lives"}],
                decision="satisfied",
            ),
        ],
        questionnaire=Questionnaire(
            constraint_satisfaction=4,
            constraint_rationale="Mostly met.",
            preference_satisfaction=5,
            preference_rationale="Liked it.",
            overall_rating=8,
            rating_reason="Good chat.",
            asked_useful_clarifying_questions=True,
            clarifying_notes="Asked about tone.",
        ),
        metric_scores=MetricScores(
            turns_to_recommendation=2,
            num_turns=2,
            recommended_item_count=1,
        ),
        created_at="2026-06-30T00:00:00Z",
    )

    artifacts = harbor_artifacts_from_result(
        result,
        session_id="sess-1",
        domain="movie",
    )
    transcript = artifacts["transcript.json"]
    assert transcript["sessionId"] == "sess-1"
    assert len(transcript["messages"]) == 4
    recommendation = artifacts["recommendation_result.json"]
    assert recommendation["recommendedItems"][0]["itemId"] == "movie-past-lives"
    assert recommendation["turnsToRecommendation"] == 2
    feedback = artifacts["user_feedback.json"]
    assert feedback["productNeedConstraintSatisfaction"] == "yes"
    assert feedback["overallExperienceRating"] == 8


def test_parse_json_stdout_skips_shell_profile_noise():
    raw = (
        'export JAVA_HOME=$(/usr/libexec/java_home) {"sessionId": "abc", "reply": "hi"}'
    )
    parsed = parse_json_stdout(raw)
    assert parsed["sessionId"] == "abc"
    assert parsed["reply"] == "hi"
