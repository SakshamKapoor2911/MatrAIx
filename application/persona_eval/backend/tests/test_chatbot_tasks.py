from pathlib import Path

from backend.service.chatbot_tasks import get_chatbot_eval_task, list_chatbot_eval_tasks

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_list_chatbot_eval_tasks_discovers_registered_chatbot_tasks():
    tasks = list_chatbot_eval_tasks()
    ids = {task.id for task in tasks}

    assert "recommender-agent-chat-api" in ids
    assert "finance-openbb-chatbot" in ids
    assert "medical-assistant-chatbot" in ids
    assert "chat-mcp-support-chatbot" in ids
    assert len(tasks) == 4

    for task in tasks:
        task_path = REPO_ROOT / Path(str(task.task_path))
        assert task_path.is_dir(), "{} has missing task path".format(task.id)


def test_get_chatbot_eval_task_reads_runtime_defaults_from_chatbot_yaml():
    task = get_chatbot_eval_task("finance-openbb-chatbot")

    assert task.transport == "external_http"
    assert task.application_id == "finance_openbb"
    assert task.application_context == "financial_research"
    assert task.default_domain == "financial_research"


def test_get_chatbot_eval_task_preserves_mcp_transport():
    task = get_chatbot_eval_task("chat-mcp-support-chatbot")

    assert task.transport == "mcp"
    assert task.application_id == "acme_support_mcp"
    assert task.can_start is True
    assert task.health_url == "http://127.0.0.1:8903"
    assert task.available in (True, False)


def test_get_chatbot_eval_task_reads_recai_sidecar_defaults():
    task = get_chatbot_eval_task("recommender-agent-chat-api")

    assert task.transport == "sidecar_http"
    assert task.application_id == "recai"
    assert task.application_context == "movie"
    assert task.default_domain == "movie"
