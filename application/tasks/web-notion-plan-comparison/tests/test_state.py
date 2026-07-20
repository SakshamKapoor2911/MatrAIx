from __future__ import annotations

import json
import os
from pathlib import Path

OUTPUT = Path("/app/output/notion_plan_comparison.json")
USER_FEEDBACK = Path("/app/output/user_feedback.json")
SOURCE_URL = "https://www.notion.com/pricing"
BILLING_MODE = "monthly"
PLAN_LABELS = {
    "free": "Free",
    "plus": "Plus",
    "business": "Business",
    "enterprise": "Enterprise",
}
BASIS_VALUES = {
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
EXPLORATION_STYLES = {"compared_multiple", "deep_research"}
SATISFACTION_BUCKETS = {"yes", "partially", "no"}


def _nonempty(value: object, field: str, *, maximum_length: int | None = None) -> str:
    assert isinstance(value, str) and value.strip(), f"{field} must be non-empty"
    cleaned = value.strip()
    if maximum_length is not None:
        assert len(cleaned) <= maximum_length, (
            f"{field} must be at most {maximum_length} characters"
        )
    return cleaned


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _integer_rating(value: object, field: str) -> int:
    assert isinstance(value, int) and not isinstance(value, bool), (
        f"{field} must be an integer"
    )
    assert 1 <= value <= 10, f"{field} must be between 1 and 10"
    return value


def _validate_monthly_price(price: str, subject_id: str, field: str) -> None:
    lowered = price.lower()
    assert "yearly" not in lowered and "annual" not in lowered, (
        f"{field} must contain standard monthly pricing, not annual pricing"
    )
    if subject_id != "enterprise":
        assert "month" in lowered, (
            f"{field} for {PLAN_LABELS[subject_id]} must contain monthly price text"
        )


def _validate_candidate(candidate: object, index: int) -> dict[str, str]:
    assert isinstance(candidate, dict), (
        f"task_options_considered[{index}] must be an object"
    )
    prefix = f"task_options_considered[{index}]"
    subject_id = _nonempty(
        candidate.get("decision_subject_id"),
        f"{prefix}.decision_subject_id",
        maximum_length=32,
    )
    assert subject_id in PLAN_LABELS, (
        f"{prefix}.decision_subject_id must be a canonical plan ID"
    )
    subject_label = _nonempty(
        candidate.get("decision_subject_label"),
        f"{prefix}.decision_subject_label",
        maximum_length=32,
    )
    assert subject_label == PLAN_LABELS[subject_id], (
        f"{prefix}.decision_subject_label must match its canonical plan ID"
    )
    price = _nonempty(
        candidate.get("task_price_text"),
        f"{prefix}.task_price_text",
        maximum_length=250,
    )
    _validate_monthly_price(price, subject_id, f"{prefix}.task_price_text")
    return {
        "decision_subject_id": subject_id,
        "decision_subject_label": subject_label,
        "task_price_text": price,
        "task_target_text": _nonempty(
            candidate.get("task_target_text"),
            f"{prefix}.task_target_text",
            maximum_length=500,
        ),
        "task_relevance_note": _nonempty(
            candidate.get("task_relevance_note"),
            f"{prefix}.task_relevance_note",
            maximum_length=1200,
        ),
    }


def _verifier_dir() -> Path:
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    if explicit:
        path = Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path

    container_default = Path("/logs/verifier")
    try:
        container_default.mkdir(parents=True, exist_ok=True)
        return container_default
    except OSError:
        pass

    raise RuntimeError(
        "HARBOR_VERIFIER_DIR is required when running outside a Harbor trial "
        "container. Point it at jobs/<job>/<trial>/verifier for local harness runs."
    )


def _write_structured_output(payload: dict[str, object]) -> None:
    path = _verifier_dir() / "structured_output.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load() -> dict[str, object]:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "notion_plan_comparison.json root must be an object"
    return data


def _load_user_feedback() -> dict[str, object] | None:
    if not USER_FEEDBACK.is_file():
        return None
    data = json.loads(USER_FEEDBACK.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "user_feedback.json root must be an object"

    need = data.get("needConstraintSatisfaction")
    assert need in SATISFACTION_BUCKETS, (
        "needConstraintSatisfaction must use a supported bucket"
    )
    preference = data.get("personalPreferenceSatisfaction")
    assert preference in SATISFACTION_BUCKETS, (
        "personalPreferenceSatisfaction must use a supported bucket"
    )
    reason = _nonempty(data.get("reason"), "feedback reason", maximum_length=2000)
    overall = _integer_rating(
        data.get("overallExperienceRating"), "overallExperienceRating"
    )

    payload: dict[str, object] = {
        "need_constraint_satisfaction": need,
        "personal_preference_satisfaction": preference,
        "overall_experience_rating": overall,
        "feedback_reason": reason,
    }

    for source_key, target_key in (
        ("trustLevel", "trust_level"),
        ("effortRating", "effort_rating"),
    ):
        value = data.get(source_key)
        if value is not None:
            payload[target_key] = _integer_rating(value, source_key)

    clarity = data.get("clarityOfNextStep")
    if clarity is not None:
        assert isinstance(clarity, bool), "clarityOfNextStep must be boolean"
        payload["clarity_of_next_step"] = "true" if clarity else "false"

    return payload


def _execution_contexts(
    *, subject_id: str, subject_label: str
) -> list[dict[str, object]]:
    return [
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
                        "The user completed a standard monthly Notion plan "
                        "choice after comparing all four plans."
                    ),
                },
                {
                    "key": "completion_evidence",
                    "label": "Completion evidence",
                    "role": "evidence",
                    "kind": "textual",
                    "value": (
                        f"Saved {OUTPUT.name} with schema-valid, internally "
                        "consistent plan comparison metadata."
                    ),
                },
            ],
        },
        {
            "key": "web_artifact.primary",
            "label": "Web artifact",
            "contextType": "web_artifact",
            "facets": [
                {
                    "key": "artifact_type",
                    "label": "Artifact type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "selection",
                },
                {
                    "key": "artifact_status",
                    "label": "Artifact status",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "correct",
                },
                {
                    "key": "artifact_subject_label",
                    "label": "Artifact subject label",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": subject_label,
                },
                {
                    "key": "artifact_subject_id",
                    "label": "Artifact subject id",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": subject_id,
                },
                {
                    "key": "artifact_evidence",
                    "label": "Artifact evidence",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        "The selected plan metadata matches exactly one entry in "
                        "the complete four-plan comparison."
                    ),
                },
            ],
        },
        {
            "key": "web_interaction.primary",
            "label": "Web interaction",
            "contextType": "web_interaction",
            "facets": [
                {
                    "key": "navigation_path_type",
                    "label": "Navigation path type",
                    "role": "primary",
                    "kind": "categorical",
                    "value": "compare_then_commit",
                },
                {
                    "key": "web_interaction_notes",
                    "label": "Web interaction notes",
                    "role": "explanation",
                    "kind": "textual",
                    "value": (
                        "The submission records a compare-then-commit path across "
                        "all four standard Notion plans in monthly billing mode."
                    ),
                },
            ],
        },
    ]


def test_output_exists() -> None:
    assert OUTPUT.is_file(), f"Missing {OUTPUT}"


def test_output_schema() -> None:
    data = _load()
    feedback = _load_user_feedback()

    subject_id = _nonempty(
        data.get("decision_subject_id"),
        "decision_subject_id",
        maximum_length=32,
    )
    assert subject_id in PLAN_LABELS, "decision_subject_id must be a canonical plan ID"
    subject_label = _nonempty(
        data.get("decision_subject_label"),
        "decision_subject_label",
        maximum_length=32,
    )
    assert subject_label == PLAN_LABELS[subject_id], (
        "decision_subject_label must match the canonical plan ID"
    )
    assert data.get("decision_outcome") == "selected", (
        "decision_outcome must be selected"
    )

    basis_primary = data.get("basis_primary")
    assert basis_primary in BASIS_VALUES, "basis_primary must use a supported bucket"
    basis_secondary = data.get("basis_secondary")
    if basis_secondary is not None:
        assert basis_secondary in BASIS_VALUES, (
            "basis_secondary must use a supported bucket"
        )
        assert basis_secondary != basis_primary, (
            "basis_secondary must differ from basis_primary"
        )

    exploration_style = data.get("exploration_style")
    assert exploration_style in EXPLORATION_STYLES, (
        "exploration_style must be compared_multiple or deep_research"
    )
    reason = _nonempty(data.get("reason"), "reason", maximum_length=2000)

    assert data.get("task_billing_mode") == BILLING_MODE, (
        "task_billing_mode must be monthly"
    )
    assert data.get("task_source_url") == SOURCE_URL, (
        f"task_source_url must be {SOURCE_URL}"
    )
    selected_price = _nonempty(
        data.get("task_price_text"),
        "task_price_text",
        maximum_length=250,
    )
    _validate_monthly_price(selected_price, subject_id, "task_price_text")
    selected_target = _nonempty(
        data.get("task_target_text"),
        "task_target_text",
        maximum_length=500,
    )

    raw_candidates = data.get("task_options_considered")
    assert isinstance(raw_candidates, list), "task_options_considered must be an array"
    assert len(raw_candidates) == len(PLAN_LABELS), (
        "task_options_considered must contain exactly four plans"
    )
    candidates = [
        _validate_candidate(item, index) for index, item in enumerate(raw_candidates)
    ]

    ids = [candidate["decision_subject_id"] for candidate in candidates]
    labels = [candidate["decision_subject_label"] for candidate in candidates]
    assert len(ids) == len(set(ids)), "candidate plan IDs must be distinct"
    assert len(labels) == len(set(labels)), "candidate plan labels must be distinct"
    assert set(ids) == set(PLAN_LABELS), (
        "candidate list must contain Free, Plus, Business, and Enterprise"
    )

    selected_matches = [
        candidate
        for candidate in candidates
        if candidate["decision_subject_id"] == subject_id
    ]
    assert len(selected_matches) == 1, (
        "selected plan must appear exactly once in candidate list"
    )
    selected = selected_matches[0]
    assert selected["decision_subject_label"] == subject_label, (
        "selected plan label must match"
    )
    assert selected["task_price_text"] == selected_price, (
        "selected plan price text must match"
    )
    assert selected["task_target_text"] == selected_target, (
        "selected plan audience description must match"
    )

    source_artifacts: dict[str, object] = {"taskOutput": str(OUTPUT)}
    contexts = _execution_contexts(
        subject_id=subject_id,
        subject_label=subject_label,
    )

    decision_facets: list[dict[str, object]] = [
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
            "value": basis_primary,
        },
        {
            "key": "reason",
            "label": "Reason",
            "role": "explanation",
            "kind": "textual",
            "explainsFacetKey": "decision_subject_label",
            "value": reason,
        },
        {
            "key": "decision_subject_id",
            "label": "Decision subject ID",
            "role": "evidence",
            "kind": "categorical",
            "value": subject_id,
        },
        {
            "key": "decision_subject_label",
            "label": "Decision subject label",
            "role": "evidence",
            "kind": "categorical",
            "value": subject_label,
        },
        {
            "key": "task_billing_mode",
            "label": "Billing mode",
            "role": "evidence",
            "kind": "categorical",
            "value": BILLING_MODE,
        },
        {
            "key": "task_price_text",
            "label": "Selected plan price",
            "role": "evidence",
            "kind": "categorical",
            "value": _normalize_whitespace(selected_price),
        },
        {
            "key": "task_target_text",
            "label": "Selected plan audience",
            "role": "evidence",
            "kind": "categorical",
            "value": _normalize_whitespace(selected_target),
        },
    ]
    if basis_secondary is not None:
        decision_facets.append(
            {
                "key": "basis_secondary",
                "label": "Secondary basis",
                "role": "primary",
                "kind": "categorical",
                "value": basis_secondary,
            }
        )

    contexts.extend(
        [
            {
                "key": "decision.primary",
                "label": "Primary decision",
                "contextType": "decision",
                "facets": decision_facets,
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
                        "key": "options_considered_count",
                        "label": "Options considered count",
                        "role": "score",
                        "kind": "numerical",
                        "value": len(candidates),
                    },
                    {
                        "key": "comparison_notes",
                        "label": "Comparison notes",
                        "role": "explanation",
                        "kind": "textual",
                        "explainsFacetKey": "exploration_style",
                        "value": (
                            "The user compared the four standard monthly "
                            "Notion plan summaries and recorded one choice."
                        ),
                    },
                ],
            },
        ]
    )

    if feedback is not None:
        source_artifacts["userFeedback"] = str(USER_FEEDBACK)
        feedback_facets: list[dict[str, object]] = [
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
                "explainsFacetKey": "overall_experience_rating",
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
        for key, label in (
            ("trust_level", "Choice confidence"),
            ("effort_rating", "Effort rating"),
        ):
            if key in feedback:
                feedback_facets.append(
                    {
                        "key": key,
                        "label": label,
                        "role": "score",
                        "kind": "numerical",
                        "value": feedback[key],
                    }
                )
        if "clarity_of_next_step" in feedback:
            feedback_facets.append(
                {
                    "key": "clarity_of_next_step",
                    "label": "Clarity of choice",
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
            "artifactType": "matraix.trial_evaluation",
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
