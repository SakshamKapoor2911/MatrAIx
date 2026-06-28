"""Harbor-backed persona survey helpers.

This module runs a structured survey through Harbor's native Persona model API.
Harbor owns persona prompt injection through ``persona-claude-code`` and the
application contributes only the survey task prompt plus artifact mapping.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import yaml

from backend.service.config import harbor_persona_model
from backend.service.harbor_persona_eval import (
    _default_harbor_command,
    _env_bool,
    _harbor_failure_summary,
    _read_env_file,
    _repo_root,
    _run_subprocess,
    harbor_persona_system_prompt,
    write_harbor_persona_yaml,
)
from persona_eval.types import DEFAULT_PERSONA_MODEL, Persona

QUESTION_TYPES = {"likert", "single_choice", "multi_choice", "free_text"}


def _default_harbor_survey_runs_root() -> Path:
    return (
        _repo_root()
        / "data"
        / "cache"
        / "persona_eval"
        / "harbor_survey_eval"
    )


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("{} must contain a JSON object".format(path.name))
    return data


def _json_dump(value: Dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


@dataclass
class SurveyQuestion:
    id: str
    prompt: str
    type: str = "likert"
    options: List[str] = field(default_factory=list)
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    construct: str = ""
    required: bool = True

    def __post_init__(self) -> None:
        if self.type not in QUESTION_TYPES:
            raise ValueError(
                "question type must be one of {}".format(sorted(QUESTION_TYPES))
            )
        if self.type == "likert":
            if self.min_value is None:
                self.min_value = 1
            else:
                self.min_value = int(self.min_value)
            if self.max_value is None:
                self.max_value = 5
            else:
                self.max_value = int(self.max_value)
            if self.min_value >= self.max_value:
                raise ValueError("likert min_value must be less than max_value")
        if self.type in {"single_choice", "multi_choice"} and not self.options:
            raise ValueError("{} questions require options".format(self.type))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurveyQuestion":
        return cls(
            id=str(data["id"]),
            prompt=str(data["prompt"]),
            type=str(data.get("type", "likert")),
            options=[str(option) for option in data.get("options", [])],
            min_value=data.get("minValue", data.get("min_value")),
            max_value=data.get("maxValue", data.get("max_value")),
            construct=str(data.get("construct", "")),
            required=bool(data.get("required", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "type": self.type,
            "options": list(self.options),
            "minValue": self.min_value,
            "maxValue": self.max_value,
            "construct": self.construct,
            "required": self.required,
        }


@dataclass
class SurveyInstrument:
    id: str
    title: str
    description: str = ""
    questions: List[SurveyQuestion] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurveyInstrument":
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data.get("description", "")),
            questions=[SurveyQuestion.from_dict(q) for q in data.get("questions", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "questions": [question.to_dict() for question in self.questions],
        }


@dataclass
class HarborSurveyEvalConfig:
    persona_model: str = DEFAULT_PERSONA_MODEL
    mode: str = "harbor_persona_survey"
    require_rationale: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "personaModel": self.persona_model,
            "mode": self.mode,
            "requireRationale": self.require_rationale,
        }


@dataclass
class SurveyAnswer:
    question_id: str
    value: Any
    rationale: str = ""
    confidence: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurveyAnswer":
        question_id = str(data.get("questionId", data.get("question_id", ""))).strip()
        if not question_id:
            raise ValueError("answer.questionId is required")
        confidence = data.get("confidence")
        if confidence is not None:
            try:
                confidence = max(0.0, min(1.0, float(confidence)))
            except (TypeError, ValueError):
                confidence = None
        return cls(
            question_id=question_id,
            value=data.get("value"),
            rationale=str(data.get("rationale", "")),
            confidence=confidence,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "questionId": self.question_id,
            "value": self.value,
            "rationale": self.rationale,
            "confidence": self.confidence,
        }


@dataclass
class TrajectoryEvent:
    timestamp: str
    actor: str
    action: str
    context: Dict[str, Any] = field(default_factory=dict)
    outcome: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrajectoryEvent":
        missing = [
            key
            for key in ("timestamp", "actor", "action", "context", "outcome")
            if key not in data
        ]
        if missing:
            raise ValueError(
                "trajectory event missing required keys: {}".format(
                    ", ".join(missing)
                )
            )
        context = data.get("context")
        outcome = data.get("outcome")
        if not isinstance(context, dict):
            raise ValueError("trajectory event context must be an object")
        if not isinstance(outcome, dict):
            raise ValueError("trajectory event outcome must be an object")
        actor = str(data.get("actor") or "").strip()
        action = str(data.get("action") or "").strip()
        timestamp = str(data.get("timestamp") or "").strip()
        if not actor or not action or not timestamp:
            raise ValueError("trajectory event timestamp, actor, and action are required")
        return cls(
            timestamp=timestamp,
            actor=actor,
            action=action,
            context=dict(context),
            outcome=dict(outcome),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "context": dict(self.context),
            "outcome": dict(self.outcome),
        }


@dataclass
class SurveyMetrics:
    num_questions: int
    num_answered: int
    mean_likert: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "numQuestions": self.num_questions,
            "numAnswered": self.num_answered,
            "meanLikert": self.mean_likert,
        }


@dataclass
class HarborSurveyEvalResult:
    config: HarborSurveyEvalConfig
    persona: Persona
    instrument: SurveyInstrument
    answers: List[SurveyAnswer]
    trajectory: List[TrajectoryEvent]
    metrics: SurveyMetrics
    created_at: str
    prompts: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "persona": self.persona.to_dict(),
            "instrument": self.instrument.to_dict(),
            "trajectory": [event.to_dict() for event in self.trajectory],
            "answers": [answer.to_dict() for answer in self.answers],
            "metrics": self.metrics.to_dict(),
            "createdAt": self.created_at,
            "prompts": dict(self.prompts),
        }


def _prompt_bundle(persona: Persona, task_prompt: str) -> Dict[str, str]:
    return {
        "harborPrompt": harbor_persona_system_prompt(persona),
        "taskPrompt": task_prompt,
    }


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


def build_survey_task_prompt(
    *, instrument: SurveyInstrument, require_rationale: bool = True
) -> str:
    """Build the application-owned survey prompt appended to Harbor instruction."""
    rationale_line = (
        "Every answer must include a concise persona-grounded rationale."
        if require_rationale
        else "Rationales are optional, but include them when they clarify the answer."
    )
    instrument_json = _json_dump(instrument.to_dict())
    return "\n".join(
        [
            "# Application task prompt: persona survey",
            "",
            "Harbor supplies the persona system prompt through the Persona model API.",
            "Use that persona as the respondent identity, values, constraints,",
            "communication style, and decision-making style. This application",
            "supplies only the survey instrument and artifact contract.",
            "",
            "Do not use a separate persona simulator or a second persona layer. Do",
            "not call another LLM to answer on behalf of the persona. Answer directly",
            "as the Harbor-injected persona.",
            "",
            "Product concept being evaluated:",
            "",
            "PersonaEval is a system for evaluating interactive applications with",
            "simulated users who have predefined persona attributes. A team can",
            "connect a task-specific survey or application prompt, run the persona",
            "agent inside a sandboxed task environment, and collect structured",
            "response artifacts for product and research analysis.",
            "",
            "Survey instrument:",
            "",
            "```json",
            instrument_json,
            "```",
            "",
            "Write exactly one valid JSON object to `/app/output/survey_result.json`.",
            "",
            "Required top-level schema:",
            "",
            "```json",
            "{",
            '  "instrument": {"id": "<instrument id>", "title": "<title>"},',
            '  "answers": [',
            "    {",
            '      "questionId": "<question id>",',
            '      "value": "<likert number, choice string/list, or free text>",',
            '      "rationale": "<short persona-grounded reason>",',
            '      "confidence": 0.0',
            "    }",
            "  ],",
            '  "trajectory": [',
            "    {",
            '      "timestamp": "2026-06-24T00:00:00Z",',
            '      "actor": "user",',
            '      "action": "answer_question",',
            '      "context": {"questionId": "<question id>"},',
            '      "outcome": {"questionId": "<question id>", "value": 4}',
            "    }",
            "  ]",
            "}",
            "```",
            "",
            "Answer requirements:",
            "- Include one answer for every required question.",
            "- For `likert`, use a number within `minValue` and `maxValue`.",
            "- For `single_choice`, use exactly one string from `options`.",
            "- For `multi_choice`, use a list of strings from `options`.",
            "- For `free_text`, use a short respondent-style text answer.",
            "- Use `construct` labels as construct-level metadata in trajectory",
            "  context; do not convert raw questionnaire wording into persona",
            "  attribute labels.",
            "- {}".format(rationale_line),
            "",
            "Trajectory requirements:",
            "- The core trajectory is actions/messages plus timestamps and outcomes.",
            "- Every trajectory event must include exactly these structural keys:",
            "  `timestamp`, `actor`, `action`, `context`, and `outcome`.",
            "- Use ISO-8601 UTC timestamps.",
            "- Include a `system` / `survey_started` event, an `assistant` /",
            "  `ask_question` event and a `user` / `answer_question` event for each",
            "  survey question, and a final `system` / `survey_completed` event.",
            "- Keep `context` and `outcome` as JSON objects, never strings.",
        ]
    )


def _coerce_likert(question: SurveyQuestion, value: Any) -> Any:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(
            "answer {} must be numeric for likert question".format(question.id)
        )
    if number < float(question.min_value) or number > float(question.max_value):
        raise ValueError(
            "answer {} must be between {} and {}".format(
                question.id, question.min_value, question.max_value
            )
        )
    return int(number) if number.is_integer() else number


def _normalize_answer(question: SurveyQuestion, data: Dict[str, Any]) -> SurveyAnswer:
    answer = SurveyAnswer.from_dict(data)
    if answer.question_id != question.id:
        raise ValueError(
            "answer questionId mismatch: expected {}, got {}".format(
                question.id, answer.question_id
            )
        )
    if question.type == "likert":
        answer.value = _coerce_likert(question, answer.value)
    elif question.type == "single_choice":
        value = str(answer.value)
        if value not in question.options:
            raise ValueError(
                "answer {} must be one of {}".format(
                    question.id, ", ".join(question.options)
                )
            )
        answer.value = value
    elif question.type == "multi_choice":
        if not isinstance(answer.value, list):
            raise ValueError("answer {} must be a list".format(question.id))
        values = [str(value) for value in answer.value]
        invalid = [value for value in values if value not in question.options]
        if invalid:
            raise ValueError(
                "answer {} includes invalid choices: {}".format(
                    question.id, ", ".join(invalid)
                )
            )
        answer.value = values
    else:
        answer.value = str(answer.value or "")
        if question.required and not answer.value.strip():
            raise ValueError("answer {} must not be empty".format(question.id))
    return answer


def _normalize_answers(
    instrument: SurveyInstrument, raw_answers: Any
) -> List[SurveyAnswer]:
    if not isinstance(raw_answers, list):
        raise ValueError("survey_result.answers must be a list")
    question_by_id = {question.id: question for question in instrument.questions}
    answers: List[SurveyAnswer] = []
    seen = set()
    for index, raw in enumerate(raw_answers):
        if not isinstance(raw, dict):
            raise ValueError("survey_result.answers[{}] must be an object".format(index))
        question_id = str(raw.get("questionId", raw.get("question_id", ""))).strip()
        if question_id not in question_by_id:
            raise ValueError("unknown answer questionId: {}".format(question_id))
        if question_id in seen:
            raise ValueError("duplicate answer questionId: {}".format(question_id))
        seen.add(question_id)
        answers.append(_normalize_answer(question_by_id[question_id], raw))
    missing = [
        question.id
        for question in instrument.questions
        if question.required and question.id not in seen
    ]
    if missing:
        raise ValueError(
            "survey_result.answers missing required question ids: {}".format(
                ", ".join(missing)
            )
        )
    return answers


def _normalize_trajectory(raw_trajectory: Any) -> List[TrajectoryEvent]:
    if not isinstance(raw_trajectory, list) or not raw_trajectory:
        raise ValueError("survey_result.trajectory must be a non-empty list")
    events: List[TrajectoryEvent] = []
    for index, raw in enumerate(raw_trajectory):
        if not isinstance(raw, dict):
            raise ValueError(
                "survey_result.trajectory[{}] must be an object".format(index)
            )
        events.append(TrajectoryEvent.from_dict(raw))
    return events


def _metrics(instrument: SurveyInstrument, answers: List[SurveyAnswer]) -> SurveyMetrics:
    question_by_id = {question.id: question for question in instrument.questions}
    likert_values: List[float] = []
    for answer in answers:
        question = question_by_id.get(answer.question_id)
        if question is None or question.type != "likert":
            continue
        try:
            likert_values.append(float(answer.value))
        except (TypeError, ValueError):
            continue
    mean = sum(likert_values) / len(likert_values) if likert_values else None
    return SurveyMetrics(
        num_questions=len(instrument.questions),
        num_answered=len(answers),
        mean_likert=mean,
    )


def build_result_from_harbor_survey_artifacts(
    *,
    output_dir: Path,
    config: HarborSurveyEvalConfig,
    persona: Persona,
    instrument: SurveyInstrument,
    created_at: str,
    prompts: Optional[Dict[str, Any]] = None,
) -> HarborSurveyEvalResult:
    """Map Harbor survey artifacts into an auditable survey result."""
    payload = _read_json(output_dir / "survey_result.json")
    artifact_instrument = payload.get("instrument")
    if isinstance(artifact_instrument, dict):
        artifact_id = str(artifact_instrument.get("id", ""))
        if artifact_id and artifact_id != instrument.id:
            raise ValueError(
                "survey_result.instrument.id mismatch: expected {}, got {}".format(
                    instrument.id, artifact_id
                )
            )
    answers = _normalize_answers(instrument, payload.get("answers"))
    trajectory = _normalize_trajectory(payload.get("trajectory"))
    return HarborSurveyEvalResult(
        config=config,
        persona=persona,
        instrument=instrument,
        answers=answers,
        trajectory=trajectory,
        metrics=_metrics(instrument, answers),
        created_at=created_at,
        prompts=_normalize_prompts(prompts, persona=persona),
    )


def _missing_required_output_artifacts(output_dir: Path) -> List[str]:
    return [
        name
        for name in ("survey_result.json",)
        if not (output_dir / name).is_file()
    ]


class HarborSurveyEvalRunner:
    """Callable runner that executes a Harbor persona-agent survey job."""

    def __init__(
        self,
        *,
        repo_root: Optional[Path] = None,
        runs_root: Optional[Path] = None,
        command_runner: Callable[..., int] = _run_subprocess,
        harbor_command: Optional[Sequence[str]] = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else _repo_root()
        self.runs_root = (
            Path(runs_root)
            if runs_root is not None
            else _default_harbor_survey_runs_root()
        )
        self.command_runner = command_runner
        self.harbor_command = tuple(harbor_command or _default_harbor_command())

    def __call__(
        self,
        persona: Persona,
        instrument: SurveyInstrument,
        config: Optional[HarborSurveyEvalConfig] = None,
        *,
        created_at: str,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> HarborSurveyEvalResult:
        config = config or HarborSurveyEvalConfig()

        def emit(event: Dict[str, Any]) -> None:
            if on_event is not None:
                on_event(event)

        job_name = "survey-form-{}".format(uuid.uuid4().hex[:12])
        run_dir = self.runs_root / job_name / "_inputs"
        run_dir.mkdir(parents=True, exist_ok=True)
        persona_path = write_harbor_persona_yaml(run_dir, persona)
        instrument_path = run_dir / "survey_instrument.json"
        instrument_path.write_text(
            _json_dump(instrument.to_dict()),
            encoding="utf-8",
        )

        task_prompt = build_survey_task_prompt(
            instrument=instrument,
            require_rationale=config.require_rationale,
        )
        task_prompt_path = run_dir / "task_prompt.md"
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
                        self.repo_root / "application" / "tasks" / "persona-survey"
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
        env["MATRIX_SURVEY_INSTRUMENT_ID"] = instrument.id
        project_env = Path("/tmp/matraix-harbor-project-venv")
        if project_env.exists():
            env.setdefault("UV_PROJECT_ENVIRONMENT", str(project_env))
        command = [
            *self.harbor_command,
            "-c",
            str(job_config_path),
            "--agent-env",
            "CLAUDE_CODE_TMPDIR=/logs/agent/claude-tmp",
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
        result = build_result_from_harbor_survey_artifacts(
            output_dir=output_dir,
            config=config,
            persona=persona,
            instrument=instrument,
            created_at=created_at,
            prompts=prompts,
        )
        emit({"type": "done", "result": result.to_dict()})
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
                "Harbor survey run did not produce required artifacts ({}): {}".format(
                    ", ".join(missing), detail
                )
            )
        return output_dir
