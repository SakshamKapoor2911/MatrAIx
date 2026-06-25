from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def load_verifier_module():
    path = Path(__file__).with_name("test_state.py")
    spec = importlib.util.spec_from_file_location("recommender_test_state", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_artifacts(
    output_dir: Path, *, turns: list[dict], recommended_items: list[dict]
) -> None:
    output_dir.mkdir()
    messages = [
        {"role": "user", "content": "I want a thoughtful movie."},
        {"role": "assistant", "content": "What tone do you prefer?"},
        {"role": "user", "content": "Quiet and reflective."},
        {"role": "assistant", "content": "Any settings you like?"},
        {"role": "user", "content": "Asian cinema would be good."},
        {"role": "assistant", "content": "Here are some ideas."},
    ]
    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "sessionId": "ses_123",
                "domain": "movie",
                "messages": messages,
                "turns": turns,
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "recommendation_result.json").write_text(
        json.dumps(
            {
                "sessionId": "ses_123",
                "domain": "movie",
                "recommendedItems": recommended_items,
                "turnsToRecommendation": 3,
            }
        ),
        encoding="utf-8",
    )


def run_verifier_against(output_dir: Path) -> int:
    module = load_verifier_module()
    module.OUTPUT_DIR = output_dir
    module.TRANSCRIPT_PATH = output_dir / "transcript.json"
    module.RESULT_PATH = output_dir / "recommendation_result.json"
    module.FEEDBACK_PATH = output_dir / "user_feedback.json"
    return module.main()


def test_instruction_delegates_feedback_rating_to_application_scorer():
    instruction = (
        Path(__file__).parents[1].joinpath("instruction.md").read_text(encoding="utf-8")
    )

    assert "application feedback scorer" in instruction
    assert "overallExperienceRating" not in instruction
    assert "7-8: the run is useful overall" not in instruction
    assert '"overallExperienceRating": 1' not in instruction


def test_verifier_shell_uses_python3_available_in_task_image():
    test_script = (
        Path(__file__).parents[1]
        .joinpath("tests", "test.sh")
        .read_text(encoding="utf-8")
    )

    assert "python3 /tests/test_state.py" in test_script
    assert "python /tests/test_state.py" not in test_script


def test_verifier_calls_application_scorer_when_context_is_present(
    tmp_path, monkeypatch
):
    output_dir = tmp_path / "output"
    write_artifacts(
        output_dir,
        turns=[
            {
                "turnId": "0",
                "userMessage": "I want a thoughtful movie.",
                "assistantMessage": "What tone do you prefer?",
                "recommendedItems": [],
            },
            {
                "turnId": "1",
                "userMessage": "Quiet and reflective.",
                "assistantMessage": "Try Movie A.",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            },
            {
                "turnId": "2",
                "userMessage": "That works.",
                "assistantMessage": "Movie A should fit well.",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            },
        ],
        recommended_items=[{"itemId": "42", "title": "Movie A"}],
    )
    package_parent = tmp_path / "package_parent"
    package_parent.mkdir()
    (package_parent / "application_scorer.py").write_text(
        """
import json

def score_harbor_artifacts_from_env(*, transcript_path, recommendation_path, output_path):
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    recommendation = json.loads(recommendation_path.read_text(encoding="utf-8"))
    payload = {
        "constraintSatisfaction": 4,
        "constraintRationale": transcript["sessionId"],
        "preferenceSatisfaction": 5,
        "preferenceRationale": recommendation["recommendedItems"][0]["itemId"],
        "overallRating": 8,
        "ratingReason": "Application scorer output.",
        "askedUsefulClarifyingQuestions": True,
        "clarifyingNotes": "Asked about tone.",
    }
    output_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload
""",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "MATRIX_SCORER_PERSONA_JSON", json.dumps({"id": "p1", "name": "Persona One"})
    )
    monkeypatch.setenv("MATRIX_SCORER_CONFIG_JSON", json.dumps({"domain": "movie"}))
    monkeypatch.setenv("MATRIX_SCORER_SUT_DESCRIPTION", "Movie recommender.")
    monkeypatch.setenv("MATRIX_SCORER_PACKAGE_PARENT", str(package_parent))
    monkeypatch.setenv("MATRIX_SCORER_MODULE", "application_scorer")
    monkeypatch.setenv(
        "MATRIX_SCORER_OUTPUT_PATH", str(output_dir / "user_feedback.json")
    )

    assert run_verifier_against(output_dir) == 0

    feedback = json.loads(
        (output_dir / "user_feedback.json").read_text(encoding="utf-8")
    )
    assert feedback["overallRating"] == 8
    assert feedback["constraintRationale"] == "ses_123"


def test_verifier_rejects_recommendations_not_grounded_in_recbot_turns(tmp_path):
    write_artifacts(
        tmp_path / "output",
        turns=[],
        recommended_items=[{"itemId": "movie_0001", "title": "Invented Movie"}],
    )

    with pytest.raises(SystemExit) as exc_info:
        run_verifier_against(tmp_path / "output")

    assert exc_info.value.code == 1


def test_verifier_accepts_recommendations_grounded_in_recbot_turns(tmp_path):
    write_artifacts(
        tmp_path / "output",
        turns=[
            {
                "turnId": "0",
                "userMessage": "I want a thoughtful movie.",
                "assistantMessage": "What tone do you prefer?",
                "recommendedItems": [],
            },
            {
                "turnId": "1",
                "userMessage": "Quiet and reflective.",
                "assistantMessage": "Try Movie A.",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            },
            {
                "turnId": "2",
                "userMessage": "That works.",
                "assistantMessage": "Movie A should fit well.",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            },
        ],
        recommended_items=[{"itemId": "42", "title": "Movie A"}],
    )

    assert run_verifier_against(tmp_path / "output") == 0
