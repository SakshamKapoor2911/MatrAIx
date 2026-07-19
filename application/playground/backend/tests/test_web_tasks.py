from backend.service.web_tasks import get_web_eval_task, list_web_eval_tasks
from harbor.models.task.paths import TaskPaths
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_web_task_path_is_absolute_and_environment_resolves():
    task = get_web_eval_task("web-playwright-quote-choice")
    task_path = REPO_ROOT / Path(str(task.task_path))
    environment_dir = TaskPaths.from_task_dir(task_path).environment_dir
    assert environment_dir.is_dir(), environment_dir


def test_all_registered_web_tasks_have_absolute_paths():
    for task in list_web_eval_tasks():
        task_path = REPO_ROOT / Path(str(task.task_path))
        assert task_path.is_dir(), "{} has missing task path".format(task.id)


def test_public_web_tasks_are_registered():
    tasks_to_check = [
        "web-playwright-books-to-scrape-book-choice",
        "web-playwright-wikipedia-article-find",
        "web-playwright-mdn-web-docs-doc-find",
        "web-playwright-github-pricing-plan-compare",
        "web-playwright-hacker-news-story-choice",
        "web-playwright-arxiv-paper-choice",
        "web-playwright-letterboxd-movie-choice",
        "web-playwright-goodreads-book-choice",
        "web-playwright-national-park-service-park-compare",
        "web-playwright-boardgamegeek-game-choice",
    ]
    for task_id in tasks_to_check:
        task = get_web_eval_task(task_id)
        assert task.task_path == f"application/tasks/{task_id}"
        assert task.task_kind == "task"
        assert task.output_artifact is not None

