"""Verifier for the price-perturbation purchase-intent survey.

Validates the agent's purchase_decision.json against the six-field schema,
emits structured_output.json for aggregation, and returns an exit code.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

OUTPUT_DIR = Path(
    os.environ.get("PERSONABENCH_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
OUTPUT_PATH = OUTPUT_DIR / "purchase_decision.json"

ALLOWED = {
    "purchase_intent": {
        "definitely_would_buy",
        "probably_would_buy",
        "might_or_might_not",
        "probably_would_not",
        "definitely_would_not",
    },
    "price_fairness": {
        "much_too_high",
        "somewhat_high",
        "about_right",
        "good_value",
        "great_value",
    },
    "alternative_seeking": {"yes", "no"},
    "purchase_timing": {"buy_now", "wait_for_sale", "not_planning_to_buy"},
    "necessity_level": {
        "essential",
        "important_but_not_urgent",
        "nice_to_have",
    },
}
REQUIRED_FIELDS = (*ALLOWED.keys(), "reasoning")


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


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _field_kind(value: object) -> str:
    if isinstance(value, bool):
        return "categorical"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "numerical"
    return "textual"


def main() -> int:
    if not OUTPUT_PATH.is_file():
        _write_structured_output({
            "schemaVersion": "1.0",
            "artifactType": "personabench.trial_evaluation",
            "taskType": "survey",
            "presenceCheck": {
                "passed": False,
                "requiredArtifacts": ["purchase_decision.json"],
                "missingArtifacts": ["purchase_decision.json"],
            },
            "contexts": [],
            "fields": [],
        })
        return fail(f"missing {OUTPUT_PATH}")
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        _write_structured_output({
            "schemaVersion": "1.0",
            "artifactType": "personabench.trial_evaluation",
            "taskType": "survey",
            "presenceCheck": {
                "passed": False,
                "requiredArtifacts": ["purchase_decision.json"],
                "missingArtifacts": [],
            },
            "contexts": [],
            "fields": [],
        })
        return fail(f"purchase_decision.json is not valid JSON: {exc}")
    if not isinstance(data, dict):
        _write_structured_output({
            "schemaVersion": "1.0",
            "artifactType": "personabench.trial_evaluation",
            "taskType": "survey",
            "contexts": [],
            "fields": [],
        })
        return fail("purchase_decision.json must contain a JSON object")

    keys = set(data)
    missing_keys = set(REQUIRED_FIELDS) - keys
    extra_keys = keys - set(REQUIRED_FIELDS)
    if missing_keys:
        _write_structured_output({
            "schemaVersion": "1.0",
            "artifactType": "personabench.trial_evaluation",
            "taskType": "survey",
            "contexts": [],
            "fields": [
                {
                    "key": "verifier.missing_fields",
                    "label": "Missing fields",
                    "group": "verifier",
                    "role": "score",
                    "kind": "categorical",
                    "value": sorted(missing_keys),
                }
            ],
        })
        return fail(f"missing fields: {sorted(missing_keys)}")
    if extra_keys:
        return fail(f"unexpected fields: {sorted(extra_keys)}")

    contexts: list[dict[str, object]] = []
    fields: list[dict[str, object]] = []

    for field, allowed in ALLOWED.items():
        value = data[field]
        if value not in allowed:
            _write_structured_output({
                "schemaVersion": "1.0",
                "artifactType": "personabench.trial_evaluation",
                "taskType": "survey",
                "contexts": [],
                "fields": [
                    {
                        "key": f"survey.{field}",
                        "label": field,
                        "group": "survey.answers",
                        "role": "primary",
                        "kind": "categorical",
                        "value": value,
                    },
                ],
            })
            return fail(f"{field}={value!r} not in {sorted(allowed)}")
        kind = _field_kind(value)
        fields.append({
            "key": f"survey.{field}",
            "label": field,
            "group": "survey.answers",
            "role": "primary",
            "kind": kind,
            "value": value,
        })
        contexts.append({
            "key": f"survey.{field}",
            "label": field,
            "contextType": "question_response",
            "facets": [
                {
                    "key": "response",
                    "label": "Selected response",
                    "role": "primary",
                    "kind": kind,
                    "value": value,
                }
            ],
        })

    reasoning = data["reasoning"]
    if not isinstance(reasoning, str) or not reasoning.strip():
        _write_structured_output({
            "schemaVersion": "1.0",
            "artifactType": "personabench.trial_evaluation",
            "taskType": "survey",
            "contexts": [],
            "fields": [
                {
                    "key": "survey.reasoning",
                    "label": "Reasoning",
                    "group": "survey.answers",
                    "role": "primary",
                    "kind": "textual",
                    "value": reasoning,
                },
            ],
        })
        return fail("reasoning must be a non-empty string")

    fields.append({
        "key": "survey.reasoning",
        "label": "Reasoning",
        "group": "survey.answers",
        "role": "primary",
        "kind": "textual",
        "value": reasoning,
    })
    contexts.append({
        "key": "survey.reasoning",
        "label": "Reasoning",
        "contextType": "question_response",
        "facets": [
            {
                "key": "response",
                "label": "Reasoning text",
                "role": "primary",
                "kind": "textual",
                "value": reasoning,
            }
        ],
    })

    _write_structured_output({
        "schemaVersion": "1.0",
        "artifactType": "personabench.trial_evaluation",
        "taskType": "survey",
        "sourceArtifacts": {"purchaseDecision": str(OUTPUT_PATH)},
        "presenceCheck": {
            "passed": True,
            "requiredArtifacts": ["purchase_decision.json"],
            "missingArtifacts": [],
        },
        "contexts": contexts,
        "fields": fields,
    })
    print("purchase_decision.json is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
