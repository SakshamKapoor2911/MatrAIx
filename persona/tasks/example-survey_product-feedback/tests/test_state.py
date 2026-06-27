import json
from pathlib import Path

OUTPUT = Path("/app/output/survey_responses.json")

VALID_CHOICES: dict[str, set[str]] = {
    "q0": {
        "q0_use_free_wont_pay",
        "q0_pay_when_roi_clear",
        "q0_subscribe_paid_launch",
        "q0_free_never_decide_tier",
        "q0_not_interested",
    },
    "q1": {
        "q1_reject_both_tiers",
        "q1_plus_after_sustained_use",
        "q1_happy_plus_or_pro",
        "q1_wont_compare_tiers",
    },
    "q2": {
        "q2_monthly_cancel_anytime",
        "q2_annual_after_long_use",
        "q2_prepay_annual_plus",
        "q2_billing_no_preference",
    },
    "q3": {
        "q3_skip_even_one_dollar",
        "q3_one_dollar_try_cancel",
        "q3_grab_dollar_promo",
        "q3_ignore_promo",
    },
    "q4": {
        "q4_seek_free_alternative",
        "q4_compare_pay_if_wins",
        "q4_pay_best_no_hunt",
        "q4_switch_only_effortless",
    },
    "q5": {
        "q5_ads_not_worth_paying",
        "q5_ads_pay_if_plus_useful",
        "q5_pay_primarily_adfree",
        "q5_ads_irrelevant_to_tier",
    },
    "q6": {
        "q6_too_expensive_stay_free",
        "q6_fair_if_use_justifies",
        "q6_premium_price_ok",
        "q6_pricing_unnoticed",
    },
}

CONTINUED_QUESTION_IDS = ("q0", "q1", "q2", "q3", "q4", "q5", "q6")
DECLINED_QUESTION_IDS = ("q0",)


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text())
    assert isinstance(data, dict), "root must be an object"
    return data


def _choice_map(data: dict) -> dict[str, str]:
    responses = data.get("responses")
    assert isinstance(responses, list) and responses, (
        "responses must be a non-empty list"
    )
    seen: dict[str, str] = {}
    for entry in responses:
        assert isinstance(entry, dict), "each response must be an object"
        qid = entry.get("question_id")
        choice_id = entry.get("choice_id")
        assert isinstance(qid, str) and qid.strip(), (
            "question_id must be a non-empty string"
        )
        assert isinstance(choice_id, str) and choice_id.strip(), (
            "choice_id must be a non-empty string"
        )
        qid = qid.strip()
        choice_id = choice_id.strip()
        assert qid in VALID_CHOICES, f"unknown question_id: {qid!r}"
        assert choice_id in VALID_CHOICES[qid], (
            f"invalid choice_id {choice_id!r} for {qid!r}"
        )
        assert qid not in seen, f"duplicate question_id: {qid!r}"
        seen[qid] = choice_id
    return seen


def test_output_exists():
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_output_schema():
    data = _load()
    participation = data.get("participation")
    assert participation in {"continued", "declined"}, (
        'participation must be "continued" or "declined"'
    )

    choices = _choice_map(data)
    required = (
        CONTINUED_QUESTION_IDS
        if participation == "continued"
        else DECLINED_QUESTION_IDS
    )
    missing = set(required) - set(choices)
    assert not missing, f"missing question_ids for {participation}: {sorted(missing)}"

    if participation == "continued":
        extra = set(choices) - set(CONTINUED_QUESTION_IDS)
        assert not extra, f"unexpected question_ids for continued: {sorted(extra)}"

    interest = data.get("overall_interest")
    assert isinstance(interest, int) and 1 <= interest <= 5, (
        "overall_interest must be an integer from 1 to 5"
    )

    assert isinstance(data.get("would_try_beta"), bool), (
        "would_try_beta must be boolean"
    )
