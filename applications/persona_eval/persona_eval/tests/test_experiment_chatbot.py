from __future__ import annotations

import json
from pathlib import Path

from persona_eval.experiments.applications import parse_application_ref
from persona_eval.experiments.batch import build_run_specs
from persona_eval.experiments.chatbot import ChatbotExperimentRunner
from persona_eval.types import Persona


class FakePersonaModel:
    def __init__(self) -> None:
        self.turns = 0

    def next_turn(self, request):
        self.turns += 1
        if self.turns == 1:
            return {"message": "I want something tense but not graphic.", "done": False}
        return {"message": "Those options sound good enough.", "done": False}

    def self_report(self, request):
        return {
            "constraintSatisfaction": 4,
            "constraintRationale": "The response avoided graphic horror.",
            "preferenceSatisfaction": 5,
            "preferenceRationale": "The items fit my atmospheric preference.",
            "overallRating": 8,
            "ratingReason": "The chatbot gave grounded recommendations quickly.",
            "askedUsefulClarifyingQuestions": True,
            "clarifyingNotes": "It asked about tone.",
        }


class FakeChatbotClient:
    def __init__(self, _config) -> None:
        self.session_id = "session_fake"
        self.messages = []

    def ready(self):
        return {"status": "ok"}

    def send_message(self, message):
        self.messages.append(message)
        index = len(self.messages)
        return {
            "sessionId": self.session_id,
            "reply": "Assistant reply {}".format(index),
            "groundedItems": [
                {"itemId": "item_{}".format(index), "title": "Item {}".format(index)}
            ],
        }

    def conversation(self, session_id):
        assert session_id == self.session_id
        turns = []
        for index, message in enumerate(self.messages, start=1):
            turns.append(
                {
                    "turnId": str(index),
                    "userMessage": message,
                    "assistantMessage": "Assistant reply {}".format(index),
                    "groundedItems": [
                        {"itemId": "item_{}".format(index), "title": "Item {}".format(index)}
                    ],
                }
            )
        return {
            "sessionId": session_id,
            "applicationId": "recai",
            "applicationContext": "movie",
            "domain": "movie",
            "turns": turns,
        }

    def application_result(self, session_id):
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


def test_chatbot_experiment_runner_writes_artifacts_and_events(tmp_path):
    persona = Persona(id="p1", name="Persona One", context="Careful movie watcher.")
    application = parse_application_ref("movie")
    spec = build_run_specs(
        personas=[persona],
        applications=[application],
        api_url="http://fake.local",
        persona_model="fake-persona",
        max_turns=2,
        min_turns=2,
        goal_context_id="scenario_default",
    )[0]
    runner = ChatbotExperimentRunner(
        persona_model_factory=lambda _spec, _persona: FakePersonaModel(),
        chatbot_client_factory=lambda config: FakeChatbotClient(config),
        now=lambda: "2026-06-26T00:00:00Z",
    )

    result = runner.run(spec, persona, tmp_path / "run", application)

    assert result.status == "done"
    assert "transcript.json" in result.artifacts
    assert "events.ndjson" in result.artifacts
    transcript = json.loads((tmp_path / "run" / "transcript.json").read_text())
    assert len(transcript["turns"]) == 2
    events = [
        json.loads(line)
        for line in (tmp_path / "run" / "events.ndjson").read_text().splitlines()
    ]
    event_types = {event["type"] for event in events}
    assert "persona.next_turn.response" in event_types
    assert "chatbot.message.response" in event_types
    assert "persona.self_report.response" in event_types
    assert events[-1]["type"] == "run.completed"


def test_chatbot_experiment_runner_records_errors(tmp_path):
    persona = Persona(id="p1", name="Persona One", context="Careful movie watcher.")
    application = parse_application_ref("movie")
    spec = build_run_specs(
        personas=[persona],
        applications=[application],
        api_url="http://fake.local",
        persona_model="fake-persona",
        max_turns=1,
        min_turns=1,
        goal_context_id="scenario_default",
    )[0]

    class BrokenChatbot(FakeChatbotClient):
        def ready(self):
            raise RuntimeError("service unavailable")

    runner = ChatbotExperimentRunner(
        persona_model_factory=lambda _spec, _persona: FakePersonaModel(),
        chatbot_client_factory=lambda config: BrokenChatbot(config),
        now=lambda: "2026-06-26T00:00:00Z",
    )

    result = runner.run(spec, persona, tmp_path / "run", application)

    assert result.status == "error"
    assert (tmp_path / "run" / "error.json").is_file()
    assert "service unavailable" in result.error
