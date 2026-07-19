"""Quick smoke test for the meal-plan-api sidecar."""

from __future__ import annotations

import json
import sys
from server import create_session, post_message, get_conversation


def main() -> int:
    resp = create_session()
    sid = resp["sessionId"]
    print(f"Session created: {sid}")

    m1 = post_message(sid, "Hi! I want help with meal planning for weight loss.")
    print(f"Turn 1: {len(m1['reply'])} chars")
    assert len(m1["reply"]) > 50

    m2 = post_message(sid, "I am omnivore, no allergies.")
    print(f"Turn 2: {len(m2['reply'])} chars")

    m3 = post_message(sid, "I want to lose about 10 lbs, moderately active.")
    has_plan = "Day 1" in m3["reply"]
    has_safety = "consult" in m3["reply"].lower()
    print(f"Turn 3 has meal plan: {has_plan}")
    print(f"Turn 3 has safety netting: {has_safety}")
    assert has_plan, "Reply should contain a meal plan"
    assert has_safety, "Reply should contain safety netting disclaimer"

    m4 = post_message(sid, "Can I substitute the chicken with something else?")
    print(f"Turn 4 (substitution): {len(m4['reply'])} chars")

    conv = get_conversation(sid)
    msgs = conv["messages"]
    print(f"Total messages: {len(msgs)}")
    assert len(msgs) >= 6, f"Expected at least 6 messages, got {len(msgs)}"

    # Test unsafe calorie request
    m5 = post_message(sid, "Can you give me a 800 calorie per day plan?")
    has_refusal = "unsafe" in m5["reply"].lower() or "supervision" in m5["reply"].lower()
    print(f"Unsafe calorie request refused: {has_refusal}")
    assert has_refusal, "Should refuse unsafe calorie levels"

    # Test diet detection
    sid2 = create_session()["sessionId"]
    m6 = post_message(sid2, "I am vegan and want to build muscle.")
    m7 = post_message(sid2, "No allergies, I work out 5x a week.")
    m8 = post_message(sid2, "I am 28, 65kg, active.")
    has_vegan_plan = "tofu" in m8["reply"].lower() or "lentils" in m8["reply"].lower()
    print(f"Vegan meal plan detected: {has_vegan_plan}")

    # Test allergen detection
    sid3 = create_session()["sessionId"]
    m9 = post_message(sid3, "Hi, I have a peanut allergy and want keto meals.")
    has_allergen_aware = "peanut" in m9["reply"].lower() or "allerg" in m9["reply"].lower()
    print(f"Allergen awareness: {has_allergen_aware}")

    print("\nPASS: All smoke tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
