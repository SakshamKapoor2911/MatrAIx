from __future__ import annotations

import pathlib
import tomllib

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[2]
HELLO_WORLD = ROOT / "examples/tasks/hello-world"
SMOKE_RECIPE = ROOT / "configs/jobs/example-job-recipe/harbor-smoke-local.yaml"
EXPECTED_HARBOR_EXAMPLES = {
    "computer-1-click-calibration",
    "describe-image",
    "hello-alpine",
    "hello-computer-use",
    "hello-cuda",
    "hello-healthcheck",
    "hello-mcp",
    "hello-multi-step-advanced",
    "hello-multi-step-bat",
    "hello-multi-step-simple",
    "hello-skills",
    "hello-user",
    "hello-workdir",
    "hello-world",
    "hello-world-bat",
    "llm-judge-example",
    "network-policy-matrix",
    "reward-kit-example",
    "separate-verifier-environment",
    "separate-verifier-multi-step",
    "sidecar-artifacts",
    "verifier-mode-matrix",
}


def test_hello_world_example_is_minimal_and_resolvable() -> None:
    required_files = [
        "environment/Dockerfile",
        "instruction.md",
        "solution/solve.sh",
        "task.toml",
        "tests/test.sh",
        "tests/test_state.py",
    ]

    for relative_path in required_files:
        assert (HELLO_WORLD / relative_path).is_file(), relative_path

    task = tomllib.loads((HELLO_WORLD / "task.toml").read_text(encoding="utf-8"))
    assert task["task"]["name"] == "harbor/hello-world"
    assert task["environment"]["gpus"] == 0


def test_harbor_smoke_recipe_targets_hello_world() -> None:
    recipe = yaml.safe_load(SMOKE_RECIPE.read_text(encoding="utf-8"))
    assert isinstance(recipe, dict)
    assert recipe["job_name"] == "harbor-smoke-local"
    assert recipe["agents"] == [{"name": "oracle"}]

    task_paths = [
        task["path"]
        for task in recipe["tasks"]
        if isinstance(task, dict) and isinstance(task.get("path"), str)
    ]
    assert task_paths == ["examples/tasks/hello-world"]
    for task_path in task_paths:
        assert (ROOT / task_path).is_dir()


def test_examples_import_excludes_generated_outputs() -> None:
    forbidden_paths = [
        "examples/jobs",
        "examples/configs",
        "examples/agents",
        "examples/metrics",
        "examples/prompts",
    ]

    for relative_path in forbidden_paths:
        assert not (ROOT / relative_path).exists(), relative_path

    large_files = [
        path
        for path in (ROOT / "examples").rglob("*")
        if path.is_file() and path.stat().st_size > 1_000_000
    ]
    assert large_files == []


def test_curated_harbor_examples_are_available() -> None:
    example_dirs = {
        path.name
        for path in (ROOT / "examples/tasks").iterdir()
        if path.is_dir()
    }

    assert EXPECTED_HARBOR_EXAMPLES <= example_dirs
