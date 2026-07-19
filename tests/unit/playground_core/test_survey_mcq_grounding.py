"""Tests for ClearQueue MCQ economic_motivation grounding (spending-posture checkpoints)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_TASK_GROUNDING = (
    Path(__file__).resolve().parents[3]
    / "persona/tasks/example-survey_product-feedback/tests/test_grounding.py"
)
_spec = importlib.util.spec_from_file_location("clearqueue_grounding", _TASK_GROUNDING)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_evaluate = _mod._evaluate_economic_motivation
_PROBE_QUESTION_IDS = _mod.PROBE_QUESTION_IDS
_ORACLE_PATHS = _mod.ORACLE_PATHS
_CONTINUED_CHOICES_BY_QUESTION = _mod.CONTINUED_CHOICES_BY_QUESTION
_POSTURES = _mod.POSTURES


def _survey_from_path(path: dict[str, str]) -> dict:
    return {
        "participation": "continued",
        "responses": [
            {"question_id": qid, "choice_id": cid} for qid, cid in path.items()
        ],
    }


def test_all_probe_questions_scored() -> None:
    assert _PROBE_QUESTION_IDS == frozenset(f"q{i}" for i in range(7))


def test_oracle_matrix_is_bijective_per_question() -> None:
    for qid in _PROBE_QUESTION_IDS:
        choices = {path[qid] for path in _ORACLE_PATHS.values()}
        assert len(choices) == len(_POSTURES), (
            f"{qid} oracle choices collide: {choices}"
        )
        assert choices == set(_CONTINUED_CHOICES_BY_QUESTION[qid])


def test_indifferent_and_value_driven_oracle_paths_differ() -> None:
    assert _ORACLE_PATHS["Indifferent"] != _ORACLE_PATHS["Value-driven"]


def test_oracle_paths_pass_for_all_postures() -> None:
    for posture, path in _ORACLE_PATHS.items():
        counterfactual, matched, _, _ = _evaluate(posture, _survey_from_path(path))
        assert counterfactual is False, f"{posture} oracle failed: {matched}"


def test_decline_not_interested_is_grounded() -> None:
    counterfactual, matched, _, per_question = _evaluate(
        "Cost-sensitive",
        {
            "participation": "declined",
            "responses": [{"question_id": "q0", "choice_id": "q0_not_interested"}],
        },
    )
    assert counterfactual is False
    assert matched == []
    assert per_question["q0"]["counterfactual"] is False


def test_premium_choice_counterfactual_for_cost_sensitive() -> None:
    path = dict(_ORACLE_PATHS["Cost-sensitive"])
    path["q0"] = "q0_subscribe_paid_launch"
    path["q1"] = "q1_happy_plus_or_pro"
    counterfactual, matched, _, _ = _evaluate("Cost-sensitive", _survey_from_path(path))
    assert counterfactual is True
    assert "q0_subscribe_paid_launch" in matched


def test_single_miss_passes_at_eighty_percent() -> None:
    path = dict(_ORACLE_PATHS["Value-driven"])
    path["q2"] = "q2_monthly_cancel_anytime"
    counterfactual, matched, rationale, _ = _evaluate(
        "Value-driven", _survey_from_path(path)
    )
    assert counterfactual is False
    assert matched == []
    assert "6/7" in rationale


def test_two_misses_fail_at_eighty_percent() -> None:
    path = dict(_ORACLE_PATHS["Value-driven"])
    path["q2"] = "q2_monthly_cancel_anytime"
    path["q3"] = "q3_skip_even_one_dollar"
    counterfactual, matched, _, _ = _evaluate("Value-driven", _survey_from_path(path))
    assert counterfactual is True
    assert len(matched) == 2


def test_value_q0_counterfactual_for_cost_sensitive() -> None:
    path = dict(_ORACLE_PATHS["Cost-sensitive"])
    path["q0"] = "q0_pay_when_roi_clear"
    path["q1"] = "q1_plus_after_sustained_use"
    counterfactual, matched, _, _ = _evaluate("Cost-sensitive", _survey_from_path(path))
    assert counterfactual is True
    assert "q0_pay_when_roi_clear" in matched


def test_indifferent_q5_oracle_not_value_gate() -> None:
    path = dict(_ORACLE_PATHS["Indifferent"])
    path["q5"] = "q5_ads_pay_if_plus_useful"
    path["q6"] = "q6_fair_if_use_justifies"
    counterfactual, matched, _, _ = _evaluate("Indifferent", _survey_from_path(path))
    assert counterfactual is True
    assert "q5_ads_pay_if_plus_useful" in matched


def test_indifferent_q5_oracle_passes() -> None:
    path = dict(_ORACLE_PATHS["Indifferent"])
    counterfactual, matched, _, _ = _evaluate("Indifferent", _survey_from_path(path))
    assert counterfactual is False
    assert matched == []


def test_free_only_counterfactual_for_premium_seeking() -> None:
    path = dict(_ORACLE_PATHS["Premium-seeking"])
    path["q0"] = "q0_use_free_wont_pay"
    path["q1"] = "q1_reject_both_tiers"
    counterfactual, matched, _, _ = _evaluate(
        "Premium-seeking", _survey_from_path(path)
    )
    assert counterfactual is True
    assert "q0_use_free_wont_pay" in matched
