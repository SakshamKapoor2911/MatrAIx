"""Registry of PersonaEval chatbot application tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from backend.service.chatbot_sidecar_service import sidecar_reachable, sidecar_status
from backend.service.example_task_catalog import (
    discover_application_tasks,
    repo_root,
    task_id_from_folder,
)
from persona_eval.chatbot_task_config import (
    ChatbotTaskConfig,
    load_chatbot_task_config_for_task_path,
)


@dataclass(frozen=True)
class ChatbotEvalTask:
    id: str
    title: str
    description: str
    task_path: Union[str, Path]
    transport: str = "http"
    application_id: str = ""
    application_context: str = ""
    default_domain: str = ""
    meta_type: str = "chatbot"
    domain: str = ""
    difficulty: str = "easy"
    task_kind: str = "task"
    available: Optional[bool] = None
    can_start: bool = False
    health_url: str = ""
    status_detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        task_path = self.task_path
        if isinstance(task_path, Path):
            parts = task_path.parts
            if "application" in parts and "tasks" in parts:
                idx = parts.index("tasks")
                task_path = "/".join(parts[idx - 1 :])
            else:
                task_path = str(task_path)
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "taskPath": str(task_path),
            "transport": self.transport,
            "applicationId": self.application_id,
            "applicationContext": self.application_context,
            "defaultDomain": self.default_domain,
            "metaType": self.meta_type,
            "domain": self.domain,
            "difficulty": self.difficulty,
            "taskKind": self.task_kind,
            "available": self.available,
            "canStart": self.can_start,
            "healthUrl": self.health_url,
            "statusDetail": self.status_detail,
        }


def _task_availability(task_config: ChatbotTaskConfig) -> dict[str, Any]:
    application_id = task_config.runtime_defaults.application_id
    try:
        status = sidecar_status(application_id, repo_root=repo_root())
    except ValueError:
        base_url = task_config.connection.resolve_base_url()
        if base_url:
            ok = sidecar_reachable(base_url)
            return {
                "available": ok,
                "canStart": False,
                "healthUrl": base_url,
                "statusDetail": (
                    "Chat API reachable at {}.".format(base_url)
                    if ok
                    else "Chat API not reachable at {}.".format(base_url)
                ),
            }
        if task_config.transport == "mcp":
            return {
                "available": None,
                "canStart": False,
                "healthUrl": "",
                "statusDetail": "MCP-backed task; no HTTP health check is configured.",
            }
        return {
            "available": None,
            "canStart": False,
            "healthUrl": "",
            "statusDetail": "No HTTP health check is configured for this chatbot task.",
        }
    return {
        "available": status["ok"],
        "canStart": status["canStart"],
        "healthUrl": status["healthUrl"],
        "statusDetail": status["detail"],
    }


def _registry() -> Dict[str, ChatbotEvalTask]:
    tasks: Dict[str, ChatbotEvalTask] = {}
    root = repo_root()
    for record in discover_application_tasks(application_type="chatbot"):
        task_id = task_id_from_folder(record.folder_name)
        task_config = load_chatbot_task_config_for_task_path(record.task_path, repo_root=root)
        availability = _task_availability(task_config) if task_config is not None else {}
        runtime = task_config.runtime_defaults if task_config is not None else None
        tasks[task_id] = ChatbotEvalTask(
            id=task_id,
            title=record.title,
            description=record.description,
            task_path=record.task_path,
            transport=task_config.transport if task_config is not None else "http",
            application_id=runtime.application_id if runtime is not None else "",
            application_context=runtime.application_context if runtime is not None else "",
            default_domain=runtime.domain if runtime is not None else "",
            meta_type=record.meta_type,
            domain=record.domain,
            difficulty=record.difficulty,
            task_kind=record.task_kind,
            available=availability.get("available"),
            can_start=bool(availability.get("canStart", False)),
            health_url=str(availability.get("healthUrl") or ""),
            status_detail=str(availability.get("statusDetail") or ""),
        )
    return tasks


def list_chatbot_eval_tasks() -> List[ChatbotEvalTask]:
    return list(_registry().values())


def get_chatbot_eval_task(task_id: str) -> ChatbotEvalTask:
    try:
        return _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown chatbot eval task: {}".format(task_id)) from exc
