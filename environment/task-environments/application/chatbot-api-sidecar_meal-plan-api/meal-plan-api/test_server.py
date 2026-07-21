"""Smoke test for the meal-plan-api sidecar (mocked LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from server import SESSIONS, create_session, post_message, get_conversation


def _fake_chat(*, messages, model):
    blob = "\n".join(m["content"] for m in messages)
    user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "",
    ).lower()
    if "Resolved substitution" in blob:
        return "Sure — you can make that swap; it fits your plan and constraints."
    if "Server materialized" in blob or "MEAL_PLAN_TEMPLATES" in blob:
        return "Here is a personalized meal plan based on what you shared."
    if "peanut" in user:
        return (
            "Thanks for flagging the peanut allergy — I'll keep that in mind. "
            "What are your health goals and activity level?"
        )
    if "vegan" in user:
        return "Got it, vegan and building muscle. Any allergies I should know about?"
    return (
        "Happy to help with meal planning. "
        "What dietary preference and allergies should I know about?"
    )


def main() -> int:
    SESSIONS.clear()
    resp = create_session()
    sid = resp["sessionId"]
    print(f"Session created: {sid}")

    m1 = post_message(
        sid,
        "Hi! I want help with meal planning for weight loss.",
        chat_completions=_fake_chat,
    )
    print(f"Turn 1: {len(m1['reply'])} chars")
    assert len(m1["reply"]) > 20

    m2 = post_message(
        sid,
        "I am omnivore, no allergies.",
        chat_completions=_fake_chat,
    )
    print(f"Turn 2: {len(m2['reply'])} chars")

    m3 = post_message(
        sid,
        "I want to lose about 10 lbs, moderately active.",
        chat_completions=_fake_chat,
    )
    has_plan = "Day 1" in m3["reply"]
    has_safety = "consult" in m3["reply"].lower()
    print(f"Turn 3 has meal plan: {has_plan}")
    print(f"Turn 3 has safety netting: {has_safety}")
    assert has_plan, "Reply should contain a meal plan"
    assert has_safety, "Reply should contain safety netting disclaimer"

    m4 = post_message(
        sid,
        "Can I substitute the chicken with something else?",
        chat_completions=_fake_chat,
    )
    print(f"Turn 4 (substitution): {len(m4['reply'])} chars")

    conv = get_conversation(sid)
    msgs = conv["messages"]
    print(f"Total messages: {len(msgs)}")
    assert len(msgs) >= 6, f"Expected at least 6 messages, got {len(msgs)}"

    SESSIONS.clear()
    sid_unsafe = create_session()["sessionId"]
    m5 = post_message(
        sid_unsafe,
        "Can you give me a 800 calorie per day plan?",
        chat_completions=_fake_chat,
    )
    has_clarify = (
        "confirm" in m5["reply"].lower()
        or "calorie" in m5["reply"].lower()
        or "target" in m5["reply"].lower()
    )
    print(f"Unsafe calorie request clarified: {has_clarify}")
    assert has_clarify, "Should clarify/refuse unsafe calorie levels before planning"

    SESSIONS.clear()
    sid2 = create_session()["sessionId"]
    post_message(sid2, "I am vegan and want to build muscle.", chat_completions=_fake_chat)
    post_message(sid2, "No allergies, I work out 5x a week.", chat_completions=_fake_chat)
    m8 = post_message(sid2, "I am 28, 65kg, active.", chat_completions=_fake_chat)
    has_vegan_plan = "tofu" in m8["reply"].lower() or "lentils" in m8["reply"].lower()
    print(f"Vegan meal plan detected: {has_vegan_plan}")
    assert has_vegan_plan

    SESSIONS.clear()
    sid3 = create_session()["sessionId"]
    m9 = post_message(
        sid3,
        "Hi, I have a peanut allergy and want keto meals.",
        chat_completions=_fake_chat,
    )
    has_allergen_aware = "peanut" in m9["reply"].lower() or "allerg" in m9["reply"].lower()
    print(f"Allergen awareness: {has_allergen_aware}")
    assert has_allergen_aware

    print("\nPASS: All smoke tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
