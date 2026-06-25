from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def load_verifier_module():
    path = Path(__file__).with_name("test_state.py")
    spec = importlib.util.spec_from_file_location("chatbot_test_state", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_artifacts(
    output_dir: Path, *, turns: list[dict], grounded_items: list[dict]
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
                "applicationId": "recai",
                "applicationContext": "movie",
                "domain": "movie",
                "messages": messages,
                "turns": turns,
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "application_result.json").write_text(
        json.dumps(
            {
                "sessionId": "ses_123",
                "applicationId": "recai",
                "applicationContext": "movie",
                "domain": "movie",
                "groundedItems": grounded_items,
                "turnsToResult": 3,
            }
        ),
        encoding="utf-8",
    )


def run_verifier_against(output_dir: Path) -> int:
    module = load_verifier_module()
    module.OUTPUT_DIR = output_dir
    module.TRANSCRIPT_PATH = output_dir / "transcript.json"
    module.RESULT_PATH = output_dir / "application_result.json"
    module.FEEDBACK_PATH = output_dir / "user_feedback.json"
    module.PERSONA_SELF_REPORT_PATH = output_dir / "persona_self_report.json"
    module.RUN_METADATA_PATH = output_dir / "run_metadata.json"
    return module.main()


def test_instruction_delegates_chat_loop_to_task_controller():
    instruction = (
        Path(__file__).parents[1].joinpath("instruction.md").read_text(encoding="utf-8")
    )

    assert "python /app/chatbot_controller.py" in instruction
    assert "Do not call `chatbot-api` manually" in instruction
    assert "Do not debug, patch, or edit" in instruction
    assert "persona_self_report.json" in instruction
    assert "overallExperienceRating" not in instruction
    assert "7-8: the run is useful overall" not in instruction
    assert '"overallExperienceRating": 1' not in instruction


def test_dockerfile_copies_task_controller():
    dockerfile = (
        Path(__file__).parents[1]
        .joinpath("environment", "Dockerfile")
        .read_text(encoding="utf-8")
    )

    assert "COPY chatbot_controller.py /app/chatbot_controller.py" in dockerfile


def test_verifier_shell_uses_python3_available_in_task_image():
    test_script = (
        Path(__file__).parents[1]
        .joinpath("tests", "test.sh")
        .read_text(encoding="utf-8")
    )

    assert "python3 /tests/test_state.py" in test_script
    assert "python /tests/test_state.py" not in test_script


def test_verifier_uses_persona_self_report_and_does_not_call_application_scorer(
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
                "groundedItems": [],
            },
            {
                "turnId": "1",
                "userMessage": "Quiet and reflective.",
                "assistantMessage": "Try Movie A.",
                "groundedItems": [{"itemId": "42", "title": "Movie A"}],
            },
            {
                "turnId": "2",
                "userMessage": "That works.",
                "assistantMessage": "Movie A should fit well.",
                "groundedItems": [{"itemId": "42", "title": "Movie A"}],
            },
        ],
        grounded_items=[{"itemId": "42", "title": "Movie A"}],
    )
    (output_dir / "persona_self_report.json").write_text(
        json.dumps(
            {
                "productNeedSatisfaction": 4,
                "personalPreferenceSatisfaction": 5,
                "overallExperienceRating": 8,
                "reason": "Persona self-report output.",
                "askedUsefulClarificationQuestions": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "MATRIX_SCORER_PERSONA_JSON", json.dumps({"id": "p1", "name": "Persona One"})
    )
    monkeypatch.setenv("MATRIX_SCORER_MODULE", "missing_application_scorer")

    assert run_verifier_against(output_dir) == 0

    feedback = json.loads((output_dir / "persona_self_report.json").read_text(encoding="utf-8"))
    assert feedback["overallExperienceRating"] == 8
    assert feedback["reason"] == "Persona self-report output."


def test_verifier_allows_short_general_chatbot_run_without_grounded_items(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "sessionId": "fin_ses_123",
                "applicationId": "finance_openbb",
                "applicationContext": "financial_research",
                "domain": "financial_research",
                "messages": [
                    {"role": "user", "content": "Can you help me compare bank stocks?"},
                    {
                        "role": "assistant",
                        "content": "What time horizon and risk constraints matter?",
                    },
                ],
                "turns": [
                    {
                        "turnId": "0",
                        "userMessage": "Can you help me compare bank stocks?",
                        "assistantMessage": (
                            "What time horizon and risk constraints matter?"
                        ),
                        "groundedItems": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "application_result.json").write_text(
        json.dumps(
            {
                "sessionId": "fin_ses_123",
                "applicationId": "finance_openbb",
                "applicationContext": "financial_research",
                "domain": "financial_research",
                "groundedItems": [],
                "turnsToResult": 1,
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "persona_self_report.json").write_text(
        json.dumps(
            {
                "productNeedSatisfaction": 2,
                "personalPreferenceSatisfaction": 2,
                "overallExperienceRating": 3,
                "reason": "The chatbot only asked a clarifying question.",
                "askedUsefulClarificationQuestions": True,
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "run_metadata.json").write_text(
        json.dumps({"maxTurns": 1, "minTurns": 1, "turns": 1}),
        encoding="utf-8",
    )

    assert run_verifier_against(output_dir) == 0


def test_verifier_rejects_application_result_not_grounded_in_chatbot_turns(tmp_path):
    write_artifacts(
        tmp_path / "output",
        turns=[],
        grounded_items=[{"itemId": "movie_0001", "title": "Invented Movie"}],
    )

    with pytest.raises(SystemExit) as exc_info:
        run_verifier_against(tmp_path / "output")

    assert exc_info.value.code == 1


def test_verifier_accepts_application_result_grounded_in_chatbot_turns(tmp_path):
    write_artifacts(
        tmp_path / "output",
        turns=[
            {
                "turnId": "0",
                "userMessage": "I want a thoughtful movie.",
                "assistantMessage": "What tone do you prefer?",
                "groundedItems": [],
            },
            {
                "turnId": "1",
                "userMessage": "Quiet and reflective.",
                "assistantMessage": "Try Movie A.",
                "groundedItems": [{"itemId": "42", "title": "Movie A"}],
            },
            {
                "turnId": "2",
                "userMessage": "That works.",
                "assistantMessage": "Movie A should fit well.",
                "groundedItems": [{"itemId": "42", "title": "Movie A"}],
            },
        ],
        grounded_items=[{"itemId": "42", "title": "Movie A"}],
    )

    assert run_verifier_against(tmp_path / "output") == 0
