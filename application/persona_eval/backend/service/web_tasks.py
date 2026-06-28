"""Registry of PersonaEval web application tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from backend.service.web_types import WebEvalTask

# Repo root, so task_path resolves regardless of the process CWD. The demo runs
# uvicorn from the persona_eval dir, so a path relative to CWD silently misses
# the task's catalog and the trace falls back to placeholder products.
# web_tasks.py -> service -> backend -> persona_eval -> application -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]


def _registry() -> Dict[str, WebEvalTask]:
    task = WebEvalTask(
        id="web-ecommerce-platform_product-discovery",
        title="Ecommerce product discovery",
        site_name="Northstar Home Goods",
        site_url="http://ecommerce-web:8000/",
        task_path=_REPO_ROOT / "application" / "tasks" / "web-ecommerce-platform_product-discovery",
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
