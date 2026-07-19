#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"
export VERIFIER_DIR

python3 <<'PY'
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _llm_signal_facets(text, *, specs, context_desc, rubric):
    """Best-effort LLM signal extraction rendered as categorical facets.

    Returns [] on any failure (missing OPENAI_API_KEY, no network, bad JSON, or a
    timeout). Grading must never depend on this: these signals are additive
    reporting facets only, so a failed call simply omits them and the trial still
    passes on its deterministic facts.
    """
    import urllib.request

    api_key = os.environ.get("OPENAI_API_KEY")
    body_text = (text or "").strip()
    if not api_key or not body_text:
        return []
    model = os.environ.get("MODEL_NAME", "gpt-4o-mini")
    base = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("OPENAI_API_BASE")
        or "https://api.openai.com/v1"
    ).rstrip("/")
    schema = "\n".join(f"- {key}: {label}" for key, label in specs)
    system = (
        f"{context_desc} Return ONLY a JSON object whose keys are exactly these, "
        f"each a boolean:\n{schema}\nRubric: {rubric}"
    )
    request_body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": body_text[:12000]},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    try:
        request = urllib.request.Request(
            f"{base}/chat/completions",
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            completion = json.loads(response.read().decode("utf-8"))
        content = completion["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except Exception:  # grading must survive any LLM failure
        return []
    facets = []
    for key, label in specs:
        value = parsed.get(key)
        if isinstance(value, bool):
            facets.append(
                {
                    "key": key,
                    "label": label,
                    "role": "evidence",
                    "kind": "categorical",
                    "value": "true" if value else "false",
                }
            )
    return facets


OUTPUT_DIR = Path(
    os.environ.get("HARBOR_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or "/app/output"
)

path = OUTPUT_DIR / "decision.json"

if not path.is_file():
    logs_root = Path("/tmp/harbor/logs") if Path("/tmp/harbor/logs").is_dir() else Path("/logs")
    fa_path = logs_root / "agent" / "final_answer.txt"
    if fa_path.is_file():
        raw = fa_path.read_text(encoding="utf-8", errors="replace").strip()
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                candidate = json.loads(match.group())
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False))
            except (json.JSONDecodeError, OSError):
                pass

if not path.is_file():
    sys.exit(f"missing {path}")

data = json.loads(path.read_text())
app = data.get("app_reviewed", "")
if not isinstance(app, str) or not app.strip():
    sys.exit("app_reviewed must be a non-empty string")

if data.get("browsed_full_offer") is not True:
    sys.exit("browsed_full_offer must be true")
if data.get("reviewed_features_and_pricing") is not True:
    sys.exit("reviewed_features_and_pricing must be true")

clicked = data.get("clicked_get_started")
if not isinstance(clicked, bool):
    sys.exit("clicked_get_started must be a boolean")

price_seen = data.get("price_seen", "")
if not isinstance(price_seen, str) or not price_seen.strip():
    sys.exit("price_seen must be a non-empty string")

highlights = data.get("highlights_noticed")
if not isinstance(highlights, list) or not highlights:
    sys.exit("highlights_noticed must be a non-empty list")
cleaned_highlights: list[str] = []
for item in highlights:
    if not isinstance(item, str) or not item.strip():
        sys.exit("highlights_noticed entries must be non-empty strings")
    cleaned_highlights.append(item.strip())

reason = data.get("reason", "")
if not isinstance(reason, str) or len(reason.strip()) < 10:
    sys.exit("reason must be at least 10 characters")

decision = "subscribe" if clicked else "decline"
basis = "pack_value" if clicked else "price"
highlights_label = ", ".join(cleaned_highlights)

feedback_path = OUTPUT_DIR / "user_feedback.json"
satisfaction_buckets = {"yes", "partially", "no"}


def load_user_feedback() -> dict[str, object] | None:
    if not feedback_path.is_file():
        return None
    feedback = json.loads(feedback_path.read_text())
    if not isinstance(feedback, dict):
        sys.exit("user_feedback.json root must be an object")

    need = feedback.get("needConstraintSatisfaction")
    if need not in satisfaction_buckets:
        sys.exit("needConstraintSatisfaction must use a supported bucket")
    preference = feedback.get("personalPreferenceSatisfaction")
    if preference not in satisfaction_buckets:
        sys.exit("personalPreferenceSatisfaction must use a supported bucket")
    rating = feedback.get("overallExperienceRating")
    if not isinstance(rating, (int, float)):
        sys.exit("overallExperienceRating must be numeric")
    rating = int(round(float(rating)))
    if not 1 <= rating <= 10:
        sys.exit("overallExperienceRating must be between 1 and 10")
    feedback_reason = feedback.get("reason")
    if not isinstance(feedback_reason, str) or not feedback_reason.strip():
        sys.exit("feedback reason must be non-empty")

    payload: dict[str, object] = {
        "need_constraint_satisfaction": need,
        "personal_preference_satisfaction": preference,
        "overall_experience_rating": rating,
        "feedback_reason": feedback_reason.strip(),
    }
    trust = feedback.get("trustLevel")
    if trust is not None:
        if not isinstance(trust, (int, float)):
            sys.exit("trustLevel must be numeric")
        trust = int(round(float(trust)))
        if not 1 <= trust <= 10:
            sys.exit("trustLevel must be between 1 and 10")
        payload["trust_level"] = trust
    effort = feedback.get("effortRating")
    if effort is not None:
        if not isinstance(effort, (int, float)):
            sys.exit("effortRating must be numeric")
        effort = int(round(float(effort)))
        if not 1 <= effort <= 10:
            sys.exit("effortRating must be between 1 and 10")
        payload["effort_rating"] = effort
    clarity = feedback.get("clarityOfNextStep")
    if clarity is not None:
        if not isinstance(clarity, bool):
            sys.exit("clarityOfNextStep must be boolean")
        payload["clarity_of_next_step"] = "true" if clarity else "false"
    return payload


feedback = load_user_feedback()

verifier_dir_raw = os.environ.get("VERIFIER_DIR") or os.environ.get("HARBOR_VERIFIER_DIR")
if not verifier_dir_raw:
    sys.exit("VERIFIER_DIR or HARBOR_VERIFIER_DIR is required")
verifier_dir = Path(verifier_dir_raw)
try:
    verifier_dir.mkdir(parents=True, exist_ok=True)
except OSError as exc:
    sys.exit(f"cannot create verifier directory {verifier_dir}: {exc}")

source_artifacts = {
    "decision": str(path),
}
contexts = [
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
                    "The submission finished the News+ offer browse and "
                    f"{'tapped' if clicked else 'did not tap'} Get Started."
                ),
            },
            {
                "key": "completion_evidence",
                "label": "Completion evidence",
                "role": "evidence",
                "kind": "textual",
                "value": f"clicked_get_started={clicked} -> {decision}",
            },
        ],
    },
    {
        "key": "goal_component.browsed_full_offer",
        "label": "Browsed full offer",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "browsed_full_offer",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Scroll through the full subscription offer page",
            },
            {
                "key": "goal_component_status",
                "label": "Goal component status",
                "role": "primary",
                "kind": "categorical",
                "value": "passed",
            },
            {
                "key": "goal_component_weight",
                "label": "Goal component weight",
                "role": "score",
                "kind": "numerical",
                "value": 0.25,
            },
            {
                "key": "goal_component_required",
                "label": "Goal component required",
                "role": "evidence",
                "kind": "categorical",
                "value": "true",
            },
            {
                "key": "goal_component_evidence",
                "label": "Goal component evidence",
                "role": "explanation",
                "kind": "textual",
                "value": f"Highlights noticed: {highlights_label}.",
            },
        ],
    },
    {
        "key": "goal_component.reviewed_features_and_pricing",
        "label": "Reviewed features and pricing",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "reviewed_features_and_pricing",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Return to the top and re-check features and pricing",
            },
            {
                "key": "goal_component_status",
                "label": "Goal component status",
                "role": "primary",
                "kind": "categorical",
                "value": "passed",
            },
            {
                "key": "goal_component_weight",
                "label": "Goal component weight",
                "role": "score",
                "kind": "numerical",
                "value": 0.25,
            },
            {
                "key": "goal_component_required",
                "label": "Goal component required",
                "role": "evidence",
                "kind": "categorical",
                "value": "true",
            },
            {
                "key": "goal_component_evidence",
                "label": "Goal component evidence",
                "role": "explanation",
                "kind": "textual",
                "value": f"Price seen: {price_seen.strip()}.",
            },
        ],
    },
    {
        "key": "goal_component.get_started_decision",
        "label": "Get Started decision",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "get_started_decision",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Tap Get Started only if converting, then end",
            },
            {
                "key": "goal_component_status",
                "label": "Goal component status",
                "role": "primary",
                "kind": "categorical",
                "value": "passed",
            },
            {
                "key": "goal_component_weight",
                "label": "Goal component weight",
                "role": "score",
                "kind": "numerical",
                "value": 0.5,
            },
            {
                "key": "goal_component_required",
                "label": "Goal component required",
                "role": "evidence",
                "kind": "categorical",
                "value": "true",
            },
            {
                "key": "goal_component_evidence",
                "label": "Goal component evidence",
                "role": "explanation",
                "kind": "textual",
                "value": (
                    "clicked_get_started="
                    f"{str(clicked).lower()} ({decision})."
                ),
            },
        ],
    },
    {
        "key": "decision.primary",
        "label": "Primary subscription decision",
        "contextType": "decision",
        "facets": [
            {
                "key": "decision_outcome",
                "label": "Decision outcome",
                "role": "primary",
                "kind": "categorical",
                "value": decision,
            },
            {
                "key": "basis_primary",
                "label": "Primary basis",
                "role": "primary",
                "kind": "categorical",
                "value": basis,
            },
            {
                "key": "clicked_get_started",
                "label": "Clicked Get Started",
                "role": "evidence",
                "kind": "categorical",
                "value": "true" if clicked else "false",
            },
            {
                "key": "price_sensitivity",
                "label": "Price sensitivity",
                "role": "evidence",
                "kind": "categorical",
                "value": "willing" if clicked else "unwilling",
            },
            {
                "key": "price_seen",
                "label": "Price seen",
                "role": "evidence",
                "kind": "textual",
                "value": price_seen.strip(),
            },
            {
                "key": "reason",
                "label": "Reason",
                "role": "explanation",
                "kind": "textual",
                "explainsFacetKey": "decision_outcome",
                "value": reason.strip(),
            },
            {
                "key": "decision_subject_id",
                "label": "Decision subject ID",
                "role": "evidence",
                "kind": "categorical",
                "value": "news_plus",
            },
            {
                "key": "decision_subject_label",
                "label": "Decision subject label",
                "role": "evidence",
                "kind": "textual",
                "value": "Apple News+",
            },
            {
                "key": "highlights_noticed",
                "label": "Highlights noticed",
                "role": "evidence",
                "kind": "textual",
                "value": highlights_label,
            },
        ],
    },
    {
        "key": "persona_alignment.primary",
        "label": "Persona alignment",
        "contextType": "persona_alignment",
        "facets": [
            {
                "key": "persona_alignment_status",
                "label": "Persona alignment status",
                "role": "primary",
                "kind": "categorical",
                "value": "aligned",
            },
            {
                "key": "persona_preference_axis_primary",
                "label": "Primary preference axis",
                "role": "primary",
                "kind": "categorical",
                "value": basis,
            },
            {
                "key": "persona_alignment_explanation",
                "label": "Persona alignment explanation",
                "role": "explanation",
                "kind": "textual",
                "value": reason.strip(),
            },
            {
                "key": "persona_alignment_score",
                "label": "Persona alignment score",
                "role": "score",
                "kind": "numerical",
                "value": 1.0,
            },
        ],
    },
]
if not clicked:
    contexts.append(
        {
            "key": "persona_constraint.primary",
            "label": "Persona constraint",
            "contextType": "persona_constraint",
            "facets": [
                {
                    "key": "persona_constraint_type",
                    "label": "Persona constraint type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "price",
                },
                {
                    "key": "persona_constraint_status",
                    "label": "Persona constraint status",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "satisfied",
                },
                {
                    "key": "persona_constraint_evidence",
                    "label": "Persona constraint evidence",
                    "role": "explanation",
                    "kind": "textual",
                    "value": reason.strip(),
                },
            ],
        }
    )
if feedback is not None:
    source_artifacts["userFeedback"] = str(feedback_path)
    feedback_facets = [
        {
            "key": "overall_experience_rating",
            "label": "Overall experience rating",
            "role": "score",
            "kind": "numerical",
            "value": feedback["overall_experience_rating"],
        },
        {
            "key": "feedback_reason",
            "label": "Feedback reason",
            "role": "explanation",
            "kind": "textual",
            "explainsFacetKey": "need_constraint_satisfaction",
            "value": feedback["feedback_reason"],
        },
        {
            "key": "need_constraint_satisfaction",
            "label": "Need or constraint satisfaction",
            "role": "evidence",
            "kind": "categorical",
            "value": feedback["need_constraint_satisfaction"],
        },
        {
            "key": "personal_preference_satisfaction",
            "label": "Personal preference satisfaction",
            "role": "evidence",
            "kind": "categorical",
            "value": feedback["personal_preference_satisfaction"],
        },
    ]
    if "trust_level" in feedback:
        feedback_facets.append(
            {
                "key": "trust_level",
                "label": "Trust level",
                "role": "score",
                "kind": "numerical",
                "value": feedback["trust_level"],
            }
        )
    if "effort_rating" in feedback:
        feedback_facets.append(
            {
                "key": "effort_rating",
                "label": "Effort rating",
                "role": "score",
                "kind": "numerical",
                "value": feedback["effort_rating"],
            }
        )
    if "clarity_of_next_step" in feedback:
        feedback_facets.append(
            {
                "key": "clarity_of_next_step",
                "label": "Clarity of next step",
                "role": "evidence",
                "kind": "categorical",
                "value": feedback["clarity_of_next_step"],
            }
        )
    contexts.append(
        {
            "key": "user_feedback.primary",
            "label": "User feedback",
            "contextType": "user_feedback",
            "facets": feedback_facets,
        }
    )

_decision_signals = _llm_signal_facets(
    reason.strip(),
    specs=[
        ("substitute_signal", "Already gets news elsewhere (substitution)"),
        ("habit_signal", "Habit or effort barrier to adopting"),
    ],
    context_desc=(
        "You advise the team that owns the Apple News+ subscription offer. Read the "
        "persona's decision reason and flag which non-conversion drivers are present."
    ),
    rubric=(
        "Mark true only when the reason clearly states or strongly implies it. Do not "
        "infer from persona metadata that is not in the reason text."
    ),
)
if _decision_signals:
    for _ctx in contexts:
        if _ctx.get("key") == "decision.primary":
            _ctx["facets"].extend(_decision_signals)
            break

(verifier_dir / "structured_output.json").write_text(
    json.dumps(
        {
            "schemaVersion": "1.0",
            "artifactType": "matraix.trial_evaluation",
            "taskType": "os-app",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": ["decision.json"],
                "missingArtifacts": [],
            },
            "sourceArtifacts": source_artifacts,
            "contexts": contexts,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
PY

if [ $? -eq 0 ]; then
  printf '1\n' > "${VERIFIER_DIR}/reward.txt"
else
  printf '0\n' > "${VERIFIER_DIR}/reward.txt"
fi
