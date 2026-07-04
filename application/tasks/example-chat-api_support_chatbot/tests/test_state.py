from __future__ import annotations

import json
import os
from pathlib import Path

TRANSCRIPT_PATH = Path("/app/output/transcript.json")


def _verifier_dir() -> Path:
    base = (
        os.environ.get("HARBOR_VERIFIER_DIR")
        or os.environ.get("PERSONABENCH_VERIFIER_DIR")
        or "/logs/verifier"
    )
    path = Path(base)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        path = Path(__file__).resolve().parent.parent / "verifier"
        path.mkdir(parents=True, exist_ok=True)
        return path


def _load_transcript() -> dict:
    assert TRANSCRIPT_PATH.is_file(), f"Missing {TRANSCRIPT_PATH}"
    data = json.loads(TRANSCRIPT_PATH.read_text())
    assert isinstance(data, dict), "transcript root must be an object"
    assert "messages" in data, "transcript must include 'messages'"
    return data


def _count_support_questions(messages: list[dict]) -> int:
    return sum(
        1
        for entry in messages
        if entry.get("role") == "support"
        and isinstance(entry.get("content"), str)
        and "?" in entry["content"]
    )


def _derive_outcome_status(combined_lower: str, support_count: int) -> str:
    if "tracking" in combined_lower and support_count >= 2:
        return "partially_resolved"
    return "unresolved"


def _derive_next_step_owner(combined_lower: str) -> str:
    followup_markers = (
        "if it still",
        "if it doesn't",
        "if it has not",
        "let us know",
        "check back",
    )
    return "user" if any(marker in combined_lower for marker in followup_markers) else "none"


def test_transcript_exists():
    assert TRANSCRIPT_PATH.is_file(), f"Missing {TRANSCRIPT_PATH}"


def test_transcript_schema():
    data = _load_transcript()
    messages = data["messages"]
    assert isinstance(messages, list) and messages, "messages must be a non-empty list"
    for entry in messages:
        assert entry.get("role") in {"customer", "support"}, "invalid message role"
        content = entry.get("content")
        assert isinstance(content, str) and content.strip(), (
            "message content must be non-empty"
        )

    customer_count = sum(1 for m in messages if m["role"] == "customer")
    support_count = sum(1 for m in messages if m["role"] == "support")
    clarification_question_count = _count_support_questions(messages)
    combined = " ".join(str(m["content"]) for m in messages)
    combined_lower = combined.lower()
    outcome_status = _derive_outcome_status(combined_lower, support_count)
    next_step_owner = _derive_next_step_owner(combined_lower)
    asked_about_address = "address" in combined_lower
    has_tracking_update = "tracking" in combined_lower
    conversation_path = "clarify_then_partial" if (
        clarification_question_count > 0 or has_tracking_update
    ) else "stalled"
    outcome_reason = (
        "Support provided a concrete shipment update and follow-up guidance, but the "
        "late delivery issue was not fully resolved within this chat."
        if has_tracking_update
        else "The chat did not produce a concrete shipment update, so the missing "
        "delivery remained unresolved."
    )
    process_notes = (
        "The conversation focused on clarifying the delivery status and reviewing "
        "tracking details before ending with a follow-up expectation."
        if asked_about_address or has_tracking_update
        else "The conversation stayed short and did not reach a concrete status update."
    )
    (_verifier_dir() / "structured_output.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "artifactType": "personabench.trial_evaluation",
                "taskType": "chatbot",
                "presenceCheck": {
                    "passed": True,
                    "requiredArtifacts": ["transcript.json"],
                    "missingArtifacts": [],
                },
                "sourceArtifacts": {
                    "transcript": str(TRANSCRIPT_PATH),
                },
                "contexts": [
                    {
                        "key": "task_outcome.primary",
                        "label": "Task outcome",
                        "contextType": "task_outcome",
                        "facets": [
                            {
                                "key": "outcome_status",
                                "label": "Outcome status",
                                "role": "primary",
                                "kind": "categorical",
                                "value": outcome_status,
                            },
                            {
                                "key": "resolution_basis",
                                "label": "Resolution basis",
                                "role": "primary",
                                "kind": "categorical",
                                "value": "conversation_commitment",
                            },
                            {
                                "key": "outcome_reason",
                                "label": "Outcome reason",
                                "role": "explanation",
                                "kind": "textual",
                                "value": outcome_reason,
                            },
                            {
                                "key": "next_step_owner",
                                "label": "Next step owner",
                                "role": "evidence",
                                "kind": "categorical",
                                "value": next_step_owner,
                            },
                            {
                                "key": "task_goal_label",
                                "label": "Task goal",
                                "role": "evidence",
                                "kind": "textual",
                                "value": "Get a useful update on a missing delivery",
                            },
                        ],
                    },
                    {
                        "key": "conversation_summary.primary",
                        "label": "Conversation summary",
                        "contextType": "conversation_summary",
                        "facets": [
                            {
                                "key": "conversation_path",
                                "label": "Conversation path",
                                "role": "primary",
                                "kind": "categorical",
                                "value": conversation_path,
                            },
                            {
                                "key": "process_notes",
                                "label": "Process notes",
                                "role": "explanation",
                                "kind": "textual",
                                "value": process_notes,
                            },
                            {
                                "key": "user_turn_count",
                                "label": "User turn count",
                                "role": "score",
                                "kind": "numerical",
                                "value": customer_count,
                            },
                            {
                                "key": "assistant_turn_count",
                                "label": "Assistant turn count",
                                "role": "score",
                                "kind": "numerical",
                                "value": support_count,
                            },
                            {
                                "key": "message_count",
                                "label": "Message count",
                                "role": "score",
                                "kind": "numerical",
                                "value": len(messages),
                            },
                            {
                                "key": "clarification_question_count",
                                "label": "Clarification question count",
                                "role": "score",
                                "kind": "numerical",
                                "value": clarification_question_count,
                            },
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
