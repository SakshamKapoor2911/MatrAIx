from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from application.playground.backend.service.recommender_eval import (
    RecommenderEvalConfig,
    RecommenderPersona,
    build_recommender_simulation_prompt,
    build_result_from_task_artifacts,
    write_harbor_persona_yaml,
)


def test_build_result_from_task_artifacts_maps_grounded_transcript_and_feedback(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "sessionId": "session-123",
                "domain": "movie",
                "messages": [
                    {"role": "user", "content": "I want a thoughtful drama."},
                    {"role": "assistant", "content": "Do you prefer recent films?"},
                    {"role": "user", "content": "Yes, and not too bleak."},
                    {"role": "assistant", "content": "Try Past Lives."},
                ],
                "turns": [
                    {
                        "turnId": "0",
                        "userMessage": "I want a thoughtful drama.",
                        "assistantMessage": "Do you prefer recent films?",
                        "recommendedItems": [],
                    },
                    {
                        "turnId": "1",
                        "userMessage": "Yes, and not too bleak.",
                        "assistantMessage": "Try Past Lives.",
                        "recommendedItems": [
                            {"itemId": "movie-past-lives", "title": "Past Lives"}
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "recommendation_result.json").write_text(
        json.dumps(
            {
                "sessionId": "session-123",
                "domain": "movie",
                "recommendedItems": [
                    {"itemId": "movie-past-lives", "title": "Past Lives"}
                ],
                "turnsToRecommendation": 2,
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "user_feedback.json").write_text(
        json.dumps(
            {
                "productNeedConstraintSatisfaction": "partially",
                "personalPreferenceSatisfaction": "yes",
                "overallExperienceRating": 8,
                "reason": "The recommendation fit, but the first turn was broad.",
                "askedUsefulClarificationQuestions": True,
            }
        ),
        encoding="utf-8",
    )

    result = build_result_from_task_artifacts(
        output_dir=output_dir,
        config=RecommenderEvalConfig(domain="movie", engine="gpt-4o-mini"),
        persona=RecommenderPersona(
            id="persona-1",
            name="Persona One",
            context="A careful viewer who likes warm dramas.",
        ),
        sut_description="Movie recommender.",
        created_at="2026-06-27T00:00:00Z",
        prompts={"harborPrompt": "Persona prompt.", "taskPrompt": "Task prompt."},
    )

    payload = result.to_dict()
    assert payload["config"]["domain"] == "movie"
    assert payload["persona"]["name"] == "Persona One"
    assert payload["recommendedItemIds"] == {
        "perTurn": [[], ["movie-past-lives"]],
        "final": ["movie-past-lives"],
    }
    assert payload["questionnaire"] == {
        "constraintSatisfaction": 3,
        "constraintRationale": "The recommendation fit, but the first turn was broad.",
        "preferenceSatisfaction": 5,
        "preferenceRationale": "The recommendation fit, but the first turn was broad.",
        "overallRating": 8,
        "ratingReason": "The recommendation fit, but the first turn was broad.",
        "askedUsefulClarifyingQuestions": True,
        "clarifyingNotes": "The recommendation fit, but the first turn was broad.",
    }
    assert payload["metricScores"] == {
        "turnsToRecommendation": 2,
        "numTurns": 2,
        "recommendedItemCount": 1,
    }
    assert payload["prompts"] == {
        "harborPrompt": "Persona prompt.",
        "taskPrompt": "Task prompt.",
    }


def test_build_result_from_task_artifacts_rejects_ungrounded_recommendations(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "sessionId": "session-123",
                "domain": "movie",
                "messages": [
                    {"role": "user", "content": "I want a movie."},
                    {"role": "assistant", "content": "Try something."},
                ],
                "turns": [],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "recommendation_result.json").write_text(
        json.dumps(
            {
                "sessionId": "session-123",
                "domain": "movie",
                "recommendedItems": [
                    {"itemId": "invented-id", "title": "Invented Movie"}
                ],
                "turnsToRecommendation": 1,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="grounded"):
        build_result_from_task_artifacts(
            output_dir=output_dir,
            config=RecommenderEvalConfig(domain="movie"),
            persona=RecommenderPersona(id="persona-1", name="Persona One"),
            sut_description="Movie recommender.",
            created_at="2026-06-27T00:00:00Z",
        )


def test_build_recommender_simulation_prompt_is_task_specific() -> None:
    prompt = build_recommender_simulation_prompt(
        domain="game",
        max_turns=7,
        sut_description="A game recommender exposed through a chat API.",
        goal_context_description="Reveal preferences gradually.",
    )

    assert "Harbor supplies the persona system prompt" in prompt
    assert "You are testing a game recommendation system" in prompt
    assert '"domain": "game"' in prompt
    assert "at least three user turns and three assistant turns" in prompt
    assert "Finish within 7 user turns" in prompt
    assert "Do not simulate the recommender" in prompt
    assert "MATRIX_" not in prompt
    assert "applications/recommendation_chatbot_eval" not in prompt


def test_write_harbor_persona_yaml_uses_context_as_system_prompt(tmp_path: Path) -> None:
    persona = RecommenderPersona(
        id="persona-1",
        name="Persona One",
        summary="A careful viewer.",
        context="Name: Persona One\nStyle: concise and skeptical",
    )

    path = write_harbor_persona_yaml(tmp_path, persona)

    assert yaml.safe_load(path.read_text(encoding="utf-8")) == {
        "persona_id": "persona-1",
        "display_name": "Persona One",
        "summary": "A careful viewer.",
        "system_prompt": "Name: Persona One\nStyle: concise and skeptical",
    }
