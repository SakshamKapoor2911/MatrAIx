from persona_eval.cli import format_transcript
from persona_eval.types import (Persona, PersonaEvalConfig, PersonaEvalTurn, Questionnaire,
                            MetricScores, PersonaEvalResult)


def _result():
    return PersonaEvalResult(
        config=PersonaEvalConfig(domain="game"),
        persona=Persona(id="p", name="Marco", summary="s", preferences=[],
                        dislikes=[], constraints=[], goal="g", communication_style="c"),
        sut_description="desc",
        transcript=[PersonaEvalTurn(1, "hi", "try A", [{"id": "1", "title": "A"}], "satisfied", 1.0)],
        questionnaire=Questionnaire(4, "r", 4, "r", 8, "good", True, "asked"),
        metric_scores=MetricScores(1, 1, 1), created_at="t")


def test_format_transcript_is_readable():
    text = format_transcript(_result())
    assert "Marco" in text and "try A" in text
    assert "Overall: 8/10" in text
    assert "turns-to-recommendation: 1" in text
