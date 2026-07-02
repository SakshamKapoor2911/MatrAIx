"""Harbor survey tasks for PersonaEval (reference example + contributing tasks)."""

from __future__ import annotations

from typing import Dict, List

from backend.service.example_task_catalog import (
    discover_survey_application_tasks,
    repo_root,
    task_id_from_folder,
)
from backend.service.survey_harbor_types import SurveyHarborTask
from backend.service.survey_task_registry import instrument_id_for_task_path
from backend.service.task_detail_service import attach_task_profile_markdown
from environment.integrations.persona_eval.survey_task_content import is_example_survey_task_folder


def _registry() -> Dict[str, SurveyHarborTask]:
    tasks: Dict[str, SurveyHarborTask] = {}
    root = repo_root()
    for record in discover_survey_application_tasks():
        instrument_id = instrument_id_for_task_path(record.task_path)
        if not instrument_id:
            continue
        task_id = "harbor-{}".format(task_id_from_folder(record.folder_name))
        profile_markdown = ""
        try:
            enriched = attach_task_profile_markdown(
                {"taskPath": record.task_path},
                repo_root=root,
            )
            profile_markdown = str(enriched.get("profileMarkdown") or "")
        except Exception:  # noqa: BLE001
            profile_markdown = ""
        tasks[task_id] = SurveyHarborTask(
            id=task_id,
            title=record.title,
            description=record.description,
            task_path=record.task_path,
            instrument_id=instrument_id,
            profile_markdown=profile_markdown,
            survey_kind="example" if is_example_survey_task_folder(record.folder_name) else "contributing",
        )
    return tasks


def list_survey_harbor_tasks() -> List[SurveyHarborTask]:
    return list(_registry().values())


def get_survey_harbor_task(task_id: str) -> SurveyHarborTask:
    try:
        return _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown survey harbor task: {}".format(task_id)) from exc
