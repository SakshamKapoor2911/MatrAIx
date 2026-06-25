from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from fastapi.testclient import TestClient

from harbor_api import router_server


def test_router_remembers_application_for_followup_messages(monkeypatch):
    calls: list[Dict[str, Any]] = []

    def fake_request_json(
        *,
        application_id: str,
        method: str,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
        query: Optional[Mapping[str, Any]] = None,
        timeout: float = 180.0,
    ) -> Dict[str, Any]:
        del timeout
        calls.append(
            {
                "applicationId": application_id,
                "method": method,
                "path": path,
                "body": dict(body or {}),
                "query": dict(query or {}),
            }
        )
        if path == "/v1/messages":
            return {
                "sessionId": "fin_ses_1",
                "applicationId": application_id,
                "reply": "Finance reply.",
                "groundedItems": [],
            }
        return {"status": "ok", "applicationId": application_id}

    monkeypatch.setattr(router_server, "_request_json", fake_request_json)
    router_server.reset_session_routes_for_tests()
    client = TestClient(router_server.app)

    first = client.post(
        "/v1/messages",
        json={
            "applicationId": "finance_openbb",
            "applicationContext": "financial_research",
            "message": "Compare conservative ETF options.",
        },
    )
    followup = client.post(
        "/v1/messages",
        json={"sessionId": "fin_ses_1", "message": "Can you make that safer?"},
    )

    assert first.status_code == 200
    assert followup.status_code == 200
    assert [call["applicationId"] for call in calls] == [
        "finance_openbb",
        "finance_openbb",
    ]


def test_router_forwards_readiness_to_selected_application(monkeypatch):
    calls: list[Dict[str, Any]] = []

    def fake_request_json(
        *,
        application_id: str,
        method: str,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
        query: Optional[Mapping[str, Any]] = None,
        timeout: float = 180.0,
    ) -> Dict[str, Any]:
        del body, timeout
        calls.append(
            {
                "applicationId": application_id,
                "method": method,
                "path": path,
                "query": dict(query or {}),
            }
        )
        return {"status": "ready", "applicationId": application_id}

    monkeypatch.setattr(router_server, "_request_json", fake_request_json)
    client = TestClient(router_server.app)

    response = client.get(
        "/ready",
        params={
            "applicationId": "recai",
            "applicationContext": "game",
            "domain": "game",
        },
    )

    assert response.status_code == 200
    assert response.json()["applicationId"] == "recai"
    assert calls == [
        {
            "applicationId": "recai",
            "method": "GET",
            "path": "/ready",
            "query": {
                "domain": "game",
                "applicationId": "recai",
                "applicationContext": "game",
            },
        }
    ]


def test_router_routes_medical_application(monkeypatch):
    calls: list[Dict[str, Any]] = []

    def fake_request_json(
        *,
        application_id: str,
        method: str,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
        query: Optional[Mapping[str, Any]] = None,
        timeout: float = 180.0,
    ) -> Dict[str, Any]:
        del query, timeout
        calls.append(
            {
                "applicationId": application_id,
                "method": method,
                "path": path,
                "body": dict(body or {}),
            }
        )
        return {
            "sessionId": "med_ses_1",
            "applicationId": application_id,
            "applicationContext": "medical_consultation",
            "reply": "Medical reply.",
            "groundedItems": [],
        }

    monkeypatch.setattr(router_server, "_request_json", fake_request_json)
    router_server.reset_session_routes_for_tests()
    client = TestClient(router_server.app)

    response = client.post(
        "/v1/messages",
        json={
            "applicationId": "medical_assistant",
            "applicationContext": "medical_consultation",
            "message": "What should I do for a mild fever?",
        },
    )

    assert response.status_code == 200
    assert response.json()["applicationId"] == "medical_assistant"
    assert calls == [
        {
            "applicationId": "medical_assistant",
            "method": "POST",
            "path": "/v1/messages",
            "body": {
                "applicationId": "medical_assistant",
                "applicationContext": "medical_consultation",
                "message": "What should I do for a mild fever?",
            },
        }
    ]
