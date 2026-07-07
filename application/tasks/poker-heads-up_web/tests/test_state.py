from __future__ import annotations

import json
import os
from pathlib import Path

OUTPUT = Path(os.environ.get("MATRIX_OUTPUT_DIR", "/app/output")) / "poker_result.json"

GAME_ID = "kuhn-heads-up-fixed-v1"
PLAYER_CARD = "Q"
OPPONENT_MODEL = "deterministic-kuhn-bot-v1"
VALID_ACTION_LINES = {
    ("bet",): {
        "opponent_actions": ["fold"],
        "terminal_state": "bot_folded",
        "winner": "player",
        "chip_delta": 1,
        "pot_size": 3,
        "showdown_revealed": False,
        "label": "Bet first and make the bot fold",
    },
    ("check", "call"): {
        "opponent_actions": ["bet"],
        "terminal_state": "showdown",
        "winner": "player",
        "chip_delta": 2,
        "pot_size": 4,
        "showdown_revealed": True,
        "label": "Check, face a bluff bet, then call",
    },
    ("check", "fold"): {
        "opponent_actions": ["bet"],
        "terminal_state": "player_folded",
        "winner": "opponent",
        "chip_delta": -1,
        "pot_size": 3,
        "showdown_revealed": False,
        "label": "Check, face a bluff bet, then fold",
    },
}
DECISION_OUTCOMES = {"selected", "considered", "rejected", "deferred", "skipped"}
BASIS_PRIMARY = {
    "price",
    "quality",
    "features",
    "convenience",
    "taste",
    "trust",
    "familiarity",
    "novelty",
    "fit",
    "other",
}
STRATEGY_BASIS = {
    "value_bet",
    "bluff_call",
    "pot_control",
    "risk_control",
    "information_gathering",
    "other",
}
RISK_POSTURES = {"risk_averse", "balanced", "risk_seeking", "opportunistic"}
EXPLORATION_STYLES = {"quick_pick", "compared_multiple", "deep_research", "hesitant"}
SATISFACTION_BUCKETS = {"yes", "partially", "no"}


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


def _write_structured_output(payload: dict[str, object]) -> None:
    path = _verifier_dir() / "structured_output.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load() -> dict[str, object]:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text(encoding="utf-8-sig"))
    assert isinstance(data, dict), "root must be an object"
    return data


def _required_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    assert isinstance(value, str) and value.strip(), f"{key} must be a non-empty string"
    return value.strip()


def _required_int(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    assert isinstance(value, int) and not isinstance(value, bool), f"{key} must be an integer"
    return value


def _rating(data: dict[str, object], key: str) -> int:
    value = _required_int(data, key)
    assert 1 <= value <= 10, f"{key} must be between 1 and 10"
    return value


def _action_sequence(data: dict[str, object]) -> tuple[str, ...]:
    value = data.get("action_sequence")
    assert isinstance(value, list), "action_sequence must be a list"
    actions = tuple(value)
    assert all(isinstance(action, str) for action in actions), (
        "action_sequence must contain strings"
    )
    assert actions in VALID_ACTION_LINES, "unsupported poker action line: {!r}".format(
        actions
    )
    return actions


def _validate_game_result(data: dict[str, object], actions: tuple[str, ...]) -> dict[str, object]:
    expected = VALID_ACTION_LINES[actions]

    opponent_actions = data.get("opponent_action_sequence")
    assert opponent_actions == expected["opponent_actions"], (
        "opponent_action_sequence must match the deterministic bot policy"
    )
    for key in ("terminal_state", "winner", "chip_delta", "pot_size", "showdown_revealed"):
        assert data.get(key) == expected[key], f"{key} does not match expected game result"

    return expected


def _contexts(
    *,
    data: dict[str, object],
    actions: tuple[str, ...],
    expected: dict[str, object],
) -> list[dict[str, object]]:
    action_line = "-".join(actions)
    reason = _required_str(data, "reason")
    decision_subject_id = _required_str(data, "decision_subject_id")
    decision_subject_label = _required_str(data, "decision_subject_label")
    strategy_basis = _required_str(data, "task_strategy_basis")
    risk_posture = _required_str(data, "risk_posture")
    exploration_style = _required_str(data, "exploration_style")

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
                    "value": "artifact_exact",
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
                        "The persona completed a valid poker hand with action line {} "
                        "and terminal state {}."
                    ).format(action_line, expected["terminal_state"]),
                },
                {
                    "key": "completion_evidence",
                    "label": "Completion evidence",
                    "role": "evidence",
                    "kind": "textual",
                    "value": "Saved poker_result.json with chip delta {}.".format(
                        expected["chip_delta"]
                    ),
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
                    "key": "artifact_subject_label",
                    "label": "Artifact subject label",
                    "role": "evidence",
                    "kind": "textual",
                    "value": decision_subject_label,
                },
                {
                    "key": "artifact_subject_id",
                    "label": "Artifact subject id",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": decision_subject_id,
                },
                {
                    "key": "artifact_evidence",
                    "label": "Artifact evidence",
                    "role": "explanation",
                    "kind": "textual",
                    "value": "The submission matches the deterministic game rules.",
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
                    "value": "The persona played the local poker table and submitted the result.",
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
                    "value": strategy_basis,
                },
                {
                    "key": "risk_posture",
                    "label": "Risk posture",
                    "role": "primary",
                    "kind": "categorical",
                    "value": risk_posture,
                },
                {
                    "key": "reason",
                    "label": "Reason",
                    "role": "explanation",
                    "kind": "textual",
                    "value": reason,
                },
                {
                    "key": "decision_subject_id",
                    "label": "Decision subject ID",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": decision_subject_id,
                },
                {
                    "key": "decision_subject_label",
                    "label": "Decision subject label",
                    "role": "evidence",
                    "kind": "textual",
                    "value": decision_subject_label,
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
                    "value": exploration_style,
                },
                {
                    "key": "action_line",
                    "label": "Action line",
                    "role": "primary",
                    "kind": "categorical",
                    "value": action_line,
                },
                {
                    "key": "comparison_notes",
                    "label": "Comparison notes",
                    "role": "explanation",
                    "kind": "textual",
                    "value": "The persona chose {} in the simplified poker hand.".format(
                        action_line
                    ),
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
                    "value": (
                        "yes" if int(data["need_satisfaction"]) >= 7 else "partially"
                    ),
                },
                {
                    "key": "personal_preference_satisfaction",
                    "label": "Personal preference satisfaction",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": (
                        "yes"
                        if int(data["overall_experience_rating"]) >= 7
                        else "partially"
                    ),
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
    assert _required_str(data, "player_card") == PLAYER_CARD
    assert _required_str(data, "opponent_model") == OPPONENT_MODEL

    actions = _action_sequence(data)
    expected = _validate_game_result(data, actions)

    decision_outcome = _required_str(data, "decision_outcome")
    assert decision_outcome in DECISION_OUTCOMES
    basis_primary = _required_str(data, "basis_primary")
    assert basis_primary in BASIS_PRIMARY
    assert _required_str(data, "task_strategy_basis") in STRATEGY_BASIS
    assert _required_str(data, "risk_posture") in RISK_POSTURES
    assert _required_str(data, "exploration_style") in EXPLORATION_STYLES

    assert _required_str(data, "decision_subject_id").startswith("line-")
    assert _required_str(data, "decision_subject_label")
    assert len(_required_str(data, "reason")) >= 20

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
            "contexts": _contexts(data=data, actions=actions, expected=expected),
        }
    )
