from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.service.survey_instruction_builder import (
    render_survey_context_markdown,
    render_survey_output_schema_markdown,
    render_survey_questionnaire_markdown,
    render_survey_task_instruction_markdown,
)
from backend.service.survey_types import (
    SurveyAnswer,
    SurveyEvalConfig,
    SurveyEvalResult,
    SurveyInstrument,
    SurveyMetrics,
    SurveyQuestion,
    SurveyTaskContent,
    TrajectoryEvent,
)
from persona_eval.model_client import build_json_client
from persona_eval.types import Persona


def persona_system_prompt(persona: Persona) -> str:
    parts = [
        "You are a simulated user with predefined persona attributes.",
        "Stay in character as this user throughout the task.",
        "",
        "Persona:",
        persona.context or persona.summary or persona.name,
    ]
    if persona.preferences:
        parts.append("Preferences: {}".format(", ".join(persona.preferences)))
    if persona.dislikes:
        parts.append("Dislikes: {}".format(", ".join(persona.dislikes)))
    if persona.constraints:
        parts.append("Constraints: {}".format(", ".join(persona.constraints)))
    if persona.communication_style:
        parts.append("Communication style: {}".format(persona.communication_style))
    return "\n".join(parts)


def build_survey_task_prompt(
    *, instrument: SurveyInstrument, require_rationale: bool = True
) -> str:
    from persona_eval.harbor.persona_eval import _repo_root
    from persona_eval.survey_task_content import (
        load_survey_task_content_for_questionnaire_id,
    )

    task_content = load_survey_task_content_for_questionnaire_id(
        instrument.id,
        repo_root=_repo_root(),
        fallback_questionnaire=instrument,
    )
    if task_content is None:
        task_content = SurveyTaskContent(
            title=instrument.title,
            instruction_markdown=render_survey_task_instruction_markdown(instrument).strip(),
            context_markdown=render_survey_context_markdown(instrument).strip(),
            questionnaire_markdown=render_survey_questionnaire_markdown(instrument).strip(),
            output_schema_markdown=render_survey_output_schema_markdown(instrument).strip(),
            instrument=instrument,
        )
    lines: list[str] = []
    if task_content.instruction_markdown.strip():
        lines.extend(["## Task instruction", "", task_content.instruction_markdown.strip(), ""])
    if task_content.context_markdown.strip():
        lines.extend(["## Context", "", task_content.context_markdown.strip(), ""])
    if task_content.questionnaire_markdown.strip():
        lines.extend(["## Questionnaire", "", task_content.questionnaire_markdown.strip(), ""])
    if task_content.output_schema_markdown.strip():
        lines.extend(["## Output schema", "", task_content.output_schema_markdown.strip(), ""])
    return "\n".join(lines).strip()


class InprocessSurveyEvalRunner:
    """Run survey completion through the configured persona model."""

    def __call__(
        self,
        persona: Persona,
        instrument: SurveyInstrument,
        config: Optional[SurveyEvalConfig] = None,
        *,
        created_at: str,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> SurveyEvalResult:
        config = config or SurveyEvalConfig()

        def emit(event: Dict[str, Any]) -> None:
            if on_event is not None:
                on_event(event)

        task_prompt = build_survey_task_prompt(
            instrument=instrument,
            require_rationale=config.require_rationale,
        )
        prompts = {
            "personaPrompt": persona_system_prompt(persona),
            "harborPrompt": persona_system_prompt(persona),
            "taskPrompt": task_prompt,
        }
        emit({"type": "prompts", "prompts": prompts})
        emit({"type": "phase", "phase": "survey_answering"})

        client = build_json_client(config.persona_model)
        raw = client.complete_json(prompts["personaPrompt"], task_prompt)
        answers = _normalize_answers(raw.get("answers"), instrument)
        metrics = _metrics(answers, instrument)
        trajectory = _build_trajectory(instrument, answers, created_at)
        result = SurveyEvalResult(
            config=config,
            persona=persona,
            instrument=instrument,
            answers=answers,
            trajectory=trajectory,
            metrics=metrics,
            created_at=created_at,
            prompts=prompts,
        )
        emit({"type": "done", "result": result.to_dict()})
        return result


def _event_timestamp(created_at: str, offset_seconds: int) -> str:
    try:
        base = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return created_at
    return (
        base.astimezone(timezone.utc) + timedelta(seconds=offset_seconds)
    ).isoformat().replace("+00:00", "Z")


def _build_trajectory(
    instrument: SurveyInstrument,
    answers: List[SurveyAnswer],
    created_at: str,
) -> List[TrajectoryEvent]:
    answer_by_id = {answer.question_id: answer for answer in answers}
    missing_required = [
        question.id
        for question in instrument.questions
        if question.required and question.id not in answer_by_id
    ]
    events = [
        TrajectoryEvent(
            timestamp=_event_timestamp(created_at, 0),
            actor="system",
            action="survey_started",
            context={
                "instrumentId": instrument.id,
                "instrumentTitle": instrument.title,
                "numQuestions": len(instrument.questions),
            },
            outcome={"status": "started"},
        )
    ]

    offset = 1
    for index, question in enumerate(instrument.questions, start=1):
        question_context = {
            "instrumentId": instrument.id,
            "questionId": question.id,
            "questionIndex": index,
            "questionType": question.type,
            "construct": question.construct,
        }
        events.append(
            TrajectoryEvent(
                timestamp=_event_timestamp(created_at, offset),
                actor="assistant",
                action="ask_question",
                context=question_context,
                outcome={
                    "prompt": question.prompt,
                    "options": list(question.options),
                },
            )
        )
        offset += 1

        answer = answer_by_id.get(question.id)
        if answer is None:
            continue
        events.append(
            TrajectoryEvent(
                timestamp=_event_timestamp(created_at, offset),
                actor="user",
                action="answer_question",
                context=question_context,
                outcome={
                    "questionId": answer.question_id,
                    "value": answer.value,
                    "rationale": answer.rationale,
                    "confidence": answer.confidence,
                },
            )
        )
        offset += 1

    events.append(
        TrajectoryEvent(
            timestamp=_event_timestamp(created_at, offset),
            actor="system",
            action="survey_completed",
            context={"instrumentId": instrument.id},
            outcome={
                "numAnswered": len(answers),
                "missingRequiredQuestionIds": missing_required,
                "valid": not missing_required,
            },
        )
    )
    return events


def _normalize_answers(raw_answers: Any, instrument: SurveyInstrument) -> List[SurveyAnswer]:
    by_id = {question.id: question for question in instrument.questions}
    answers: List[SurveyAnswer] = []
    if not isinstance(raw_answers, list):
        raw_answers = []
    seen = set()
    for raw in raw_answers:
        if not isinstance(raw, dict):
            continue
        answer = SurveyAnswer.from_dict(raw)
        question = by_id.get(answer.question_id)
        if question is None or answer.question_id in seen:
            continue
        answer.value = _normalize_value(answer.value, question)
        answers.append(answer)
        seen.add(answer.question_id)
    for question in instrument.questions:
        if question.required and question.id not in seen:
            answers.append(
                SurveyAnswer(
                    question_id=question.id,
                    value=_default_value(question),
                    rationale="No persona-specific answer was produced, so a neutral answer was used.",
                    confidence=0.0,
                )
            )
    return answers


def _normalize_value(value: Any, question: SurveyQuestion) -> Any:
    if question.type == "likert":
        try:
            number = int(round(float(value)))
        except (TypeError, ValueError):
            low = question.min_value or 1
            high = question.max_value or 5
            number = int(round((low + high) / 2))
        return max(question.min_value or 1, min(question.max_value or 5, number))
    if question.type == "single_choice":
        text = str(value)
        return text if text in question.options else question.options[0]
    if question.type == "multi_choice":
        values = value if isinstance(value, list) else [value]
        selected = [str(item) for item in values if str(item) in question.options]
        return selected or [question.options[0]]
    return str(value or "").strip()


def _default_value(question: SurveyQuestion) -> Any:
    if question.type == "likert":
        low = question.min_value or 1
        high = question.max_value or 5
        return int(round((low + high) / 2))
    if question.type == "single_choice":
        return question.options[0]
    if question.type == "multi_choice":
        return [question.options[0]]
    return ""


def _metrics(answers: List[SurveyAnswer], instrument: SurveyInstrument) -> SurveyMetrics:
    likert_values: List[float] = []
    question_types = {question.id: question.type for question in instrument.questions}
    for answer in answers:
        if question_types.get(answer.question_id) != "likert":
            continue
        try:
            likert_values.append(float(answer.value))
        except (TypeError, ValueError):
            continue
    mean = round(sum(likert_values) / len(likert_values), 2) if likert_values else None
    return SurveyMetrics(
        num_questions=len(instrument.questions),
        num_answered=len(answers),
        mean_likert=mean,
    )
