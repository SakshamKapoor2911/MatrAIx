"""Validate checked-in MatrAIx job recipe YAML files."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from harbor.models.job.config import JobConfig

REPO_ROOT = Path(__file__).resolve().parents[3]
JOB_CONFIGS = sorted(REPO_ROOT.glob("configs/jobs/**/*.yaml"))


@pytest.mark.parametrize(
    "job_yaml",
    JOB_CONFIGS,
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_job_config_yaml_loads(job_yaml: Path) -> None:
    payload = yaml.safe_load(job_yaml.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), job_yaml
    cfg = JobConfig.model_validate(payload)
    assert cfg.job_name
    assert cfg.tasks or cfg.datasets, f"{job_yaml}: expected tasks or datasets"


@pytest.mark.parametrize(
    "job_yaml",
    JOB_CONFIGS,
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_job_config_task_paths_exist(job_yaml: Path) -> None:
    payload = yaml.safe_load(job_yaml.read_text(encoding="utf-8"))
    cfg = JobConfig.model_validate(payload)
    for task in cfg.tasks:
        assert task.path is not None, f"{job_yaml}: task missing path"
        task_dir = REPO_ROOT / task.path
        assert task_dir.is_dir(), f"{job_yaml}: missing task directory {task.path}"
        assert (task_dir / "task.toml").is_file(), (
            f"{job_yaml}: missing task.toml under {task.path}"
        )


@pytest.mark.parametrize(
    "job_yaml",
    JOB_CONFIGS,
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_job_config_persona_paths_exist(job_yaml: Path) -> None:
    payload = yaml.safe_load(job_yaml.read_text(encoding="utf-8"))
    cfg = JobConfig.model_validate(payload)
    for agent in cfg.agents:
        persona_path = (agent.kwargs or {}).get("persona_path")
        if persona_path is None:
            continue
        resolved = REPO_ROOT / str(persona_path)
        assert resolved.is_file(), f"{job_yaml}: missing persona file {persona_path}"
