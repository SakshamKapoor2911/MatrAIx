from __future__ import annotations

import json
import os
import re
from pathlib import Path

OUTPUT = Path(os.environ.get("MATRIX_OUTPUT_DIR", "/app/output")) / "holdem_result.json"

GAME_ID = "texas-holdem-heads-up-v1"

VALID_HAND_RANKS = {
    "straight_flush",
    "four_of_a_kind",
    "full_house",
    "flush",
    "straight",
    "three_of_a_kind",
    "two_pair",
    "pair",
    "high_card",
}
VALID_WINNERS = {"player", "opponent", "tie"}
VALID_STREET_ACTIONS = {"fold", "check", "call", "raise"}
CARD_PATTERN = re.compile(r"^[2-9TJQKA][shdc]$")

DECISION_OUTCOMES = {"selected", "considered", "rejected", "deferred", "skipped"}
BASIS_PRIMARY = {
    "price", "quality", "features", "convenience", "taste",
    "trust", "familiarity", "novelty", "fit", "other",
}
STRATEGY_BASIS = {
    "hand_strength", "pot_odds", "position_play", "bluff", "pot_control", "other",
}
RISK_POSTURES = {"risk_averse", "balanced", "risk_seeking", "opportunistic"}
EXPLORATION_STYLES = {"quick_pick", "compared_multiple", "deep_research", "hesitant"}


def _verifier_dir() -> Path:
    base = (
        os.environ.get("HARBOR_VERIFIER_DIR")
        or os.environ.get("PERSONABENCH_VERIFIER_DIR")
        or "/logs/verifier"
    )
    path = Path(base)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        path = Path(__file__).resolve().parent.parent / "verifier"
        path.mkdir(parents=True, exist_ok=True)
        return path


def _write_structured_output(payload: dict) -> None:
    path = _verifier_dir() / "structured_output.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text(encoding="utf-8-sig"))
    assert isinstance(data, dict), "root must be an object"
    return data


def _required_str(data: dict, key: str) -> str:
    value = data.get(key)
    assert isinstance(value, str) and value.strip(), f"{key} must be a non-empty string"
    return value.strip()


def _required_int(data: dict, key: str) -> int:
    value = data.get(key)
    assert isinstance(value, int) and not isinstance(value, bool), f"{key} must be an integer"
    return value


def _rating(data: dict, key: str) -> int:
    value = _required_int(data, key)
    assert 1 <= value <= 10, f"{key} must be between 1 and 10"
    return value


def _validate_card(card: object, label: str) -> str:
    assert isinstance(card, str), f"{label} must be a string"
    assert CARD_PATTERN.match(card), f"{label} '{card}' is not a valid card (e.g. 'Ah', 'Kd')"
    return card


def _validate_hole_cards(data: dict) -> list[str]:
    cards = data.get("hole_cards")
    assert isinstance(cards, list) and len(cards) == 2, "hole_cards must be a list of exactly 2 cards"
    return [_validate_card(c, f"hole_cards[{i}]") for i, c in enumerate(cards)]


def _validate_community_cards(data: dict, hole_cards: list[str]) -> list[str]:
    cards = data.get("community_cards")
    assert isinstance(cards, list) and len(cards) <= 5, "community_cards must be a list of at most 5 cards"
    validated = [_validate_card(c, f"community_cards[{i}]") for i, c in enumerate(cards)]
    all_cards = hole_cards + validated
    assert len(all_cards) == len(set(all_cards)), "duplicate cards between hole and community"
    return validated


def _validate_street_actions(data: dict) -> dict:
    sa = data.get("street_actions")
    assert isinstance(sa, dict), "street_actions must be an object"
    for street, actions in sa.items():
        assert isinstance(actions, list), f"street_actions.{street} must be a list"
        for a in actions:
            assert a in VALID_STREET_ACTIONS, f"invalid action '{a}' in street_actions.{street}"
    return sa


def _contexts(*, data: dict) -> list[dict]:
    reason = _required_str(data, "reason")
    winner = data["winner"]
    chip_delta = data["chip_delta"]
    action_summary = ";".join(
        f"{s}:{','.join(acts)}"
        for s, acts in data.get("street_actions", {}).items()
        if acts
    )

    return [
        {
            "key": "task_outcome.primary",
            "label": "Task outcome",
            "contextType": "task_outcome",
            "facets": [
                {
                    "key": "outcome_status",
                    "label": "Outcome status",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "passed",
                },
                {
                    "key": "goal_completion_ratio",
                    "label": "Goal completion ratio",
                    "role": "score",
                    "kind": "numerical",
                    "value": 1.0,
                },
                {
                    "key": "goal_completion_bucket",
                    "label": "Goal completion bucket",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "complete",
                },
                {
                    "key": "verifier_mode",
                    "label": "Verifier mode",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": "artifact_format",
                },
                {
                    "key": "primary_failure_reason",
                    "label": "Primary failure reason",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "none",
                },
                {
                    "key": "outcome_explanation",
                    "label": "Outcome explanation",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        "The persona completed a Texas Hold'em hand. "
                        "Winner: {}. Chip delta: {}.".format(winner, chip_delta)
                    ),
                },
                {
                    "key": "completion_evidence",
                    "label": "Completion evidence",
                    "role": "evidence",
                    "kind": "textual",
                    "value": "Saved holdem_result.json with valid schema.",
                },
            ],
        },
        {
            "key": "web_artifact.primary",
            "label": "Web artifact",
            "contextType": "web_artifact",
            "facets": [
                {
                    "key": "artifact_type",
                    "label": "Artifact type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "task_submission",
                },
                {
                    "key": "artifact_status",
                    "label": "Artifact status",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "correct",
                },
                {
                    "key": "artifact_evidence",
                    "label": "Artifact evidence",
                    "role": "explanation",
                    "kind": "textual",
                    "value": "The submission passed schema validation.",
                },
            ],
        },
        {
            "key": "web_interaction.primary",
            "label": "Web interaction",
            "contextType": "web_interaction",
            "facets": [
                {
                    "key": "navigation_path_type",
                    "label": "Navigation path type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "direct",
                },
                {
                    "key": "web_interaction_notes",
                    "label": "Web interaction notes",
                    "role": "explanation",
                    "kind": "textual",
                    "value": "The persona played a Texas Hold'em hand and submitted the result. Actions: {}.".format(action_summary),
                },
            ],
        },
        {
            "key": "decision.primary",
            "label": "Primary poker decision",
            "contextType": "decision",
            "facets": [
                {
                    "key": "decision_outcome",
                    "label": "Decision outcome",
                    "role": "primary",
                    "kind": "categorical",
                    "value": data["decision_outcome"],
                },
                {
                    "key": "basis_primary",
                    "label": "Primary basis",
                    "role": "primary",
                    "kind": "categorical",
                    "value": data["basis_primary"],
                },
                {
                    "key": "task_strategy_basis",
                    "label": "Poker strategy basis",
                    "role": "primary",
                    "kind": "categorical",
                    "value": data["task_strategy_basis"],
                },
                {
                    "key": "risk_posture",
                    "label": "Risk posture",
                    "role": "primary",
                    "kind": "categorical",
                    "value": data["risk_posture"],
                },
                {
                    "key": "reason",
                    "label": "Reason",
                    "role": "explanation",
                    "kind": "textual",
                    "value": reason,
                },
            ],
        },
        {
            "key": "decision.process",
            "label": "Poker decision process",
            "contextType": "decision_process",
            "facets": [
                {
                    "key": "exploration_style",
                    "label": "Exploration style",
                    "role": "primary",
                    "kind": "categorical",
                    "value": data["exploration_style"],
                },
                {
                    "key": "action_summary",
                    "label": "Action summary",
                    "role": "primary",
                    "kind": "textual",
                    "value": action_summary,
                },
            ],
        },
        {
            "key": "user_feedback.primary",
            "label": "User feedback",
            "contextType": "user_feedback",
            "facets": [
                {
                    "key": "overall_experience_rating",
                    "label": "Overall experience rating",
                    "role": "score",
                    "kind": "numerical",
                    "value": data["overall_experience_rating"],
                },
                {
                    "key": "feedback_reason",
                    "label": "Feedback reason",
                    "role": "explanation",
                    "kind": "textual",
                    "value": reason,
                },
                {
                    "key": "need_constraint_satisfaction",
                    "label": "Need or constraint satisfaction",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": "yes" if int(data["need_satisfaction"]) >= 7 else "partially",
                },
                {
                    "key": "personal_preference_satisfaction",
                    "label": "Personal preference satisfaction",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": "yes" if int(data["overall_experience_rating"]) >= 7 else "partially",
                },
                {
                    "key": "effort_rating",
                    "label": "Effort rating",
                    "role": "score",
                    "kind": "numerical",
                    "value": data["ease_of_use"],
                },
            ],
        },
    ]


def test_output_exists() -> None:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_output_schema_and_game_semantics() -> None:
    data = _load()

    assert _required_str(data, "game_id") == GAME_ID

    hole_cards = _validate_hole_cards(data)
    _validate_community_cards(data, hole_cards)
    _validate_street_actions(data)

    final_hand_rank = data.get("final_hand_rank")
    assert final_hand_rank is None or final_hand_rank in VALID_HAND_RANKS, (
        f"final_hand_rank '{final_hand_rank}' is not valid"
    )

    winner = _required_str(data, "winner")
    assert winner in VALID_WINNERS, f"winner must be one of {VALID_WINNERS}"

    chip_delta = _required_int(data, "chip_delta")
    assert isinstance(chip_delta, int)

    _required_int(data, "pot_size")

    decision_outcome = _required_str(data, "decision_outcome")
    assert decision_outcome in DECISION_OUTCOMES, f"decision_outcome '{decision_outcome}' not valid"

    basis_primary = _required_str(data, "basis_primary")
    assert basis_primary in BASIS_PRIMARY, f"basis_primary '{basis_primary}' not valid"

    strategy_basis = _required_str(data, "task_strategy_basis")
    assert strategy_basis in STRATEGY_BASIS, f"task_strategy_basis '{strategy_basis}' not valid"

    risk_posture = _required_str(data, "risk_posture")
    assert risk_posture in RISK_POSTURES, f"risk_posture '{risk_posture}' not valid"

    exploration_style = _required_str(data, "exploration_style")
    assert exploration_style in EXPLORATION_STYLES, f"exploration_style '{exploration_style}' not valid"

    assert len(_required_str(data, "reason")) >= 20, "reason must be at least 20 characters"

    _rating(data, "need_satisfaction")
    _rating(data, "ease_of_use")
    _rating(data, "overall_experience_rating")

    _write_structured_output(
        {
            "schemaVersion": "1.0",
            "artifactType": "personabench.trial_evaluation",
            "taskType": "web",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": [OUTPUT.name],
                "missingArtifacts": [],
            },
            "sourceArtifacts": {
                "taskOutput": str(OUTPUT),
            },
            "contexts": _contexts(data=data),
        }
    )
