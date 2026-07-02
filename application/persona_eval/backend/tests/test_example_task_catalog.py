from backend.service.example_task_catalog import categorize_task, discover_example_tasks, discover_survey_application_tasks
from backend.service.survey_harbor_tasks import list_survey_harbor_tasks
from backend.service.web_tasks import list_web_eval_tasks
from backend.service.cua_tasks import list_cua_eval_tasks


def test_discover_example_tasks_by_category():
    survey = discover_example_tasks(category="survey")
    web = discover_example_tasks(category="web")
    cua = discover_example_tasks(category="cua")
    assert len(survey) == 1
    assert survey[0].folder_name == "example-survey_product-feedback"
    assert any("example-survey_" in task.folder_name for task in survey)
    assert any("example-web-playwright" in task.folder_name for task in web)
    assert not any("example-web-cua" in task.folder_name for task in web)
    assert any("example-computer-use-" in task.folder_name for task in cua)
    assert any("example-web-cua" in task.folder_name for task in cua)


def test_categorize_task():
    assert categorize_task("example-survey_product-feedback", "survey") == "survey"
    assert categorize_task("survey_nike-air-max-dn", "survey") == "survey"
    assert categorize_task("example-web-playwright_books-interest", "web") == "web"
    assert categorize_task("example-web-cua_books-interest", "web") == "cua"
    assert categorize_task("example-computer-use-linux_notification-preferences", "desktop") == "cua"


def test_list_survey_harbor_tasks_includes_product_feedback():
    tasks = list_survey_harbor_tasks()
    match = [task for task in tasks if task.task_path.endswith("example-survey_product-feedback")]
    assert match
    assert match[0].instrument_id == "product_feedback_v1"
    assert match[0].survey_kind == "example"


def test_discover_survey_application_tasks_includes_contributing_tasks():
    records = discover_survey_application_tasks()
    assert len(records) == 6
    folders = {record.folder_name for record in records}
    assert "example-survey_product-feedback" in folders
    assert "survey_nike-air-max-dn" in folders
    assert "example-survey_nike-air-max-dn" not in folders


def test_list_web_eval_tasks_includes_example_web_tasks():
    tasks = list_web_eval_tasks()
    ids = {task.id for task in tasks}
    assert "web-playwright-books-interest" in ids
    assert "web-cua-books-interest" not in ids


def test_list_cua_eval_tasks_includes_computer_use_and_web_cua():
    tasks = list_cua_eval_tasks()
    ids = {task.id for task in tasks}
    assert "computer-use-linux-notification-preferences" in ids
    assert "web-cua-books-interest" in ids
