from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_controller_module():
    path = Path(__file__).parents[1] / "environment" / "chatbot_controller.py"
    spec = importlib.util.spec_from_file_location("chatbot_controller", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakePersonaModel:
    def __init__(self) -> None:
        self.turn_requests = []
        self.feedback_requests = []

    def next_turn(self, request):
        self.turn_requests.append(request)
        turn_number = len(self.turn_requests)
        if turn_number == 1:
            return {"message": "I want something atmospheric tonight.", "done": False}
        if turn_number == 2:
            return {"message": "I prefer thoughtful options, not graphic horror.", "done": False}
        return {"message": "Please give me specific grounded recommendations now.", "done": False}

    def self_report(self, request):
        self.feedback_requests.append(request)
        return {
            "constraintSatisfaction": 4,
            "constraintRationale": "The chatbot asked useful questions.",
            "preferenceSatisfaction": 5,
            "preferenceRationale": "The grounded options fit my preferences.",
            "overallRating": 8,
            "ratingReason": "The chatbot asked useful questions and gave grounded options.",
            "askedUsefulClarifyingQuestions": True,
            "clarifyingNotes": "It asked about tone and constraints.",
        }


class FakeChatbotClient:
    def __init__(self) -> None:
        self.messages = []
        self.session_id = "ses_controller"

    def ready(self):
        return {"status": "ok"}

    def send_message(self, message: str):
        self.messages.append(message)
        turn_number = len(self.messages)
        item = {"itemId": "item_{}".format(turn_number), "title": "Item {}".format(turn_number)}
        return {
            "sessionId": self.session_id,
            "reply": "Assistant reply {}".format(turn_number),
            "groundedItems": [item],
            "terminal": False,
        }

    def conversation(self, session_id: str):
        assert session_id == self.session_id
        messages = []
        turns = []
        for index, user_message in enumerate(self.messages, start=1):
            item = {"itemId": "item_{}".format(index), "title": "Item {}".format(index)}
            assistant_message = "Assistant reply {}".format(index)
            messages.extend(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message},
                ]
            )
            turns.append(
                {
                    "turnId": str(index),
                    "userMessage": user_message,
                    "assistantMessage": assistant_message,
                    "groundedItems": [item],
                }
            )
        return {
            "sessionId": session_id,
            "applicationId": "recai",
            "applicationContext": "movie",
            "domain": "movie",
            "messages": messages,
            "turns": turns,
        }

    def application_result(self, session_id: str):
        assert session_id == self.session_id
        return {
            "sessionId": session_id,
            "applicationId": "recai",
            "applicationContext": "movie",
            "domain": "movie",
            "groundedItems": [
                {"itemId": "item_{}".format(index), "title": "Item {}".format(index)}
                for index in range(1, len(self.messages) + 1)
            ],
            "turnsToResult": len(self.messages),
        }


def test_controller_drives_chatbot_until_max_turns_and_writes_artifacts(tmp_path):
    controller = load_controller_module()
    persona_model = FakePersonaModel()
    chatbot = FakeChatbotClient()

    result = controller.run_controller(
        config=controller.ControllerConfig(
            application_id="recai",
            application_context="movie",
            domain="movie",
            max_turns=3,
            min_turns=3,
            output_dir=tmp_path,
            task_prompt="You are a user of a movie recommendation system.",
            persona_prompt="A careful movie watcher.",
        ),
        persona_model=persona_model,
        chatbot=chatbot,
    )

    assert result["stopReason"] == "max_turns"
    assert chatbot.messages == [
        "I want something atmospheric tonight.",
        "I prefer thoughtful options, not graphic horror.",
        "Please give me specific grounded recommendations now.",
    ]
    assert len(persona_model.feedback_requests) == 1

    transcript = json.loads((tmp_path / "transcript.json").read_text(encoding="utf-8"))
    application_result = json.loads(
        (tmp_path / "application_result.json").read_text(encoding="utf-8")
    )
    self_report = json.loads(
        (tmp_path / "persona_self_report.json").read_text(encoding="utf-8")
    )
    evaluation = json.loads(
        (tmp_path / "evaluation_result.json").read_text(encoding="utf-8")
    )
    legacy_feedback = json.loads(
        (tmp_path / "user_feedback.json").read_text(encoding="utf-8")
    )

    assert len(transcript["turns"]) == 3
    assert application_result["turnsToResult"] == 3
    assert self_report["overallRating"] == 8
    assert evaluation["scores"]["overallRating"] == 8
    assert legacy_feedback["overallRating"] == 8


def test_controller_respects_persona_done_after_min_turns(tmp_path):
    controller = load_controller_module()

    class DonePersona(FakePersonaModel):
        def next_turn(self, request):
            self.turn_requests.append(request)
            if len(self.turn_requests) < 3:
                return {"message": "Turn {}".format(len(self.turn_requests)), "done": False}
            return {"message": None, "done": True, "doneReason": "Satisfied."}

    persona_model = DonePersona()
    chatbot = FakeChatbotClient()

    result = controller.run_controller(
        config=controller.ControllerConfig(
            application_id="recai",
            application_context="movie",
            domain="movie",
            max_turns=8,
            min_turns=2,
            output_dir=tmp_path,
            task_prompt="You are a user of a movie recommendation system.",
            persona_prompt="A careful movie watcher.",
        ),
        persona_model=persona_model,
        chatbot=chatbot,
    )

    assert result["stopReason"] == "persona_done"
    assert len(chatbot.messages) == 2
    run_metadata = json.loads((tmp_path / "run_metadata.json").read_text(encoding="utf-8"))
    assert run_metadata["stopReason"] == "persona_done"


def test_controller_writes_artifacts_when_application_has_no_grounded_items(tmp_path):
    controller = load_controller_module()

    class OneTurnPersona(FakePersonaModel):
        def next_turn(self, request):
            self.turn_requests.append(request)
            return {"message": "Can you help me compare bank stocks?", "done": False}

        def self_report(self, request):
            self.feedback_requests.append(request)
            return {
                "constraintSatisfaction": 2,
                "constraintRationale": "The chatbot only asked a clarifying question.",
                "preferenceSatisfaction": 2,
                "preferenceRationale": "No concrete research was provided.",
                "overallRating": 3,
                "ratingReason": "The chatbot only asked a clarifying question.",
                "askedUsefulClarifyingQuestions": True,
                "clarifyingNotes": "It asked about time horizon and risk constraints.",
            }

    class EmptyResultChatbot(FakeChatbotClient):
        def send_message(self, message: str):
            self.messages.append(message)
            return {
                "sessionId": self.session_id,
                "reply": "What time horizon and risk constraints matter?",
                "groundedItems": [],
                "terminal": False,
            }

        def conversation(self, session_id: str):
            assert session_id == self.session_id
            return {
                "sessionId": session_id,
                "applicationId": "finance_openbb",
                "applicationContext": "financial_research",
                "domain": "financial_research",
                "messages": [
                    {"role": "user", "content": self.messages[0]},
                    {
                        "role": "assistant",
                        "content": "What time horizon and risk constraints matter?",
                    },
                ],
                "turns": [
                    {
                        "turnId": "0",
                        "userMessage": self.messages[0],
                        "assistantMessage": (
                            "What time horizon and risk constraints matter?"
                        ),
                        "groundedItems": [],
                    }
                ],
            }

        def application_result(self, session_id: str):
            assert session_id == self.session_id
            return {
                "sessionId": session_id,
                "applicationId": "finance_openbb",
                "applicationContext": "financial_research",
                "domain": "financial_research",
                "groundedItems": [],
                "turnsToResult": 1,
            }

    persona_model = OneTurnPersona()
    chatbot = EmptyResultChatbot()

    result = controller.run_controller(
        config=controller.ControllerConfig(
            application_id="finance_openbb",
            application_context="financial_research",
            domain="financial_research",
            max_turns=1,
            min_turns=1,
            output_dir=tmp_path,
            task_prompt="You are a user of a financial research system.",
            persona_prompt="A cautious finance user.",
        ),
        persona_model=persona_model,
        chatbot=chatbot,
    )

    assert result["turns"] == 1
    assert (tmp_path / "transcript.json").is_file()
    assert (tmp_path / "application_result.json").is_file()
    assert (tmp_path / "persona_self_report.json").is_file()
    application_result = json.loads(
        (tmp_path / "application_result.json").read_text(encoding="utf-8")
    )
    assert application_result["groundedItems"] == []


def test_anthropic_self_report_prompt_escapes_json_schema_braces():
    controller = load_controller_module()

    class CapturingPersonaModel(controller.AnthropicPersonaModel):
        def __init__(self) -> None:
            self.prompt = ""

        def _json_completion(self, *, system: str, prompt: str):
            self.prompt = prompt
            return {
                "constraintSatisfaction": 4,
                "constraintRationale": "ok",
                "preferenceSatisfaction": 4,
                "preferenceRationale": "ok",
                "overallRating": 7,
                "ratingReason": "ok",
                "askedUsefulClarifyingQuestions": True,
                "clarifyingNotes": "ok",
            }

    model = CapturingPersonaModel()
    result = model.self_report(
        {
            "personaPrompt": "A practical user.",
            "taskPrompt": "Use the chatbot.",
            "transcript": {
                "turns": [
                    {
                        "userMessage": "I want a quiet film.",
                        "assistantMessage": "Try Movie A.",
                        "groundedItems": [{"itemId": "42", "title": "Movie A"}],
                    }
                ]
            },
            "applicationResult": {
                "groundedItems": [{"itemId": "42", "title": "Movie A"}]
            },
        }
    )

    assert result["overallRating"] == 7
    assert "post-use questionnaire as strict JSON" in model.prompt
    assert "Final grounded items (id — title): 42 — Movie A" in model.prompt
    assert '"constraintSatisfaction"' in model.prompt
    assert '"overallRating"' in model.prompt
    assert "overallExperienceRating" not in model.prompt


def test_anthropic_next_turn_prompt_escapes_json_schema_braces():
    controller = load_controller_module()

    class CapturingPersonaModel(controller.AnthropicPersonaModel):
        def __init__(self) -> None:
            self.prompt = ""

        def _json_completion(self, *, system: str, prompt: str):
            self.prompt = prompt
            return {"message": "I want a light movie.", "done": False}

    model = CapturingPersonaModel()
    result = model.next_turn(
        {
            "personaPrompt": "A practical user.",
            "taskPrompt": "Use the chatbot.",
            "conversationHistory": [],
        }
    )

    assert result["message"] == "I want a light movie."
    assert '"message"' in model.prompt
