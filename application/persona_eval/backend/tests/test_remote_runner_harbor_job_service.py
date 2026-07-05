"""Tests for HarborJobService remote plane dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.service.harbor_job_service import HarborJobService


@dataclass
class _FakeRemoteRun:
    id: str
    status: str = "succeeded"


class _FakeRemoteClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create_run(self, *, task_type: str, payload: dict) -> _FakeRemoteRun:
        self.calls.append({"task_type": task_type, "payload": payload})
        return _FakeRemoteRun(id="run_fake")

    def wait_for_run(self, run_id: str) -> _FakeRemoteRun:
        assert run_id == "run_fake"
        return _FakeRemoteRun(id=run_id, status="succeeded")


def test_launch_remote_plane_dispatches_harbor_job(tmp_path, monkeypatch) -> None:
    repo = tmp_path
    jobs_dir = repo / "jobs"
    jobs_dir.mkdir()
    (repo / "persona" / "datasets" / "bench-dev-sample").mkdir(parents=True)
    (repo / "persona" / "datasets" / "bench-dev-sample" / "persona_0001.yaml").write_text(
        "persona_id: '0001'\nversion: '1.0'\nsource: Nemotron\ndimensions: {}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "persona_eval.harbor.persona_eval._repo_root",
        lambda: repo,
    )
    monkeypatch.setenv("REMOTE_RUNNER_API_URL", "http://127.0.0.1:9999")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-leak-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-leak-test")

    fake_client = _FakeRemoteClient()
    service = HarborJobService(
        repo_root=repo,
        jobs_dir=jobs_dir,
        generated_configs_dir=repo / "configs" / "jobs" / "application-task-job-recipe",
        command_runner=lambda *args, **kwargs: 0,
        harbor_command=("echo", "harbor"),
        remote_runner_client=fake_client,
    )

    job_name = service.launch(
        task_path="application/tasks/example-survey_product-feedback",
        sample_size=1,
        persona_pool="persona/datasets/bench-dev-sample",
        persona_ids=["0001"],
        job_name="remote-survey-job",
        execution_plane="remote",
    )

    service._executor.shutdown(wait=True)
    assert job_name == "remote-survey-job"
    assert fake_client.calls
    assert fake_client.calls[0]["task_type"] == "harbor_job"
    assert "configYaml" in fake_client.calls[0]["payload"]
    remote_env = fake_client.calls[0]["payload"]["env"]
    assert remote_env["MATRIX_SURVEY_TASK_PATH"] == "application/tasks/example-survey_product-feedback"
    assert "PYTHONPATH" in remote_env
    assert "ANTHROPIC_API_KEY" not in remote_env
    assert "OPENAI_API_KEY" not in remote_env
    assert "REMOTE_RUNNER_API_URL" not in remote_env
    launch = service._launches[job_name]
    assert launch.execution_plane == "remote"
    assert launch.remote_run_id == "run_fake"
    assert launch.status == "completed"
