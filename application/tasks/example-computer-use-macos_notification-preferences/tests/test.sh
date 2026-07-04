#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"

python3 <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path("/tmp/personabench-macos-calendar-reminder-handoff")
handoff_path = root / "handoff.txt"
plan_path = root / "plan.json"
if not handoff_path.is_file():
    sys.exit(f"missing {handoff_path}")
if not plan_path.is_file():
    sys.exit(f"missing {plan_path}")

data = json.loads(plan_path.read_text())
calendar_event_title = data.get("calendar_event_title", "")
if calendar_event_title != "Dentist follow-up":
    sys.exit("calendar_event_title must be 'Dentist follow-up'")
reminder_title = data.get("reminder_title", "")
if reminder_title != "Bring insurance card":
    sys.exit("reminder_title must be 'Bring insurance card'")
location = data.get("location", "")
if location != "North Clinic":
    sys.exit("location must be 'North Clinic'")
reason = data.get("reason", "")
if not isinstance(reason, str) or len(reason.strip()) < 10:
    sys.exit("reason must be at least 10 characters")

expected_lines = [
    "Calendar: Dentist follow-up | 2026-08-14 09:30 | North Clinic",
    "Reminder: Bring insurance card",
]
lines = handoff_path.read_text().splitlines()
if lines != expected_lines:
    sys.exit("handoff.txt must match the expected two-line format")

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
    os.environ.get("HARBOR_VERIFIER_DIR")
    or os.environ.get("PERSONABENCH_VERIFIER_DIR")
    or "/logs/verifier"
)
try:
    verifier_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    verifier_dir = Path.cwd() / "verifier"
    verifier_dir.mkdir(parents=True, exist_ok=True)

source_artifacts = {
    "handoff": str(handoff_path),
    "plan": str(plan_path),
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
                "value": "hybrid",
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
                "value": "The submission produced both the cross-app handoff note and the matching plan JSON.",
            },
            {
                "key": "completion_evidence",
                "label": "Completion evidence",
                "role": "evidence",
                "kind": "textual",
                "value": f"{handoff_path} and {plan_path}",
            },
        ],
    },
    {
        "key": "goal_component.handoff_note_created",
        "label": "Handoff note created",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "handoff_note_created",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Create the calendar/reminder handoff note",
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
                "value": "handoff.txt matches the expected two-line handoff format.",
            },
        ],
    },
    {
        "key": "goal_component.plan_json_created",
        "label": "Plan JSON created",
        "contextType": "goal_component",
        "facets": [
            {
                "key": "goal_component_key",
                "label": "Goal component key",
                "role": "evidence",
                "kind": "categorical",
                "value": "plan_json_created",
            },
            {
                "key": "goal_component_label",
                "label": "Goal component label",
                "role": "evidence",
                "kind": "textual",
                "value": "Create the matching plan JSON",
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
                "value": "plan.json contains the expected event title, reminder title, and location.",
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
                "value": "convenience",
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
            "artifactType": "personabench.trial_evaluation",
            "taskType": "os-app",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": ["handoff.txt", "plan.json"],
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
