import json
import urllib.request

from persona_eval.inprocess.chatbot_eval import DirectApplicationSession
from persona_eval.inprocess.survey_eval import InprocessSurveyEvalRunner
from backend.service.survey_types import SurveyEvalConfig, SurveyInstrument, SurveyQuestion
from persona_eval.types import Persona, PersonaEvalConfig


class FakeJSONClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete_json(self, system, user):
        self.calls.append((system, user))
        return self.payload


def _persona():
    return Persona(
        id="p1",
        name="Persona One",
        context="A budget-conscious user who prefers clear information.",
    )


def test_inprocess_survey_runner_returns_result_and_prompts(monkeypatch):
    client = FakeJSONClient(
        {
            "answers": [
                {
                    "questionId": "fit",
                    "value": 5,
                    "rationale": "It fits the persona's needs.",
                    "confidence": 0.9,
                }
            ]
        }
    )
    monkeypatch.setattr(
        "persona_eval.inprocess.survey_eval.build_json_client",
        lambda model: client,
    )
    instrument = SurveyInstrument(
        id="survey1",
        title="Survey",
        description="A survey about a concrete feature.",
        questions=[SurveyQuestion(id="fit", prompt="This fits me.")],
    )

    result = InprocessSurveyEvalRunner()(
        _persona(),
        instrument,
        SurveyEvalConfig(persona_model="openai/gpt-4o-mini"),
        created_at="2026-06-26T00:00:00Z",
    )

    assert result.config.mode == "inprocess_persona_survey"
    assert result.answers[0].question_id == "fit"
    assert result.metrics.num_answered == 1
    assert result.prompts["personaPrompt"]
    assert result.prompts["taskPrompt"]
    assert "## Task instruction" in result.prompts["taskPrompt"]
    assert "## Questionnaire" in result.prompts["taskPrompt"]
    assert "This fits me." in result.prompts["taskPrompt"]
    assert [event.action for event in result.trajectory] == [
        "survey_started",
        "ask_question",
        "answer_question",
        "survey_completed",
    ]
    assert [event.actor for event in result.trajectory] == [
        "system",
        "assistant",
        "user",
        "system",
    ]
    assert result.trajectory[1].context == {
        "instrumentId": "survey1",
        "questionId": "fit",
        "questionIndex": 1,
        "questionType": "likert",
        "construct": "",
    }
    assert result.trajectory[1].outcome["prompt"] == "This fits me."
    assert result.trajectory[2].outcome == {
        "questionId": "fit",
        "value": 5,
        "rationale": "It fits the persona's needs.",
        "confidence": 0.9,
    }
    assert result.trajectory[-1].outcome == {
        "numAnswered": 1,
        "missingRequiredQuestionIds": [],
        "valid": True,
    }
    assert client.calls


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_direct_finance_session_uses_http_sidecar(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "body": json.loads(request.data.decode("utf-8")),
            }
        )
        return FakeHTTPResponse(
            {
                "sessionId": "fin_ses_1",
                "reply": "I can compare ETFs and risk constraints.",
                "turn": {
                    "turnId": "fin_turn_1",
                    "conversationId": "fin_ses_1",
                    "backend": "finance_openbb",
                    "assistantMessage": "I can compare ETFs and risk constraints.",
                    "recommendedItems": [
                        {
                            "itemId": "finance:openbb:etf_search:0",
                            "title": "ETF data",
                        }
                    ],
                },
            }
        )

    monkeypatch.setenv("CHATBOT_UPSTREAM_FINANCE", "http://finance.local")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    session = DirectApplicationSession(
        PersonaEvalConfig(
            application_id="finance_openbb",
            application_context="financial_research",
        )
    )
    turn = session.run_turn_sync("Can you compare low-cost broad market ETFs?")

    assert calls[0]["url"] == "http://finance.local/v1/messages"
    assert calls[0]["body"]["applicationId"] == "finance_openbb"
    assert calls[0]["body"]["applicationContext"] == "financial_research"
    assert calls[0]["body"]["message"] == "Can you compare low-cost broad market ETFs?"
    assert turn["assistantMessage"] == "I can compare ETFs and risk constraints."
    assert isinstance(turn.get("personaExposure"), list)


def test_direct_medical_session_uses_http_sidecar(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data.decode("utf-8")))
        return FakeHTTPResponse(
            {
                "sessionId": "med_ses_1",
                "reply": "I can explain symptoms and suggest when to seek care.",
                "turn": {
                    "turnId": "med_turn_1",
                    "conversationId": "med_ses_1",
                    "backend": "medical_assistant",
                    "assistantMessage": "I can explain symptoms and suggest when to seek care.",
                    "recommendedItems": [],
                },
            }
        )

    monkeypatch.setenv("CHATBOT_UPSTREAM_MEDICAL", "http://medical.local")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    session = DirectApplicationSession(
        PersonaEvalConfig(
            application_id="medical_assistant",
            application_context="medical_consultation",
        )
    )
    turn = session.run_turn_sync("I have a sore throat. What should I consider?")

    assert calls[0]["applicationId"] == "medical_assistant"
    assert calls[0]["applicationContext"] == "medical_consultation"
    assert turn["assistantMessage"].startswith("I can explain symptoms")
