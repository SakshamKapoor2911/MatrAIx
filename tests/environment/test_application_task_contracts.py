"""CI contract checks for every task under application/tasks/.

Scans all task folders (not only the canonical examples) against
application/task-spec/authoring-bundle.md so new tasks cannot slip through
with a custom runtime shape while curated example-only tests stay green.

Chatbot tasks must use ``application/shared-chat-persona`` and, when
``local_compose`` is set, a matching ``chatbot-*-sidecar_*`` host that
exists on disk and aligns with ``input/chatbot.yaml`` transport.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import tomllib
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS_ROOT = REPO_ROOT / "application" / "tasks"
ENVIRONMENTS_ROOT = REPO_ROOT / "environment" / "task-environments"
ALLOWED_TYPES = frozenset({"survey", "chatbot", "web", "os-app"})


def _task_dirs() -> list[Path]:
    return sorted(
        path
        for path in TASKS_ROOT.iterdir()
        if path.is_dir() and (path / "task.toml").is_file()
    )


def _load_task(task_dir: Path) -> dict:
    return tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))


def _env_dir(definition: str) -> Path:
    return ENVIRONMENTS_ROOT / definition


def _require(errors: list[str], ok: bool, message: str) -> None:
    if not ok:
        errors.append(message)


@pytest.mark.parametrize("task_dir", _task_dirs(), ids=lambda p: p.name)
def test_application_task_matches_type_contract(task_dir: Path) -> None:
    errors: list[str] = []
    raw = _load_task(task_dir)

    task_name = str((raw.get("task") or {}).get("name") or "").strip()
    meta = raw.get("metadata") or {}
    task_type = str(meta.get("type") or "").strip()
    env = raw.get("environment") or {}
    definition = str(env.get("definition") or "").strip()
    artifacts = raw.get("artifacts") or []

    _require(errors, bool(task_name), "task.toml [task].name is required")
    _require(
        errors,
        task_name.startswith("application/"),
        f"task name must start with 'application/' (got {task_name!r})",
    )
    _require(
        errors,
        task_type in ALLOWED_TYPES,
        f"metadata.type must be one of {sorted(ALLOWED_TYPES)} (got {task_type!r})",
    )
    _require(errors, bool(definition), "task.toml [environment].definition is required")
    _require(
        errors,
        isinstance(artifacts, list) and bool(artifacts),
        "artifacts must be a non-empty list",
    )
    _require(
        errors,
        (task_dir / "instruction.md").is_file(),
        "instruction.md is required",
    )
    _require(
        errors,
        (task_dir / "reporting.json").is_file(),
        "reporting.json is required",
    )
    _require(
        errors,
        (task_dir / "tests").is_dir(),
        "tests/ is required",
    )
    _require(
        errors,
        (task_dir / "tests" / "test.sh").is_file(),
        "tests/test.sh is required",
    )
    _require(
        errors,
        not (task_dir / "environment").exists(),
        "do not embed environment/ under the task folder",
    )
    _require(
        errors,
        not (task_dir / "input" / "output_schema.md").exists(),
        "do not add input/output_schema.md (platform owns the answer envelope)",
    )
    _require(
        errors,
        not (task_dir / "verifier").exists(),
        "do not commit verifier/ under the task folder (trial runtime output only)",
    )

    # Survey / chatbot / web verifiers emit structured_output via test_state.py.
    # Some os-app examples still use shell-only verifiers.
    if task_type in {"survey", "chatbot", "web"}:
        _require(
            errors,
            (task_dir / "tests" / "test_state.py").is_file(),
            "tests/test_state.py is required",
        )

    if (task_dir / "reporting.json").is_file():
        try:
            reporting = json.loads((task_dir / "reporting.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"reporting.json is not valid JSON: {exc}")
        else:
            _require(
                errors,
                isinstance(reporting, dict) and "schemaVersion" in reporting,
                "reporting.json must be an object with schemaVersion",
            )

    if definition:
        env_path = _env_dir(definition)
        _require(
            errors,
            env_path.is_dir(),
            f"environment definition not found: {env_path.relative_to(REPO_ROOT)}",
        )

    if task_type == "survey":
        q_path = task_dir / "input" / "questionnaire.yaml"
        _require(
            errors,
            q_path.is_file(),
            "survey tasks require input/questionnaire.yaml",
        )
        if q_path.is_file():
            try:
                questionnaire = yaml.safe_load(q_path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                errors.append(f"questionnaire.yaml is not valid YAML: {exc}")
            else:
                _require(
                    errors,
                    isinstance(questionnaire, dict),
                    "questionnaire.yaml must parse to a mapping",
                )
                if isinstance(questionnaire, dict):
                    _require(
                        errors,
                        isinstance(questionnaire.get("questions"), list)
                        and bool(questionnaire.get("questions")),
                        "questionnaire.yaml must define a non-empty questions list",
                    )
                    _require(
                        errors,
                        "output_schema" not in questionnaire,
                        "questionnaire.yaml must not define output_schema",
                    )
        _require(
            errors,
            definition == "application/shared-survey-form",
            "survey tasks must use environment.definition = "
            "'application/shared-survey-form'",
        )

    elif task_type == "chatbot":
        _require(
            errors,
            (task_dir / "input" / "chatbot.yaml").is_file(),
            "chatbot tasks require input/chatbot.yaml",
        )
        _require(
            errors,
            (task_dir / "input" / "self_report_schema.yaml").is_file(),
            "chatbot tasks require input/self_report_schema.yaml",
        )
        _require(
            errors,
            definition == "application/shared-chat-persona",
            "chatbot tasks must use environment.definition = "
            "'application/shared-chat-persona'",
        )
        local_compose = str(env.get("local_compose") or "").strip()
        if local_compose:
            compose_path = _env_dir(local_compose)
            _require(
                errors,
                compose_path.is_dir(),
                f"environment.local_compose not found: "
                f"{compose_path.relative_to(REPO_ROOT)}",
            )
            _require(
                errors,
                (compose_path / "docker-compose.yaml").is_file(),
                f"{compose_path.relative_to(REPO_ROOT)} must include "
                "docker-compose.yaml",
            )
            chatbot_yaml = task_dir / "input" / "chatbot.yaml"
            if chatbot_yaml.is_file():
                try:
                    chatbot_cfg = yaml.safe_load(
                        chatbot_yaml.read_text(encoding="utf-8")
                    )
                except yaml.YAMLError as exc:
                    errors.append(f"chatbot.yaml is not valid YAML: {exc}")
                    chatbot_cfg = None
                transport = ""
                if isinstance(chatbot_cfg, dict):
                    transport = str(chatbot_cfg.get("transport") or "").strip().lower()
                if transport == "mcp":
                    _require(
                        errors,
                        local_compose.startswith("application/chatbot-mcp-sidecar_"),
                        "MCP chatbot local_compose must be "
                        "application/chatbot-mcp-sidecar_<sut>",
                    )
                elif transport in {"sidecar_http", "external_http"}:
                    _require(
                        errors,
                        local_compose.startswith("application/chatbot-api-sidecar_")
                        or local_compose == "application/shared-chat-sim",
                        "HTTP chatbot local_compose must be "
                        "application/chatbot-api-sidecar_<sut> or application/shared-chat-sim",
                    )

        persona_env = _env_dir("application/shared-chat-persona")
        _require(
            errors,
            (persona_env / "Dockerfile").is_file(),
            "shared-chat-persona must include Dockerfile",
        )

    assert not errors, (
        f"{task_dir.relative_to(REPO_ROOT)} failed application task contract:\n- "
        + "\n- ".join(errors)
    )
