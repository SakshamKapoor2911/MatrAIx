#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python3 <<'PY'
import json
import re
from pathlib import Path

output = Path("/app/output/survey_responses.json")
persona_path = Path("/app/input/persona.yaml")

posture = "Value-driven"
if persona_path.is_file():
    match = re.search(r"economic_motivation:\s*(.+)", persona_path.read_text(encoding="utf-8"))
    if match:
        posture = match.group(1).strip().strip("'\"")

PATHS: dict[str, dict[str, str]] = {
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

choices = PATHS.get(posture, PATHS["Value-driven"])
responses = [{"question_id": q, "choice_id": cid} for q, cid in choices.items()]

payload = {
    "participation": "continued",
    "responses": responses,
    "overall_interest": 3,
    "would_try_beta": False,
}

output.write_text(json.dumps(payload, indent=2) + "\n")
PY
