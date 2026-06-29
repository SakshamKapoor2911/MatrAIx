"""Harbor-backed persona-eval helpers.

This module keeps the Harbor-specific artifact contract out of the generic
``PersonaEvalService``. Harbor owns the persona system prompt injection; the
application supplies a task-specific chatbot simulation instruction and then
maps Harbor artifacts back to the existing Studio UI shape.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

import yaml

from backend.service.config import harbor_persona_model
from persona_eval.types import Persona, PersonaEvalConfig

SCORER_PACKAGE_TARGET = "/app/persona_eval"
SCORER_PACKAGE_PARENT = "/app"
SCORER_OUTPUT_PATH = "/logs/verifier/user_feedback.json"


def _path_prefix(parts: Sequence[str], end: int) -> Path:
    return Path(*parts[:end]) if end > 0 else Path(".")


def resolve_repo_root(file_path: Path) -> Path:
    """Resolve the repo/app root for local and containerized layouts."""
    path = Path(file_path).resolve()
    parts = path.parts
    for index in range(len(parts) - 1):
        if parts[index] == "application" and parts[index + 1] == "persona_eval":
            return _path_prefix(parts, index)
        if parts[index] == "applications" and parts[index + 1] == "persona_eval":
            return _path_prefix(parts, index)
    for index in range(len(parts) - 1):
        if parts[index] == "backend" and parts[index + 1] == "service":
            return _path_prefix(parts, index)
    raise ValueError("cannot resolve repo root from {}".format(path))


def _repo_root() -> Path:
    return resolve_repo_root(Path(__file__))


def _default_harbor_runs_root() -> Path:
    return (
        _repo_root()
        / "data"
        / "cache"
        / "persona_eval"
        / "harbor_persona_eval"
    )


def _run_subprocess(command: Sequence[str], *, cwd: Path, env: Dict[str, str]) -> int:
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        env=env,
        check=False,
    ).returncode


def _read_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value
    return values


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_harbor_command() -> Sequence[str]:
    command = os.environ.get("MATRIX_HARBOR_COMMAND") or os.environ.get(
        "HARBOR_COMMAND"
    )
    if command:
        return tuple(shlex.split(command))

    binary = os.environ.get("MATRIX_HARBOR_BIN") or os.environ.get("HARBOR_BIN")
    if binary:
        return (binary, "run")

    found = shutil.which("harbor")
    return (found or "harbor", "run")


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("{} must contain a JSON object".format(path.name))
    return data


def _coerce_score(value: Any, default: int) -> int:
    text = str(value or "").strip().lower()
    if text == "yes":
        return 5
    if text == "partially":
        return 3
    if text == "no":
        return 1
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(5, n))


def _coerce_overall(value: Any, default: int = 5) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(10, n))


def _item_id(item: Dict[str, Any]) -> str:
    return str(item.get("itemId", item.get("id", "")))


def harbor_persona_system_prompt(persona: Persona) -> str:
    """Return the exact system prompt text written into Harbor persona YAML."""
    return persona.context or persona.summary or persona.name


def _prompt_bundle(persona: Persona, task_prompt: str) -> Dict[str, str]:
    return {
        "harborPrompt": harbor_persona_system_prompt(persona),
        "taskPrompt": task_prompt,
    }


def _scorer_mount(repo_root: Path) -> Dict[str, Any]:
    return {
        "type": "bind",
        "source": str(repo_root / "application" / "persona_eval" / "persona_eval"),
        "target": SCORER_PACKAGE_TARGET,
        "read_only": True,
    }


def _file_mount(source: Path, target: str) -> Dict[str, Any]:
    return {
        "type": "bind",
        "source": str(source),
        "target": target,
        "read_only": True,
    }


def _json_env(value: Dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _verifier_env_assignments(
    *, persona: Persona, sut_description: str, config: PersonaEvalConfig
) -> Dict[str, str]:
    return {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "OPENAI_BASE_URL": "${OPENAI_BASE_URL:-https://api.openai.com/v1}",
        "MATRIX_SCORER_PACKAGE_PARENT": SCORER_PACKAGE_PARENT,
        "MATRIX_SCORER_MODULE": "persona_eval.scoring",
        "MATRIX_SCORER_OUTPUT_PATH": SCORER_OUTPUT_PATH,
        "MATRIX_SCORER_PERSONA_JSON": _json_env(persona.to_dict()),
        "MATRIX_SCORER_CONFIG_JSON": _json_env(config.to_dict()),
        "MATRIX_SCORER_SUT_DESCRIPTION": sut_description,
    }


def _verifier_env_args(assignments: Dict[str, str]) -> List[str]:
    args: List[str] = []
    for key, value in assignments.items():
        args.extend(["--verifier-env", "{}={}".format(key, value)])
    return args


def _agent_env_args(assignments: Dict[str, str]) -> List[str]:
    args: List[str] = []
    for key, value in assignments.items():
        args.extend(["--agent-env", "{}={}".format(key, value)])
    return args


def _normalize_prompts(
    prompts: Optional[Dict[str, Any]], *, persona: Persona
) -> Dict[str, str]:
    data = prompts or {}
    return {
        "harborPrompt": str(
            data.get("harborPrompt") or harbor_persona_system_prompt(persona)
        ),
        "taskPrompt": str(data.get("taskPrompt") or ""),
    }


def write_harbor_persona_yaml(base_dir: Path, persona: Persona) -> Path:
    """Write a v0 Harbor persona YAML file for ``persona`` and return its path."""
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "persona.yaml"
    system_prompt = harbor_persona_system_prompt(persona)
    payload = {
        "persona_id": persona.id,
        "display_name": persona.name,
        "summary": persona.summary,
        "system_prompt": system_prompt,
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def build_recommender_simulation_prompt(
    *,
    domain: str,
    max_turns: int,
    sut_description: str,
    goal_context_description: str,
) -> str:
    """Build the application-owned task prompt appended to Harbor instruction."""
    return """You are a user of a {domain} recommendation system.

{sut_description}

Context for this interaction: {goal_context_description}

Based on your assigned persona, silently decide what kind of {domain} items you
realistically want and which constraints or preferences matter to you. Start the
conversation naturally. Do not reveal everything at once. Let the system ask
follow-up questions, answer in character, and give feedback when
recommendations do not fit. Continue until you can judge whether the
recommendations satisfy your need.

""".format(
        domain=domain,
        sut_description=sut_description,
        goal_context_description=goal_context_description,
    )


def build_chatbot_simulation_prompt(
    *,
    application_id: str,
    application_context: str,
    max_turns: int,
    sut_description: str,
    goal_context_description: str,
) -> str:
    """Build the application-owned generic chatbot task prompt."""
    system_label = _chatbot_system_label(
        application_id=application_id,
        application_context=application_context,
    )
    return """You are a user of a {system_label}.

{sut_description}

Context for this interaction: {goal_context_description}

Based on your assigned persona, silently decide what you realistically want from
this system and which constraints or preferences matter to you. Start the
conversation naturally. Do not reveal everything at once. Let the system ask
follow-up questions, answer in character, and give feedback when a response does
not fit. Continue until you can judge whether the system satisfied your need.

""".format(
        system_label=system_label,
        sut_description=sut_description,
        goal_context_description=goal_context_description,
    )


def _chatbot_system_label(*, application_id: str, application_context: str) -> str:
    context = application_context.replace("_", " ").strip() or "chatbot"
    if application_id == "recai":
        return "{} recommendation system".format(context)
    if application_id == "finance_openbb":
        return "financial research system"
    if application_id == "medical_assistant":
        return "medical assistant"
    return "{} system".format(context)


class HarborPersonaEvalRunner:
    """Callable runner that executes a Harbor persona-agent job."""

    def __init__(
        self,
        *,
        repo_root: Optional[Path] = None,
        runs_root: Optional[Path] = None,
        command_runner: Callable[[Sequence[str]], int] = _run_subprocess,
        harbor_command: Optional[Sequence[str]] = None,
        goal_context_description_for: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else _repo_root()
        self.runs_root = (
            Path(runs_root) if runs_root is not None else _default_harbor_runs_root()
        )
        self.command_runner = command_runner
        self.harbor_command = tuple(harbor_command or _default_harbor_command())
        self.goal_context_description_for = goal_context_description_for or (
            lambda goal_context_id: goal_context_id
        )

    def __call__(
        self,
        session: Any,
        persona: Persona,
        sut_description: str,
        config: PersonaEvalConfig,
        _simulator: Any,
        *,
        created_at: str,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> HarborPersonaEvalResult:
        def emit(event: Dict[str, Any]) -> None:
            if on_event is not None:
                on_event(event)

        job_name = "persona-eval-{}".format(uuid.uuid4().hex[:12])
        run_dir = self.runs_root / job_name / "_inputs"
        run_dir.mkdir(parents=True, exist_ok=True)
        persona_path = write_harbor_persona_yaml(run_dir, persona)
        task_prompt_path = run_dir / "task_prompt.md"
        application_context = config.application_context or config.domain
        task_prompt = build_chatbot_simulation_prompt(
            application_id=config.application_id,
            application_context=application_context,
            max_turns=config.max_turns,
            sut_description=sut_description,
            goal_context_description=self.goal_context_description_for(
                config.goal_context_id
            ),
        )
        task_prompt_path.write_text(task_prompt, encoding="utf-8")
        prompts = _prompt_bundle(persona, task_prompt)

        job_config_path = run_dir / "harbor_job.yaml"
        job_config = {
            "job_name": job_name,
            "jobs_dir": str(self.runs_root),
            "n_attempts": 1,
            "timeout_multiplier": 1.0,
            "n_concurrent_trials": 1,
            "quiet": False,
            "environment": {
                "type": "docker",
                "delete": _env_bool("MATRIX_HARBOR_DELETE", False),
                "force_build": _env_bool("MATRIX_HARBOR_FORCE_BUILD", False),
                "mounts": [
                    _scorer_mount(self.repo_root),
                    _file_mount(task_prompt_path, "/app/input/task_prompt.md"),
                ],
            },
            "agents": [
                {
                    "name": "persona-claude-code",
                    "model_name": config.persona_model or harbor_persona_model(),
                    "kwargs": {"persona_path": str(persona_path)},
                }
            ],
            "tasks": [
                {
                    "path": str(
                        self.repo_root
                        / "application"
                        / "tasks"
                        / "recommender-agent_chat_api"
                    )
                }
            ],
            "extra_instruction_paths": [str(task_prompt_path)],
        }
        job_config_path.write_text(
            yaml.safe_dump(job_config, sort_keys=False),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env_file = self.repo_root / ".env.local"
        for key, value in _read_env_file(env_file).items():
            env.setdefault(key, value)
        env["INTERECAGENT_ENGINE"] = config.engine
        env["RECBOT_READY_DOMAIN"] = config.domain
        env["MATRIX_CHATBOT_APPLICATION_ID"] = config.application_id
        env["MATRIX_CHATBOT_APPLICATION_CONTEXT"] = application_context
        if config.application_id == "finance_openbb":
            env["COMPOSE_PROFILES"] = "finance"
            env.setdefault("FINANCE_AGENT_MODEL", config.engine)
        elif config.application_id == "medical_assistant":
            env["COMPOSE_PROFILES"] = "medical"
        else:
            env["COMPOSE_PROFILES"] = "recai"
        project_env = Path("/tmp/matraix-harbor-project-venv")
        if project_env.exists():
            env.setdefault("UV_PROJECT_ENVIRONMENT", str(project_env))
        command = [
            *self.harbor_command,
            "-c",
            str(job_config_path),
            "--agent-env",
            "CLAUDE_CODE_TMPDIR=/logs/agent/claude-tmp",
            *_agent_env_args(
                {
                    "MATRIX_CHATBOT_APPLICATION_ID": config.application_id,
                    "MATRIX_CHATBOT_APPLICATION_CONTEXT": application_context,
                    "MATRIX_CHATBOT_DOMAIN": config.domain,
                    "MATRIX_CHATBOT_MAX_TURNS": str(config.max_turns),
                    "MATRIX_CHATBOT_MIN_TURNS": str(min(3, config.max_turns)),
                    "MATRIX_CHATBOT_TASK_PROMPT_PATH": "/app/input/task_prompt.md",
                    "MATRIX_CHATBOT_PERSONA_PATH": "/app/input/persona.yaml",
                    "MATRIX_CHATBOT_OUTPUT_DIR": "/app/output",
                    "MATRIX_CHATBOT_API_URL": "http://chatbot-api:8000",
                    "MATRIX_CHATBOT_PERSONA_MODEL": config.persona_model
                    or harbor_persona_model(),
                }
            ),
            "-y",
        ]
        if env_file.is_file():
            command.extend(["--env-file", str(env_file)])

        emit({"type": "prompts", "prompts": dict(prompts)})
        emit({"type": "phase", "phase": "harbor_starting"})
        code = self.command_runner(command, cwd=self.repo_root, env=env)
        if code != 0:
            raise RuntimeError("Harbor run failed with exit code {}".format(code))

        emit({"type": "phase", "phase": "harbor_collecting_artifacts"})
        output_dir = self._find_output_dir(job_name)
        result = build_result_from_harbor_artifacts(
            output_dir=output_dir,
            config=config,
            persona=persona,
            sut_description=sut_description,
            created_at=created_at,
            prompts=prompts,
        )
        session.turns = list(result.turn_views)
        return result

    def _find_output_dir(self, job_name: str) -> Path:
        job_dir = self.runs_root / job_name
        matches = sorted(job_dir.glob("*/artifacts/app/output"))
        if not matches:
            matches = sorted(job_dir.rglob("artifacts/app/output"))
        if not matches:
            failure = _harbor_failure_summary(job_dir)
            if failure:
                raise RuntimeError(
                    "Harbor run did not produce output artifacts: {}".format(failure)
                )
            raise FileNotFoundError(
                "Harbor output artifacts not found under {}".format(job_dir)
            )
        output_dir = matches[0]
        missing = _missing_required_output_artifacts(output_dir)
        if missing:
            failure = _harbor_failure_summary(job_dir)
            detail = failure or "missing required artifacts: {}".format(
                ", ".join(missing)
            )
            raise RuntimeError(
                "Harbor run did not produce required artifacts ({}): {}".format(
                    ", ".join(missing), detail
                )
            )
        return output_dir


def _missing_required_output_artifacts(output_dir: Path) -> List[str]:
    missing: List[str] = []
    if not (output_dir / "transcript.json").is_file():
        missing.append("transcript.json")
    if not _application_result_path(output_dir).is_file():
        missing.append("application_result.json")
    return missing


def _application_result_path(output_dir: Path) -> Path:
    generic = output_dir / "application_result.json"
    if generic.is_file():
        return generic
    return output_dir / "recommendation_result.json"


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _content_text(value.get("content"))
    if isinstance(value, list):
        parts = []
        for entry in value:
            if isinstance(entry, dict):
                text = entry.get("text", entry.get("content"))
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            elif isinstance(entry, str) and entry.strip():
                parts.append(entry.strip())
        return " ".join(parts)
    return ""


def _compact_log_text(value: str, *, max_chars: int = 1000) -> str:
    return " ".join(str(value or "").split())[:max_chars]


def _message_contains_error(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    content = value.get("content")
    if not isinstance(content, list):
        return False
    return any(isinstance(entry, dict) and bool(entry.get("is_error")) for entry in content)


def _agent_error_summary(job_dir: Path) -> str:
    for path in sorted(job_dir.glob("*/agent/claude-code.txt")):
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            tool_result = event.get("tool_use_result")
            if isinstance(tool_result, str) and (
                "Error:" in tool_result or "Exit code" in tool_result
            ):
                return "Agent failed: {}".format(_compact_log_text(tool_result))
            error = event.get("error")
            status = event.get("api_error_status")
            message_has_error = _message_contains_error(event.get("message"))
            if not (event.get("is_error") or error or status or message_has_error):
                continue
            result = event.get("result")
            message = _content_text(event.get("message"))
            text = str(result or message or error or "").strip()
            if not text:
                continue
            meta = []
            if error:
                meta.append(str(error))
            if status:
                meta.append("status {}".format(status))
            return "Agent failed: {}{}".format(
                _compact_log_text(text),
                " ({})".format(", ".join(meta)) if meta else "",
            )
    return ""


def _harbor_failure_summary(job_dir: Path) -> str:
    agent_error = _agent_error_summary(job_dir)
    if agent_error:
        return agent_error

    for path in sorted(job_dir.glob("*/exception.txt")):
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            return " ".join(text.split())[:1000]

    result_path = job_dir / "result.json"
    if not result_path.is_file():
        return ""
    try:
        result = _read_json(result_path)
    except Exception:
        return ""
    stats = result.get("stats") or {}
    errored = stats.get("n_errored_trials")
    if errored:
        details: List[str] = []
        evals = stats.get("evals") or {}
        if isinstance(evals, dict):
            for value in evals.values():
                if not isinstance(value, dict):
                    continue
                exception_stats = value.get("exception_stats") or {}
                if isinstance(exception_stats, dict):
                    for exc_type, trials in exception_stats.items():
                        details.append("{}: {}".format(exc_type, trials))
        suffix = "; ".join(details[:3])
        return "n_errored_trials={}".format(errored) + (
            "; {}".format(suffix) if suffix else ""
        )
    return ""


def _build_turns_from_messages(transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
    messages = transcript.get("messages") or []
    if not isinstance(messages, list):
        return []

    turns: List[Dict[str, Any]] = []
    pending_user: Optional[str] = None
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = str(message.get("content") or "")
        if role == "user":
            pending_user = content
        elif role == "assistant" and pending_user is not None:
            index = len(turns)
            turns.append(
                {
                    "turnId": str(index),
                    "conversationId": transcript.get("sessionId"),
                    "backend": "interecagent",
                    "userMessage": pending_user,
                    "assistantMessage": content,
                    "plan": [],
                    "recommendedItems": [],
                    "groundedItems": [],
                    "nativeRaw": None,
                    "rawToolOutputs": None,
                }
            )
            pending_user = None
    return turns


def _turn_views(transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
    turns = transcript.get("turns")
    if isinstance(turns, list) and all(isinstance(t, dict) for t in turns):
        return [dict(t) for t in turns]
    return _build_turns_from_messages(transcript)


def _questionnaire(feedback: Dict[str, Any]) -> Dict[str, Any]:
    if "constraintSatisfaction" in feedback or "overallRating" in feedback:
        return {
            "constraintSatisfaction": _coerce_score(
                feedback.get("constraintSatisfaction"), 3
            ),
            "constraintRationale": str(feedback.get("constraintRationale") or ""),
            "preferenceSatisfaction": _coerce_score(
                feedback.get("preferenceSatisfaction"), 3
            ),
            "preferenceRationale": str(feedback.get("preferenceRationale") or ""),
            "overallRating": _coerce_overall(feedback.get("overallRating")),
            "ratingReason": str(feedback.get("ratingReason") or ""),
            "askedUsefulClarifyingQuestions": bool(
                feedback.get("askedUsefulClarifyingQuestions", False)
            ),
            "clarifyingNotes": str(feedback.get("clarifyingNotes") or ""),
        }

    reason = str(feedback.get("reason") or "")
    return {
        "constraintSatisfaction": _coerce_score(
            feedback.get(
                "productNeedSatisfaction",
                feedback.get("productNeedConstraintSatisfaction"),
            ),
            3,
        ),
        "constraintRationale": reason,
        "preferenceSatisfaction": _coerce_score(
            feedback.get("personalPreferenceSatisfaction"), 3
        ),
        "preferenceRationale": reason,
        "overallRating": _coerce_overall(feedback.get("overallExperienceRating")),
        "ratingReason": reason,
        "askedUsefulClarifyingQuestions": bool(
            feedback.get("askedUsefulClarificationQuestions", False)
        ),
        "clarifyingNotes": reason,
    }


def _feedback_path(output_dir: Path) -> Optional[Path]:
    app_feedback = output_dir / "user_feedback.json"
    if app_feedback.is_file():
        return app_feedback
    try:
        verifier_feedback = output_dir.parents[2] / "verifier" / "user_feedback.json"
    except IndexError:
        return None
    return verifier_feedback if verifier_feedback.is_file() else None


def _recommended_ids_per_turn(turn_views: List[Dict[str, Any]]) -> List[List[str]]:
    per_turn: List[List[str]] = []
    for turn in turn_views:
        items = turn.get("groundedItems") or turn.get("recommendedItems") or []
        if not isinstance(items, list):
            per_turn.append([])
            continue
        per_turn.append(
            [
                _item_id(item)
                for item in items
                if isinstance(item, dict) and _item_id(item)
            ]
        )
    return per_turn


def _normalize_recommended_items(value: Any) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("application_result.groundedItems must be a list")
    items: List[Dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(
                "application_result.groundedItems[{}] must be an object".format(
                    index
                )
            )
        item_id = _item_id(item).strip()
        if not item_id:
            raise ValueError(
                "application_result.groundedItems[{}].itemId is required".format(
                    index
                )
            )
        items.append({**item, "itemId": item_id})
    return items


def _grounded_item_ids(turn_views: List[Dict[str, Any]]) -> Set[str]:
    ids: Set[str] = set()
    for turn in turn_views:
        items = turn.get("groundedItems") or turn.get("recommendedItems") or []
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                item_id = _item_id(item).strip()
                if item_id:
                    ids.add(item_id)
    return ids


def _validate_recommendation_grounding(
    *, turn_views: List[Dict[str, Any]], recommended_items: List[Dict[str, Any]]
) -> None:
    grounded_ids = _grounded_item_ids(turn_views)
    missing = [
        item["itemId"]
        for item in recommended_items
        if item["itemId"] not in grounded_ids
    ]
    if missing:
        raise ValueError(
            "application_result.groundedItems must be grounded in "
            "transcript.turns groundedItems/recommendedItems; missing ids: {}".format(
                ", ".join(missing[:5])
            )
        )


@dataclass
class HarborPersonaEvalResult:
    config: PersonaEvalConfig
    persona: Persona
    sut_description: str
    turn_views: List[Dict[str, Any]]
    recommended_items: List[Dict[str, Any]]
    questionnaire: Dict[str, Any]
    metric_scores: Dict[str, Any]
    created_at: str
    prompts: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        per_turn = _recommended_ids_per_turn(self.turn_views)
        final = next((ids for ids in reversed(per_turn) if ids), [])
        return {
            "config": self.config.to_dict(),
            "persona": self.persona.to_dict(),
            "sutDescription": self.sut_description,
            "transcript": [dict(t) for t in self.turn_views],
            "recommendedItemIds": {"perTurn": per_turn, "final": final},
            "questionnaire": dict(self.questionnaire),
            "metricScores": dict(self.metric_scores),
            "createdAt": self.created_at,
            "prompts": dict(self.prompts),
        }


def build_result_from_harbor_artifacts(
    *,
    output_dir: Path,
    config: PersonaEvalConfig,
    persona: Persona,
    sut_description: str,
    created_at: str,
    prompts: Optional[Dict[str, Any]] = None,
) -> HarborPersonaEvalResult:
    """Map Harbor task artifacts into the existing PersonaEval UI result."""
    transcript = _read_json(output_dir / "transcript.json")
    recommendation = _read_json(_application_result_path(output_dir))
    feedback_path = _feedback_path(output_dir)
    feedback = _read_json(feedback_path) if feedback_path is not None else {}

    turn_views = _turn_views(transcript)
    recommended_items = _normalize_recommended_items(
        recommendation.get("groundedItems", recommendation.get("recommendedItems"))
    )
    _validate_recommendation_grounding(
        turn_views=turn_views, recommended_items=recommended_items
    )

    metric_scores = {
        "turnsToRecommendation": recommendation.get(
            "turnsToRecommendation", recommendation.get("turnsToResult")
        ),
        "numTurns": len(turn_views),
        "recommendedItemCount": len(recommended_items),
    }
    return HarborPersonaEvalResult(
        config=config,
        persona=persona,
        sut_description=sut_description,
        turn_views=turn_views,
        recommended_items=recommended_items,
        questionnaire=_questionnaire(feedback),
        metric_scores=metric_scores,
        created_at=created_at,
        prompts=_normalize_prompts(prompts, persona=persona),
    )
