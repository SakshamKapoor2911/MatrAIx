#!/bin/bash
set -euo pipefail

mkdir -p /app/output

# Reference solution. Selects this trial's case (CASE_ID, default 1) from
# /app/input/cases.jsonl, reads the injected persona's economic posture,
# and writes a schema-valid purchase_decision.json whose answers are
# internally consistent for that posture and the kind of change. Exists to
# prove the task is solvable and to exercise the verifier — a real run has
# the assigned persona reason through its own case.
python3 <<'PY'
import json
import os
import re
from pathlib import Path

output = Path("/app/output/purchase_decision.json")
persona_path = Path("/app/input/persona.yaml")
cases_path = Path("/app/input/cases.jsonl")

case_id = int(os.environ.get("CASE_ID", "1"))
case = None
if cases_path.is_file():
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("case_id") == case_id:
                case = row
                break

posture = "Value-driven"
if persona_path.is_file():
    match = re.search(
        r"economic_motivation:\s*(.+)", persona_path.read_text(encoding="utf-8")
    )
    if match:
        posture = match.group(1).strip().strip("'\"")

change_type = (case or {}).get("change", {}).get("type", "price")
what = "higher price" if change_type == "price" else "change"

# One internally consistent answer set per spending posture (case-agnostic
# reasoning; a real persona grounds this in the specific product).
DECISIONS = {
    "Cost-sensitive": {
        "purchase_intent": "probably_would_not",
        "price_fairness": "somewhat_high",
        "alternative_seeking": "yes",
        "purchase_timing": "wait_for_sale",
        "necessity_level": "nice_to_have",
        "reasoning": (
            f"After the {what} this is a want, not a need, and I can find a "
            "comparable option for less, so I'd hold off and wait for a deal."
        ),
    },
    "Value-driven": {
        "purchase_intent": "might_or_might_not",
        "price_fairness": "somewhat_high",
        "alternative_seeking": "yes",
        "purchase_timing": "wait_for_sale",
        "necessity_level": "important_but_not_urgent",
        "reasoning": (
            f"It's a solid product, but the {what} pushes it past what I'd "
            "happily pay, so I'd compare alternatives and wait for a better price."
        ),
    },
    "Premium-seeking": {
        "purchase_intent": "probably_would_buy",
        "price_fairness": "about_right",
        "alternative_seeking": "no",
        "purchase_timing": "buy_now",
        "necessity_level": "important_but_not_urgent",
        "reasoning": (
            f"I want this specific product and the quality justifies it; the "
            f"{what} doesn't really change my mind."
        ),
    },
    "Indifferent": {
        "purchase_intent": "might_or_might_not",
        "price_fairness": "about_right",
        "alternative_seeking": "no",
        "purchase_timing": "buy_now",
        "necessity_level": "nice_to_have",
        "reasoning": (
            f"The {what} is minor to me and I don't track this category closely, "
            "so it doesn't really sway me either way."
        ),
    },
}

payload = DECISIONS.get(posture, DECISIONS["Value-driven"])
output.write_text(json.dumps(payload, indent=2) + "\n")
PY
