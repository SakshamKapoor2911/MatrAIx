from __future__ import annotations

from persona_eval.scoring import OriginalPromptFeedbackScorer
from persona_eval.types import Persona, PersonaEvalConfig


class FakeClient:
    def __init__(self) -> None:
        self.calls = []

    def complete_json(self, system: str, user: str):
        self.calls.append({"system": system, "user": user})
        return {
            "constraintSatisfaction": 4,
            "constraintRationale": "The final items fit the main constraint.",
            "preferenceSatisfaction": 5,
            "preferenceRationale": "The final items match the stated taste.",
            "overallRating": 8,
            "ratingReason": "The conversation adapted after feedback.",
            "askedUsefulClarifyingQuestions": True,
            "clarifyingNotes": "The recommender asked about tone.",
        }


def test_original_prompt_feedback_scorer_reuses_user_simulator_feedback_prompt():
    fake_client = FakeClient()
    scorer = OriginalPromptFeedbackScorer(client_factory=lambda _model: fake_client)

    questionnaire = scorer(
        persona=Persona(
            id="p1",
            name="Persona One",
            context="Name: Persona One\nHow you talk: concise and skeptical",
        ),
        sut_description="Movie recommender.",
        config=PersonaEvalConfig(domain="movie", engine="gpt-4o-mini"),
        turn_views=[
            {
                "turnId": "0",
                "userMessage": "I want a quiet film.",
                "assistantMessage": "What tone do you prefer?",
                "recommendedItems": [],
            },
            {
                "turnId": "1",
                "userMessage": "Atmospheric and reflective.",
                "assistantMessage": "Try Movie A.",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
            },
        ],
        recommended_items=[{"itemId": "42", "title": "Movie A"}],
    )

    assert questionnaire["overallRating"] == 8
    assert questionnaire["constraintSatisfaction"] == 4
    assert questionnaire["preferenceSatisfaction"] == 5
    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert "post-use questionnaire as strict JSON" in call["user"]
    assert "Final recommended items (id — title): 42 — Movie A" in call["user"]
    assert "you: I want a quiet film." in call["user"]
    assert "agent: Try Movie A." in call["user"]
    assert "Name: Persona One" in call["system"]
