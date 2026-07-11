"""Harbor survey tasks for Playground (reference example + contributing tasks)."""

from __future__ import annotations

from typing import Dict, List

from backend.service.example_task_catalog import (
    discover_survey_application_tasks,
    repo_root,
    task_id_from_folder,
)
from backend.service.survey_harbor_types import SurveyHarborTask
from backend.service.survey_task_registry import survey_questionnaire_id_for_task_path
from backend.service.task_detail_service import attach_task_profile_markdown


def _registry() -> Dict[str, SurveyHarborTask]:
    tasks: Dict[str, SurveyHarborTask] = {}
    root = repo_root()
    for record in discover_survey_application_tasks():
        questionnaire_id = survey_questionnaire_id_for_task_path(record.task_path)
        if not questionnaire_id:
            continue
        task_id = "harbor-{}".format(task_id_from_folder(record.folder_name))
        profile_markdown = ""
        instruction_markdown = ""
        context_markdown = ""
        questionnaire_markdown = ""
        output_schema_markdown = ""
        questionnaire = None
        try:
            enriched = attach_task_profile_markdown(
                {"taskPath": record.task_path},
                repo_root=root,
            )
            profile_markdown = str(enriched.get("profileMarkdown") or "")
            instruction_markdown = str(enriched.get("instructionMarkdown") or "")
            context_markdown = str(enriched.get("contextMarkdown") or "")
            questionnaire_markdown = str(enriched.get("questionnaireMarkdown") or "")
            output_schema_markdown = str(enriched.get("outputSchemaMarkdown") or "")
            questionnaire = enriched.get("questionnaire")
        except Exception:  # noqa: BLE001
            profile_markdown = ""
            instruction_markdown = ""
            context_markdown = ""
            questionnaire_markdown = ""
            output_schema_markdown = ""
            questionnaire = None
        tasks[task_id] = SurveyHarborTask(
            id=task_id,
            title=record.title,
            description=record.description,
            task_path=record.task_path,
            instrument_id=questionnaire_id,
            profile_markdown=profile_markdown,
            instruction_markdown=instruction_markdown,
            context_markdown=context_markdown,
            questionnaire_markdown=questionnaire_markdown,
            output_schema_markdown=output_schema_markdown,
            questionnaire=questionnaire,
            survey_kind="example" if record.task_kind == "example" else "contributing",
            meta_type=record.meta_type,
            domain=record.domain,
            difficulty=record.difficulty,
            task_kind=record.task_kind,
            tags=tuple(record.tags),
        )
    return tasks


def list_survey_harbor_tasks() -> List[SurveyHarborTask]:
    return list(_registry().values())


def get_survey_harbor_task(task_id: str) -> SurveyHarborTask:
    try:
        return _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown survey harbor task: {}".format(task_id)) from exc
