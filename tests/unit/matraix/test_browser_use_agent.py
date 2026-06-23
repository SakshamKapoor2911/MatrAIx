from __future__ import annotations

import json
from pathlib import Path

import pytest

from harbor.models.agent.context import AgentContext
from matraix.agents.installed.browser_use import BrowserUseHarborAgent


@pytest.mark.unit
def test_populate_context_post_run_reads_final_metrics(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    trajectory = {
        "schema_version": "ATIF-v1.6",
        "steps": [],
        "final_metrics": {
            "total_prompt_tokens": 27601,
            "total_completion_tokens": 2043,
            "total_cached_tokens": 1200,
            "total_cost_usd": 0.12,
        },
        "extra": {
            "browser_use": {
                "final_result": "Done",
                "is_done": True,
            }
        },
    }
    (logs_dir / "trajectory.json").write_text(json.dumps(trajectory), encoding="utf-8")

    agent = BrowserUseHarborAgent(logs_dir=logs_dir, model_name="anthropic/claude-sonnet-4-6")
    context = AgentContext()
    agent.populate_context_post_run(context)

    assert context.n_input_tokens == 27601
    assert context.n_output_tokens == 2043
    assert context.n_cache_tokens == 1200
    assert context.cost_usd == 0.12
    assert context.metadata is not None
    assert context.metadata["browser_use"]["final_result"] == "Done"


@pytest.mark.unit
def test_populate_context_post_run_zero_cost(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    trajectory = {
        "final_metrics": {
            "total_prompt_tokens": 100,
            "total_completion_tokens": 50,
            "total_cached_tokens": None,
            "total_cost_usd": 0.0,
        },
        "extra": {"browser_use": {}},
    }
    (logs_dir / "trajectory.json").write_text(json.dumps(trajectory), encoding="utf-8")

    agent = BrowserUseHarborAgent(logs_dir=logs_dir, model_name="anthropic/claude-sonnet-4-6")
    context = AgentContext()
    agent.populate_context_post_run(context)

    assert context.n_input_tokens == 100
    assert context.n_output_tokens == 50
    assert context.n_cache_tokens is None
    assert context.cost_usd == 0.0


@pytest.mark.unit
def test_populate_context_post_run_missing_trajectory(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    agent = BrowserUseHarborAgent(logs_dir=logs_dir, model_name="anthropic/claude-sonnet-4-6")
    context = AgentContext()
    agent.populate_context_post_run(context)

    assert context.cost_usd is None
    assert context.n_input_tokens is None
