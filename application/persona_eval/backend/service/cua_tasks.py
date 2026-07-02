"""Registry of Harbor computer-use (CUA) tasks for PersonaEval."""

from __future__ import annotations

from typing import Dict, List

from backend.service.cua_types import CuaEvalTask
from backend.service.example_task_catalog import discover_example_tasks, task_id_from_folder


def _platform_for(folder_name: str) -> str:
    lowered = folder_name.lower()
    if "linux" in lowered:
        return "linux"
    if "macos" in lowered:
        return "macos"
    if "ios" in lowered:
        return "ios"
    if "web-cua" in lowered or "books" in lowered:
        return "web"
    return "desktop"


def _output_artifact_for(folder_name: str) -> str:
    if "books" in folder_name.lower():
        return "book_interest.json"
    return "decision.json"


def _cua_submission_profile_for(folder_name: str) -> str | None:
    if "books" in folder_name.lower():
        return "book_interest"
    return None


def _cua_backend_for(platform: str) -> str:
    if platform == "macos":
        return "macos"
    if platform == "ios":
        return "ios"
    return "docker"


def _environment_label_for(folder_name: str, platform: str) -> str:
    if platform == "linux":
        return "Docker Xvfb · persona-computer-1"
    if platform == "macos":
        return "use.computer · persona-computer-1"
    if platform == "ios":
        return "use.computer iOS · persona-computer-1"
    if platform == "web":
        return "Docker web CUA · persona-computer-1"
    return "persona-computer-1"


def _registry() -> Dict[str, CuaEvalTask]:
    tasks: Dict[str, CuaEvalTask] = {}
    for record in discover_example_tasks(category="cua"):
        platform = _platform_for(record.folder_name)
        task_id = task_id_from_folder(record.folder_name)
        tasks[task_id] = CuaEvalTask(
            id=task_id,
            title=record.title,
            platform=platform,
            description=record.description,
            task_path=record.task_path,
            output_artifact=_output_artifact_for(record.folder_name),
            cua_submission_profile=_cua_submission_profile_for(record.folder_name),
            environment_label=_environment_label_for(record.folder_name, platform),
            cua_backend=_cua_backend_for(platform),
        )
    return tasks


def list_cua_eval_tasks() -> List[CuaEvalTask]:
    return list(_registry().values())


def get_cua_eval_task(task_id: str) -> CuaEvalTask:
    try:
        return _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown CUA eval task: {}".format(task_id)) from exc
