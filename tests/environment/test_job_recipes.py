from __future__ import annotations

import pathlib
from typing import Any

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[2]
RECIPES_DIR = ROOT / "configs/jobs"
EXPECTED_CURATED_RECIPES = {
    "configs/jobs/application-task-job-recipe/appSim-example-survey-product-feedback-random-n4.yaml",
    "configs/jobs/example-job-recipe/playground-example-survey-local.yaml",
    "configs/jobs/persona-task-grounding-job-recipe/playground-example-survey-product-feedback-economic-motivation-pg2.yaml",
}


def _recipe_paths() -> list[pathlib.Path]:
    return sorted(RECIPES_DIR.rglob("*.yaml"))


def _agent_persona_paths(recipe: dict[str, Any]) -> list[str]:
    persona_paths: list[str] = []
    for agent in recipe.get("agents") or []:
        if not isinstance(agent, dict):
            continue
        kwargs = agent.get("kwargs") or {}
        if isinstance(kwargs, dict) and isinstance(kwargs.get("persona_path"), str):
            persona_paths.append(kwargs["persona_path"])
    return persona_paths


def _task_paths(recipe: dict[str, Any]) -> list[str]:
    task_paths: list[str] = []
    for task in recipe.get("tasks") or []:
        if isinstance(task, dict) and isinstance(task.get("path"), str):
            task_paths.append(task["path"])
    return task_paths


def test_job_recipes_are_curated_and_resolvable() -> None:
    recipe_paths = _recipe_paths()
    relative_recipe_paths = {
        str(recipe_path.relative_to(ROOT)) for recipe_path in recipe_paths
    }

    assert recipe_paths
    assert EXPECTED_CURATED_RECIPES <= relative_recipe_paths

    for recipe_path in recipe_paths:
        recipe_text = recipe_path.read_text(encoding="utf-8")
        assert "bench-dev-2000" not in recipe_text

        recipe = yaml.safe_load(recipe_text)
        assert isinstance(recipe, dict), recipe_path

        for persona_path in _agent_persona_paths(recipe):
            assert (ROOT / persona_path).is_file(), (recipe_path, persona_path)

        for task_path in _task_paths(recipe):
            assert (ROOT / task_path).is_dir(), (recipe_path, task_path)
