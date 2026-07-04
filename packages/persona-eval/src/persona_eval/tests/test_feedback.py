from __future__ import annotations

from persona_eval.feedback import questionnaire_from_feedback


def test_questionnaire_from_feedback_normalizes_artifact_payload():
    questionnaire = questionnaire_from_feedback(
        {
            "needConstraintSatisfaction": "false",
            "personalPreferenceSatisfaction": True,
            "overallExperienceRating": 2,
            "reason": "It did not adapt after I clarified my constraints.",
            "askedUsefulClarificationQuestions": True,
            "clarifyingNotes": "The questions were fine, but the follow-through failed.",
            "customFacet": "preserve me",
        }
    )

    assert questionnaire.to_dict()["constraintSatisfaction"] == 1
    assert questionnaire.to_dict()["preferenceSatisfaction"] == 5
    assert questionnaire.artifact_dict()["needConstraintSatisfaction"] == "no"
    assert questionnaire.artifact_dict()["personalPreferenceSatisfaction"] == "yes"
    assert questionnaire.artifact_dict()["customFacet"] == "preserve me"
