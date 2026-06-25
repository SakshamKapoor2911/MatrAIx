"""Registry of PersonaEval web application tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from backend.service.harbor_web_eval import WebEvalTask


def _registry() -> Dict[str, WebEvalTask]:
    task = WebEvalTask(
        id="web-ecommerce-platform_product-discovery",
        title="Ecommerce product discovery",
        site_name="Northstar Home Goods",
        site_url="http://ecommerce-web:8000/",
        task_path=Path("applications/tasks/web-ecommerce-platform_product-discovery"),
        description=(
            "Browse a task-hosted ecommerce site, state a realistic website task, "
            "compare products, choose one item, and report the shopping experience."
        ),
        output_artifact="ecommerce_interaction.json",
        submission_profile="persona_eval_final_json",
    )
    return {task.id: task}


def list_web_eval_tasks() -> List[WebEvalTask]:
    return list(_registry().values())


def get_web_eval_task(task_id: str) -> WebEvalTask:
    try:
        return _registry()[task_id]
    except KeyError as exc:
        raise KeyError("unknown web eval task: {}".format(task_id)) from exc
