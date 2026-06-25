from __future__ import annotations

import json
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
TASKS_ROOT = REPO_ROOT / "applications" / "tasks"
INTERFACE_ROOT = TASKS_ROOT / "application_interface"


def test_application_interface_manifest_groups_core_protocols() -> None:
    manifest = json.loads((INTERFACE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["schemaVersion"] == "application-task-interface-v1"
    assert set(manifest["applicationTypes"]) == {"survey", "chatbot", "web"}
    assert manifest["applicationTypes"]["survey"]["canonicalTask"] == (
        "applications/tasks/survey_form"
    )
    assert manifest["applicationTypes"]["chatbot"]["canonicalTask"] == (
        "applications/tasks/chatbot_chat_api"
    )
    assert manifest["applicationTypes"]["web"]["canonicalTask"] == (
        "applications/tasks/web-ecommerce-platform_product-discovery"
    )


def test_application_interface_docs_exist_for_each_protocol() -> None:
    for dirname in ("survey", "chatbot", "web"):
        doc = INTERFACE_ROOT / dirname / "README.md"
        assert doc.is_file(), doc
        text = doc.read_text(encoding="utf-8")
        assert "Task instruction" in text
        assert "Interaction protocol" in text
        assert "Evaluation contract" in text


def test_canonical_survey_task_shape() -> None:
    task = TASKS_ROOT / "survey_form"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["task"]["name"] == "matraix/application-survey-form"
    assert raw["metadata"]["type"] == "survey"
    assert raw["metadata"]["domain"] == "software"
    assert "/app/output" in raw["artifacts"]
    assert "python3 /tests/test_state.py" in (
        task / "tests" / "test.sh"
    ).read_text(encoding="utf-8")


def test_canonical_chatbot_task_shape() -> None:
    task = TASKS_ROOT / "chatbot_chat_api"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["task"]["name"] == "matraix/application-chatbot-chat-api"
    assert raw["metadata"]["type"] == "chat"
    assert raw["metadata"]["domain"] == "chatbot-applications"
    assert "/app/output" in raw["artifacts"]
    assert (task / "environment" / "chatbot_api" / "harbor_api").is_dir()


def test_canonical_web_task_shape() -> None:
    task = TASKS_ROOT / "web-ecommerce-platform_product-discovery"
    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))

    assert raw["task"]["name"] == (
        "matraix/application-web-ecommerce-platform-product-discovery"
    )
    assert raw["metadata"]["type"] == "web"
    assert raw["metadata"]["domain"] == "commerce-retail"
    assert "/app/output" in raw["artifacts"]

    site = task / "environment" / "ecommerce-web" / "site"
    catalog = json.loads((site / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["products"]
    assert '<img class="product-media"' in (site / "index.html").read_text(
        encoding="utf-8"
    )
