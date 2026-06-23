from __future__ import annotations

from matraix.persona_grounding import (
    AGE_BRACKET_COUNTERFACTUAL,
    build_job_grounding_report,
    extract_survey_text,
    heuristic_dim_grounding,
)


def test_heuristic_flags_empty_nester_for_18_24() -> None:
    survey = {
        "responses": [
            {
                "question_id": "q1",
                "answer": "I'm an empty nester now, so school apps don't apply.",
            }
        ],
        "summary": "Not in the target demographic as an empty nester.",
    }
    text = extract_survey_text(survey)
    result = heuristic_dim_grounding(
        probe_dimension="dimensions.age_bracket",
        probe_value="18-24",
        survey_text=text,
    )
    assert result.counterfactual is True
    assert result.dim_grounding == 0.0
    assert result.matched_cues


def test_heuristic_passes_plausible_young_adult() -> None:
    survey = {
        "responses": [
            {
                "question_id": "q1",
                "answer": "As a college student juggling classes and part-time work, this could help.",
            }
        ],
        "summary": "Might try it if my roommates also adopt it.",
    }
    text = extract_survey_text(survey)
    result = heuristic_dim_grounding(
        probe_dimension="dimensions.age_bracket",
        probe_value="18-24",
        survey_text=text,
    )
    assert result.counterfactual is False
    assert result.dim_grounding == 1.0


def test_build_job_report_conclusion_on_counterfactuals() -> None:
    trials = [
        {
            "trial": "t1",
            "final_dim_grounding": 0.0,
            "counterfactual": True,
        },
        {
            "trial": "t2",
            "final_dim_grounding": 1.0,
            "counterfactual": False,
        },
    ]
    report = build_job_grounding_report(
        trials,
        job_meta={
            "job_slug": "test-job",
            "probe": {
                "dimension": "dimensions.age_bracket",
                "value": "18-24",
            },
        },
    )
    assert report["counterfactual_rate"] == 0.5
    assert "counterfactual" in report["conclusion"].lower()


def test_age_bracket_patterns_non_empty() -> None:
    assert AGE_BRACKET_COUNTERFACTUAL["18-24"]
