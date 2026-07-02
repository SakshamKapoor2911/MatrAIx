"""Map Harbor ``jobs/<job>/<trial>/`` artifacts into PersonaEval debrief shapes."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from backend.service import run_store
from backend.service.survey_eval_service import survey_result_view
from backend.service.survey_types import SurveyInstrument, SurveyQuestion
from persona_eval.types import Persona, PersonaEvalConfig


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("{} must contain a JSON object".format(path.name))
    return data


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


def find_trial_output_dir(trial_dir: Path) -> Path | None:
    """Return ``artifacts/app/output`` when present."""
    matches = sorted(trial_dir.glob("artifacts/app/output"))
    if not matches:
        matches = sorted(trial_dir.rglob("artifacts/app/output"))
    return matches[0] if matches else None


def find_trial_logs_dir(trial_dir: Path) -> Path | None:
    logs = trial_dir / "agent"
    return logs if logs.is_dir() else None


def _persona_path_from_trial(trial_dir: Path, repo_root: Path) -> str | None:
    result_path = trial_dir / "result.json"
    if result_path.is_file():
        try:
            payload = _read_json(result_path)
        except Exception:  # noqa: BLE001
            payload = {}
        config = payload.get("config")
        if isinstance(config, dict):
            agent = config.get("agent")
            if isinstance(agent, dict):
                kwargs = agent.get("kwargs")
                if isinstance(kwargs, dict):
                    rel = kwargs.get("persona_path")
                    if isinstance(rel, str) and rel.strip():
                        return rel.strip()
    config_path = trial_dir / "config.json"
    if config_path.is_file():
        try:
            payload = _read_json(config_path)
        except Exception:  # noqa: BLE001
            payload = {}
        agent = payload.get("agent")
        if isinstance(agent, dict):
            kwargs = agent.get("kwargs")
            if isinstance(kwargs, dict):
                rel = kwargs.get("persona_path")
                if isinstance(rel, str) and rel.strip():
                    return rel.strip()
    return None


def _load_persona_eval_persona(repo_root: Path, persona_rel: str | None) -> Persona:
    if persona_rel:
        abs_path = (repo_root / persona_rel).resolve()
        if abs_path.is_file():
            stem = abs_path.stem
            try:
                from persona_eval.persona import get_persona

                return get_persona(stem)
            except KeyError:
                pass
            try:
                from personabench.agents.persona.loader import load_persona as load_harbor_persona

                prev = os.getcwd()
                try:
                    os.chdir(repo_root)
                    loaded = load_harbor_persona(persona_rel)
                finally:
                    os.chdir(prev)
            except Exception:  # noqa: BLE001
                loaded = None
            if loaded is not None:
                raw = loaded.data
                context = loaded.system_prompt or loaded.summary or ""
                if not context and loaded.has_dimensions_schema():
                    context = "Persona {}".format(loaded.persona_id or stem)
                return Persona(
                    id=str(loaded.persona_id or stem),
                    name=str(loaded.display_name or loaded.persona_id or stem),
                    source=str(raw.get("source") or ""),
                    context=context,
                )
            raw = yaml.safe_load(abs_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                pid = str(raw.get("persona_id") or raw.get("id") or stem)
                return Persona(
                    id=pid,
                    name=str(raw.get("display_name") or raw.get("name") or pid),
                    source=str(raw.get("source") or ""),
                    context=str(raw.get("system_prompt") or raw.get("summary") or pid),
                )
    return Persona(id="unknown", name="Persona", source="", context="")


def _task_path_from_trial(trial_dir: Path) -> str | None:
    config_path = trial_dir / "config.json"
    if not config_path.is_file():
        return None
    try:
        payload = _read_json(config_path)
    except Exception:  # noqa: BLE001
        return None
    task = payload.get("task")
    if not isinstance(task, dict):
        return None
    path = task.get("path")
    if isinstance(path, str) and path.strip():
        return path.strip().replace("\\", "/")
    return None


def _application_type_from_task_toml(repo_root: Path, task_rel: str) -> str | None:
    toml_path = repo_root / task_rel / "task.toml"
    if not toml_path.is_file():
        return None
    try:
        import tomllib

        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        return None
    app_type = metadata.get("type")
    if isinstance(app_type, str) and app_type.strip():
        mapped = app_type.strip().lower()
        if mapped in {"web", "survey", "chatbot", "cua"}:
            return mapped
    return None


def _resolve_application_type(
    repo_root: Path,
    trial_dir: Path,
    output_dir: Path,
) -> str:
    task_path = _task_path_from_trial(trial_dir)
    if task_path:
        from_toml = _application_type_from_task_toml(repo_root, task_path)
        if from_toml:
            return from_toml
    return _detect_application_type(output_dir)


def _detect_application_type(output_dir: Path) -> str:
    if (output_dir / "transcript.json").is_file():
        return "chatbot"
    if (output_dir / "survey_result.json").is_file():
        return "survey"
    if (output_dir / "survey_responses.json").is_file():
        return "survey"
    for path in output_dir.glob("*.json"):
        name = path.name.lower()
        if name in {"decision.json", "book_interest.json"}:
            return "cua"
        if "notification" in name and "preference" in name:
            return "cua"
        if "web" in name or "ecommerce" in name or "interaction" in name:
            return "web"
    return "unknown"


def _instrument_from_survey_payload(payload: dict[str, Any]) -> SurveyInstrument:
    instrument = payload.get("instrument")
    if isinstance(instrument, dict) and instrument.get("questions"):
        return SurveyInstrument.from_dict(instrument)
    answers = payload.get("answers")
    if isinstance(answers, list) and answers:
        questions = []
        for index, entry in enumerate(answers):
            if not isinstance(entry, dict):
                continue
            qid = str(entry.get("questionId") or entry.get("question_id") or "q{}".format(index))
            questions.append(
                SurveyQuestion(
                    id=qid,
                    prompt=str(entry.get("prompt") or entry.get("question") or qid),
                    type=str(entry.get("type") or "free_text"),
                )
            )
        if questions:
            title = ""
            if isinstance(instrument, dict):
                title = str(instrument.get("title") or instrument.get("id") or "Survey")
            return SurveyInstrument(
                id=str((instrument or {}).get("id") if isinstance(instrument, dict) else "harbor_survey"),
                title=title or "Harbor survey",
                questions=questions,
            )
    return SurveyInstrument(
        id="harbor_survey",
        title="Harbor survey",
        questions=[SurveyQuestion(id="response", prompt="Survey response", type="free_text")],
    )


def _map_chatbot_debrief(
    *,
    output_dir: Path,
    persona: Persona,
    created_at: str,
) -> dict[str, Any]:
    from environment.integrations.persona_eval.harbor.persona_eval import (
        build_result_from_harbor_artifacts,
    )

    transcript = _read_json(output_dir / "transcript.json")
    domain = str(transcript.get("domain") or "movie")
    result = build_result_from_harbor_artifacts(
        output_dir=output_dir,
        config=PersonaEvalConfig(domain=domain, engine="gpt-4o-mini", max_turns=8),
        persona=persona,
        sut_description="Chat application under test.",
        created_at=created_at,
    )
    payload = result.to_dict()
    payload["id"] = "harbor-trial"
    payload["applicationType"] = "chatbot"
    payload["createdAt"] = created_at
    payload["persona"] = run_store.persona_summary(persona)
    return payload


def _map_survey_debrief(
    *,
    output_dir: Path,
    persona: Persona,
    created_at: str,
) -> dict[str, Any]:
    from environment.integrations.persona_eval.harbor.survey_eval import (
        HarborSurveyEvalConfig,
        build_result_from_harbor_survey_artifacts,
    )

    if (output_dir / "survey_result.json").is_file():
        raw = _read_json(output_dir / "survey_result.json")
        instrument = _instrument_from_survey_payload(raw)
        result = build_result_from_harbor_survey_artifacts(
            output_dir=output_dir,
            config=HarborSurveyEvalConfig(),
            persona=persona,
            instrument=instrument,
            created_at=created_at,
        )
        result_view = survey_result_view(result)
    else:
        raw = _read_json(output_dir / "survey_responses.json")
        responses = raw.get("responses")
        if not isinstance(responses, list):
            responses = raw.get("answers") if isinstance(raw.get("answers"), list) else []
        answers = []
        for index, entry in enumerate(responses):
            if not isinstance(entry, dict):
                continue
            answers.append(
                {
                    "questionId": str(
                        entry.get("question_id")
                        or entry.get("questionId")
                        or "q{}".format(index)
                    ),
                    "value": entry.get("choice_id")
                    or entry.get("value")
                    or entry.get("response")
                    or "",
                    "rationale": entry.get("rationale"),
                }
            )
        instrument = SurveyInstrument(
            id="harbor_survey_responses",
            title="Survey responses",
            questions=[
                SurveyQuestion(
                    id=str(a["questionId"]),
                    prompt=str(a["questionId"]),
                    type="free_text",
                )
                for a in answers
            ],
        )
        from backend.service.survey_types import (
            SurveyAnswer,
            SurveyEvalConfig,
            SurveyEvalResult,
            SurveyMetrics,
        )

        typed_answers = [
            SurveyAnswer(
                question_id=str(a["questionId"]),
                value=a["value"],
                rationale=str(a.get("rationale") or ""),
            )
            for a in answers
        ]
        metrics = SurveyMetrics(
            num_questions=len(typed_answers),
            num_answered=len(typed_answers),
            mean_likert=None,
        )
        result = SurveyEvalResult(
            config=SurveyEvalConfig(),
            persona=persona,
            instrument=instrument,
            answers=typed_answers,
            trajectory=[],
            metrics=metrics,
            created_at=created_at,
            prompts={},
        )
        result_view = survey_result_view(result)

    return {
        "id": "harbor-trial",
        "applicationType": "survey",
        "createdAt": created_at,
        "persona": run_store.persona_summary(persona),
        "instrumentTitle": result_view.get("instrument", {}).get("title"),
        "surveyResult": result_view,
    }


def _resolve_web_eval_task(
    repo_root: Path,
    trial_dir: Path,
    output_dir: Path,
) -> "WebEvalTask":
    from backend.service.web_tasks import list_web_eval_tasks
    from backend.service.web_types import WebEvalTask

    task_rel = _task_path_from_trial(trial_dir)
    if task_rel:
        folder = Path(task_rel.replace("\\", "/")).name
        for task in list_web_eval_tasks():
            if task.task_path.name == folder:
                return task
    artifact_name = next(
        (
            path.name
            for path in sorted(output_dir.glob("*.json"))
            if path.name not in {"survey_result.json", "survey_responses.json", "transcript.json"}
        ),
        "ecommerce_interaction.json",
    )
    return WebEvalTask(
        id="harbor_web",
        title="Website task",
        site_name="Website",
        site_url="https://example.com",
        task_path=repo_root / task_rel if task_rel else output_dir,
        description="Harbor web trial",
        output_artifact=artifact_name,
    )


def _web_result_from_book_interest(data: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    title = str(data.get("title", "")).strip() or "Book"
    reason = str(data.get("reason", "")).strip() or "Book selection recorded."
    interested = bool(data.get("interested", True))
    score = 8 if interested else 5
    return {
        "selectedProductId": title,
        "selectedProductName": title,
        "needSatisfaction": score,
        "easeOfUse": score,
        "overallExperienceRating": score,
        "reason": reason,
        "createdAt": created_at,
        "valid": len(reason) >= 20,
    }


def _map_web_debrief(
    *,
    output_dir: Path,
    logs_dir: Path | None,
    persona: Persona,
    created_at: str,
    job_name: str,
    trial_name: str,
    trial_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    from environment.integrations.persona_eval.harbor.web_eval import (
        HarborWebEvalConfig,
        build_result_from_harbor_web_artifacts,
    )

    task = _resolve_web_eval_task(repo_root, trial_dir, output_dir)
    from backend.service.harbor_web_trace import read_harbor_web_trace

    trace = read_harbor_web_trace(
        logs_dir,
        job_name=job_name,
        trial_name=trial_name,
    )
    web_result: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None
    try:
        result = build_result_from_harbor_web_artifacts(
            output_dir=output_dir,
            logs_dir=logs_dir,
            config=HarborWebEvalConfig(),
            persona=persona,
            task=task,
            created_at=created_at,
        )
        payload = result.to_dict()
        web_result = payload.get("webResult")
        prompts = payload.get("prompts")
    except (ValueError, FileNotFoundError):
        artifact_path = output_dir / task.output_artifact
        if artifact_path.is_file() and artifact_path.name == "book_interest.json":
            web_result = _web_result_from_book_interest(
                _read_json(artifact_path),
                created_at=created_at,
            )
    return {
        "id": "harbor-trial",
        "applicationType": "web",
        "createdAt": created_at,
        "persona": run_store.persona_summary(persona),
        "siteName": task.site_name,
        "taskTitle": task.title,
        "webResult": web_result,
        "webTrace": trace,
        "prompts": prompts,
    }


def _read_reward_score(trial_dir: Path) -> float | None:
    reward_path = trial_dir / "reward.txt"
    if not reward_path.is_file():
        return None
    try:
        return float(reward_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _verifier_summary(trial_dir: Path) -> dict[str, Any] | None:
    reward = _read_reward_score(trial_dir)
    if reward is None:
        return None
    detail: str | None = None
    detail_path = trial_dir / "verifier" / "test-stdout.txt"
    if detail_path.is_file():
        raw = detail_path.read_text(encoding="utf-8", errors="replace").strip()
        if raw:
            detail = raw[:2000]
    return {
        "passed": reward >= 1.0,
        "reward": reward,
        "detail": detail,
    }


def _map_cua_debrief(
    *,
    output_dir: Path,
    logs_dir: Path | None,
    trial_dir: Path,
    persona: Persona,
    created_at: str,
    job_name: str,
    trial_name: str,
) -> dict[str, Any]:
    artifact_path = next(
        (
            path
            for path in sorted(output_dir.glob("*.json"))
            if path.name.lower() in {"decision.json", "book_interest.json"}
            or "notification" in path.name.lower()
        ),
        None,
    )
    if artifact_path is None:
        artifacts = sorted(path.name for path in output_dir.glob("*.json"))
        artifact_path = output_dir / artifacts[0] if artifacts else None
    artifact: dict[str, Any] | None = None
    if artifact_path is not None and artifact_path.is_file():
        artifact = _read_json(artifact_path)

    trace: dict[str, Any] | None = None
    if logs_dir is not None:
        trajectory_path = logs_dir / "trajectory.json"
        if trajectory_path.is_file():
            try:
                from environment.integrations.persona_eval.harbor.web_eval import _trace_from_trajectory

                mapped = _trace_from_trajectory(_read_json(trajectory_path))
                trace = mapped.to_dict()
            except Exception:  # noqa: BLE001
                trace = {"events": [], "raw": {}}

    from backend.service.harbor_web_trace import attach_harbor_trace_screenshot_urls

    trace = attach_harbor_trace_screenshot_urls(
        trace,
        job_name=job_name,
        trial_name=trial_name,
    )

    reward = _read_reward_score(trial_dir)
    success = reward is not None and reward >= 1.0
    return {
        "id": "harbor-trial",
        "applicationType": "cua",
        "createdAt": created_at,
        "persona": run_store.persona_summary(persona),
        "cuaResult": {
            "success": success if reward is not None else artifact is not None,
            "score": reward if reward is not None else (1.0 if success else 0.0),
            "artifactName": artifact_path.name if artifact_path is not None else None,
            "artifact": artifact,
            "createdAt": created_at,
        },
        "cuaTrace": trace,
        "trace": trace,
    }


def map_trial_debrief(
    *,
    repo_root: Path,
    jobs_dir: Path,
    job_name: str,
    trial_name: str,
) -> dict[str, Any]:
    """Build a PersonaEval-compatible debrief payload for one Harbor trial."""
    trial_dir = jobs_dir / job_name / trial_name
    if not trial_dir.is_dir():
        raise FileNotFoundError("trial not found")

    output_dir = find_trial_output_dir(trial_dir)
    if output_dir is None:
        raise FileNotFoundError("trial output artifacts not found")

    persona_rel = _persona_path_from_trial(trial_dir, repo_root)
    persona = _load_persona_eval_persona(repo_root, persona_rel)
    created_at = _utc_now()
    result_path = trial_dir / "result.json"
    if result_path.is_file():
        try:
            finished = _read_json(result_path).get("finished_at")
            if isinstance(finished, str) and finished:
                created_at = finished
        except Exception:  # noqa: BLE001
            pass

    app_type = _resolve_application_type(repo_root, trial_dir, output_dir)
    if app_type == "chatbot":
        debrief = _map_chatbot_debrief(
            output_dir=output_dir,
            persona=persona,
            created_at=created_at,
        )
    elif app_type == "survey":
        debrief = _map_survey_debrief(
            output_dir=output_dir,
            persona=persona,
            created_at=created_at,
        )
    elif app_type == "web":
        debrief = _map_web_debrief(
            output_dir=output_dir,
            logs_dir=find_trial_logs_dir(trial_dir),
            persona=persona,
            created_at=created_at,
            job_name=job_name,
            trial_name=trial_name,
            trial_dir=trial_dir,
            repo_root=repo_root,
        )
    elif app_type == "cua":
        debrief = _map_cua_debrief(
            output_dir=output_dir,
            logs_dir=find_trial_logs_dir(trial_dir),
            trial_dir=trial_dir,
            persona=persona,
            created_at=created_at,
            job_name=job_name,
            trial_name=trial_name,
        )
    else:
        artifacts = sorted(path.name for path in output_dir.glob("*") if path.is_file())
        debrief = {
            "id": "harbor-trial",
            "applicationType": "unknown",
            "createdAt": created_at,
            "persona": run_store.persona_summary(persona),
            "artifacts": artifacts,
        }

    debrief["harbor"] = {
        "jobName": job_name,
        "trialName": trial_name,
        "outputDir": str(output_dir.relative_to(repo_root)),
        "personaPath": persona_rel,
    }
    trial_error: str | None = None
    result_path = trial_dir / "result.json"
    if result_path.is_file():
        try:
            trial_error = _trial_result_error(_read_json(result_path))
        except Exception:  # noqa: BLE001
            trial_error = None
    if trial_error:
        debrief["error"] = trial_error
        debrief["status"] = "error"
        if isinstance(debrief.get("harbor"), dict):
            debrief["harbor"]["failed"] = True
    verifier = _verifier_summary(trial_dir)
    if verifier is not None:
        debrief["verifier"] = verifier
    return debrief
