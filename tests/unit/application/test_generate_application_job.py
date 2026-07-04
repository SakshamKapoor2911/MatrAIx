"""Tests for application job generation helpers."""

from __future__ import annotations

from pathlib import Path

from personabench.application_job import collect_run_env_exports

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_collect_run_env_exports_survey() -> None:
    exports = collect_run_env_exports(
        trial_profile="json_survey",
        task_path="application/tasks/example-survey_product-feedback",
        repo_root=REPO_ROOT,
    )
    assert exports == [("MATRIX_SURVEY_TASK_PATH", "application/tasks/example-survey_product-feedback")]


def test_collect_run_env_exports_chat() -> None:
    exports = collect_run_env_exports(
        trial_profile="user_sim_chat",
        task_path="application/tasks/recommender-agent_chat_api",
        repo_root=REPO_ROOT,
    )
    assert exports == [("MATRIX_CHATBOT_TASK_PATH", "application/tasks/recommender-agent_chat_api")]
