from __future__ import annotations

import json
import pathlib
import stat
import tomllib

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[2]
ADAPTERS = ROOT / "environment/adapters"
SIMPLEQA = ADAPTERS / "simpleqa"


def test_adapters_live_under_environment_boundary() -> None:
    assert not (ROOT / "adapters").exists()
    assert (ADAPTERS / "README.md").is_file()
    assert (ADAPTERS / "manifest.schema.json").is_file()
    assert SIMPLEQA.is_dir()


def test_adapter_manifest_records_source_and_policy() -> None:
    manifest = tomllib.loads((SIMPLEQA / "manifest.toml").read_text())
    schema = json.loads((ADAPTERS / "manifest.schema.json").read_text())

    assert set(schema["required"]).issubset(manifest)
    assert manifest["schema_version"] == "1.0"
    assert manifest["name"] == "simpleqa"
    assert manifest["status"] == "experimental"
    assert manifest["target_path"] == "environment/adapters/simpleqa"
    assert manifest["source_repository"] == "MatrAIx-ai/MatrAIx"
    assert manifest["source_path"] == "adapters/simpleqa"
    assert manifest["source_commit"] == "e50592a4cbfca86b3207e1f9d5247ca9f93ee4d0"
    assert manifest["generated_output"] == "environment/adapters/simpleqa/_generated/"
    assert "adapters/simpleqa/uv.lock" in manifest["excluded_source_paths"]
    assert all(
        "environment/adapters/simpleqa" in command
        for command in manifest["smoke_commands"]
    )


def test_simpleqa_package_uses_setuptools_and_packages_templates() -> None:
    pyproject = tomllib.loads((SIMPLEQA / "pyproject.toml").read_text())

    assert pyproject["project"]["name"] == "harbor-simpleqa-adapter"
    assert pyproject["project"]["scripts"] == {"simpleqa": "simpleqa.main:main"}
    assert pyproject["build-system"]["build-backend"] == "setuptools.build_meta"
    assert pyproject["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
    assert pyproject["tool"]["setuptools"]["package-data"]["simpleqa"] == [
        "task-template/*.md",
        "task-template/*.toml",
        "task-template/environment/Dockerfile",
        "task-template/solution/*.sh",
        "task-template/tests/*.py",
        "task-template/tests/*.sh",
    ]


def test_simpleqa_recipes_use_adapter_local_generated_paths() -> None:
    recipe_paths = [
        SIMPLEQA / "run_simpleqa.yaml",
        SIMPLEQA / "simpleqa_oracle.yaml",
        SIMPLEQA / "simpleqa_parity_claude_opus4_6.yaml",
    ]

    for recipe_path in recipe_paths:
        recipe = yaml.safe_load(recipe_path.read_text())
        dataset_paths = [
            dataset["path"]
            for dataset in recipe["datasets"]
            if isinstance(dataset, dict) and isinstance(dataset.get("path"), str)
        ]
        assert dataset_paths, recipe_path
        assert all(
            path.startswith("environment/adapters/simpleqa/_generated/")
            for path in dataset_paths
        )
        assert all(not path.startswith("datasets/") for path in dataset_paths)


def test_adapter_import_excludes_generated_and_large_files() -> None:
    forbidden_paths = [
        SIMPLEQA / "uv.lock",
        SIMPLEQA / "_generated",
        ROOT / "datasets/simpleqa",
        ROOT / "jobs",
    ]

    for path in forbidden_paths:
        assert not path.exists(), path

    large_files = [
        path
        for path in SIMPLEQA.rglob("*")
        if path.is_file() and path.stat().st_size > 1_000_000
    ]
    assert large_files == []


def test_simpleqa_task_template_keeps_scripts_executable() -> None:
    script_paths = [
        SIMPLEQA / "src/simpleqa/task-template/solution/solve.sh",
        SIMPLEQA / "src/simpleqa/task-template/tests/test.sh",
    ]

    for script_path in script_paths:
        mode = script_path.stat().st_mode
        assert mode & stat.S_IXUSR, script_path
