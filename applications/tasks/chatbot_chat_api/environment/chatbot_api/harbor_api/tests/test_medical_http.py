from __future__ import annotations

from typing import Any, Dict, List, Optional

from harbor_api.medical_http import (
    MEDICAL_APPLICATION_ID,
    MEDICAL_CONTEXT,
    MedicalAssistantApplication,
    MedicalAssistantConfig,
    MedicalAssistantService,
)


class FakeMedicalClient:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def health(self) -> Dict[str, Any]:
        self.calls.append({"method": "health"})
        return {"status": "healthy"}

    def chat(
        self,
        *,
        message: str,
        history: List[Dict[str, str]],
        cookie: Optional[str],
    ) -> tuple[Dict[str, Any], Optional[str]]:
        self.calls.append(
            {
                "method": "chat",
                "message": message,
                "history": [dict(item) for item in history],
                "cookie": cookie,
            }
        )
        return (
            {
                "status": "success",
                "response": "Drink fluids and seek care if symptoms worsen.",
                "agent": "CONVERSATION_AGENT",
            },
            "session_id=abc",
        )


def test_medical_application_wraps_external_chat_contract() -> None:
    client = FakeMedicalClient()
    service = MedicalAssistantService(
        client=client,
        config=MedicalAssistantConfig(base_url="http://medical.example"),
    )
    app = MedicalAssistantApplication(service=service)

    app.ready(MEDICAL_CONTEXT)
    first = app.send_message(
        session_id=None,
        message="What can I do for a mild fever?",
        title=None,
        context=MEDICAL_CONTEXT,
        engine=None,
        bot_type=None,
    )
    session_id = first["sessionId"]
    followup = app.send_message(
        session_id=session_id,
        message="When should I seek urgent care?",
        title=None,
        context=MEDICAL_CONTEXT,
        engine=None,
        bot_type=None,
    )
    conversation = app.conversation(session_id=session_id)
    result = app.recommendations(session_id=session_id)

    assert first["applicationId"] == MEDICAL_APPLICATION_ID
    assert first["applicationContext"] == MEDICAL_CONTEXT
    assert first["turn"]["backend"] == MEDICAL_APPLICATION_ID
    assert first["turn"]["plan"][0]["tool"] == "CONVERSATION_AGENT"
    assert followup["messages"][-1]["role"] == "assistant"
    assert conversation["turns"][0]["assistantMessage"].startswith("Drink fluids")
    assert result["groundedItems"] == []
    assert result["turnsToResult"] == 2
    assert client.calls[2]["history"][0]["content"] == "What can I do for a mild fever?"
    assert client.calls[2]["cookie"] == "session_id=abc"
