from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from harbor_api import server


@dataclass
class FakeSession:
    id: str
    config: Dict[str, Any]
    title: str = "Harbor recommender session"
    messages: List[Dict[str, str]] = field(default_factory=list)
    turns: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "config": dict(self.config),
            "messages": [dict(message) for message in self.messages],
            "turns": [dict(turn) for turn in self.turns],
            "createdAt": "2026-06-23T00:00:00Z",
        }


class FakeManager:
    def __init__(self) -> None:
        self.sessions: Dict[str, FakeSession] = {}
        self.created = 0

    def create(
        self, title: Optional[str] = None, config: Optional[Dict[str, Any]] = None
    ) -> FakeSession:
        self.created += 1
        session = FakeSession(
            id="ses_{}".format(self.created),
            title=title or "Harbor recommender session",
            config=dict(config or {}),
        )
        self.sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[FakeSession]:
        return self.sessions.get(session_id)

    def run_turn_sync(self, session_id: str, message: str) -> Dict[str, Any]:
        session = self.sessions[session_id]
        turn_id = str(len(session.turns))
        turn = {
            "turnId": turn_id,
            "conversationId": session_id,
            "backend": "interecagent",
            "userMessage": message,
            "assistantMessage": "Try Arrival and Moon for tense, smart science fiction.",
            "recommendedItems": [
                {"itemId": "movie:arrival", "rank": 1, "title": "Arrival"},
                {"itemId": "movie:moon", "rank": 2, "title": "Moon"},
            ],
            "plan": [{"tool": "RankingTool", "status": "ok"}],
        }
        session.messages.append({"role": "user", "content": message})
        session.messages.append(
            {"role": "assistant", "content": turn["assistantMessage"]}
        )
        session.turns.append(turn)
        return turn


class FakeState:
    def __init__(self) -> None:
        self.manager = FakeManager()


def client_with_fake_state(monkeypatch):
    fake_state = FakeState()
    monkeypatch.setattr(server, "build_state", lambda: fake_state)
    server.reset_state_for_tests()
    return TestClient(server.app), fake_state


def test_create_session_uses_harbor_config(monkeypatch):
    client, fake_state = client_with_fake_state(monkeypatch)

    response = client.post(
        "/v1/session",
        json={"domain": "game", "engine": "gpt-4o", "title": "Games run"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sessionId"] == "ses_1"
    assert body["config"]["domain"] == "game"
    assert body["config"]["engine"] == "gpt-4o"
    assert fake_state.manager.sessions["ses_1"].title == "Games run"


def test_message_creates_session_when_omitted(monkeypatch):
    client, _fake_state = client_with_fake_state(monkeypatch)

    response = client.post(
        "/v1/messages",
        json={"message": "I want a tense but not graphic movie.", "domain": "movie"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sessionId"] == "ses_1"
    assert body["reply"].startswith("Try Arrival")
    assert [item["itemId"] for item in body["recommendedItems"]] == [
        "movie:arrival",
        "movie:moon",
    ]
    assert body["turn"]["conversationId"] == "ses_1"


def test_ready_prewarms_native_recommender(monkeypatch):
    client, _fake_state = client_with_fake_state(monkeypatch)
    warmed = []

    monkeypatch.setattr(server, "warm_recommender", warmed.append)

    response = client.get("/ready", params={"domain": "game"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "applicationId": "recai",
        "applicationContext": "game",
        "domain": "game",
    }
    assert warmed == ["game"]


def test_message_appends_to_existing_conversation(monkeypatch):
    client, _fake_state = client_with_fake_state(monkeypatch)
    session = client.post("/v1/session", json={"domain": "movie"}).json()

    response = client.post(
        "/v1/messages",
        json={"sessionId": session["sessionId"], "message": "I liked Arrival."},
    )
    conversation = client.get(
        "/v1/conversation", params={"sessionId": session["sessionId"]}
    )

    assert response.status_code == 200
    assert conversation.status_code == 200
    assert conversation.json()["messages"] == [
        {"role": "user", "content": "I liked Arrival."},
        {
            "role": "assistant",
            "content": "Try Arrival and Moon for tense, smart science fiction.",
        },
    ]


def test_recommendations_are_deduped_across_turns(monkeypatch):
    client, _fake_state = client_with_fake_state(monkeypatch)
    session = client.post("/v1/session", json={"domain": "movie"}).json()
    for message in ("I want sci-fi.", "Anything lesser known?"):
        client.post(
            "/v1/messages",
            json={"sessionId": session["sessionId"], "message": message},
        )

    response = client.get(
        "/v1/recommendations", params={"sessionId": session["sessionId"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["turnsToResult"] == 2
    assert [item["itemId"] for item in body["recommendedItems"]] == [
        "movie:arrival",
        "movie:moon",
    ]


def test_recommendations_prefer_latest_refined_turns():
    turns = [
        {
            "recommendedItems": [
                {"itemId": "old", "rank": 1, "title": "Old Broad Match"},
                {"itemId": "shared", "rank": 2, "title": "Shared"},
            ]
        },
        {
            "recommendedItems": [
                {"itemId": "new", "rank": 1, "title": "New Refined Match"},
                {"itemId": "shared", "rank": 2, "title": "Shared"},
            ]
        },
    ]

    assert [item["itemId"] for item in server._recommended_items_from_turns(turns)] == [
        "new",
        "shared",
        "old",
    ]


def test_unknown_session_returns_404(monkeypatch):
    client, _fake_state = client_with_fake_state(monkeypatch)

    response = client.post(
        "/v1/messages", json={"sessionId": "ses_missing", "message": "hello"}
    )

    assert response.status_code == 404


def test_recai_turns_are_serialized_process_wide(monkeypatch):
    class SlowManager:
        def __init__(self) -> None:
            self.active = 0
            self.max_active = 0
            self.entered = threading.Event()
            self.guard = threading.Lock()

        def run_turn_sync(self, session_id: str, message: str) -> Dict[str, Any]:
            del session_id, message
            with self.guard:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.entered.set()
            time.sleep(0.1)
            with self.guard:
                self.active -= 1
            return {
                "assistantMessage": "done",
                "recommendedItems": [],
            }

    manager = SlowManager()
    monkeypatch.setattr(server, "build_state", lambda: type("State", (), {"manager": manager})())
    server.reset_state_for_tests()

    first = threading.Thread(target=server._run_turn, args=("ses_1", "first"))
    second = threading.Thread(target=server._run_turn, args=("ses_2", "second"))
    first.start()
    assert manager.entered.wait(1)
    second.start()
    first.join()
    second.join()

    assert manager.max_active == 1


def test_recai_turn_execution_value_error_is_server_error(monkeypatch):
    class BrokenManager:
        def run_turn_sync(self, session_id: str, message: str) -> Dict[str, Any]:
            del session_id, message
            raise ValueError("ranker failed")

    monkeypatch.setattr(
        server, "build_state", lambda: type("State", (), {"manager": BrokenManager()})()
    )
    server.reset_state_for_tests()

    with pytest.raises(HTTPException) as exc_info:
        server._run_turn("ses_1", "recommend something")

    assert exc_info.value.status_code == 500
    assert "ranker failed" in str(exc_info.value.detail)


def test_recai_dockerfile_removes_downloaded_resource_zip():
    dockerfile = (
        Path(__file__).parents[1].joinpath("Dockerfile").read_text(encoding="utf-8")
    )

    assert "setup_resources.py &&" in dockerfile
    assert "rm -f /all_resources.zip" in dockerfile


def test_health_reports_generic_chatbot_applications(monkeypatch):
    client, _fake_state = client_with_fake_state(monkeypatch)

    response = client.get("/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "applications" in body
    assert [app["applicationId"] for app in body["applications"]] == [
        "recai",
        "finance_openbb",
    ]
    recai = body["applications"][0]
    assert recai["defaultContext"] == "movie"
    assert "movie" in recai["contexts"]


def test_finance_application_routes_through_generic_contract(monkeypatch):
    class FakeFinanceApp:
        application_id = "finance_openbb"
        default_context = "financial_research"
        contexts = ("financial_research",)

        def ready(self, context: str) -> None:
            self.ready_context = context

        def create_session(
            self, *, title: Optional[str], context: str, engine: Optional[str], bot_type: Optional[str]
        ) -> Dict[str, Any]:
            self.session = {
                "sessionId": "fin_ses_1",
                "applicationId": "finance_openbb",
                "applicationContext": context,
                "config": {"applicationId": "finance_openbb", "applicationContext": context},
                "session": {
                    "id": "fin_ses_1",
                    "title": title or "Finance chat",
                    "messages": [],
                    "turns": [],
                    "createdAt": "2026-06-23T00:00:00Z",
                },
            }
            return self.session

        def send_message(
            self, *, session_id: Optional[str], message: str, title: Optional[str], context: str, engine: Optional[str], bot_type: Optional[str]
        ) -> Dict[str, Any]:
            if not hasattr(self, "session"):
                self.create_session(
                    title=title,
                    context=context,
                    engine=engine,
                    bot_type=bot_type,
                )
            turn = {
                "turnId": "fin_turn_1",
                "conversationId": "fin_ses_1",
                "backend": "finance_openbb",
                "userMessage": message,
                "assistantMessage": "I can compare broad-market ETFs using OpenBB data.",
                "recommendedItems": [
                    {"itemId": "finance:ETF:VTI", "title": "VTI", "rank": 1}
                ],
                "plan": [{"tool": "OpenBB MCP", "status": "ok"}],
            }
            self.session["session"]["messages"] = [
                {"role": "user", "content": message},
                {"role": "assistant", "content": turn["assistantMessage"]},
            ]
            self.session["session"]["turns"] = [turn]
            return {
                "sessionId": "fin_ses_1",
                "applicationId": "finance_openbb",
                "applicationContext": context,
                "reply": turn["assistantMessage"],
                "turn": turn,
                "recommendedItems": turn["recommendedItems"],
                "groundedItems": turn["recommendedItems"],
                "messages": list(self.session["session"]["messages"]),
            }

        def conversation(self, *, session_id: str) -> Dict[str, Any]:
            return {
                "sessionId": session_id,
                "applicationId": "finance_openbb",
                "applicationContext": "financial_research",
                "messages": list(self.session["session"]["messages"]),
                "turns": list(self.session["session"]["turns"]),
            }

        def recommendations(self, *, session_id: str) -> Dict[str, Any]:
            return {
                "sessionId": session_id,
                "applicationId": "finance_openbb",
                "applicationContext": "financial_research",
                "recommendedItems": [
                    {"itemId": "finance:ETF:VTI", "title": "VTI", "rank": 1}
                ],
                "groundedItems": [
                    {"itemId": "finance:ETF:VTI", "title": "VTI", "rank": 1}
                ],
                "turnsToResult": 1,
                "total": 1,
            }

    fake_app = FakeFinanceApp()
    monkeypatch.setattr(server, "get_application", lambda application_id: fake_app)
    client, _fake_state = client_with_fake_state(monkeypatch)

    ready = client.get(
        "/v1/ready",
        params={
            "applicationId": "finance_openbb",
            "applicationContext": "financial_research",
        },
    )
    message = client.post(
        "/v1/messages",
        json={
            "applicationId": "finance_openbb",
            "applicationContext": "financial_research",
            "message": "I want a conservative ETF comparison.",
        },
    )
    conversation = client.get(
        "/v1/conversation",
        params={"sessionId": "fin_ses_1", "applicationId": "finance_openbb"},
    )
    grounded = client.get(
        "/v1/recommendations",
        params={"sessionId": "fin_ses_1", "applicationId": "finance_openbb"},
    )

    assert ready.status_code == 200
    assert ready.json()["applicationId"] == "finance_openbb"
    assert fake_app.ready_context == "financial_research"
    assert message.status_code == 200
    assert message.json()["applicationId"] == "finance_openbb"
    assert message.json()["groundedItems"][0]["itemId"] == "finance:ETF:VTI"
    assert conversation.json()["turns"][0]["backend"] == "finance_openbb"
    assert grounded.json()["turnsToResult"] == 1
    assert grounded.json()["groundedItems"][0]["title"] == "VTI"
