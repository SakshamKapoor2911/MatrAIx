from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from harbor.models.task.paths import TaskPaths
import tomllib


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_SURVEY = ROOT / "application/tasks/example-survey_product-feedback"
RECOMMENDER_CHAT = ROOT / "application/tasks/recommender-agent_chat_api"
TASK_SPEC_ROOT = ROOT / "application/task-spec"


def test_example_survey_task_metadata_is_clean() -> None:
    task_text = (EXAMPLE_SURVEY / "task.toml").read_text(encoding="utf-8")
    task = tomllib.loads(task_text)

    assert task["task"]["name"] == "personabench/application-survey-product-feedback"
    assert task["metadata"]["type"] == "survey"
    assert "matraix/" not in task_text.lower()

    readme = (EXAMPLE_SURVEY / "README.md").read_text(encoding="utf-8")
    assert "bench-dev-2000" not in readme


def test_example_survey_verifier_accepts_minimal_valid_result(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "survey_result.json").write_text(
        json.dumps(
            {
                "instrument": {"id": "smoke", "title": "Smoke survey"},
                "answers": [
                    {
                        "questionId": "q1",
                        "value": 4,
                        "rationale": "Fits the assigned persona.",
                        "confidence": 0.8,
                    }
                ],
                "trajectory": [
                    {
                        "timestamp": "2026-06-24T00:00:00Z",
                        "actor": "user",
                        "action": "answer_question",
                        "context": {"questionId": "q1"},
                        "outcome": {"questionId": "q1", "value": 4},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    verifier_path = EXAMPLE_SURVEY / "tests/test_state.py"
    spec = importlib.util.spec_from_file_location("example_survey_test_state", verifier_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.OUTPUT_DIR = output_dir
    module.RESULT_PATH = output_dir / "survey_result.json"
    assert module.main() == 0


def test_recommender_chat_task_metadata_is_clean() -> None:
    task_text = (RECOMMENDER_CHAT / "task.toml").read_text(encoding="utf-8")
    task = tomllib.loads(task_text)

    assert task["task"]["name"] == "personabench/application-recommender-agent-chat-api"
    assert task["metadata"]["type"] == "chatbot"
    assert task["metadata"]["domain"] == "commerce-retail"
    assert "matraix/" not in task_text.lower()

    readme = (RECOMMENDER_CHAT / "README.md").read_text(encoding="utf-8")
    assert "applications/recommendation_chatbot_eval" not in readme
    assert "--persona-ids 0042" in readme
    assert "recommender-agent-chat-api-auto-n1.yaml" in readme


def test_recommender_chat_verifier_accepts_minimal_valid_result(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    session_id = "session-123"
    messages = [
        {"role": "user", "content": "I want a thoughtful movie for a quiet night."},
        {"role": "assistant", "content": "Do you prefer drama, comedy, or sci-fi?"},
        {"role": "user", "content": "Drama, but not too bleak."},
        {"role": "assistant", "content": "I can look for warm dramas with strong characters."},
        {"role": "user", "content": "A recent film would be best."},
        {"role": "assistant", "content": "Past Lives is a good fit."},
    ]
    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "sessionId": session_id,
                "domain": "movie",
                "messages": messages,
                "turns": [],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "user_feedback.json").write_text(
        json.dumps(
            {
                "needConstraintSatisfaction": "yes",
                "personalPreferenceSatisfaction": "partially",
                "overallExperienceRating": 8,
                "reason": "The recommendation fit the quiet drama request.",
                "askedUsefulClarificationQuestions": True,
            }
        ),
        encoding="utf-8",
    )

    verifier_path = RECOMMENDER_CHAT / "tests/test_state.py"
    spec = importlib.util.spec_from_file_location(
        "recommender_chat_test_state", verifier_path
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.OUTPUT_DIR = output_dir
    module.TRANSCRIPT_PATH = output_dir / "transcript.json"
    module.FEEDBACK_PATH = output_dir / "user_feedback.json"
    assert module.main() == 0


def test_recommender_chat_sidecar_contract() -> None:
    server_path = (
        TaskPaths.from_task_dir(RECOMMENDER_CHAT).environment_dir
        / "recommender-api"
        / "server.py"
    )
    spec = importlib.util.spec_from_file_location("recommender_api_server", server_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    session = module.create_session("movie")
    first_turn = module.post_message(
        session["sessionId"], "I want a warm, character-driven movie."
    )
    second_turn = module.post_message(
        session["sessionId"], "Please avoid bleak endings."
    )
    third_turn = module.post_message(session["sessionId"], "Something recent is ideal.")

    assert first_turn["reply"]
    assert second_turn["reply"]
    assert third_turn["recommendedItems"]

    conversation = module.get_conversation(session["sessionId"])
    recommendations = module.get_recommendations(session["sessionId"])

    assert len(conversation["messages"]) == 6
    assert recommendations["total"] >= 1
    assert recommendations["recommendedItems"][0]["itemId"].startswith("movie-")


def test_application_task_spec_manifest_uses_clean_task_paths() -> None:
    manifest = json.loads((TASK_SPEC_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["schemaVersion"] == "application-task-spec-v1"
    assert set(manifest["applicationTypes"]) == {
        "survey",
        "chatbot",
        "web",
        "os-app",
    }
    assert manifest["applicationTypes"]["survey"]["canonicalTask"] == (
        "application/tasks/example-survey_product-feedback"
    )
    assert manifest["applicationTypes"]["chatbot"]["canonicalTask"] == (
        "application/tasks/recommender-agent_chat_api"
    )
    assert manifest["applicationTypes"]["web"]["canonicalTask"] == (
        "application/tasks/example-web-playwright_quote-choice"
    )
    assert manifest["applicationTypes"]["os-app"]["canonicalTask"] == (
        "application/tasks/example-computer-use-ios_photo-access-review"
    )


def test_application_task_spec_docs_cover_each_protocol() -> None:
    for dirname in ("survey", "chatbot", "web"):
        doc = TASK_SPEC_ROOT / dirname / "README.md"
        assert doc.is_file(), doc
        text = doc.read_text(encoding="utf-8")
        assert "Task instruction" in text
        assert "Interaction protocol" in text
        assert "Evaluation contract" in text
        assert "applications/tasks/" not in text

    os_app_doc = TASK_SPEC_ROOT / "os-app" / "README.md"
    assert os_app_doc.is_file()
    os_app_text = os_app_doc.read_text(encoding="utf-8")
    assert "evaluation and reporting contract" in os_app_text.lower()
