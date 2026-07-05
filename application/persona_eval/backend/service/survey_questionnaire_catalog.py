"""Task-backed survey questionnaire catalog for PersonaEval survey tasks."""

from __future__ import annotations

from pathlib import Path

from persona_eval.survey_task_content import (
    SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID,
    load_survey_task_content_for_questionnaire_id,
)

from .survey_types import SurveyInstrument

__all__ = [
    "DEFAULT_SURVEY_QUESTIONNAIRE_ID",
    "get_survey_questionnaire",
    "list_survey_questionnaires",
]

DEFAULT_SURVEY_QUESTIONNAIRE_ID = "product_attitudes_v1"


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _known_questionnaire_ids() -> list[str]:
    return list(SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID.keys())


def list_survey_questionnaires(*, repo_root: Path | None = None) -> list[SurveyInstrument]:
    """Return all task-backed survey questionnaires in stable display order."""
    root = Path(repo_root) if repo_root is not None else _default_repo_root()
    return [get_survey_questionnaire(questionnaire_id, repo_root=root) for questionnaire_id in _known_questionnaire_ids()]


def get_survey_questionnaire(
    questionnaire_id: str,
    *,
    repo_root: Path | None = None,
) -> SurveyInstrument:
    """Return one task-backed survey questionnaire loaded from task-local docs."""
    if questionnaire_id not in SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID:
        raise KeyError("unknown survey questionnaire: {}".format(questionnaire_id))

    root = Path(repo_root) if repo_root is not None else _default_repo_root()
    try:
        content = load_survey_task_content_for_questionnaire_id(
            questionnaire_id,
            repo_root=root,
        )
    except Exception as exc:  # noqa: BLE001
        task_folder = SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID[questionnaire_id]
        raise FileNotFoundError(
            "failed to load survey questionnaire {} from application/tasks/{}/input/questionnaire.yaml".format(
                questionnaire_id,
                task_folder,
            )
        ) from exc
    if content is None or content.instrument is None:
        task_folder = SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID[questionnaire_id]
        raise FileNotFoundError(
            "missing survey questionnaire {} under application/tasks/{}/input/questionnaire.yaml".format(
                questionnaire_id,
                task_folder,
            )
        )
    return content.instrument
