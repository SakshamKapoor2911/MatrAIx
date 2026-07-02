"""Unit tests for Harbor job launch config generation."""

from __future__ import annotations

from pathlib import Path

from backend.service.harbor_job_service import HarborJobService


def test_launch_writes_job_config(tmp_path, monkeypatch):
    repo = tmp_path
    jobs_dir = repo / "jobs"
    jobs_dir.mkdir()
    (repo / "persona" / "datasets" / "bench-dev-sample").mkdir(parents=True)
    (repo / "persona" / "datasets" / "bench-dev-sample" / "persona_0001.yaml").write_text(
        "persona_id: '0001'\nversion: '1.0'\nsource: Nemotron\ndimensions: {}\n",
        encoding="utf-8",
    )
    (repo / "persona" / "datasets" / "bench-dev-sample" / "persona_0002.yaml").write_text(
        "persona_id: '0002'\nversion: '1.0'\nsource: OASIS\ndimensions: {}\n",
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    def _fake_run(command, *, cwd, env):
        calls.append(list(command))
        return 0

    monkeypatch.setattr(
        "environment.integrations.persona_eval.harbor.persona_eval._repo_root",
        lambda: repo,
    )
    service = HarborJobService(
        repo_root=repo,
        jobs_dir=jobs_dir,
        generated_configs_dir=repo / "configs" / "jobs" / "application-task-job-recipe",
        command_runner=_fake_run,
        harbor_command=("echo", "harbor"),
    )

    job_name = service.launch(
        task_path="application/tasks/example-survey_product-feedback",
        sample_size=2,
        seed=1,
        persona_pool="persona/datasets/bench-dev-sample",
        persona_model="anthropic/claude-haiku-4-5",
        job_name="test-harbor-job",
    )
    assert job_name == "test-harbor-job"
    config_path = repo / "configs" / "jobs" / "application-task-job-recipe" / "test-harbor-job.yaml"
    assert config_path.is_file()
    text = config_path.read_text(encoding="utf-8")
    assert "persona_0001.yaml" in text or "persona_0002.yaml" in text
    assert calls
    assert calls[0][-1].endswith("test-harbor-job.yaml")

    detail = service.get_job("test-harbor-job")
    assert detail is not None
    assert detail["launch"]["status"] in {"completed", "running", "queued"}

    service.shutdown()


def test_launch_with_frozen_cohort(tmp_path, monkeypatch):
    from application.persona_eval.backend.tests.test_persona_pool_service import _write_pool

    repo = tmp_path
    _write_pool(repo)
    jobs_dir = repo / "jobs"
    jobs_dir.mkdir()

    from backend.service.persona_pool_service import PersonaPoolService

    pool_service = PersonaPoolService(repo_root=repo)
    pool_service.save_cohort(
        cohort_id="frozen-oasis",
        kind="frozen",
        seed=1,
        sample_size=1,
        dimension_filters={"economic_motivation": "Indifferent"},
    )

    calls: list[list[str]] = []

    def _fake_run(command, *, cwd, env):
        calls.append(list(command))
        return 0

    monkeypatch.setattr(
        "environment.integrations.persona_eval.harbor.persona_eval._repo_root",
        lambda: repo,
    )
    service = HarborJobService(
        repo_root=repo,
        jobs_dir=jobs_dir,
        generated_configs_dir=repo / "configs" / "jobs" / "application-task-job-recipe",
        command_runner=_fake_run,
        harbor_command=("echo", "harbor"),
    )

    job_name = service.launch(
        task_path="application/tasks/example-survey_product-feedback",
        cohort_id="frozen-oasis",
        persona_model="anthropic/claude-haiku-4-5",
        job_name="cohort-job",
    )
    assert job_name == "cohort-job"
    config_path = repo / "configs" / "jobs" / "application-task-job-recipe" / "cohort-job.yaml"
    text = config_path.read_text(encoding="utf-8")
    assert "persona_0002.yaml" in text
    assert "# Cohort: frozen-oasis" in text
    assert calls
    service.shutdown()


def test_launch_with_explicit_persona_ids(tmp_path, monkeypatch):
    repo = tmp_path
    jobs_dir = repo / "jobs"
    jobs_dir.mkdir()
    pool = repo / "persona" / "datasets" / "bench-dev-sample"
    pool.mkdir(parents=True)
    (pool / "persona_0042.yaml").write_text(
        "persona_id: '0042'\nversion: '1.0'\nsource: Nemotron\ndimensions: {}\n",
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    def _fake_run(command, *, cwd, env):
        calls.append(list(command))
        return 0

    monkeypatch.setattr(
        "environment.integrations.persona_eval.harbor.persona_eval._repo_root",
        lambda: repo,
    )
    service = HarborJobService(
        repo_root=repo,
        jobs_dir=jobs_dir,
        generated_configs_dir=repo / "configs" / "jobs" / "application-task-job-recipe",
        command_runner=_fake_run,
        harbor_command=("echo", "harbor"),
    )

    job_name = service.launch(
        task_path="application/tasks/example-survey_product-feedback",
        persona_ids=["0042"],
        persona_model="anthropic/claude-haiku-4-5",
        execution_mode="auto",
        job_name="explicit-persona-job",
    )
    assert job_name == "explicit-persona-job"
    config_path = repo / "configs" / "jobs" / "application-task-job-recipe" / "explicit-persona-job.yaml"
    text = config_path.read_text(encoding="utf-8")
    assert "persona_0042.yaml" in text
    assert "# Mode: auto" in text
    assert "# Trial profile: json_survey" in text
    assert "type: host" in text
    assert "application/tasks/persona-survey" in text
    service.shutdown()


def test_resolve_trial_profile_auto_survey_and_chat(tmp_path):
    repo = tmp_path
    survey_dir = repo / "application" / "tasks" / "example-survey_product-feedback"
    survey_dir.mkdir(parents=True)
    (survey_dir / "task.toml").write_text("metadata:\n  type: survey\n", encoding="utf-8")
    chat_dir = repo / "application" / "tasks" / "recommender-agent_chat_api"
    chat_dir.mkdir(parents=True)
    (chat_dir / "task.toml").write_text("metadata:\n  type: chat\n", encoding="utf-8")

    from backend.service.harbor_job_service import resolve_trial_profile

    assert (
        resolve_trial_profile(
            "application/tasks/example-survey_product-feedback",
            mode="auto",
            repo_root=repo,
        )
        == "json_survey"
    )
    assert (
        resolve_trial_profile(
            "application/tasks/recommender-agent_chat_api",
            mode="auto",
            repo_root=repo,
        )
        == "user_sim_chat"
    )
    assert (
        resolve_trial_profile(
            "application/tasks/recommender-agent_chat_api",
            mode="force_docker",
            repo_root=repo,
        )
        == "docker_agent"
    )


def test_resolve_agent_name_json_survey_profile(tmp_path):
    repo = tmp_path
    survey_dir = repo / "application" / "tasks" / "example-survey_product-feedback"
    survey_dir.mkdir(parents=True)
    (survey_dir / "task.toml").write_text("metadata:\n  type: survey\n", encoding="utf-8")

    from backend.service.harbor_job_service import resolve_agent_name, resolve_trial_profile

    profile = resolve_trial_profile(
        "application/tasks/example-survey_product-feedback",
        mode="auto",
        repo_root=repo,
    )
    assert profile == "json_survey"
    assert (
        resolve_agent_name(
            "application/tasks/example-survey_product-feedback",
            repo_root=repo,
            mode="auto",
            trial_profile=profile,
        )
        == "persona-json-survey"
    )
    assert (
        resolve_agent_name(
            "application/tasks/example-survey_product-feedback",
            repo_root=repo,
            mode="force_docker",
            trial_profile="docker_agent",
        )
        == "persona-claude-code"
    )


def test_resolve_agent_name_for_chat_task(tmp_path):
    repo = tmp_path
    task_dir = repo / "application" / "tasks" / "recommender-agent_chat_api"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text(
        "metadata:\n  type: chat\n",
        encoding="utf-8",
    )
    from backend.service.harbor_job_service import resolve_agent_name

    assert (
        resolve_agent_name(
            "application/tasks/recommender-agent_chat_api",
            repo_root=repo,
            mode="auto",
        )
        == "persona-user-sim"
    )
    assert (
        resolve_agent_name(
            "application/tasks/recommender-agent_chat_api",
            repo_root=repo,
            mode="force_docker",
            trial_profile="docker_agent",
        )
        == "persona-claude-code"
    )


def test_launch_ios_cua_uses_use_computer_environment(tmp_path, monkeypatch):
    repo = tmp_path
    jobs_dir = repo / "jobs"
    jobs_dir.mkdir()
    pool = repo / "persona" / "datasets" / "bench-dev-sample"
    pool.mkdir(parents=True)
    (pool / "persona_0020.yaml").write_text(
        "persona_id: '0020'\nversion: '1.0'\nsource: OASIS\ndimensions: {}\n",
        encoding="utf-8",
    )
    task_dir = repo / "application" / "tasks" / "example-computer-use-ios_notification-preferences"
    task_dir.mkdir(parents=True)
    (task_dir / "task.toml").write_text("metadata:\n  type: mobile\n", encoding="utf-8")

    def _fake_run(command, *, cwd, env):
        return 0

    monkeypatch.setattr(
        "environment.integrations.persona_eval.harbor.persona_eval._repo_root",
        lambda: repo,
    )
    service = HarborJobService(
        repo_root=repo,
        jobs_dir=jobs_dir,
        generated_configs_dir=repo / "configs" / "jobs" / "application-task-job-recipe",
        command_runner=_fake_run,
        harbor_command=("echo", "harbor"),
    )

    job_name = service.launch(
        task_path="application/tasks/example-computer-use-ios_notification-preferences",
        persona_ids=["0020"],
        persona_model="anthropic/claude-sonnet-4-6",
        cua_backend="ios",
        job_name="ios-cua-job",
    )
    assert job_name == "ios-cua-job"
    text = (
        repo / "configs" / "jobs" / "application-task-job-recipe" / "ios-cua-job.yaml"
    ).read_text(encoding="utf-8")
    assert "type: use-computer" in text
    assert "platform: ios" in text
    assert "cua_backend: ios" in text
    service.shutdown()


def test_trial_live_stage_from_artifacts(tmp_path):
    from backend.service.harbor_job_service import (
        _resolve_trial_stage,
        _stage_from_phase,
        _trial_live_stage,
    )

    trial_dir = tmp_path / "trial-a"
    assert _trial_live_stage(trial_dir) == "queued"

    trial_dir.mkdir()
    (trial_dir / "config.json").write_text("{}", encoding="utf-8")
    assert _trial_live_stage(trial_dir) == "starting_env"

    agent_dir = trial_dir / "agent"
    agent_dir.mkdir()
    (agent_dir / "setup").mkdir()
    assert _trial_live_stage(trial_dir) == "starting_env"

    (agent_dir / "trajectory.json").write_text("[]", encoding="utf-8")
    assert _trial_live_stage(trial_dir) == "agent_running"

    verifier_dir = trial_dir / "verifier"
    verifier_dir.mkdir()
    (verifier_dir / "reward.txt").write_text("1.0", encoding="utf-8")
    assert _trial_live_stage(trial_dir) == "verifying"

    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    assert _trial_live_stage(trial_dir) is None

    assert _stage_from_phase("persona_thinking") == "agent_running"
    assert _stage_from_phase("harbor_collecting_artifacts") == "verifying"
    assert _resolve_trial_stage(trial_dir, phase="persona_kickoff", completed=False) == "agent_running"


def test_list_jobs_reports_success_and_failed_status(tmp_path):
    import json

    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    success_job = jobs_dir / "job-success"
    success_job.mkdir()
    (success_job / "trial-a").mkdir()
    (success_job / "trial-a" / "result.json").write_text("{}", encoding="utf-8")
    (success_job / "result.json").write_text(
        json.dumps(
            {
                "finished_at": "2026-07-01T12:00:00Z",
                "stats": {"n_errored_trials": 0},
            }
        ),
        encoding="utf-8",
    )

    failed_job = jobs_dir / "job-failed"
    failed_job.mkdir()
    (failed_job / "trial-a").mkdir()
    (failed_job / "trial-a" / "result.json").write_text("{}", encoding="utf-8")
    (failed_job / "result.json").write_text(
        json.dumps(
            {
                "finished_at": "2026-07-01T12:05:00Z",
                "stats": {"n_errored_trials": 1},
            }
        ),
        encoding="utf-8",
    )

    running_job = jobs_dir / "job-running"
    running_job.mkdir()
    (running_job / "trial-a").mkdir()

    service = HarborJobService(
        repo_root=tmp_path,
        jobs_dir=jobs_dir,
        generated_configs_dir=tmp_path / "configs",
    )
    rows = {row["jobName"]: row for row in service.list_jobs()}

    assert rows["job-success"]["status"] == "success"
    assert rows["job-success"]["failedTrials"] == 0
    assert rows["job-failed"]["status"] == "failed"
    assert rows["job-failed"]["failedTrials"] == 1
    assert rows["job-running"]["status"] == "running"
    service.shutdown()
