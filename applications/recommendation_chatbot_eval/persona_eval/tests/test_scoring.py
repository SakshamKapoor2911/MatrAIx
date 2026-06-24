from __future__ import annotations

import json

from persona_eval.scoring import OriginalPromptFeedbackScorer, score_harbor_artifacts
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
            "clarifyingNotes": "The application asked about tone.",
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
    assert "Final grounded items (id — title): 42 — Movie A" in call["user"]
    assert "you: I want a quiet film." in call["user"]
    assert "agent: Try Movie A." in call["user"]
    assert "Name: Persona One" in call["system"]


def test_score_harbor_artifacts_writes_original_questionnaire(tmp_path):
    fake_client = FakeClient()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "sessionId": "ses_123",
                "domain": "movie",
                "turns": [
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
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "recommendation_result.json").write_text(
        json.dumps(
            {
                "sessionId": "ses_123",
                "domain": "movie",
                "recommendedItems": [{"itemId": "42", "title": "Movie A"}],
                "turnsToRecommendation": 2,
            }
        ),
        encoding="utf-8",
    )

    feedback = score_harbor_artifacts(
        transcript_path=output_dir / "transcript.json",
        recommendation_path=output_dir / "recommendation_result.json",
        output_path=output_dir / "user_feedback.json",
        persona=Persona(
            id="p1",
            name="Persona One",
            context="Name: Persona One\nHow you talk: concise and skeptical",
        ),
        sut_description="Movie recommender.",
        config=PersonaEvalConfig(domain="movie", engine="gpt-4o-mini"),
        client_factory=lambda _model: fake_client,
    )

    written = json.loads(
        (output_dir / "user_feedback.json").read_text(encoding="utf-8")
    )
    assert written == feedback
    assert written["overallRating"] == 8
    assert written["constraintSatisfaction"] == 4
    assert written["preferenceSatisfaction"] == 5
    assert (
        "Final grounded items (id — title): 42 — Movie A"
        in fake_client.calls[0]["user"]
    )


def test_score_harbor_artifacts_accepts_application_result_path(tmp_path):
    fake_client = FakeClient()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "sessionId": "ses_123",
                "applicationId": "finance_openbb",
                "applicationContext": "financial_research",
                "domain": "financial_research",
                "turns": [
                    {
                        "turnId": "0",
                        "userMessage": "Compare conservative ETFs.",
                        "assistantMessage": "I used OpenBB data for VTI.",
                        "groundedItems": [
                            {"itemId": "finance:ETF:VTI", "title": "VTI"}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "application_result.json").write_text(
        json.dumps(
            {
                "sessionId": "ses_123",
                "applicationId": "finance_openbb",
                "applicationContext": "financial_research",
                "domain": "financial_research",
                "groundedItems": [{"itemId": "finance:ETF:VTI", "title": "VTI"}],
                "turnsToResult": 1,
            }
        ),
        encoding="utf-8",
    )

    feedback = score_harbor_artifacts(
        transcript_path=output_dir / "transcript.json",
        application_path=output_dir / "application_result.json",
        output_path=output_dir / "user_feedback.json",
        persona=Persona(id="p1", name="Persona One", context="Careful investor."),
        sut_description="Financial research chatbot.",
        config=PersonaEvalConfig(
            domain="financial_research",
            application_id="finance_openbb",
            application_context="financial_research",
            engine="gpt-4o-mini",
        ),
        client_factory=lambda _model: fake_client,
    )

    assert feedback["overallRating"] == 8
    assert "finance:ETF:VTI — VTI" in fake_client.calls[0]["user"]
