import json
import urllib.request

from backend.service.local_chatbot_eval import DirectApplicationSession
from backend.service.local_survey_eval import LocalSurveyEvalRunner
from backend.service.local_web_eval import LocalWebEvalRunner
from backend.service.survey_types import SurveyEvalConfig, SurveyInstrument, SurveyQuestion
from backend.service.web_types import WebEvalConfig, WebEvalTask
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


def test_local_survey_runner_returns_result_and_prompts(monkeypatch):
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
        "backend.service.local_survey_eval.build_json_client",
        lambda model: client,
    )
    instrument = SurveyInstrument(
        id="survey1",
        title="Survey",
        description="A survey about a concrete feature.",
        questions=[SurveyQuestion(id="fit", prompt="This fits me.")],
    )

    result = LocalSurveyEvalRunner()(
        _persona(),
        instrument,
        SurveyEvalConfig(persona_model="openai/gpt-4o-mini"),
        created_at="2026-06-26T00:00:00Z",
    )

    assert result.config.mode == "local_persona_survey"
    assert result.answers[0].question_id == "fit"
    assert result.metrics.num_answered == 1
    assert result.prompts["personaPrompt"]
    assert result.prompts["taskPrompt"]
    assert "Survey: A survey about a concrete feature." in result.prompts["taskPrompt"]
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


def test_local_web_runner_returns_result_trace_and_prompts(monkeypatch, tmp_path):
    client = FakeJSONClient(
        {
            "goal": "Find a compact desk lamp.",
            "steps": [
                {
                    "message": "I searched for desk lamps and compared two options.",
                    "actions": [{"name": "search", "arguments": {"q": "desk lamp"}}],
                }
            ],
            "selected_product_id": "lamp-1",
            "selected_product_name": "Compact Lamp",
            "need_satisfaction": 8,
            "ease_of_use": 7,
            "information_quality": 8,
            "overall_quality": 8,
            "reason": "The site made it easy to compare products and choose a lamp.",
        }
    )
    monkeypatch.setattr(
        "backend.service.local_web_eval.build_json_client",
        lambda model: client,
    )
    task = WebEvalTask(
        id="web1",
        title="Web task",
        site_name="Shop",
        site_url="http://local.test/",
        task_path=tmp_path,
        description="Find and choose a product.",
    )

    result = LocalWebEvalRunner()(
        _persona(),
        task,
        WebEvalConfig(persona_model="openai/gpt-4o-mini"),
        created_at="2026-06-26T00:00:00Z",
    )

    assert result.config.mode == "local_persona_web"
    assert result.web_result.selected_product_id == "lamp-1"
    assert result.web_result.information_quality == 8
    assert result.trace.events[0]["actions"][0]["name"] == "search"
    assert result.trace.screenshots_dir is not None
    screenshot_file = result.trace.events[0]["screenshotFile"]
    assert screenshot_file == "screenshot_001.svg"
    screenshot_path = result.trace.screenshots_dir / screenshot_file
    assert screenshot_path.is_file()
    assert "Shop" in screenshot_path.read_text(encoding="utf-8")
    assert result.prompts["personaPrompt"]
    assert result.prompts["taskPrompt"]
    assert client.calls


def test_local_web_runner_grounds_prompt_in_catalog(monkeypatch, tmp_path):
    """The persona must choose from the real catalog, not invent a product.

    The task prompt must surface the catalog's product ids/names so the model
    selects a real item (otherwise selected_product_id is a hallucination and
    never matches a product in the rendered trace).
    """
    client = FakeJSONClient(
        {
            "goal": "Buy a mortar and pestle.",
            "steps": [{"message": "Looked at kitchen tools.", "actions": []}],
            "selected_product_id": "granite-mortar-pestle-lg",
            "selected_product_name": "Granite Mortar and Pestle",
            "need_satisfaction": 8,
            "ease_of_use": 8,
            "information_quality": 8,
            "overall_quality": 8,
            "reason": "Found a good kitchen tool.",
        }
    )
    monkeypatch.setattr(
        "backend.service.local_web_eval.build_json_client",
        lambda model: client,
    )
    site_dir = tmp_path / "environment" / "ecommerce-web" / "site"
    site_dir.mkdir(parents=True)
    (site_dir / "catalog.json").write_text(
        json.dumps(
            {
                "products": [
                    {
                        "id": "granite-mortar-pestle-lg",
                        "name": "Granite Mortar and Pestle",
                        "category": "Kitchen",
                        "price_usd": 39,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    task = WebEvalTask(
        id="web1",
        title="Web task",
        site_name="Shop",
        site_url="http://local.test/",
        task_path=tmp_path,
        description="Find and choose a product.",
    )

    result = LocalWebEvalRunner()(
        _persona(),
        task,
        WebEvalConfig(persona_model="openai/gpt-4o-mini"),
        created_at="2026-06-26T00:00:00Z",
    )

    task_prompt = result.prompts["taskPrompt"]
    assert "granite-mortar-pestle-lg" in task_prompt
    assert "Granite Mortar and Pestle" in task_prompt


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
                    "groundedItems": [
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
            domain="financial_research",
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
    assert turn["groundedItems"][0]["itemId"] == "finance:openbb:etf_search:0"


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
                    "groundedItems": [],
                },
            }
        )

    monkeypatch.setenv("CHATBOT_UPSTREAM_MEDICAL", "http://medical.local")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    session = DirectApplicationSession(
        PersonaEvalConfig(
            domain="medical_consultation",
            application_id="medical_assistant",
            application_context="medical_consultation",
        )
    )
    turn = session.run_turn_sync("I have a sore throat. What should I consider?")

    assert calls[0]["applicationId"] == "medical_assistant"
    assert calls[0]["applicationContext"] == "medical_consultation"
    assert turn["assistantMessage"].startswith("I can explain symptoms")
