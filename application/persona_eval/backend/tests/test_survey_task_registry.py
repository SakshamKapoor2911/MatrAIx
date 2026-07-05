from pathlib import Path

from backend.service.example_task_catalog import repo_root
from backend.service.survey_harbor_tasks import list_survey_harbor_tasks
from backend.service.survey_task_registry import (
    survey_questionnaire_id_for_task_path,
    survey_task_instruction_markdown_for_questionnaire_id,
    survey_task_path_for_questionnaire_id,
)
from persona_eval.survey_task_content import (
    SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID,
    instruction_markdown_for_questionnaire_id,
)


def test_questionnaire_id_for_product_attitudes_task():
    assert (
        survey_questionnaire_id_for_task_path("application/tasks/survey_product-attitudes")
        == "product_attitudes_v1"
    )


def test_questionnaire_id_for_product_feedback_task():
    assert (
        survey_questionnaire_id_for_task_path("application/tasks/example-survey_product-feedback")
        == "product_feedback_v1"
    )


def test_task_path_for_product_attitudes_questionnaire():
    assert (
        survey_task_path_for_questionnaire_id("product_attitudes_v1")
        == "application/tasks/survey_product-attitudes"
    )


def test_task_path_for_product_feedback_questionnaire():
    assert survey_task_path_for_questionnaire_id("product_feedback_v1") == (
        "application/tasks/example-survey_product-feedback"
    )


def test_survey_instruction_markdown_includes_product_concept():
    root = repo_root()
    md = survey_task_instruction_markdown_for_questionnaire_id(
        "product_feedback_v1",
        repo_root=root,
    )
    assert md
    assert "FocusLoop" in md
    assert "q0" in md


def test_harbor_tasks_expose_instrument_and_profile():
    tasks = list_survey_harbor_tasks()
    assert len(tasks) == 6
    product = next(
        task for task in tasks if task.task_path.endswith("example-survey_product-feedback")
    )
    assert product.instrument_id == "product_feedback_v1"
    assert product.survey_kind == "example"
    assert "FocusLoop" in product.profile_markdown
    assert product.questionnaire_markdown.startswith("# Survey Product Feedback")
    assert "Return strict JSON matching this shape." in product.output_schema_markdown
    assert "backend/runtime" not in product.output_schema_markdown
    assert product.questionnaire is not None
    assert product.questionnaire["questions"][0]["optionDetails"][0]["label"].startswith(
        "Keep using free."
    )
    contributing = [task for task in tasks if task.survey_kind == "contributing"]
    assert len(contributing) == 5


def test_every_questionnaire_id_has_harbor_task_folder():
    root = repo_root()
    for questionnaire_id, folder in SURVEY_TASK_FOLDER_BY_QUESTIONNAIRE_ID.items():
        instruction = root / "application" / "tasks" / folder / "instruction.md"
        assert instruction.is_file(), "missing instruction for {}".format(questionnaire_id)
        assert survey_task_path_for_questionnaire_id(questionnaire_id)


def test_shared_content_module_reads_instruction_md():
    root = repo_root()
    md = instruction_markdown_for_questionnaire_id("product_feedback_v1", repo_root=Path(root))
    assert md
    assert md.startswith("# Survey Product Feedback")
