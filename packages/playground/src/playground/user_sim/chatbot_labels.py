from __future__ import annotations


_CHATBOT_LABELS = {
    "recai": "RecAI",
    "finance_openbb": "FinAI / OpenBB",
    "medical_assistant": "Medical Assistant",
}


def chatbot_display_name(application_id: str | None) -> str:
    value = str(application_id or "").strip()
    if not value:
        return "Chatbot"
    return _CHATBOT_LABELS.get(value, value.replace("_", " ").strip().title() or "Chatbot")
