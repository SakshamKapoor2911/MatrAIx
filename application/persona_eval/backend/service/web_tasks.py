"""Registry of PersonaEval web application tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from backend.service.example_task_catalog import discover_example_tasks, repo_root, task_id_from_folder
from backend.service.web_types import WebEvalTask


def _site_meta_for(folder_name: str) -> tuple[str, str]:
    lowered = folder_name.lower()
    if "books" in lowered or "toscrape" in lowered:
        return "books.toscrape.com", "https://books.toscrape.com/"
    if "ecommerce" in lowered:
        return "Northstar Home Goods", "http://ecommerce-web:8000/"
    return "Website", "https://example.com/"


def _output_artifact_for(folder_name: str) -> str:
    if "books" in folder_name.lower():
        return "book_interest.json"
    return "ecommerce_interaction.json"


def _submission_profile_for(folder_name: str) -> str:
    if "books" in folder_name.lower():
        return "book_interest"
    return "persona_eval_final_json"


def _ecommerce_task(root: Path) -> WebEvalTask | None:
    task_dir = root / "application" / "tasks" / "web-ecommerce-platform_product-discovery"
    if not task_dir.is_dir():
        return None
    return WebEvalTask(
        id="web-ecommerce-platform_product-discovery",
        title="Ecommerce product discovery",
        site_name="Northstar Home Goods",
        site_url="http://ecommerce-web:8000/",
        task_path=task_dir,
        description=(
            "Browse a task-hosted ecommerce site, state a realistic website task, "
            "compare products, choose one item, and report the shopping experience."
        ),
        output_artifact="ecommerce_interaction.json",
        submission_profile="persona_eval_final_json",
    )


def _registry() -> Dict[str, WebEvalTask]:
    root = repo_root()
    tasks: Dict[str, WebEvalTask] = {}

    ecommerce = _ecommerce_task(root)
    if ecommerce is not None:
        tasks[ecommerce.id] = ecommerce

    for record in discover_example_tasks(category="web"):
        site_name, site_url = _site_meta_for(record.folder_name)
        task_id = task_id_from_folder(record.folder_name)
        tasks[task_id] = WebEvalTask(
            id=task_id,
            title=record.title,
            site_name=site_name,
            site_url=site_url,
            task_path=root / "application" / "tasks" / record.folder_name,
            description=record.description,
            output_artifact=_output_artifact_for(record.folder_name),
            submission_profile=_submission_profile_for(record.folder_name),
        )
    return tasks


def list_web_eval_tasks() -> List[WebEvalTask]:
    return list(_registry().values())


def get_web_eval_task(task_id: str) -> WebEvalTask:
    try:
        return _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown web eval task: {}".format(task_id)) from exc
