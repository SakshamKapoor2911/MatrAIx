"""Launch and inspect Harbor batch jobs from PersonaEval."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import tomllib
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from backend.service.application_types import normalize_metadata_type
from backend.service.config import persona_model as default_persona_model
from backend.service.job_aggregation import (
    DEFAULT_REPORTING_LLM_MODEL,
    REPORTING_LLM_ENABLE_ENV,
    REPORTING_LLM_MODEL_ENV,
    build_job_aggregation,
    read_reporting_status_artifact,
    reporting_status_artifact_path,
    write_reporting_status_artifact,
)
from persona_eval.harbor.persona_eval import (
    _default_harbor_command,
    _repo_root,
    _run_subprocess,
)
from persona_eval.remote_runner.dispatch import filter_remote_harbor_payload_env
from personabench.application_job import (
    DEFAULT_APPLICATION_JOBS_DIR,
    build_application_job_config,
    resolve_job_environment,
)

DEFAULT_AGENT_BY_TYPE: dict[str, str] = {
    # Keys here stay canonical; ``normalize_metadata_type()`` handles legacy
    # task metadata aliases before these lookup tables are consulted.
    "survey": "persona-json-survey",
    "chatbot": "persona-user-sim",
    "web": "persona-openhands-sdk",
    "os-app": "persona-computer-1",
}

AUTO_TRIAL_PROFILE_BY_TYPE: dict[str, str] = {
    "survey": "json_survey",
    "chatbot": "user_sim_chat",
    "web": "docker_agent",
    "os-app": "docker_agent",
}


def _should_use_local_distributed_harbor(
    *,
    execution_mode: str,
    execution_plane: str,
    trial_profile: str | None,
) -> bool:
    return (
        (execution_mode or "auto").strip().lower() == "auto"
        and execution_plane == "harbor"
        and trial_profile in {"json_survey", "user_sim_chat"}
    )


def _read_task_metadata_type(task_path: str, *, repo_root: Path | None = None) -> str | None:
    root = repo_root or _repo_root()
    toml_path = Path(task_path)
    if toml_path.is_absolute() and toml_path.is_dir():
        toml_path = toml_path / "task.toml"
    elif toml_path.is_absolute() and toml_path.is_file():
        pass
    elif toml_path.is_dir():
        toml_path = toml_path / "task.toml"
    elif str(task_path).endswith(".toml"):
        toml_path = Path(task_path)
    else:
        toml_path = root / task_path / "task.toml"
    if not toml_path.is_file():
        return None
    raw = toml_path.read_text(encoding="utf-8")
    payload: dict[str, Any] | None = None
    try:
        loaded = tomllib.loads(raw)
        payload = loaded if isinstance(loaded, dict) else None
    except Exception:  # noqa: BLE001
        try:
            loaded = yaml.safe_load(raw)
            payload = loaded if isinstance(loaded, dict) else None
        except Exception:  # noqa: BLE001
            payload = None
    if payload is None:
        return None
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and metadata.get("type"):
        return str(metadata["type"])
    task = payload.get("task")
    if isinstance(task, dict) and task.get("type"):
        return str(task["type"])
    return None


def resolve_trial_profile(
    task_path: str,
    *,
    mode: str = "auto",
    repo_root: Path | None = None,
) -> str:
    """Return the Harbor trial profile label for a task + execution mode."""
    normalized_mode = (mode or "auto").strip().lower()
    if normalized_mode == "smoke":
        return "smoke"
    if normalized_mode == "force_docker":
        return "docker_agent"
    task_type = normalize_metadata_type(_read_task_metadata_type(task_path, repo_root=repo_root))
    if not task_type and repo_root is not None:
        _ = repo_root
    return AUTO_TRIAL_PROFILE_BY_TYPE.get(task_type or "survey", "docker_agent")


def resolve_agent_name(
    task_path: str,
    *,
    repo_root: Path,
    explicit: str | None = None,
    mode: str = "auto",
    trial_profile: str | None = None,
) -> str:
    if explicit:
        return explicit
    profile = trial_profile or resolve_trial_profile(
        task_path, mode=mode, repo_root=repo_root
    )
    if profile == "json_survey":
        return "persona-json-survey"
    if profile == "user_sim_chat":
        return "persona-user-sim"
    normalized_mode = (mode or "auto").strip().lower()
    if normalized_mode == "smoke":
        return DEFAULT_AGENT_BY_TYPE.get("survey", "persona-claude-code")
    normalized = task_path.replace("\\", "/").lower()
    if "browser-use" in normalized:
        return "persona-browser-use"
    if "cocoa" in normalized:
        return "persona-cocoa"
    if "computer-use" in normalized or "os-app" in normalized or "cua" in normalized:
        return "persona-computer-1"
    task_type = normalize_metadata_type(_read_task_metadata_type(task_path, repo_root=repo_root))
    if task_type == "web":
        return "persona-openhands-sdk"
    if normalized_mode == "force_docker" or profile == "docker_agent":
        return "persona-claude-code"
    return DEFAULT_AGENT_BY_TYPE.get(task_type or "survey", "persona-claude-code")


def _map_task_metadata_type(task_type: str | None) -> str:
    if not task_type:
        return "unknown"
    mapped = normalize_metadata_type(task_type)
    if mapped in {"web", "survey", "chatbot", "os-app"}:
        return mapped
    return "unknown"


def _task_path_from_generated_config(config_path: Path) -> str | None:
    if not config_path.is_file():
        return None
    try:
        for line in config_path.read_text(encoding="utf-8").splitlines()[:24]:
            if line.startswith("# Task:"):
                task_path = line[len("# Task:") :].strip()
                return task_path or None
    except OSError:
        return None
    return None


def _task_path_from_trial_config(trial_dir: Path) -> str | None:
    config_path = trial_dir / "config.json"
    if not config_path.is_file():
        return None
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    task_block = config.get("task") if isinstance(config.get("task"), dict) else {}
    task_path = str(task_block.get("path") or "").strip()
    return task_path or None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _trial_result_error(result: dict[str, Any] | None) -> str | None:
    if not result:
        return None
    exc = result.get("exception_info")
    if not exc:
        return None
    if isinstance(exc, dict):
        return str(
            exc.get("exception_message")
            or exc.get("exception_type")
            or "Harbor trial failed"
        )
    return "Harbor trial failed"


def _trial_live_phase(trial_dir: Path) -> str | None:
    from persona_eval.harbor.trial_events import (
        EVENTS_FILENAME,
        read_events_after,
    )

    events, _ = read_events_after(trial_dir / EVENTS_FILENAME, 0)
    for event in reversed(events):
        if event.get("type") == "phase" and event.get("phase"):
            return str(event["phase"])
    return None


_PHASE_TO_STAGE: dict[str, str] = {
    "harbor_starting": "starting_env",
    "persona_kickoff": "agent_running",
    "application_thinking": "agent_running",
    "persona_thinking": "agent_running",
    "web_simulating": "agent_running",
    "survey_answering": "agent_running",
    "appworld_simulating": "agent_running",
    "harbor_collecting_artifacts": "verifying",
    "persona_feedback": "verifying",
}


def _stage_from_phase(phase: str | None) -> str | None:
    if not phase:
        return None
    return _PHASE_TO_STAGE.get(phase)


def _trial_live_stage(trial_dir: Path) -> str | None:
    """Infer Harbor trial lifecycle stage from on-disk artifacts."""
    if not trial_dir.is_dir():
        return "queued"
    if (trial_dir / "result.json").is_file():
        return None

    verifier_dir = trial_dir / "verifier"
    if verifier_dir.is_dir():
        verifier_markers = (
            "test-stdout.txt",
            "reward.txt",
            "reward.json",
            "ctrf.json",
        )
        if any((verifier_dir / name).is_file() for name in verifier_markers):
            return "verifying"
        try:
            if any(verifier_dir.iterdir()):
                return "verifying"
        except OSError:
            pass

    agent_dir = trial_dir / "agent"
    if agent_dir.is_dir():
        try:
            for path in agent_dir.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(agent_dir)
                if rel.parts and rel.parts[0] == "setup":
                    continue
                return "agent_running"
        except OSError:
            pass

    if (trial_dir / "trial.log").is_file() or (trial_dir / "config.json").is_file():
        return "starting_env"

    return "starting_env"


def _resolve_trial_stage(trial_dir: Path, *, phase: str | None, completed: bool) -> str | None:
    if completed:
        return None
    from_phase = _stage_from_phase(phase)
    if from_phase:
        return from_phase
    return _trial_live_stage(trial_dir)


def _persona_meta_from_trial(trial_dir: Path) -> dict[str, Any]:
    meta_path = trial_dir / "persona_meta.json"
    if not meta_path.is_file():
        return {}
    try:
        import json

        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _parse_iso_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _job_list_status(
    *,
    trial_count: int,
    completed_trials: int,
    job_result: dict[str, Any] | None,
    launch: HarborLaunchRecord | None,
) -> tuple[str, int]:
    """Return ``(status, failedTrials)`` for a Harbor job list row."""
    failed_trials = 0
    if isinstance(job_result, dict):
        stats = job_result.get("stats")
        if isinstance(stats, dict):
            failed_trials = int(stats.get("n_errored_trials") or 0)
        if job_result.get("finished_at"):
            if failed_trials > 0:
                return "failed", failed_trials
            if launch is not None and launch.status == "failed":
                return "failed", failed_trials
            return "success", 0

    if launch is not None:
        if launch.status in {"queued", "running"}:
            return "running", 0
        if launch.status == "failed":
            return "failed", failed_trials

    if trial_count > 0 and completed_trials < trial_count:
        return "running", 0

    if trial_count > 0 and completed_trials >= trial_count:
        return "running", 0

    return "running", 0


def _job_listing_times(job_dir: Path) -> tuple[str | None, str | None, str | None, float]:
    """Return (startedAt, updatedAt, finishedAt, sortTimestamp) for a job directory."""
    result_path = job_dir / "result.json"
    lock_path = job_dir / "lock.json"
    started_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None
    sort_ts: float | None = None

    if result_path.is_file():
        try:
            import json

            result = json.loads(result_path.read_text(encoding="utf-8"))
            if isinstance(result, dict):
                started_at = result.get("started_at")
                updated_at = result.get("updated_at")
                finished_at = result.get("finished_at")
                sort_ts = _parse_iso_timestamp(updated_at) or _parse_iso_timestamp(started_at)
        except Exception:  # noqa: BLE001
            pass

    if started_at is None and lock_path.is_file():
        try:
            import json

            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            if isinstance(lock, dict):
                started_at = lock.get("created_at")
                sort_ts = sort_ts or _parse_iso_timestamp(started_at)
        except Exception:  # noqa: BLE001
            pass

    if sort_ts is None:
        try:
            sort_ts = job_dir.stat().st_mtime
        except OSError:
            sort_ts = 0.0

    return started_at, updated_at, finished_at, sort_ts


def _validate_job_name(job_name: str) -> None:
    if not job_name or job_name in {".", ".."}:
        raise ValueError("Invalid job name")
    if "/" in job_name or "\\" in job_name or ".." in job_name:
        raise ValueError("Invalid job name")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "harbor-job"


@dataclass
class HarborLaunchRecord:
    job_name: str
    status: str = "queued"
    config_path: str | None = None
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    execution_plane: str = "harbor"
    remote_run_id: str | None = None


@dataclass
class HarborJobService:
    """Spawn ``harbor run`` jobs and read ``jobs_dir`` for trial progress."""

    repo_root: Path
    jobs_dir: Path
    generated_configs_dir: Path
    command_runner: Callable[..., int] = _run_subprocess
    harbor_command: tuple[str, ...] = field(default_factory=lambda: tuple(_default_harbor_command()))
    remote_runner_client: Any | None = None
    _executor: ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(max_workers=2))
    _launches: dict[str, HarborLaunchRecord] = field(default_factory=dict)
    _reporting_jobs: set[str] = field(default_factory=set)
    _guard: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def from_repo(cls, *, repo_root: Path | None = None, jobs_dir: Path | None = None) -> "HarborJobService":
        root = Path(repo_root) if repo_root is not None else _repo_root()
        resolved_jobs = Path(jobs_dir) if jobs_dir is not None else root / "jobs"
        return cls(
            repo_root=root,
            jobs_dir=resolved_jobs,
            generated_configs_dir=root / DEFAULT_APPLICATION_JOBS_DIR,
        )

    def _list_job_names(self) -> list[str]:
        if not self.jobs_dir.is_dir():
            return []
        return sorted(
            [d.name for d in self.jobs_dir.iterdir() if d.is_dir()],
            reverse=True,
        )

    def _list_trial_names(self, job_name: str) -> list[str]:
        job_dir = self.jobs_dir / job_name
        if not job_dir.is_dir():
            return []
        skip = {"_inputs", "_generated"}
        return sorted(
            [
                d.name
                for d in job_dir.iterdir()
                if d.is_dir() and d.name not in skip and not d.name.startswith(".")
            ]
        )

    def _trial_has_result(self, job_name: str, trial_name: str) -> bool:
        return (self.jobs_dir / job_name / trial_name / "result.json").is_file()

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:  # noqa: BLE001
            return None

    def _job_application_type(self, job_name: str, job_dir: Path) -> str:
        task_path = _task_path_from_generated_config(
            self.generated_configs_dir / "{}.yaml".format(job_name),
        )
        if not task_path:
            for trial_name in self._list_trial_names(job_name):
                task_path = _task_path_from_trial_config(job_dir / trial_name)
                if task_path:
                    break
        if not task_path:
            return "unknown"
        return _map_task_metadata_type(
            _read_task_metadata_type(task_path, repo_root=self.repo_root),
        )

    def _reporting_enabled(self) -> bool:
        raw = os.environ.get(REPORTING_LLM_ENABLE_ENV, "").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _reporting_model(self) -> str:
        return (
            os.environ.get(REPORTING_LLM_MODEL_ENV, "").strip()
            or DEFAULT_REPORTING_LLM_MODEL
        )

    def _job_reporting_ready(self, job_name: str, trials: list[str] | None = None) -> bool:
        trial_names = trials if trials is not None else self._list_trial_names(job_name)
        if not trial_names:
            return False
        return all(self._trial_has_result(job_name, trial_name) for trial_name in trial_names)

    def _aggregation_reporting_status(
        self,
        aggregation: dict[str, Any] | None,
    ) -> str | None:
        if not isinstance(aggregation, dict):
            return None
        reporting = aggregation.get("reporting")
        if not isinstance(reporting, dict):
            return None
        status = reporting.get("status")
        return str(status) if status else None

    def _merge_reporting_status(
        self,
        aggregation: dict[str, Any] | None,
        *,
        job_dir: Path,
    ) -> dict[str, Any] | None:
        if aggregation is None:
            return None
        live = read_reporting_status_artifact(job_dir)
        if not isinstance(live, dict):
            return aggregation
        live_status = str(live.get("status") or "").strip().lower()
        if live_status not in {"queued", "running", "failed"}:
            return aggregation
        merged = dict(aggregation)
        reporting = dict(merged.get("reporting") or {})
        reporting["status"] = live_status
        reporting["liveStatus"] = live_status
        for key in ("queuedAt", "startedAt", "finishedAt", "error", "model"):
            value = live.get(key)
            if value is not None:
                reporting[key] = value
        merged["reporting"] = reporting
        return merged

    def _build_job_aggregation_view(
        self,
        job_name: str,
        job_dir: Path,
        *,
        trials: list[str] | None = None,
    ) -> dict[str, Any] | None:
        aggregation = build_job_aggregation(
            job_dir,
            repo_root=self.repo_root,
            enable_llm=False,
        )
        self._maybe_schedule_reporting(
            job_name,
            job_dir,
            trials=trials,
            aggregation=aggregation,
        )
        return self._merge_reporting_status(aggregation, job_dir=job_dir)

    def _maybe_schedule_reporting(
        self,
        job_name: str,
        job_dir: Path,
        *,
        trials: list[str] | None = None,
        aggregation: dict[str, Any] | None = None,
    ) -> None:
        if not self._reporting_enabled():
            return
        if not self._job_reporting_ready(job_name, trials):
            return
        live = read_reporting_status_artifact(job_dir)
        if isinstance(live, dict):
            live_status = str(live.get("status") or "").strip().lower()
            if live_status in {"queued", "running", "failed"}:
                return
        if aggregation is None:
            aggregation = build_job_aggregation(
                job_dir,
                repo_root=self.repo_root,
                enable_llm=False,
            )
        status = self._aggregation_reporting_status(aggregation)
        if status not in {"ready", "partial", "partial_with_errors"}:
            return
        should_submit = False
        with self._guard:
            if job_name not in self._reporting_jobs:
                self._reporting_jobs.add(job_name)
                should_submit = True
        if not should_submit:
            return
        write_reporting_status_artifact(
            job_dir,
            {
                "status": "queued",
                "queuedAt": _utc_now(),
                "model": self._reporting_model(),
            },
        )
        self._executor.submit(self._run_job_reporting, job_name)

    def _run_job_reporting(self, job_name: str) -> None:
        job_dir = self.jobs_dir / job_name
        model = self._reporting_model()
        try:
            write_reporting_status_artifact(
                job_dir,
                {
                    "status": "running",
                    "queuedAt": _utc_now(),
                    "startedAt": _utc_now(),
                    "model": model,
                },
            )
            build_job_aggregation(
                job_dir,
                repo_root=self.repo_root,
                enable_llm=True,
            )
            status_path = reporting_status_artifact_path(job_dir)
            if status_path.is_file():
                status_path.unlink()
        except Exception as exc:  # noqa: BLE001
            write_reporting_status_artifact(
                job_dir,
                {
                    "status": "failed",
                    "startedAt": _utc_now(),
                    "finishedAt": _utc_now(),
                    "model": model,
                    "error": str(exc),
                },
            )
        finally:
            with self._guard:
                self._reporting_jobs.discard(job_name)

    def list_jobs(self) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for job_name in self._list_job_names():
            job_dir = self.jobs_dir / job_name
            trials = self._list_trial_names(job_name)
            aggregation = self._build_job_aggregation_view(job_name, job_dir, trials=trials)
            started_at, updated_at, finished_at, sort_ts = _job_listing_times(job_dir)
            completed_trials = sum(
                1 for trial_name in trials if self._trial_has_result(job_name, trial_name)
            )
            job_result = self._read_json(job_dir / "result.json")
            with self._guard:
                launch = self._launches.get(job_name)
            status, failed_trials = _job_list_status(
                trial_count=len(trials),
                completed_trials=completed_trials,
                job_result=job_result,
                launch=launch,
            )
            summaries.append(
                {
                    "jobName": job_name,
                    "applicationType": self._job_application_type(job_name, job_dir),
                    "trialCount": len(trials),
                    "completedTrials": completed_trials,
                    "startedAt": started_at,
                    "updatedAt": updated_at,
                    "finishedAt": finished_at,
                    "jobResult": job_result,
                    "status": status,
                    "failedTrials": failed_trials,
                    "launchStatus": launch.status if launch is not None else None,
                    "aggregation": aggregation,
                    "_sortTs": sort_ts,
                }
            )
        summaries.sort(key=lambda row: row.get("_sortTs") or 0.0, reverse=True)
        for row in summaries:
            row.pop("_sortTs", None)
        return summaries

    def delete_job(self, job_name: str) -> None:
        _validate_job_name(job_name)
        job_dir = self.jobs_dir / job_name
        if job_dir.is_dir():
            shutil.rmtree(job_dir)
        else:
            with self._guard:
                if job_name not in self._launches:
                    raise ValueError("Job not found: {}".format(job_name))
        with self._guard:
            self._launches.pop(job_name, None)
        config_path = self.generated_configs_dir / "{}.yaml".format(job_name)
        if config_path.is_file():
            config_path.unlink()

    def get_job(self, job_name: str) -> dict[str, Any] | None:
        job_dir = self.jobs_dir / job_name
        if not job_dir.is_dir():
            with self._guard:
                launch = self._launches.get(job_name)
            if launch is None:
                return None
            return {
                "jobName": job_name,
                "launch": _launch_view(launch),
                "trials": [],
                "aggregation": None,
            }

        trials: list[dict[str, Any]] = []
        for trial_name in self._list_trial_names(job_name):
            trial_dir = job_dir / trial_name
            result = self._read_json(trial_dir / "result.json")
            completed = self._trial_has_result(job_name, trial_name)
            error = _trial_result_error(result)
            persona_meta = _persona_meta_from_trial(trial_dir)
            trials.append(
                {
                    "trialName": trial_name,
                    "personaId": persona_meta.get("persona_id"),
                    "personaName": persona_meta.get("display_name"),
                    "completed": completed,
                    "succeeded": completed and error is None,
                    "error": error,
                    "result": result,
                }
            )

        with self._guard:
            launch = self._launches.get(job_name)

        return {
            "jobName": job_name,
            "jobsDir": _rel_path(self.jobs_dir, self.repo_root),
            "config": self._read_json(job_dir / "config.json"),
            "result": self._read_json(job_dir / "result.json"),
            "trials": trials,
            "launch": _launch_view(launch) if launch else None,
            "aggregation": self._build_job_aggregation_view(
                job_name,
                job_dir,
                trials=[str(trial.get("trialName") or "") for trial in trials if trial.get("trialName")],
            ),
        }

    def get_job_aggregation(self, job_name: str) -> dict[str, Any]:
        job_dir = self.jobs_dir / job_name
        if not job_dir.is_dir():
            raise ValueError("Job not found: {}".format(job_name))
        aggregation = self._build_job_aggregation_view(job_name, job_dir)
        if aggregation is None:
            raise ValueError("Aggregation not available for job: {}".format(job_name))
        return aggregation

    def launch(
        self,
        *,
        task_path: str,
        sample_size: int = 1,
        seed: int = 42,
        persona_pool: str = "persona/datasets/bench-dev-sample",
        persona_ids: list[str] | None = None,
        agent_name: str | None = None,
        persona_model: str | None = None,
        n_concurrent_trials: int = 2,
        execution_mode: str = "auto",
        job_name: str | None = None,
        chat_domain: str | None = None,
        chat_application_id: str | None = None,
        chat_application_context: str | None = None,
        chat_max_turns: int | None = None,
        persona_sources: list[str] | None = None,
        persona_filters: dict[str, str] | None = None,
        cohort_id: str | None = None,
        os_app_submission_profile: str | None = None,
        os_app_backend: str | None = None,
        cua_backend: str | None = None,
        execution_plane: str | None = None,
    ) -> str:
        from backend.service.execution_plane import (
            ExecutionPlaneError,
            default_execution_plane,
            normalize_execution_plane,
            remote_runner_configured,
        )

        try:
            resolved_plane = normalize_execution_plane(
                execution_plane or default_execution_plane()
            )
        except ExecutionPlaneError as exc:
            raise ValueError(str(exc)) from exc
        if resolved_plane == "remote" and not remote_runner_configured():
            raise ValueError(
                "execution plane 'remote' requires REMOTE_RUNNER_API_URL"
            )
        if os_app_backend is None and cua_backend is not None:
            os_app_backend = cua_backend
        if persona_ids is not None and len(persona_ids) == 0:
            raise ValueError("persona_ids must not be empty when provided")
        if not persona_ids and sample_size < 1:
            raise ValueError("sample_size must be >= 1")

        resolved_persona_ids = list(persona_ids or [])
        resolved_pool = persona_pool
        resolved_seed = seed
        resolved_sources = persona_sources
        resolved_filters = persona_filters

        if cohort_id:
            from backend.service.persona_pool_service import PersonaPoolService

            resolved = PersonaPoolService.from_repo(repo_root=self.repo_root).resolve_cohort_launch(
                cohort_id,
                sample_size_override=sample_size if not resolved_persona_ids else None,
            )
            resolved_pool = str(resolved.get("pool") or persona_pool)
            resolved_seed = int(resolved.get("seed") or seed)
            resolved_sources = list(resolved.get("sources") or []) or None
            resolved_filters = dict(resolved.get("dimensionFilters") or {}) or None
            if resolved.get("personaIds"):
                resolved_persona_ids = list(resolved["personaIds"])

        if not resolved_persona_ids and (resolved_sources or resolved_filters):
            from backend.service.persona_pool_service import PersonaPoolService

            sampled = PersonaPoolService.from_repo(repo_root=self.repo_root).sample_pool(
                persona_pool=resolved_pool,
                sample_size=sample_size,
                seed=resolved_seed,
                sources=resolved_sources,
                dimension_filters=resolved_filters,
            )
            resolved_persona_ids = list(sampled["personaIds"])

        task_slug = _slug(Path(task_path).name)
        resolved_job_name = job_name or "pe-{}-{}".format(task_slug, uuid.uuid4().hex[:8])
        model = persona_model or default_persona_model()
        trial_profile = resolve_trial_profile(
            task_path,
            mode=execution_mode,
            repo_root=self.repo_root,
        )
        resolved_survey_task_path: str | None = None
        resolved_chat_task_path: str | None = None
        if trial_profile == "json_survey":
            normalized_task_path = task_path.strip().replace("\\", "/")
            resolved_survey_task_path = normalized_task_path
        elif trial_profile == "user_sim_chat":
            resolved_chat_task_path = task_path.strip().replace("\\", "/")
        agent = resolve_agent_name(
            task_path,
            repo_root=self.repo_root,
            explicit=agent_name,
            mode=execution_mode,
            trial_profile=trial_profile,
        )

        spec = {
            "name": resolved_job_name,
            "task": task_path,
            "persona_pool": resolved_pool,
            "sample_size": len(resolved_persona_ids) if resolved_persona_ids else sample_size,
            "seed": resolved_seed,
            "persona_ids": resolved_persona_ids,
            "execution_mode": execution_mode,
            "trial_profile": trial_profile,
            "cua_backend": os_app_backend,
            "agent": {"name": agent, "model_name": model},
            "job": {
                "job_name": resolved_job_name,
                "jobs_dir": _rel_path(self.jobs_dir, self.repo_root),
                "n_concurrent_trials": n_concurrent_trials,
            },
        }
        from personabench.application_job import resolve_harbor_task_path

        resolved_task_path = resolve_harbor_task_path(task_path, trial_profile=trial_profile)
        job_config = build_application_job_config(spec, repo_root=self.repo_root)
        if os_app_submission_profile:
            for agent in job_config.get("agents", []):
                if isinstance(agent, dict):
                    kwargs = agent.setdefault("kwargs", {})
                    if isinstance(kwargs, dict):
                        kwargs["cua_submission_profile"] = os_app_submission_profile
        if os_app_backend:
            job_config["environment"] = resolve_job_environment(
                execution_mode=execution_mode,
                trial_profile=trial_profile,
                cua_backend=os_app_backend,
            )
            for agent in job_config.get("agents", []):
                if isinstance(agent, dict):
                    kwargs = agent.setdefault("kwargs", {})
                    if isinstance(kwargs, dict):
                        kwargs["cua_backend"] = os_app_backend
        job_meta = job_config.pop("_job_meta", None)

        self.generated_configs_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.generated_configs_dir / "{}.yaml".format(resolved_job_name)
        header = (
            "# Generated by PersonaEval POST /api/harbor/jobs\n"
            "# Task: {}\n"
            "# Harbor task: {}\n"
            "# Mode: {}\n"
            "# Trial profile: {}\n"
            "# Seed: {}\n"
            "# Persona pool: {}\n"
            "# Cohort: {}\n"
            "# Persona sources: {}\n"
            "# Persona filters: {}\n"
            "# Personas: {}\n"
            "# Jobs output: {}/\n\n".format(
                task_path,
                resolved_task_path,
                job_meta.get("execution_mode", "auto") if job_meta else "auto",
                job_meta.get("trial_profile", "docker_agent") if job_meta else "docker_agent",
                seed,
                resolved_pool,
                cohort_id or "(none)",
                ", ".join(resolved_sources or []) or "(all)",
                ", ".join(
                    "{}={}".format(key, value)
                    for key, value in sorted((resolved_filters or {}).items())
                )
                or "(none)",
                ", ".join(job_meta.get("selected_persona_ids", []) if job_meta else []),
                _rel_path(self.jobs_dir, self.repo_root),
            )
        )
        config_path.write_text(
            header + yaml.safe_dump(job_config, sort_keys=False),
            encoding="utf-8",
        )

        record = HarborLaunchRecord(
            job_name=resolved_job_name,
            status="queued",
            config_path=_rel_path(config_path, self.repo_root),
            started_at=_utc_now(),
            execution_plane=resolved_plane,
        )
        with self._guard:
            self._launches[resolved_job_name] = record

        if _should_use_local_distributed_harbor(
            execution_mode=execution_mode,
            execution_plane=resolved_plane,
            trial_profile=trial_profile,
        ):
            self._executor.submit(
                self._run_local_distributed,
                resolved_job_name,
                job_config,
                resolved_survey_task_path,
                resolved_chat_task_path,
                chat_domain,
                chat_application_id,
                chat_application_context,
                chat_max_turns,
                trial_profile,
            )
        else:
            dispatch_kwargs = (
                resolved_job_name,
                config_path,
                resolved_survey_task_path,
                resolved_chat_task_path,
                os_app_submission_profile,
                chat_domain,
                chat_application_id,
                chat_application_context,
                chat_max_turns,
                trial_profile,
            )
            if resolved_plane == "remote":
                self._executor.submit(self._dispatch_remote, *dispatch_kwargs)
            else:
                self._executor.submit(self._run_harbor, *dispatch_kwargs)
        return resolved_job_name

    def _build_harbor_launch_env(
        self,
        *,
        survey_task_path: str | None,
        chat_task_path: str | None,
        trial_profile: str | None,
        chat_domain: str | None,
        chat_application_id: str | None,
        chat_application_context: str | None,
        chat_max_turns: int | None,
        for_remote: bool = False,
    ) -> dict[str, str]:
        env = {} if for_remote else dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        path_entries = [entry for entry in existing.split(":") if entry]
        required_paths = [
            str(self.repo_root),
            str(self.repo_root / "environment" / "runtime"),
            str(self.repo_root / "packages" / "persona-eval" / "src"),
            str(self.repo_root / "application" / "persona_eval"),
            str(
                self.repo_root
                / "environment"
                / "task-environments"
                / "application"
                / "shared-chat-api-recommender"
                / "recommender-api"
            ),
        ]
        for path in reversed(required_paths):
            if path not in path_entries:
                path_entries.insert(0, path)
        env["PYTHONPATH"] = ":".join(path_entries)
        if survey_task_path:
            env["MATRIX_SURVEY_TASK_PATH"] = survey_task_path
        if trial_profile == "user_sim_chat":
            if chat_task_path:
                env["MATRIX_CHATBOT_TASK_PATH"] = chat_task_path
            if chat_domain:
                env["MATRIX_CHATBOT_DOMAIN"] = chat_domain
            if chat_application_id:
                env["MATRIX_CHATBOT_APPLICATION_ID"] = chat_application_id
            if chat_application_context:
                env["MATRIX_CHATBOT_APPLICATION_CONTEXT"] = chat_application_context
            if chat_max_turns is not None:
                env["MATRIX_CHATBOT_MAX_TURNS"] = str(chat_max_turns)
        return env

    def _remote_client(self):
        if self.remote_runner_client is not None:
            return self.remote_runner_client
        from persona_eval.remote_runner.client import (
            RemoteRunnerClient,
        )

        return RemoteRunnerClient()

    def _run_local_distributed(
        self,
        job_name: str,
        job_config_payload: dict[str, Any],
        survey_task_path: str | None = None,
        chat_task_path: str | None = None,
        chat_domain: str | None = None,
        chat_application_id: str | None = None,
        chat_application_context: str | None = None,
        chat_max_turns: int | None = None,
        trial_profile: str | None = None,
    ) -> None:
        with self._guard:
            record = self._launches[job_name]
            record.status = "running"

        env = self._build_harbor_launch_env(
            survey_task_path=survey_task_path,
            chat_task_path=chat_task_path,
            trial_profile=trial_profile,
            chat_domain=chat_domain,
            chat_application_id=chat_application_id,
            chat_application_context=chat_application_context,
            chat_max_turns=chat_max_turns,
        )
        try:
            from backend.service.local_distributed_harbor import (
                LocalDistributedHarborCoordinator,
            )

            coordinator = LocalDistributedHarborCoordinator(
                repo_root=self.repo_root,
                job_name=job_name,
                job_config=job_config_payload,
                launch_env=env,
                command_runner=self.command_runner,
                harbor_command=self.harbor_command,
            )
            coordinator.run()
            status = "completed"
            error = None
            exit_code = 0
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = str(exc)
            exit_code = 1

        with self._guard:
            record = self._launches[job_name]
            record.status = status
            record.exit_code = exit_code
            record.error = error
            record.finished_at = _utc_now()
        self._maybe_generate_post_run_feedback(job_name)
        self._maybe_schedule_reporting(job_name, self.jobs_dir / job_name)

    def _run_harbor(
        self,
        job_name: str,
        config_path: Path,
        survey_task_path: str | None = None,
        chat_task_path: str | None = None,
        os_app_submission_profile: str | None = None,
        chat_domain: str | None = None,
        chat_application_id: str | None = None,
        chat_application_context: str | None = None,
        chat_max_turns: int | None = None,
        trial_profile: str | None = None,
    ) -> None:
        with self._guard:
            record = self._launches[job_name]
            record.status = "running"

        command = list(self.harbor_command) + [
            "-c",
            _rel_path(config_path, self.repo_root),
        ]
        env = self._build_harbor_launch_env(
            survey_task_path=survey_task_path,
            chat_task_path=chat_task_path,
            trial_profile=trial_profile,
            chat_domain=chat_domain,
            chat_application_id=chat_application_id,
            chat_application_context=chat_application_context,
            chat_max_turns=chat_max_turns,
        )
        try:
            exit_code = self.command_runner(
                command,
                cwd=self.repo_root,
                env=env,
            )
            error = None if exit_code == 0 else "harbor run exited with code {}".format(exit_code)
            status = "completed" if exit_code == 0 else "failed"
        except Exception as exc:  # noqa: BLE001
            exit_code = 1
            error = str(exc)
            status = "failed"

        with self._guard:
            record = self._launches[job_name]
            record.status = status
            record.exit_code = exit_code
            record.error = error
            record.finished_at = _utc_now()
        self._maybe_generate_post_run_feedback(job_name)
        self._maybe_schedule_reporting(job_name, self.jobs_dir / job_name)

    def _dispatch_remote(
        self,
        job_name: str,
        config_path: Path,
        survey_task_path: str | None = None,
        chat_task_path: str | None = None,
        os_app_submission_profile: str | None = None,
        chat_domain: str | None = None,
        chat_application_id: str | None = None,
        chat_application_context: str | None = None,
        chat_max_turns: int | None = None,
        trial_profile: str | None = None,
    ) -> None:
        del os_app_submission_profile
        with self._guard:
            record = self._launches[job_name]
            record.status = "running"

        env = self._build_harbor_launch_env(
            survey_task_path=survey_task_path,
            chat_task_path=chat_task_path,
            trial_profile=trial_profile,
            chat_domain=chat_domain,
            chat_application_id=chat_application_id,
            chat_application_context=chat_application_context,
            chat_max_turns=chat_max_turns,
            for_remote=True,
        )
        payload = {
            "jobName": job_name,
            "configYaml": config_path.read_text(encoding="utf-8"),
            "repoRoot": str(self.repo_root.resolve()),
            "jobsDir": _rel_path(self.jobs_dir, self.repo_root),
            "env": filter_remote_harbor_payload_env(env),
        }
        try:
            client = self._remote_client()
            run = client.create_run(task_type="harbor_job", payload=payload)
            with self._guard:
                record = self._launches[job_name]
                record.remote_run_id = run.id
            client.wait_for_run(run.id)
            status = "completed"
            error = None
            exit_code = 0
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = str(exc)
            exit_code = 1

        with self._guard:
            record = self._launches[job_name]
            record.status = status
            record.exit_code = exit_code
            record.error = error
            record.finished_at = _utc_now()
        self._maybe_generate_post_run_feedback(job_name)
        self._maybe_schedule_reporting(job_name, self.jobs_dir / job_name)

    def _maybe_generate_post_run_feedback(self, job_name: str) -> None:
        from persona_eval.post_run_feedback import (
            maybe_write_trial_user_feedback,
        )

        job_dir = self.jobs_dir / job_name
        if not job_dir.is_dir():
            return
        for trial_dir in sorted(job_dir.iterdir()):
            if not trial_dir.is_dir() or trial_dir.name.startswith("_"):
                continue
            if not (trial_dir / "config.json").is_file():
                continue
            try:
                maybe_write_trial_user_feedback(repo_root=self.repo_root, trial_dir=trial_dir)
            except Exception:
                continue

    def get_trial_events(
        self,
        job_name: str,
        trial_name: str,
        *,
        after: int = 0,
    ) -> dict[str, Any]:
        trial_dir = self.jobs_dir / job_name / trial_name
        if not trial_dir.is_dir():
            raise ValueError("Trial not found: {}/{}".format(job_name, trial_name))
        from persona_eval.harbor.trial_events import (
            EVENTS_FILENAME,
            read_events_after,
        )

        events, offset = read_events_after(trial_dir / EVENTS_FILENAME, after)
        return {"events": events, "offset": offset}

    def get_trial_web_trace(self, job_name: str, trial_name: str) -> dict[str, Any]:
        from backend.service.harbor_trial_debrief import find_trial_logs_dir
        from backend.service.harbor_web_trace import read_harbor_web_trace

        trial_dir = self.jobs_dir / job_name / trial_name
        if not trial_dir.is_dir():
            raise ValueError("Trial not found: {}/{}".format(job_name, trial_name))
        trace = read_harbor_web_trace(
            find_trial_logs_dir(trial_dir),
            job_name=job_name,
            trial_name=trial_name,
        )
        return {"trace": trace}

    def trial_screenshot_path(self, job_name: str, trial_name: str, filename: str) -> Path:
        from backend.service.harbor_trial_debrief import find_trial_logs_dir
        from backend.service.harbor_web_trace import resolve_trial_screenshot_path

        trial_dir = self.jobs_dir / job_name / trial_name
        if not trial_dir.is_dir():
            raise ValueError("Trial not found: {}/{}".format(job_name, trial_name))
        logs_dir = find_trial_logs_dir(trial_dir)
        if logs_dir is None:
            raise FileNotFoundError("trial logs not found")
        return resolve_trial_screenshot_path(logs_dir, filename)

    def trial_recording_path(self, job_name: str, trial_name: str) -> Path:
        from backend.service.harbor_trial_debrief import find_trial_logs_dir

        trial_dir = self.jobs_dir / job_name / trial_name
        if not trial_dir.is_dir():
            raise ValueError("Trial not found: {}/{}".format(job_name, trial_name))
        logs_dir = find_trial_logs_dir(trial_dir)
        if logs_dir is None:
            raise FileNotFoundError("trial logs not found")
        path = logs_dir / "recording.mp4"
        if not path.is_file():
            raise FileNotFoundError("recording not found")
        return path

    def get_job_live(self, job_name: str) -> dict[str, Any]:
        job = self.get_job(job_name)
        if job is None:
            raise ValueError("Job not found: {}".format(job_name))
        live_trials: list[dict[str, Any]] = []
        for trial in job.get("trials", []):
            if not isinstance(trial, dict):
                continue
            trial_name = str(trial.get("trialName") or "")
            if not trial_name:
                continue
            trial_dir = self.jobs_dir / job_name / trial_name
            persona_meta = _persona_meta_from_trial(trial_dir)
            instruction_path = trial_dir / "instruction.md"
            phase = _trial_live_phase(trial_dir) if trial_dir.is_dir() else None
            completed = bool(trial.get("completed"))
            live_trials.append(
                {
                    "trialName": trial_name,
                    "personaId": persona_meta.get("persona_id"),
                    "personaName": persona_meta.get("display_name"),
                    "completed": completed,
                    "succeeded": trial.get("succeeded"),
                    "error": trial.get("error"),
                    "phase": phase,
                    "stage": _resolve_trial_stage(trial_dir, phase=phase, completed=completed),
                    "hasInstruction": instruction_path.is_file(),
                }
            )
        launch = job.get("launch") if isinstance(job.get("launch"), dict) else None
        launch_status = launch.get("status") if launch else None
        completed_count = sum(1 for trial in live_trials if trial.get("completed"))
        return {
            "jobName": job_name,
            "launchStatus": launch_status,
            "trialCount": len(live_trials),
            "completedTrials": completed_count,
            "trials": live_trials,
        }

    def get_trial_debrief(self, job_name: str, trial_name: str) -> dict[str, Any]:
        from backend.service.harbor_trial_debrief import map_trial_debrief

        try:
            return map_trial_debrief(
                repo_root=self.repo_root,
                jobs_dir=self.jobs_dir,
                job_name=job_name,
                trial_name=trial_name,
            )
        except FileNotFoundError as exc:
            raise ValueError(str(exc)) from exc

    def get_trial_instruction(self, job_name: str, trial_name: str) -> dict[str, Any]:
        trial_dir = self.jobs_dir / job_name / trial_name
        if not trial_dir.is_dir():
            raise ValueError("Trial not found: {}/{}".format(job_name, trial_name))
        task_instruction_markdown = ""
        context_markdown = ""
        questionnaire_markdown = ""
        output_schema_markdown = ""
        self_report_markdown = ""
        instruction_path = trial_dir / "instruction.md"
        task_instruction_path = trial_dir / "task_instruction.md"
        context_path = trial_dir / "context.md"
        questionnaire_path = trial_dir / "questionnaire.md"
        output_schema_path = trial_dir / "output_schema.md"
        if task_instruction_path.is_file():
            task_instruction_markdown = task_instruction_path.read_text(encoding="utf-8").strip()
        if context_path.is_file():
            context_markdown = context_path.read_text(encoding="utf-8").strip()
        if questionnaire_path.is_file():
            questionnaire_markdown = questionnaire_path.read_text(encoding="utf-8").strip()
        if output_schema_path.is_file():
            output_schema_markdown = output_schema_path.read_text(encoding="utf-8").strip()
        task_path = ""
        config_path = trial_dir / "config.json"
        if config_path.is_file():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                task_block = config.get("task") if isinstance(config.get("task"), dict) else {}
                task_path = str(task_block.get("path") or "")
            except Exception:  # noqa: BLE001
                task_path = ""
        detail = None
        if task_path and (
            not task_instruction_markdown
            or not context_markdown
            or not questionnaire_markdown
            or not output_schema_markdown
            or not self_report_markdown
        ):
            from backend.service.task_detail_service import get_task_detail

            detail = get_task_detail(task_path, repo_root=self.repo_root)
            task_instruction_markdown = task_instruction_markdown or str(
                detail.get("instructionMarkdown") or ""
            ).strip()
            context_markdown = context_markdown or str(detail.get("contextMarkdown") or "").strip()
            questionnaire_markdown = questionnaire_markdown or str(
                detail.get("questionnaireMarkdown") or ""
            ).strip()
            output_schema_markdown = output_schema_markdown or str(
                detail.get("outputSchemaMarkdown") or ""
            ).strip()
            self_report_markdown = self_report_markdown or str(
                detail.get("selfReportMarkdown") or ""
            ).strip()
        if instruction_path.is_file():
            markdown = instruction_path.read_text(encoding="utf-8").strip()
            title = ""
            for line in markdown.splitlines():
                stripped = line.strip()
                if stripped.startswith("# "):
                    title = stripped.lstrip("# ").strip()
                    break
            return {
                "title": title or None,
                "markdown": markdown,
                "instructionMarkdown": task_instruction_markdown or None,
                "contextMarkdown": context_markdown or None,
                "questionnaireMarkdown": questionnaire_markdown or None,
                "outputSchemaMarkdown": output_schema_markdown or None,
                "selfReportMarkdown": self_report_markdown or None,
            }
        if task_path:
            from backend.service.task_detail_service import get_task_detail

            detail = detail or get_task_detail(task_path, repo_root=self.repo_root)
            markdown = str(detail.get("instructionMarkdown") or detail.get("profileMarkdown") or "").strip()
            if markdown:
                return {
                    "title": detail.get("title"),
                    "markdown": markdown,
                    "instructionMarkdown": detail.get("instructionMarkdown") or None,
                    "contextMarkdown": detail.get("contextMarkdown") or None,
                    "questionnaireMarkdown": detail.get("questionnaireMarkdown") or None,
                    "outputSchemaMarkdown": detail.get("outputSchemaMarkdown") or None,
                    "selfReportMarkdown": detail.get("selfReportMarkdown") or None,
                }
        raise FileNotFoundError("instruction not found for trial {}/{}".format(job_name, trial_name))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


def _launch_view(record: HarborLaunchRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "status": record.status,
        "configPath": record.config_path,
        "error": record.error,
        "startedAt": record.started_at,
        "finishedAt": record.finished_at,
        "exitCode": record.exit_code,
        "executionPlane": record.execution_plane,
        "remoteRunId": record.remote_run_id,
    }


def _rel_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
