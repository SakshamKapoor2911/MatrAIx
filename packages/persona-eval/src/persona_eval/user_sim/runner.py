"""Tool-driven user simulator chat eval runner."""

from __future__ import annotations

import inspect
from itertools import count
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from persona_eval.chatbot_task_config import (
    load_chatbot_task_config_for_task_path,
)
from persona_eval.self_report_task_config import (
    load_self_report_schema_for_task_path,
)
from persona_eval.task_content_bundle import (
    TaskContentBundle,
    load_task_content_bundle_for_task_path,
)
from persona_eval.model_client import build_json_client
from persona_eval.types import (
    MetricScores,
    Persona,
    PersonaEvalConfig,
    PersonaEvalResult,
    PersonaEvalTurn,
)
from persona_eval.user_sim.chatbot_labels import chatbot_display_name
from persona_eval.user_sim.kickoff import get_goal_context
from persona_eval.user_sim.port import ChatSessionPort, normalize_agent_turn
from persona_eval.user_sim.prompt import (
    assemble_report_system_prompt,
    prompt_bundle,
)
from persona_eval.user_sim.self_report import final_self_report
from persona_eval.user_sim.session import UserSimSession
from persona_eval.user_sim.tool_client import build_tool_step_client


def _format_exposure_value(value: Any, *, kind: str) -> str:
    if kind == "item_list" and isinstance(value, list):
        parts = []
        for item in value:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "").strip()
            item_id = str(item.get("itemId") or item.get("id") or "").strip()
            if title and item_id:
                parts.append("{} ({})".format(title, item_id))
            elif title:
                parts.append(title)
            elif item_id:
                parts.append(item_id)
        return ", ".join(parts) or "[]"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _chatbot_observation(
    chatbot_label: str,
    assistant_message: str,
    persona_exposure: Optional[List[Dict[str, Any]]] = None,
) -> str:
    details = []
    for item in persona_exposure or []:
        value = _format_exposure_value(
            item.get("value"), kind=str(item.get("format") or "text")
        ).strip()
        if not value:
            continue
        label = str(item.get("label") or item.get("key") or "Visible detail")
        details.append("- {}: {}".format(label, value))
    extra = (
        "\nVisible structured details:\n{}\n".format("\n".join(details))
        if details
        else "\n"
    )
    return (
        '{label} Answer:\n"""{message}"""{extra}'
        "\nDecide your next move in character using the available tools."
    ).format(label=chatbot_label, message=assistant_message, extra=extra)


def _turn_indices(max_turns: int | None):
    return range(1, max_turns + 1) if max_turns is not None else count(1)


def _load_task_bundle(
    *,
    task_path: Optional[str],
    repo_root: Optional[Path],
) -> TaskContentBundle:
    if not task_path or repo_root is None:
        return TaskContentBundle()
    try:
        return load_task_content_bundle_for_task_path(task_path, repo_root=repo_root)
    except Exception:
        return TaskContentBundle()


def _load_chatbot_runtime_config(
    *,
    task_path: Optional[str],
    repo_root: Optional[Path],
):
    if not task_path or repo_root is None:
        return None
    try:
        return load_chatbot_task_config_for_task_path(task_path, repo_root=repo_root)
    except Exception:
        return None


def run_persona_eval(
    session: ChatSessionPort,
    persona: Persona,
    sut_description: str,
    config: PersonaEvalConfig,
    *,
    created_at: str,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    task_path: Optional[str] = None,
    persona_yaml_path: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> PersonaEvalResult:
    def emit(event: Dict[str, Any]) -> None:
        if on_event is not None:
            on_event(event)

    goal_context = get_goal_context("scenario_default")
    chatbot_label = chatbot_display_name(config.application_id)
    task_bundle = _load_task_bundle(task_path=task_path, repo_root=repo_root)
    task_config = _load_chatbot_runtime_config(task_path=task_path, repo_root=repo_root)
    self_report_schema = load_self_report_schema_for_task_path(
        task_path or "",
        repo_root=repo_root or Path("."),
    )

    tool_client = build_tool_step_client(config.persona_model)
    sim = UserSimSession(
        tool_client,
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
    )
    prompts = prompt_bundle(
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
        task_prompt=goal_context.description,
    )
    report_prompt = assemble_report_system_prompt(
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
    )
    emit({"type": "prompts", "prompts": prompts})

    transcript: List[PersonaEvalTurn] = []
    action = sim.opening_action()
    emit({"type": "phase", "phase": "persona_kickoff"})

    for index in _turn_indices(config.max_turns):
        message = (action.message or "").strip()
        if not message:
            break

        emit({"type": "user_message", "turnIndex": index, "message": message})
        emit({"type": "phase", "phase": "application_thinking", "userMessage": message})
        raw_view = session.run_turn_sync(message)
        view = normalize_agent_turn(
            raw_view,
            message,
            persona_exposure_fields=task_config.persona_exposure if task_config else None,
        )
        assistant = str(view.get("assistantMessage") or "")
        persona_exposure = list(view.get("personaExposure") or [])
        emit(
            {
                "type": "assistant_message",
                "turnIndex": index,
                "userMessage": message,
                "assistantMessage": assistant,
                "personaExposure": persona_exposure,
                "durationSeconds": view.get("durationSeconds"),
            }
        )
        emit({"type": "phase", "phase": "persona_thinking"})
        action = sim.next_action(
            _chatbot_observation(chatbot_label, assistant, persona_exposure)
        )

        decision = action.decision if action.end_reason else "continue"
        turn = PersonaEvalTurn(
            turn_index=index,
            user_message=message,
            assistant_message=assistant,
            persona_exposure=persona_exposure,
            decision=decision,
            duration_seconds=view.get("durationSeconds"),
        )
        transcript.append(turn)
        emit({"type": "turn", "turn": turn.to_dict()})

        if decision != "continue":
            break

    emit({"type": "phase", "phase": "persona_feedback"})
    questionnaire = final_self_report(
        build_json_client(config.persona_model),
        system_prompt=report_prompt,
        persona=persona,
        transcript=transcript,
        schema=self_report_schema,
        chatbot_label=chatbot_label,
    )

    result = PersonaEvalResult(
        config=config,
        persona=persona,
        sut_description=sut_description,
        transcript=transcript,
        questionnaire=questionnaire,
        metric_scores=MetricScores(num_turns=len(transcript)),
        created_at=created_at,
        prompts=prompts,
    )
    emit({"type": "done", "result": result.to_dict()})
    return result


async def run_persona_eval_async(
    session: ChatSessionPort,
    persona: Persona,
    sut_description: str,
    config: PersonaEvalConfig,
    *,
    created_at: str,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    task_path: Optional[str] = None,
    persona_yaml_path: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> PersonaEvalResult:
    """Like :func:`run_persona_eval` but awaits async Harbor sidecar turns."""

    def emit(event: Dict[str, Any]) -> None:
        if on_event is not None:
            on_event(event)

    goal_context = get_goal_context("scenario_default")
    chatbot_label = chatbot_display_name(config.application_id)
    task_bundle = _load_task_bundle(task_path=task_path, repo_root=repo_root)
    task_config = _load_chatbot_runtime_config(task_path=task_path, repo_root=repo_root)
    self_report_schema = load_self_report_schema_for_task_path(
        task_path or "",
        repo_root=repo_root or Path("."),
    )

    tool_client = build_tool_step_client(config.persona_model)
    sim = UserSimSession(
        tool_client,
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
    )
    prompts = prompt_bundle(
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
        task_prompt=goal_context.description,
    )
    report_prompt = assemble_report_system_prompt(
        persona,
        persona_yaml_path=persona_yaml_path,
        task_bundle=task_bundle,
    )
    emit({"type": "prompts", "prompts": prompts})

    transcript: List[PersonaEvalTurn] = []
    action = sim.opening_action()
    emit({"type": "phase", "phase": "persona_kickoff"})

    for index in _turn_indices(config.max_turns):
        message = (action.message or "").strip()
        if not message:
            break

        emit({"type": "user_message", "turnIndex": index, "message": message})
        emit({"type": "phase", "phase": "application_thinking", "userMessage": message})
        raw_view = session.run_turn_sync(message)
        if inspect.isawaitable(raw_view):
            raw_view = await raw_view
        view = normalize_agent_turn(
            raw_view,
            message,
            persona_exposure_fields=task_config.persona_exposure if task_config else None,
        )
        assistant = str(view.get("assistantMessage") or "")
        persona_exposure = list(view.get("personaExposure") or [])
        emit(
            {
                "type": "assistant_message",
                "turnIndex": index,
                "userMessage": message,
                "assistantMessage": assistant,
                "personaExposure": persona_exposure,
                "durationSeconds": view.get("durationSeconds"),
            }
        )
        emit({"type": "phase", "phase": "persona_thinking"})
        action = sim.next_action(
            _chatbot_observation(chatbot_label, assistant, persona_exposure)
        )

        decision = action.decision if action.end_reason else "continue"
        turn = PersonaEvalTurn(
            turn_index=index,
            user_message=message,
            assistant_message=assistant,
            persona_exposure=persona_exposure,
            decision=decision,
            duration_seconds=view.get("durationSeconds"),
        )
        transcript.append(turn)
        emit({"type": "turn", "turn": turn.to_dict()})

        if decision != "continue":
            break

    emit({"type": "phase", "phase": "persona_feedback"})
    questionnaire = final_self_report(
        build_json_client(config.persona_model),
        system_prompt=report_prompt,
        persona=persona,
        transcript=transcript,
        schema=self_report_schema,
        chatbot_label=chatbot_label,
    )

    result = PersonaEvalResult(
        config=config,
        persona=persona,
        sut_description=sut_description,
        transcript=transcript,
        questionnaire=questionnaire,
        metric_scores=MetricScores(num_turns=len(transcript)),
        created_at=created_at,
        prompts=prompts,
    )
    emit({"type": "done", "result": result.to_dict()})
    return result
