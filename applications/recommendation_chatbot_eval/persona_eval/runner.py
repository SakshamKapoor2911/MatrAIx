from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from persona_eval.types import (
    MetricScores, Persona, Questionnaire, PersonaEvalConfig, PersonaEvalResult, PersonaEvalTurn,
)


def _items_id_title(turn_view: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for item in turn_view.get("recommendedItems", []) or []:
        out.append({"id": str(item.get("itemId", item.get("id"))), "title": item.get("title")})
    return out


def run_persona_eval(
    session: Any,
    persona: Persona,
    sut_description: str,
    config: PersonaEvalConfig,
    simulator: Any,
    *,
    created_at: str,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> PersonaEvalResult:
    def emit(event: Dict[str, Any]) -> None:
        if on_event is not None:
            on_event(event)

    transcript: List[PersonaEvalTurn] = []
    pairs: List[Tuple[str, str]] = []

    emit({"type": "phase", "phase": "persona_kickoff"})
    message = simulator.kickoff(persona, sut_description)

    for index in range(1, config.max_turns + 1):
        emit({"type": "phase", "phase": "recommender_thinking", "userMessage": message})
        view = session.run_turn_sync(message)
        assistant = str(view.get("assistantMessage") or "")
        items = _items_id_title(view)

        emit({"type": "phase", "phase": "persona_thinking"})
        sim_turn = simulator.respond(persona, sut_description, list(pairs), assistant, items)

        turn = PersonaEvalTurn(
            turn_index=index, user_message=message, assistant_message=assistant,
            recommended_items=items, decision=sim_turn.decision,
            duration_seconds=view.get("durationSeconds"),
        )
        transcript.append(turn)
        pairs.append((message, assistant))
        emit({"type": "turn", "turn": turn.to_dict()})

        if sim_turn.decision in {"satisfied", "give_up"}:
            break
        message = sim_turn.message

    final_items = next((t.recommended_items for t in reversed(transcript) if t.recommended_items), [])
    turns_to_rec = next((t.turn_index for t in transcript if t.recommended_items), None)

    emit({"type": "phase", "phase": "persona_feedback"})
    questionnaire: Questionnaire = simulator.final_feedback(
        persona, sut_description, transcript, final_items)

    result = PersonaEvalResult(
        config=config, persona=persona, sut_description=sut_description, transcript=transcript,
        questionnaire=questionnaire,
        metric_scores=MetricScores(
            turns_to_recommendation=turns_to_rec, num_turns=len(transcript),
            recommended_item_count=len(final_items)),
        created_at=created_at,
    )
    emit({"type": "done", "result": result.to_dict()})
    return result
