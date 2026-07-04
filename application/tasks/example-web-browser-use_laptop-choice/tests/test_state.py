from __future__ import annotations

import json
import os
import re
from pathlib import Path

OUTPUT = Path("/app/output/laptop_choice.json")
USER_FEEDBACK = Path("/app/output/user_feedback.json")
PRICE_PATTERN = re.compile(r"^\$\d+\.\d{2}$")
DECISION_OUTCOMES = {"selected", "considered", "rejected", "deferred", "skipped"}
BASIS_PRIMARY = {
    "price",
    "quality",
    "features",
    "convenience",
    "taste",
    "trust",
    "familiarity",
    "novelty",
    "fit",
    "other",
}
EXPLORATION_STYLES = {"quick_pick", "compared_multiple", "deep_research", "hesitant"}
SATISFACTION_BUCKETS = {"yes", "partially", "no"}


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


def _load() -> dict:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text())
    assert isinstance(data, dict), "root must be an object"
    return data


def _load_user_feedback() -> dict[str, object] | None:
    if not USER_FEEDBACK.is_file():
        return None
    data = json.loads(USER_FEEDBACK.read_text())
    assert isinstance(data, dict), "user_feedback.json root must be an object"

    need = data.get("needConstraintSatisfaction")
    assert need in SATISFACTION_BUCKETS, "needConstraintSatisfaction must use a supported bucket"
    preference = data.get("personalPreferenceSatisfaction")
    assert (
        preference in SATISFACTION_BUCKETS
    ), "personalPreferenceSatisfaction must use a supported bucket"
    reason = data.get("reason")
    assert isinstance(reason, str) and reason.strip(), "feedback reason must be non-empty"

    overall = data.get("overallExperienceRating")
    assert isinstance(overall, (int, float)), "overallExperienceRating must be numeric"
    overall = int(round(float(overall)))
    assert 1 <= overall <= 10, "overallExperienceRating must be between 1 and 10"

    payload: dict[str, object] = {
        "need_constraint_satisfaction": need,
        "personal_preference_satisfaction": preference,
        "overall_experience_rating": overall,
        "feedback_reason": reason.strip(),
    }

    trust = data.get("trustLevel")
    if trust is not None:
        assert isinstance(trust, (int, float)), "trustLevel must be numeric"
        trust = int(round(float(trust)))
        assert 1 <= trust <= 10, "trustLevel must be between 1 and 10"
        payload["trust_level"] = trust

    effort = data.get("effortRating")
    if effort is not None:
        assert isinstance(effort, (int, float)), "effortRating must be numeric"
        effort = int(round(float(effort)))
        assert 1 <= effort <= 10, "effortRating must be between 1 and 10"
        payload["effort_rating"] = effort

    clarity = data.get("clarityOfNextStep")
    if clarity is not None:
        assert isinstance(clarity, bool), "clarityOfNextStep must be boolean"
        payload["clarity_of_next_step"] = "true" if clarity else "false"

    return payload


def test_output_exists():
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_output_schema():
    data = _load()
    feedback = _load_user_feedback()
    subject_id = data.get("decision_subject_id")
    assert isinstance(subject_id, str) and subject_id.strip(), "decision_subject_id must be non-empty"
    subject_label = data.get("decision_subject_label")
    assert isinstance(subject_label, str) and subject_label.strip(), "decision_subject_label must be non-empty"
    outcome = data.get("decision_outcome")
    assert outcome in DECISION_OUTCOMES, "decision_outcome must use a supported bucket"
    basis_primary = data.get("basis_primary")
    assert basis_primary in BASIS_PRIMARY, "basis_primary must use a supported bucket"
    exploration_style = data.get("exploration_style")
    assert exploration_style in EXPLORATION_STYLES, "exploration_style must use a supported bucket"
    price = data.get("task_price_text")
    assert isinstance(price, str) and PRICE_PATTERN.match(price.strip()), (
        "task_price_text must look like $123.45"
    )
    reason = data.get("reason")
    assert isinstance(reason, str) and reason.strip(), "reason must be non-empty"

    source_artifacts: dict[str, object] = {
        "taskOutput": str(OUTPUT),
    }
    contexts: list[dict[str, object]] = [
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
                    "value": outcome,
                },
                {
                    "key": "basis_primary",
                    "label": "Primary basis",
                    "role": "primary",
                    "kind": "categorical",
                    "value": basis_primary,
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
                    "value": subject_id.strip(),
                },
                {
                    "key": "decision_subject_label",
                    "label": "Decision subject label",
                    "role": "evidence",
                    "kind": "textual",
                    "value": subject_label.strip(),
                },
                {
                    "key": "task_price_text",
                    "label": "Displayed price",
                    "role": "evidence",
                    "kind": "textual",
                    "value": price.strip(),
                },
            ],
        },
        {
            "key": "decision.process",
            "label": "Decision process",
            "contextType": "decision_process",
            "facets": [
                {
                    "key": "exploration_style",
                    "label": "Exploration style",
                    "role": "primary",
                    "kind": "categorical",
                    "value": exploration_style,
                },
                {
                    "key": "comparison_notes",
                    "label": "Comparison notes",
                    "role": "explanation",
                    "kind": "textual",
                    "value": "The persona described a {} browsing pattern before settling on this laptop.".format(
                        exploration_style.replace("_", " ")
                    ),
                },
            ],
        },
    ]
    if feedback is not None:
        source_artifacts["userFeedback"] = str(USER_FEEDBACK)
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

    _write_structured_output(
        {
            "schemaVersion": "1.0",
            "artifactType": "personabench.trial_evaluation",
            "taskType": "web",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": [OUTPUT.name],
                "missingArtifacts": [],
            },
            "sourceArtifacts": source_artifacts,
            "contexts": contexts,
        }
    )
