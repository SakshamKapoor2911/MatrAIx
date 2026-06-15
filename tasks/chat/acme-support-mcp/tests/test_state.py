import json
from pathlib import Path

TRANSCRIPT_PATH = Path("/app/output/transcript.json")


def _load_transcript() -> dict:
    assert TRANSCRIPT_PATH.is_file(), f"Missing {TRANSCRIPT_PATH}"
    data = json.loads(TRANSCRIPT_PATH.read_text())
    assert isinstance(data, dict), "transcript root must be an object"
    assert "messages" in data, "transcript must include 'messages'"
    return data


def test_transcript_exists():
    assert TRANSCRIPT_PATH.is_file(), f"Missing {TRANSCRIPT_PATH}"


def test_transcript_schema():
    data = _load_transcript()
    messages = data["messages"]
    assert isinstance(messages, list) and messages, "messages must be a non-empty list"
    for entry in messages:
        assert entry.get("role") in {"customer", "support"}, "invalid message role"
        content = entry.get("content")
        assert isinstance(content, str) and content.strip(), "message content must be non-empty"


def test_transcript_multi_turn():
    messages = _load_transcript()["messages"]
    customer_count = sum(1 for m in messages if m["role"] == "customer")
    support_count = sum(1 for m in messages if m["role"] == "support")
    assert customer_count >= 2, "expected at least two customer messages"
    assert support_count >= 2, "expected at least two support replies"
    assert len(messages) >= 4, "expected at least four messages total"


def test_transcript_mentions_order():
    messages = _load_transcript()["messages"]
    combined = " ".join(m["content"] for m in messages)
    assert "4521" in combined, "conversation should reference order #4521"
