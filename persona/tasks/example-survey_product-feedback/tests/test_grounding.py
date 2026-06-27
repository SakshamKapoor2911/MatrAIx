"""Trial-level economic_motivation grounding — spending-posture MCQ checkpoints.

Each continued question (q0–q6) has four options in a 1:1 mapping to probe postures.
Scoring is oracle whitelist with an alignment threshold (default 80% = 6/7 on continued).
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import yaml

OUTPUT = Path("/app/output/survey_responses.json")
PERSONA = Path("/app/input/persona.yaml")
GROUNDING_LOG = Path("/logs/verifier/grounding.json")

ALIGNMENT_PASS_THRESHOLD = 0.8

POSTURES = (
    "Cost-sensitive",
    "Value-driven",
    "Premium-seeking",
    "Indifferent",
)

PROBE_QUESTION_IDS = frozenset({f"q{i}" for i in range(7)})

# 4×7 oracle matrix — one accepted choice per (posture, question).
ORACLE_PATHS: dict[str, dict[str, str]] = {
    "Cost-sensitive": {
        "q0": "q0_use_free_wont_pay",
        "q1": "q1_reject_both_tiers",
        "q2": "q2_monthly_cancel_anytime",
        "q3": "q3_skip_even_one_dollar",
        "q4": "q4_seek_free_alternative",
        "q5": "q5_ads_not_worth_paying",
        "q6": "q6_too_expensive_stay_free",
    },
    "Value-driven": {
        "q0": "q0_pay_when_roi_clear",
        "q1": "q1_plus_after_sustained_use",
        "q2": "q2_annual_after_long_use",
        "q3": "q3_one_dollar_try_cancel",
        "q4": "q4_compare_pay_if_wins",
        "q5": "q5_ads_pay_if_plus_useful",
        "q6": "q6_fair_if_use_justifies",
    },
    "Premium-seeking": {
        "q0": "q0_subscribe_paid_launch",
        "q1": "q1_happy_plus_or_pro",
        "q2": "q2_prepay_annual_plus",
        "q3": "q3_grab_dollar_promo",
        "q4": "q4_pay_best_no_hunt",
        "q5": "q5_pay_primarily_adfree",
        "q6": "q6_premium_price_ok",
    },
    "Indifferent": {
        "q0": "q0_free_never_decide_tier",
        "q1": "q1_wont_compare_tiers",
        "q2": "q2_billing_no_preference",
        "q3": "q3_ignore_promo",
        "q4": "q4_switch_only_effortless",
        "q5": "q5_ads_irrelevant_to_tier",
        "q6": "q6_pricing_unnoticed",
    },
}

CONTINUED_CHOICES_BY_QUESTION: dict[str, frozenset[str]] = {
    qid: frozenset(path[qid] for path in ORACLE_PATHS.values())
    for qid in PROBE_QUESTION_IDS
}

# Derived blacklist: any continued choice that is not the oracle for this posture.
COUNTERFACTUAL_CHOICES: dict[str, frozenset[str]] = {
    posture: frozenset(
        choice_id
        for qid in PROBE_QUESTION_IDS
        for choice_id in CONTINUED_CHOICES_BY_QUESTION[qid]
        if ORACLE_PATHS[posture][qid] != choice_id
    )
    for posture in POSTURES
}

DECLINE_GROUNDED_Q0: dict[str, frozenset[str]] = {
    posture: frozenset({"q0_not_interested"}) for posture in POSTURES
}


def _min_oracle_matches(
    n_scored: int, *, threshold: float = ALIGNMENT_PASS_THRESHOLD
) -> int:
    if n_scored <= 0:
        return 0
    return math.ceil(n_scored * threshold)


def _alignment_rate(n_oracle_matches: int, n_scored: int) -> float:
    if n_scored <= 0:
        return 0.0
    return n_oracle_matches / n_scored


def _passes_alignment(n_oracle_matches: int, n_scored: int) -> bool:
    return _alignment_rate(n_oracle_matches, n_scored) >= ALIGNMENT_PASS_THRESHOLD


def _write_grounding(payload: dict) -> None:
    GROUNDING_LOG.parent.mkdir(parents=True, exist_ok=True)
    GROUNDING_LOG.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _probe_choice_map(survey: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in survey.get("responses") or []:
        if not isinstance(entry, dict):
            continue
        qid = entry.get("question_id")
        cid = entry.get("choice_id")
        if not isinstance(qid, str) or not isinstance(cid, str):
            continue
        qid = qid.strip()
        if qid in PROBE_QUESTION_IDS:
            out[qid] = cid.strip()
    return out


def _per_question_hits(
    *,
    choices: dict[str, str],
    counterfactual_set: frozenset[str],
    participation: str,
    probe_value: str,
) -> dict[str, dict[str, object]]:
    decline_ok = DECLINE_GROUNDED_Q0.get(probe_value, frozenset())
    per_question: dict[str, dict[str, object]] = {}

    for qid in sorted(PROBE_QUESTION_IDS):
        cid = choices.get(qid)
        if cid is None:
            continue
        if participation == "declined" and qid != "q0":
            continue
        if participation == "declined" and qid == "q0":
            counterfactual = cid not in decline_ok
        else:
            counterfactual = cid in counterfactual_set
        oracle = ORACLE_PATHS.get(probe_value, {}).get(qid)
        per_question[qid] = {
            "choice_id": cid,
            "counterfactual": counterfactual,
            "oracle_choice_id": oracle,
            "oracle_match": cid == oracle if oracle else None,
        }

    return per_question


def _evaluate_economic_motivation(
    probe_value: str, survey: dict
) -> tuple[bool, list[str], str, dict[str, dict[str, object]]]:
    choices = _probe_choice_map(survey)
    participation = survey.get("participation")
    counterfactual_set = COUNTERFACTUAL_CHOICES.get(probe_value, frozenset())
    per_question = _per_question_hits(
        choices=choices,
        counterfactual_set=counterfactual_set,
        participation=participation,
        probe_value=probe_value,
    )
    matched = sorted(
        entry["choice_id"]
        for entry in per_question.values()
        if entry.get("oracle_match") is False
    )

    if participation == "declined":
        q0 = choices.get("q0")
        decline_ok = DECLINE_GROUNDED_Q0.get(probe_value, frozenset())
        if q0 in decline_ok:
            return False, [], "Declined — not interested in this product.", per_question
        if matched:
            return True, matched, "Declined with counterfactual q0.", per_question
        return False, [], "Declined — no counterfactual checkpoint hit.", per_question

    n_scored = len(per_question)
    n_oracle_matches = sum(
        1 for entry in per_question.values() if entry.get("oracle_match") is True
    )
    rate = _alignment_rate(n_oracle_matches, n_scored)
    if _passes_alignment(n_oracle_matches, n_scored):
        return (
            False,
            [],
            f"Aligned {n_oracle_matches}/{n_scored} ({rate:.0%} ≥ {ALIGNMENT_PASS_THRESHOLD:.0%}).",
            per_question,
        )

    return (
        True,
        matched,
        (
            f"Below {ALIGNMENT_PASS_THRESHOLD:.0%} alignment for {probe_value}: "
            f"{n_oracle_matches}/{n_scored} ({rate:.0%}); need "
            f"{_min_oracle_matches(n_scored)}."
        ),
        per_question,
    )


def test_dim_grounding_heuristic() -> None:
    probe_dimension = (
        os.environ.get("PERSONABENCH_PROBE_DIMENSION")
        or os.environ.get("MATRAIX_PROBE_DIMENSION", "")
    ).strip()
    if not probe_dimension:
        _write_grounding(
            {
                "skipped": True,
                "reason": "PERSONABENCH_PROBE_DIMENSION env not set",
            }
        )
        return

    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    assert PERSONA.is_file(), f"Missing {PERSONA}"
    persona = yaml.safe_load(PERSONA.read_text(encoding="utf-8"))
    assert isinstance(persona, dict)

    probe_value = (
        os.environ.get("PERSONABENCH_PROBE_VALUE")
        or os.environ.get("MATRAIX_PROBE_VALUE", "")
    ).strip()
    if not probe_value:
        parts = probe_dimension.split(".")
        current: object = persona
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        probe_value = str(current) if current is not None else ""

    if not probe_value:
        _write_grounding(
            {
                "skipped": True,
                "reason": f"Could not resolve {probe_dimension!r} from persona",
            }
        )
        return

    survey = json.loads(OUTPUT.read_text(encoding="utf-8"))
    counterfactual = False
    matched: list[str] = []
    rationale = "Probe not evaluated."
    per_question: dict[str, dict[str, object]] = {}

    if probe_dimension == "dimensions.economic_motivation":
        counterfactual, matched, rationale, per_question = (
            _evaluate_economic_motivation(probe_value, survey)
        )
    else:
        rationale = f"No checkpoint table for {probe_dimension!r}."

    n_scored = len(per_question)
    n_counterfactual_choices = sum(
        1 for entry in per_question.values() if entry.get("counterfactual")
    )
    oracle_path = ORACLE_PATHS.get(probe_value, {})
    n_oracle_matches = sum(
        1 for qid, entry in per_question.items() if entry.get("oracle_match") is True
    )
    alignment_rate = _alignment_rate(n_oracle_matches, n_scored)
    grounding_pass = _passes_alignment(n_oracle_matches, n_scored)
    min_matches = _min_oracle_matches(n_scored)

    payload = {
        "probe_dimension": probe_dimension,
        "probe_value": probe_value,
        "participation": survey.get("participation"),
        "probe_questions": sorted(PROBE_QUESTION_IDS),
        "oracle_path": oracle_path,
        "per_question": per_question,
        "probe_hits": n_counterfactual_choices,
        "probe_questions_scored": n_scored,
        "oracle_match_count": n_oracle_matches,
        "min_oracle_matches": min_matches,
        "pass_threshold": ALIGNMENT_PASS_THRESHOLD,
        "alignment_rate": alignment_rate,
        "dim_grounding": 1.0 if grounding_pass else 0.0,
        "counterfactual": not grounding_pass,
        "method": "mcq_oracle_threshold",
        "matched_cues": matched,
        "rationale": rationale,
        "persona_id": persona.get("persona_id"),
    }

    _write_grounding(payload)
    assert grounding_pass, (
        f"Grounding below {ALIGNMENT_PASS_THRESHOLD:.0%} for {probe_value}: "
        f"{n_oracle_matches}/{n_scored} ({alignment_rate:.0%}); need {min_matches}. "
        f"Misses: {matched}"
    )
