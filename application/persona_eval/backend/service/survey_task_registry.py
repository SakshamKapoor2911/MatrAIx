"""Map Harbor example-survey tasks to PersonaEval survey instruments."""

from __future__ import annotations

from pathlib import Path

from environment.integrations.persona_eval.survey_task_content import (
    instruction_markdown_for_instrument as _instruction_md,
    instrument_id_for_task_folder,
    task_folder_for_instrument,
)

# Re-export mapping helpers for backend callers.


def instrument_id_for_task_path(task_path: str) -> str | None:
    folder = Path(task_path.strip().replace("\\", "/")).name
    return instrument_id_for_task_folder(folder)


def task_path_for_instrument(instrument_id: str) -> str | None:
    folder = task_folder_for_instrument(instrument_id)
    if not folder:
        return None
    return "application/tasks/{}".format(folder)


def survey_instruction_markdown_for_instrument(
    instrument_id: str,
    *,
    repo_root: Path,
) -> str | None:
    """Return task ``instruction.md`` when this instrument has a Harbor content task."""
    direct = _instruction_md(instrument_id, repo_root=repo_root)
    if direct:
        return direct
    task_path = task_path_for_instrument(instrument_id)
    if not task_path:
        return None
    from backend.service.task_detail_service import get_task_detail

    try:
        detail = get_task_detail(task_path, repo_root=repo_root)
    except (FileNotFoundError, ValueError, OSError):
        return None
    instruction_md = str(detail.get("instructionMarkdown") or "").strip()
    if instruction_md:
        return instruction_md
    profile = str(detail.get("profileMarkdown") or "").strip()
    return profile or None
