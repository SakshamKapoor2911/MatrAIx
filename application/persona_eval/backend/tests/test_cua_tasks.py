from backend.service.cua_tasks import get_cua_eval_task, list_cua_eval_tasks


def test_list_cua_eval_tasks_includes_harbor_computer_use_tasks():
    tasks = list_cua_eval_tasks()
    ids = {task.id for task in tasks}
    assert "computer-use-linux-notification-preferences" in ids
    assert "web-cua-books-interest" in ids
    assert all(task.task_path.startswith("application/tasks/") for task in tasks)


def test_get_cua_eval_task_web_cua_has_submission_profile():
    task = get_cua_eval_task("web-cua-books-interest")
    assert task.cua_submission_profile == "book_interest"
    assert task.output_artifact == "book_interest.json"
