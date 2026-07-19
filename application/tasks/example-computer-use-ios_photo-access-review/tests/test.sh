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
level = data.get("photo_access_level")
if level not in {"full_access", "selected_photos", "none"}:
    sys.exit("photo_access_level must be one of: full_access, selected_photos, none")
reason = data.get("reason", "")
if not isinstance(reason, str) or len(reason.strip()) < 10:
    sys.exit("reason must be at least 10 characters")

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
                "value": f"The submission selected a valid photo access level for {app.strip()}.",
            },
            {
                "key": "completion_evidence",
                "label": "Completion evidence",
                "role": "evidence",
                "kind": "textual",
                "value": f"{app.strip()} -> {level}",
            },
        ],
    },
    {
        "key": "goal_component.reviewed_app",
        "label": "Reviewed app",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "reviewed_app",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Review one app in the Photos privacy area",
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
                "value": f"The submission reviewed {app.strip()}.",
            },
        ],
    },
    {
        "key": "goal_component.access_level_decided",
        "label": "Access level decided",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "access_level_decided",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Choose a valid photo access level",
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
                "value": f"The submission chose {level}.",
            },
        ],
    },
    {
        "key": "decision.primary",
        "label": "Primary decision",
        "contextType": "decision",
        "facets": [
            {
                "key": "decision_outcome",
                "label": "Decision outcome",
                "role": "primary",
                "kind": "categorical",
                "value": "selected",
            },
            {
                "key": "basis_primary",
                "label": "Primary basis",
                "role": "primary",
                "kind": "categorical",
                "value": "privacy",
            },
            {
                "key": "reason",
                "label": "Reason",
                "role": "explanation",
                "kind": "textual",
                "value": reason.strip(),
            },
            {
                "key": "decision_subject_id",
                "label": "Decision subject ID",
                "role": "evidence",
                "kind": "categorical",
                "value": app.strip().lower().replace(" ", "_"),
            },
            {
                "key": "decision_subject_label",
                "label": "Decision subject label",
                "role": "evidence",
                "kind": "textual",
                "value": app.strip(),
            },
            {
                "key": "photo_access_level",
                "label": "Photo access level",
                "role": "evidence",
                "kind": "categorical",
                "value": level,
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
                "value": "privacy",
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
if level in {"selected_photos", "none"}:
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
                    "value": "privacy",
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
