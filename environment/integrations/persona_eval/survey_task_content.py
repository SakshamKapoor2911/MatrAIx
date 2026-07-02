"""Harbor survey task content for json_survey / complete_json runs."""

from __future__ import annotations

from pathlib import Path

# instrument id → ``application/tasks/`` folder name.
# Only ``example-survey_product-feedback`` is a contributor reference example;
# the other folders are real application survey tasks (``survey_*``).
SURVEY_INSTRUMENT_TASK_FOLDERS: dict[str, str] = {
    "product_attitudes_v1": "survey_product-attitudes",
    "product_feedback_v1": "example-survey_product-feedback",
    "software_claude_code_vscode_checkpoints_v1": "survey_claude-code-vscode-checkpoints",
    "finance_robinhood_cortex_digests_v1": "survey_robinhood-cortex-digests",
    "healthcare_cvs_app_prescription_ai_v1": "survey_cvs-prescription-ai",
    "commerce_nike_air_max_dn_dynamic_air_v1": "survey_nike-air-max-dn",
}

_INSTRUMENT_TASK_FOLDER = SURVEY_INSTRUMENT_TASK_FOLDERS


def is_example_survey_task_folder(folder: str) -> bool:
    return folder.startswith("example-survey_")


def instrument_id_for_task_folder(folder: str) -> str | None:
    for instrument_id, mapped_folder in _INSTRUMENT_TASK_FOLDER.items():
        if mapped_folder == folder:
            return instrument_id
    return None


def task_folder_for_instrument(instrument_id: str) -> str | None:
    return _INSTRUMENT_TASK_FOLDER.get(instrument_id)


def instruction_markdown_for_instrument(
    instrument_id: str,
    *,
    repo_root: Path,
) -> str | None:
    """Return ``instruction.md`` when this instrument has a Harbor content task."""
    folder = task_folder_for_instrument(instrument_id)
    if not folder:
        return None
    instruction_path = repo_root / "application" / "tasks" / folder / "instruction.md"
    if not instruction_path.is_file():
        return None
    text = instruction_path.read_text(encoding="utf-8").strip()
    return text or None
