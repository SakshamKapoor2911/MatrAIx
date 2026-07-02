from pathlib import Path

from backend.service.example_task_catalog import repo_root
from backend.service.survey_harbor_tasks import list_survey_harbor_tasks
from backend.service.survey_task_registry import (
    instrument_id_for_task_path,
    survey_instruction_markdown_for_instrument,
    task_path_for_instrument,
)
from environment.integrations.persona_eval.survey_task_content import (
    instruction_markdown_for_instrument,
)


def test_instrument_id_for_product_attitudes_task():
    assert instrument_id_for_task_path("application/tasks/survey_product-attitudes") == "product_attitudes_v1"


def test_instrument_id_for_product_feedback_task():
    assert (
        instrument_id_for_task_path("application/tasks/example-survey_product-feedback")
        == "product_feedback_v1"
    )


def test_task_path_for_product_attitudes_instrument():
    assert task_path_for_instrument("product_attitudes_v1") == "application/tasks/survey_product-attitudes"


def test_task_path_for_product_feedback_instrument():
    assert task_path_for_instrument("product_feedback_v1") == (
        "application/tasks/example-survey_product-feedback"
    )


def test_survey_instruction_markdown_includes_product_concept():
    root = repo_root()
    md = survey_instruction_markdown_for_instrument("product_feedback_v1", repo_root=root)
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
    contributing = [task for task in tasks if task.survey_kind == "contributing"]
    assert len(contributing) == 5


def test_every_instrument_has_harbor_task_folder():
    from environment.integrations.persona_eval.survey_task_content import (
        SURVEY_INSTRUMENT_TASK_FOLDERS,
    )

    root = repo_root()
    for instrument_id, folder in SURVEY_INSTRUMENT_TASK_FOLDERS.items():
        instruction = root / "application" / "tasks" / folder / "instruction.md"
        assert instruction.is_file(), "missing instruction for {}".format(instrument_id)
        assert task_path_for_instrument(instrument_id)


def test_shared_content_module_reads_instruction_md():
    root = repo_root()
    md = instruction_markdown_for_instrument("product_feedback_v1", repo_root=Path(root))
    assert md
    assert md.startswith("# Survey Product Feedback")
