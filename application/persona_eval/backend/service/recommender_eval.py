"""Recommender PersonaEval artifact helpers.

This module preserves the useful pure-Python contract from the MatrAIx
recommender evaluation work without importing the full historical backend,
frontend, or generated catalog bundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RecommenderPersona:
    id: str
    name: str
    summary: str = ""
    context: str = ""
    source: str = ""
    preferences: list[str] = field(default_factory=list)
    dislikes: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    goal: str = ""
    communication_style: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "context": self.context,
            "source": self.source,
            "preferences": list(self.preferences),
            "dislikes": list(self.dislikes),
            "constraints": list(self.constraints),
            "goal": self.goal,
            "communicationStyle": self.communication_style,
        }


@dataclass(frozen=True)
class RecommenderEvalConfig:
    domain: str
    engine: str = "gpt-4o-mini"
    ranker_mode: str = "native"
    resource_mode: str = "task_local"
    max_turns: int = 8
    goal_context_id: str = "scenario_default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "engine": self.engine,
            "rankerMode": self.ranker_mode,
            "resourceMode": self.resource_mode,
            "maxTurns": self.max_turns,
            "goalContextId": self.goal_context_id,
        }


@dataclass(frozen=True)
class RecommenderEvalResult:
    config: RecommenderEvalConfig
    persona: RecommenderPersona
    sut_description: str
    turn_views: list[dict[str, Any]]
    recommended_items: list[dict[str, Any]]
    questionnaire: dict[str, Any]
    metric_scores: dict[str, Any]
    created_at: str
    prompts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        per_turn = _recommended_ids_per_turn(self.turn_views)
        final = next((ids for ids in reversed(per_turn) if ids), [])
        return {
            "config": self.config.to_dict(),
            "persona": self.persona.to_dict(),
            "sutDescription": self.sut_description,
            "transcript": [dict(turn) for turn in self.turn_views],
            "recommendedItemIds": {"perTurn": per_turn, "final": final},
            "questionnaire": dict(self.questionnaire),
            "metricScores": dict(self.metric_scores),
            "createdAt": self.created_at,
            "prompts": dict(self.prompts),
        }


def write_harbor_persona_yaml(base_dir: Path, persona: RecommenderPersona) -> Path:
    """Write a Harbor persona YAML file for a recommender eval run."""
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "persona.yaml"
    payload = {
        "persona_id": persona.id,
        "display_name": persona.name,
        "summary": persona.summary,
        "system_prompt": persona.context or persona.summary or persona.name,
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
    """Build the application-owned task prompt for a Harbor persona agent."""
    return f"""# Application task prompt: recommender simulation

Harbor supplies the persona system prompt. Use that persona as your identity,
communication style, preferences, and decision-making style. This application
supplies only the task-specific simulation prompt below.

You are testing a {domain} recommendation system.

{sut_description}

Goal context: {goal_context_description}

Start by deciding, silently and in character, what kind of {domain} items you
realistically want and which constraints or personal preferences matter. Do not
reveal everything at once.

Interact naturally with the recommender, answer its follow-up questions, push
back when recommendations do not fit, and stop when you can judge whether the
recommendations satisfy your need.

Use the recommender API sidecar exactly as described in the base task
instruction. Use this request body when creating the session or sending the
first message:

```json
{{"domain": "{domain}"}}
```

If the sidecar is unavailable, unhealthy, or fails during the conversation,
fail the task. Do not simulate the recommender, do not call another LLM as a
replacement recommender, and do not invent item ids or recommendation results.

Required behavior:
- Have at least three user turns and three assistant turns unless the agent is
  completely unusable.
- Finish within {max_turns} user turns.
- Base every final recommendation id on items returned by `/v1/messages` or
  `/v1/recommendations`.
- Save `transcript.json` from `/v1/conversation`; it should include real
  `turns[*].recommendedItems` from the recommender API when the sidecar returns
  turn-level recommendation data.
- Save `/app/output/transcript.json`.
- Save `/app/output/recommendation_result.json`.
"""


def build_result_from_task_artifacts(
    *,
    output_dir: Path,
    config: RecommenderEvalConfig,
    persona: RecommenderPersona,
    sut_description: str,
    created_at: str,
    prompts: dict[str, Any] | None = None,
) -> RecommenderEvalResult:
    """Map recommender task artifacts into a PersonaEval-style result."""
    transcript = _read_json(output_dir / "transcript.json")
    recommendation = _read_json(output_dir / "recommendation_result.json")
    feedback_path = _feedback_path(output_dir)
    feedback = _read_json(feedback_path) if feedback_path is not None else {}

    turn_views = _turn_views(transcript)
    recommended_items = _normalize_recommended_items(
        recommendation.get("recommendedItems")
    )
    _validate_recommendation_grounding(
        turn_views=turn_views,
        recommended_items=recommended_items,
    )

    metric_scores = {
        "turnsToRecommendation": recommendation.get("turnsToRecommendation"),
        "numTurns": len(turn_views),
        "recommendedItemCount": len(recommended_items),
    }
    return RecommenderEvalResult(
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


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("itemId", item.get("id", "")))


def _feedback_path(output_dir: Path) -> Path | None:
    app_feedback = output_dir / "user_feedback.json"
    if app_feedback.is_file():
        return app_feedback
    try:
        verifier_feedback = output_dir.parents[2] / "verifier" / "user_feedback.json"
    except IndexError:
        return None
    return verifier_feedback if verifier_feedback.is_file() else None


def _coerce_score(value: Any, default: int) -> int:
    text = str(value or "").strip().lower()
    if text == "yes":
        return 5
    if text == "partially":
        return 3
    if text == "no":
        return 1
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(5, number))


def _coerce_overall(value: Any, default: int = 5) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(1, min(10, number))


def _questionnaire(feedback: dict[str, Any]) -> dict[str, Any]:
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
            feedback.get("productNeedConstraintSatisfaction"), 3
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


def _build_turns_from_messages(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    messages = transcript.get("messages") or []
    if not isinstance(messages, list):
        return []

    turns: list[dict[str, Any]] = []
    pending_user: str | None = None
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
                    "userMessage": pending_user,
                    "assistantMessage": content,
                    "recommendedItems": [],
                }
            )
            pending_user = None
    return turns


def _turn_views(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    turns = transcript.get("turns")
    if isinstance(turns, list) and all(isinstance(turn, dict) for turn in turns):
        return [dict(turn) for turn in turns]
    return _build_turns_from_messages(transcript)


def _normalize_recommended_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("recommendation_result.recommendedItems must not be empty")
    items: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(
                f"recommendation_result.recommendedItems[{index}] must be an object"
            )
        item_id = _item_id(item).strip()
        if not item_id:
            raise ValueError(
                f"recommendation_result.recommendedItems[{index}].itemId is required"
            )
        items.append({**item, "itemId": item_id})
    return items


def _grounded_item_ids(turn_views: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for turn in turn_views:
        items = turn.get("recommendedItems") or []
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                item_id = _item_id(item).strip()
                if item_id:
                    ids.add(item_id)
    return ids


def _validate_recommendation_grounding(
    *,
    turn_views: list[dict[str, Any]],
    recommended_items: list[dict[str, Any]],
) -> None:
    grounded_ids = _grounded_item_ids(turn_views)
    missing = [
        item["itemId"]
        for item in recommended_items
        if item["itemId"] not in grounded_ids
    ]
    if missing:
        raise ValueError(
            "recommendation_result.recommendedItems must be grounded in "
            "transcript.turns recommendedItems; missing ids: {}".format(
                ", ".join(missing[:5])
            )
        )


def _recommended_ids_per_turn(turn_views: list[dict[str, Any]]) -> list[list[str]]:
    per_turn: list[list[str]] = []
    for turn in turn_views:
        items = turn.get("recommendedItems") or []
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


def _normalize_prompts(
    prompts: dict[str, Any] | None,
    *,
    persona: RecommenderPersona,
) -> dict[str, str]:
    values = prompts or {}
    return {
        "harborPrompt": str(
            values.get("harborPrompt")
            or persona.context
            or persona.summary
            or persona.name
        ),
        "taskPrompt": str(values.get("taskPrompt") or ""),
    }
