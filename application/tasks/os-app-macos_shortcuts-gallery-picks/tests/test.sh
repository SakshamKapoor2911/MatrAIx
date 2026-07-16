#!/usr/bin/env bash
set -uo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"

# Ensure VERIFIER_DIR exists and is writable; fall back to /tmp if not.
if ! mkdir -p "${VERIFIER_DIR}" 2>/dev/null || ! [ -w "${VERIFIER_DIR}" ]; then
  VERIFIER_DIR="/tmp/verifier_output"
  mkdir -p "${VERIFIER_DIR}"
fi
export VERIFIER_DIR

set +e
python3 <<'PY'
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

path = Path("/tmp/os-app-macos-shortcuts-gallery-picks/picks.json")

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

if data.get("browsed_gallery") is not True:
    sys.exit("browsed_gallery must be true")

categories = data.get("categories_seen")
if not isinstance(categories, list) or len(categories) < 2:
    sys.exit("categories_seen must list at least two category names")
for cat in categories:
    if not isinstance(cat, str) or not cat.strip():
        sys.exit("categories_seen entries must be non-empty strings")
cleaned_categories = [c.strip() for c in categories]

picks = data.get("picks")
if not isinstance(picks, list) or len(picks) != 3:
    sys.exit("picks must contain exactly three items")

pick_names: list[str] = []
pick_reasons: list[str] = []
pick_categories: list[str] = []
for i, pick in enumerate(picks):
    if not isinstance(pick, dict):
        sys.exit(f"pick {i} must be an object")
    name = pick.get("name", "")
    if not isinstance(name, str) or not name.strip():
        sys.exit(f"pick {i} name must be a non-empty string")
    cat = pick.get("category", "")
    if not isinstance(cat, str) or not cat.strip():
        sys.exit(f"pick {i} category must be a non-empty string")
    reason = pick.get("reason", "")
    if not isinstance(reason, str) or len(reason.strip()) < 10:
        sys.exit(f"pick {i} reason must be at least 10 characters")
    pick_names.append(name.strip())
    pick_categories.append(cat.strip())
    pick_reasons.append(reason.strip())

if len(set(pick_names)) < 3:
    sys.exit("all three picks must be distinct shortcuts")

feedback_path = Path("/app/output/user_feedback.json")
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

verifier_dir = Path(
    os.environ.get("VERIFIER_DIR")
    or os.environ.get("HARBOR_VERIFIER_DIR")
    or "/logs/verifier"
)
try:
    verifier_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    verifier_dir = Path("/tmp/verifier_output")
    verifier_dir.mkdir(parents=True, exist_ok=True)

picks_label = "; ".join(
    f"{n} ({c})" for n, c in zip(pick_names, pick_categories)
)
reasons_label = " | ".join(pick_reasons)

source_artifacts = {
    "picks": str(path),
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
                "value": f"Selected 3 shortcuts from the Gallery: {picks_label}.",
            },
            {
                "key": "completion_evidence",
                "label": "Completion evidence",
                "role": "evidence",
                "kind": "textual",
                "value": str(path),
            },
        ],
    },
    {
        "key": "goal_component.browsed_gallery",
        "label": "Browsed Gallery",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "browsed_gallery",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Browse the Shortcuts Gallery across categories",
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
                "value": 0.3,
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
                "value": f"Categories seen: {', '.join(cleaned_categories)}.",
            },
        ],
    },
    {
        "key": "goal_component.three_picks",
        "label": "Three shortcut picks",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "three_picks",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Select three shortcuts with personal-fit reasoning",
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
                "value": 0.7,
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
                "value": f"Picks: {picks_label}.",
            },
        ],
    },
]

for i, (name, cat, reason) in enumerate(zip(pick_names, pick_categories, pick_reasons)):
    contexts.append(
        {
            "key": f"decision.pick_{i + 1}",
            "label": f"Pick {i + 1}: {name}",
            "contextType": "decision",
            "facets": [
                {
                    "key": "decision_outcome",
                    "label": "Decision outcome",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "add",
                },
                {
                    "key": "basis_primary",
                    "label": "Primary basis",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "personal_fit",
                },
                {
                    "key": "decision_subject_id",
                    "label": "Decision subject ID",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": name.lower().replace(" ", "_"),
                },
                {
                    "key": "decision_subject_label",
                    "label": "Decision subject label",
                    "role": "evidence",
                    "kind": "textual",
                    "value": name,
                },
                {
                    "key": "decision_category",
                    "label": "Gallery category",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": cat,
                },
                {
                    "key": "reason",
                    "label": "Reason",
                    "role": "explanation",
                    "kind": "textual",
                    "value": reason,
                },
            ],
        }
    )

contexts.append(
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
                "value": "personal_fit",
            },
            {
                "key": "persona_alignment_explanation",
                "label": "Persona alignment explanation",
                "role": "explanation",
                "kind": "textual",
                "value": reasons_label,
            },
            {
                "key": "persona_alignment_score",
                "label": "Persona alignment score",
                "role": "score",
                "kind": "numerical",
                "value": 1.0,
            },
        ],
    }
)

contexts.append(
    {
        "key": "decision_process.primary",
        "label": "Decision process",
        "contextType": "decision_process",
        "facets": [
            {
                "key": "exploration_style",
                "label": "Exploration style",
                "role": "primary",
                "kind": "categorical",
                "value": "browse_and_categorize",
            },
            {
                "key": "process_notes",
                "label": "Process notes",
                "role": "explanation",
                "kind": "textual",
                "value": (
                    f"Browsed {len(cleaned_categories)} categories "
                    f"({', '.join(cleaned_categories)}), "
                    f"then selected: {picks_label}."
                ),
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

(verifier_dir / "structured_output.json").write_text(
    json.dumps(
        {
            "schemaVersion": "1.0",
            "artifactType": "matraix.trial_evaluation",
            "taskType": "os-app",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": ["picks.json"],
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
py_exit=$?
set -e

if [ $py_exit -eq 0 ]; then
  printf '1\n' > "${VERIFIER_DIR}/reward.txt"
else
  printf '0\n' > "${VERIFIER_DIR}/reward.txt"
fi
