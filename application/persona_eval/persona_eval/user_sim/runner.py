"""UserSim v2 chat eval runner."""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from persona_eval.goal_contexts import get_goal_context
from persona_eval.model_client import build_json_client
from persona_eval.runner import _items_id_title
from persona_eval.types import (
    MetricScores,
    Persona,
    PersonaEvalConfig,
    PersonaEvalResult,
    PersonaEvalTurn,
)
from persona_eval.user_sim.port import ChatSessionPort, normalize_agent_turn
from persona_eval.user_sim.prompt import prompt_bundle
from persona_eval.user_sim.scenario import UserScenario, resolve_user_scenario
from persona_eval.user_sim.self_report import final_self_report
from persona_eval.user_sim.session import UserSimSession
from persona_eval.user_sim.tool_client import build_tool_step_client


def user_sim_v2_enabled() -> bool:
    raw = os.environ.get("MATRIX_USER_SIM_V2", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def run_persona_eval_v2(
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

    goal_context = get_goal_context(config.goal_context_id)
    scenario = resolve_user_scenario(
        task_path=task_path,
        goal_context=goal_context,
        domain=config.domain,
        sut_description=sut_description,
        repo_root=repo_root,
    )
    if scenario.domain and scenario.domain != config.domain:
        scenario = UserScenario(
            identity=scenario.identity,
            goal=scenario.goal,
            domain=config.domain,
            preferences=list(scenario.preferences),
            style=scenario.style,
            stop_when=scenario.stop_when,
            sut_context=scenario.sut_context,
            hidden_facts=list(scenario.hidden_facts),
        )

    tool_client = build_tool_step_client(config.persona_model)
    sim = UserSimSession(
        tool_client,
        persona,
        scenario,
        persona_yaml_path=persona_yaml_path,
    )
    prompts = prompt_bundle(
        persona,
        scenario,
        persona_yaml_path=persona_yaml_path,
        task_prompt=goal_context.description,
    )
    emit({"type": "prompts", "prompts": prompts})

    transcript: List[PersonaEvalTurn] = []
    action = sim.opening_action()
    emit({"type": "phase", "phase": "persona_kickoff"})

    for index in range(1, config.max_turns + 1):
        message = (action.message or "").strip()
        if not message:
            break

        emit({"type": "user_message", "turnIndex": index, "message": message})
        emit({"type": "phase", "phase": "recommender_thinking", "userMessage": message})
        raw_view = session.run_turn_sync(message)
        view = normalize_agent_turn(raw_view, message)
        assistant = str(view.get("assistantMessage") or "")
        items = _items_id_title(view)

        emit(
            {
                "type": "assistant_message",
                "turnIndex": index,
                "userMessage": message,
                "assistantMessage": assistant,
                "recommendedItems": [dict(i) for i in items],
                "durationSeconds": view.get("durationSeconds"),
            }
        )
        emit({"type": "phase", "phase": "persona_thinking"})
        action = sim.next_action(
            "The application chatbot replied:\n\"\"\"{}\"\"\"\n\n"
            "Grounded items (id — title): {}\n\n"
            "Decide your next move in character using the available tools.".format(
                assistant,
                "; ".join("{} — {}".format(i.get("id"), i.get("title") or "?") for i in items)
                or "(none yet)",
            )
        )

        decision = action.decision if action.end_reason else "continue"
        turn = PersonaEvalTurn(
            turn_index=index,
            user_message=message,
            assistant_message=assistant,
            recommended_items=items,
            decision=decision,
            duration_seconds=view.get("durationSeconds"),
        )
        transcript.append(turn)
        emit({"type": "turn", "turn": turn.to_dict()})

        if decision != "continue":
            break

    final_items = next(
        (turn.recommended_items for turn in reversed(transcript) if turn.recommended_items),
        [],
    )
    turns_to_rec = next((turn.turn_index for turn in transcript if turn.recommended_items), None)

    emit({"type": "phase", "phase": "persona_feedback"})
    questionnaire = final_self_report(
        build_json_client(config.persona_model),
        system_prompt=sim.system_prompt,
        persona=persona,
        transcript=transcript,
        final_recommended_items=final_items,
    )

    result = PersonaEvalResult(
        config=config,
        persona=persona,
        sut_description=sut_description,
        transcript=transcript,
        questionnaire=questionnaire,
        metric_scores=MetricScores(
            turns_to_recommendation=turns_to_rec,
            num_turns=len(transcript),
            recommended_item_count=len(final_items),
        ),
        created_at=created_at,
        prompts=prompts,
    )
    emit({"type": "done", "result": result.to_dict()})
    return result


async def run_persona_eval_v2_async(
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
    """Like :func:`run_persona_eval_v2` but awaits async Harbor sidecar turns."""

    def emit(event: Dict[str, Any]) -> None:
        if on_event is not None:
            on_event(event)

    goal_context = get_goal_context(config.goal_context_id)
    scenario = resolve_user_scenario(
        task_path=task_path,
        goal_context=goal_context,
        domain=config.domain,
        sut_description=sut_description,
        repo_root=repo_root,
    )
    if scenario.domain and scenario.domain != config.domain:
        scenario = UserScenario(
            identity=scenario.identity,
            goal=scenario.goal,
            domain=config.domain,
            preferences=list(scenario.preferences),
            style=scenario.style,
            stop_when=scenario.stop_when,
            sut_context=scenario.sut_context,
            hidden_facts=list(scenario.hidden_facts),
        )

    tool_client = build_tool_step_client(config.persona_model)
    sim = UserSimSession(
        tool_client,
        persona,
        scenario,
        persona_yaml_path=persona_yaml_path,
    )
    prompts = prompt_bundle(
        persona,
        scenario,
        persona_yaml_path=persona_yaml_path,
        task_prompt=goal_context.description,
    )
    emit({"type": "prompts", "prompts": prompts})

    transcript: List[PersonaEvalTurn] = []
    action = sim.opening_action()
    emit({"type": "phase", "phase": "persona_kickoff"})

    for index in range(1, config.max_turns + 1):
        message = (action.message or "").strip()
        if not message:
            break

        emit({"type": "user_message", "turnIndex": index, "message": message})
        emit({"type": "phase", "phase": "recommender_thinking", "userMessage": message})
        raw_view = session.run_turn_sync(message)
        if inspect.isawaitable(raw_view):
            raw_view = await raw_view
        view = normalize_agent_turn(raw_view, message)
        assistant = str(view.get("assistantMessage") or "")
        items = _items_id_title(view)

        emit(
            {
                "type": "assistant_message",
                "turnIndex": index,
                "userMessage": message,
                "assistantMessage": assistant,
                "recommendedItems": [dict(i) for i in items],
                "durationSeconds": view.get("durationSeconds"),
            }
        )
        emit({"type": "phase", "phase": "persona_thinking"})
        action = sim.next_action(
            "The application chatbot replied:\n\"\"\"{}\"\"\"\n\n"
            "Grounded items (id — title): {}\n\n"
            "Decide your next move in character using the available tools.".format(
                assistant,
                "; ".join("{} — {}".format(i.get("id"), i.get("title") or "?") for i in items)
                or "(none yet)",
            )
        )

        decision = action.decision if action.end_reason else "continue"
        turn = PersonaEvalTurn(
            turn_index=index,
            user_message=message,
            assistant_message=assistant,
            recommended_items=items,
            decision=decision,
            duration_seconds=view.get("durationSeconds"),
        )
        transcript.append(turn)
        emit({"type": "turn", "turn": turn.to_dict()})

        if decision != "continue":
            break

    final_items = next(
        (turn.recommended_items for turn in reversed(transcript) if turn.recommended_items),
        [],
    )
    turns_to_rec = next((turn.turn_index for turn in transcript if turn.recommended_items), None)

    emit({"type": "phase", "phase": "persona_feedback"})
    questionnaire = final_self_report(
        build_json_client(config.persona_model),
        system_prompt=sim.system_prompt,
        persona=persona,
        transcript=transcript,
        final_recommended_items=final_items,
    )

    result = PersonaEvalResult(
        config=config,
        persona=persona,
        sut_description=sut_description,
        transcript=transcript,
        questionnaire=questionnaire,
        metric_scores=MetricScores(
            turns_to_recommendation=turns_to_rec,
            num_turns=len(transcript),
            recommended_item_count=len(final_items),
        ),
        created_at=created_at,
        prompts=prompts,
    )
    emit({"type": "done", "result": result.to_dict()})
    return result
