from __future__ import annotations

from pathlib import Path

from persona_eval.chatbot_task_config import (
    load_chatbot_task_config_for_task_path,
)
from persona_eval.harbor.chat_eval import (
    chat_api_url_from_env,
    harbor_chat_task_config_from_env,
)


def test_load_chatbot_task_config_from_input_dir(tmp_path, monkeypatch) -> None:
    task_dir = tmp_path / "application" / "tasks" / "finance-openbb_chatbot" / "input"
    task_dir.mkdir(parents=True)
    (task_dir / "chatbot.yaml").write_text(
        "\n".join(
            [
                "transport: external_http",
                "runtimeDefaults:",
                "  applicationId: finance_openbb",
                "  applicationContext: financial_research",
                "  domain: financial_research",
                "  maxTurns: 9",
                "connection:",
                "  baseUrlEnv: CHATBOT_UPSTREAM_FINANCE",
                "  legacyBaseUrlEnv: FINANCE_CHATBOT_URL",
                "  baseUrl: http://finance-chatbot:8000",
                "protocol:",
                "  sendMessage:",
                "    method: POST",
                "    path: /v1/messages",
                "    engineField: engine",
                "    staticBody:",
                "      applicationId: finance_openbb",
                "      applicationContext: financial_research",
                "  response:",
                "    replyField: reply",
                "personaExposure:",
                "  fields:",
                "    - key: recommendedItems",
                "      label: Suggested instruments",
                "      selector: recommendedItems",
                "      format: item_list",
            ]
        ),
        encoding="utf-8",
    )
    config = load_chatbot_task_config_for_task_path(
        "application/tasks/finance-openbb_chatbot",
        repo_root=tmp_path,
    )
    assert config is not None
    assert config.transport == "external_http"
    assert config.runtime_defaults.application_id == "finance_openbb"
    assert config.runtime_defaults.max_turns == 9
    assert config.protocol.engine_field == "engine"
    assert config.protocol.static_body["applicationId"] == "finance_openbb"
    assert config.persona_exposure[0].selector == "recommendedItems"

    monkeypatch.setenv("CHATBOT_UPSTREAM_FINANCE", "http://finance.local:9000")
    assert chat_api_url_from_env("finance_openbb", task_config=config) == "http://finance.local:9000"


def test_harbor_chat_task_config_from_env_uses_task_path(tmp_path, monkeypatch) -> None:
    task_dir = tmp_path / "application" / "tasks" / "medical-assistant_chatbot" / "input"
    task_dir.mkdir(parents=True)
    (task_dir / "chatbot.yaml").write_text(
        "\n".join(
            [
                "transport: external_http",
                "runtimeDefaults:",
                "  applicationId: medical_assistant",
                "  applicationContext: medical_consultation",
                "  domain: medical_consultation",
                "connection:",
                "  baseUrlEnv: CHATBOT_UPSTREAM_MEDICAL",
                "  baseUrl: http://medical-chatbot:8000",
                "protocol:",
                "  sendMessage:",
                "    path: /v1/messages",
                "    staticBody:",
                "      applicationId: medical_assistant",
                "      applicationContext: medical_consultation",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "MATRIX_CHATBOT_TASK_PATH",
        "application/tasks/medical-assistant_chatbot",
    )
    config = harbor_chat_task_config_from_env(repo_root=tmp_path)
    assert config is not None
    assert config.connection.base_url == "http://medical-chatbot:8000"
    assert config.runtime_defaults.application_id == "medical_assistant"
    assert config.protocol.static_body["applicationContext"] == "medical_consultation"
