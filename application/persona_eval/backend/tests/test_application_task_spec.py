from __future__ import annotations

import json
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
TASKS_ROOT = REPO_ROOT / "application" / "tasks"
ENVIRONMENTS_ROOT = REPO_ROOT / "environment" / "task-environments" / "application"
TASK_SPEC_ROOT = REPO_ROOT / "application" / "task-spec"


def test_application_task_spec_manifest_groups_core_protocols() -> None:
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


def test_application_task_spec_docs_exist_for_each_protocol() -> None:
    for dirname in ("survey", "chatbot", "web"):
        doc = TASK_SPEC_ROOT / dirname / "README.md"
        assert doc.is_file(), doc
        text = doc.read_text(encoding="utf-8")
        assert "Task instruction" in text
        assert "Interaction protocol" in text
        assert "Evaluation contract" in text


def test_application_tasks_do_not_embed_runtime_environments() -> None:
    embedded = sorted(path.relative_to(TASKS_ROOT) for path in TASKS_ROOT.glob("*/environment"))
    assert embedded == []


def test_canonical_survey_task_shape() -> None:
    task = TASKS_ROOT / "example-survey_product-feedback"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["task"]["name"] == "personabench/application-survey-product-feedback"
    assert raw["metadata"]["type"] == "survey"
    assert raw["metadata"]["domain"] == "software"
    assert "/app/output" in raw["artifacts"]
    assert raw["environment"]["definition"] == "application/shared-survey-form"
    assert (task / "input" / "questionnaire.yaml").is_file()
    assert "test_state.py" in (
        task / "tests" / "test.sh"
    ).read_text(encoding="utf-8")


def test_survey_reference_tasks_use_shared_runtime_and_task_local_input() -> None:
    for folder in ("example-survey_product-feedback", "survey_product-attitudes"):
        task = TASKS_ROOT / folder
        raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

        assert raw["metadata"]["type"] == "survey"
        assert raw["environment"]["definition"] == "application/shared-survey-form"
        assert (task / "instruction.md").is_file()
        assert (task / "input" / "context.md").is_file()
        assert (task / "input" / "questionnaire.yaml").is_file()
        assert (task / "input" / "output_schema.md").is_file()


def test_canonical_chatbot_task_shape() -> None:
    task = TASKS_ROOT / "recommender-agent_chat_api"
    env = ENVIRONMENTS_ROOT / "shared-chat-api-recommender"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["task"]["name"] == "personabench/application-recommender-agent-chat-api"
    assert raw["metadata"]["type"] == "chatbot"
    assert raw["metadata"]["domain"] == "commerce-retail"
    assert raw["environment"]["definition"] == "application/shared-chat-api-recommender"
    assert "/app/output" in raw["artifacts"]
    assert (env / "recommender-api" / "server.py").is_file()
    assert (task / "input" / "self_report_schema.yaml").is_file()
    assert not (task / "input" / "output_schema.md").exists()


def test_canonical_web_task_shape() -> None:
    task = TASKS_ROOT / "example-web-playwright_quote-choice"
    env = ENVIRONMENTS_ROOT / "shared-web-playwright"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["task"]["name"] == (
        "personabench/application-web-playwright-quote-choice"
    )
    assert raw["metadata"]["type"] == "web"
    assert raw["metadata"]["domain"] == "arts-culture"
    assert raw["environment"]["definition"] == "application/shared-web-playwright"
    assert "/app/output" in raw["artifacts"]
    assert (task / "input" / "self_report_schema.yaml").is_file()
    assert "quote_choice.json" in (task / "instruction.md").read_text(encoding="utf-8")
    dockerfile = (env / "Dockerfile").read_text(encoding="utf-8")
    assert "playwright" in dockerfile.lower()
    assert "python" in dockerfile.lower()
