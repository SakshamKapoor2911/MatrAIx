from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
    assert [item["itemId"] for item in body["recommendedItems"]] == [
        "movie:arrival",
        "movie:moon",
    ]


def test_unknown_session_returns_404(monkeypatch):
    client, _fake_state = client_with_fake_state(monkeypatch)

    response = client.post(
        "/v1/messages", json={"sessionId": "ses_missing", "message": "hello"}
    )

    assert response.status_code == 404
