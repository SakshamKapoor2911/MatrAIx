from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from persona_eval.goal_contexts import get_goal_context
from persona_eval.openai_client import OpenAIChatClient
from persona_eval.types import Persona, PersonaEvalConfig, PersonaEvalTurn
from persona_eval.user_simulator import UserSimulator


def _rec_item(item: Dict[str, Any]) -> Dict[str, Any]:
    item_id = item.get("itemId", item.get("id"))
    return {"id": str(item_id), "title": item.get("title")}


def _turn_from_view(index: int, turn: Dict[str, Any]) -> PersonaEvalTurn:
    return PersonaEvalTurn(
        turn_index=index,
        user_message=str(turn.get("userMessage") or ""),
        assistant_message=str(turn.get("assistantMessage") or ""),
        recommended_items=[
            _rec_item(item)
            for item in (turn.get("recommendedItems") or [])
            if isinstance(item, dict) and (item.get("itemId") or item.get("id")) is not None
        ],
        decision=str(turn.get("decision") or "continue"),
        duration_seconds=turn.get("durationSeconds"),
    )


class OriginalPromptFeedbackScorer:
    """Score Harbor recommender runs with the original persona-eval prompt."""

    def __init__(
        self,
        *,
        client_factory: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.client_factory = client_factory or (lambda model: OpenAIChatClient(model=model))

    def __call__(
        self,
        *,
        persona: Persona,
        sut_description: str,
        config: PersonaEvalConfig,
        turn_views: List[Dict[str, Any]],
        recommended_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        goal_context = get_goal_context(config.goal_context_id)
        simulator = UserSimulator(
            self.client_factory(config.engine),
            goal_context,
            config.domain,
        )
        transcript = [
            _turn_from_view(index, turn) for index, turn in enumerate(turn_views)
        ]
        final_items = [
            _rec_item(item)
            for item in recommended_items
            if isinstance(item, dict) and (item.get("itemId") or item.get("id")) is not None
        ]
        return simulator.final_feedback(
            persona,
            sut_description,
            transcript,
            final_items,
        ).to_dict()
