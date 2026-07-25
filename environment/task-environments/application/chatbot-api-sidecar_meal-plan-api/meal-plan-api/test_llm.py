"""Unit tests for grounded LLM prompt builder and hybrid reply path."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm import build_grounded_messages, llm_enabled
from server import SESSIONS, _SESSION_LOCKS, create_session, post_message


def _clear_sessions() -> None:
    SESSIONS.clear()
    _SESSION_LOCKS.clear()


def test_llm_enabled_respects_flag_and_key() -> None:
    prev_key = os.environ.pop("OPENAI_API_KEY", None)
    prev_flag = os.environ.pop("MEAL_PLAN_LLM", None)
    try:
        assert llm_enabled() is False
        os.environ["OPENAI_API_KEY"] = "sk-test"
        assert llm_enabled() is True
        os.environ["MEAL_PLAN_LLM"] = "0"
        assert llm_enabled() is False
        os.environ["MEAL_PLAN_LLM"] = "1"
        assert llm_enabled() is True
    finally:
        if prev_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = prev_key
        if prev_flag is None:
            os.environ.pop("MEAL_PLAN_LLM", None)
        else:
            os.environ["MEAL_PLAN_LLM"] = prev_flag


def test_grounded_prompt_includes_plan_and_allergens() -> None:
    _clear_sessions()
    sid = create_session()["sessionId"]
    session = SESSIONS[sid]
    session["dietary_preference"] = "vegan"
    session["health_goal"] = "muscle gain"
    session["allergens"] = ["peanut"]
    session["plan_generated"] = True
    session["current_plan"] = [
        {
            "day": 1,
            "meals": [
                {
                    "meal": "Breakfast",
                    "items": [{"id": "protein-tofu", "servings": 1}],
                    "total_calories": 300,
                    "total_protein_g": 20,
                    "total_carbs_g": 10,
                    "total_fat_g": 15,
                }
            ],
            "daily_totals": {
                "calories": 300,
                "protein_g": 20,
                "carbs_g": 10,
                "fat_g": 15,
            },
        }
    ]
    session["messages"] = [
        {"role": "user", "content": "I am vegan with a peanut allergy."},
        {"role": "assistant", "content": "Got it."},
        {"role": "user", "content": "Can I swap tofu?"},
    ]
    messages = build_grounded_messages(
        session=session,
        user_message="Can I swap tofu?",
        action_notes=["Resolved substitution from FOOD_DATABASE: replace Tofu with Tempeh."],
        formatted_plan=None,
    )
    blob = "\n".join(m["content"] for m in messages)
    assert "peanut" in blob
    assert "vegan" in blob
    assert "Day 1" in blob
    assert "prot-tofu" in blob or "tofu" in blob.lower()
    assert "FOOD_DATABASE" in blob or "substitution" in blob.lower()
    assert "Do NOT invent a new multi-day menu" in blob or "do not invent" in blob.lower()


def test_mock_llm_path_appends_plan_when_omitted() -> None:
    _clear_sessions()
    try:
        sid = create_session()["sessionId"]

        def fake_chat(*, messages, model):
            assert any("Grounded product context" in m["content"] for m in messages)
            blob = "\n".join(m["content"] for m in messages)
            assert "omnivore" in blob or "weight loss" in blob or "allerg" in blob.lower()
            return "Happy to help — here is a plan tailored to you."

        post_message(
            sid,
            "Hi! I want help with meal planning for weight loss.",
            chat_completions=fake_chat,
        )
        post_message(sid, "I am omnivore, no allergies.", chat_completions=fake_chat)
        m3 = post_message(
            sid,
            "I want to lose about 10 lbs, moderately active.",
            chat_completions=fake_chat,
        )
        assert "Happy to help" in m3["reply"]
        assert "Day 1" in m3["reply"]
        assert "consult" in m3["reply"].lower()
    finally:
        _clear_sessions()


def test_template_isolation_under_allergen_adapt() -> None:
    from nutrition_data import MEAL_PLAN_TEMPLATES
    from server import _adapt_plan_for_allergens, _get_plan

    before = json.dumps(MEAL_PLAN_TEMPLATES["vegan_high_protein"], sort_keys=True, default=str)
    plan_a = _get_plan("vegan_high_protein")
    plan_b = _get_plan("vegan_high_protein")
    _adapt_plan_for_allergens(plan_a, ["dairy", "gluten", "peanut", "soy"])
    after = json.dumps(MEAL_PLAN_TEMPLATES["vegan_high_protein"], sort_keys=True, default=str)
    assert before == after
    assert plan_a is not plan_b


def test_concurrent_sessions() -> None:
    import threading

    _clear_sessions()
    errors: list[str] = []

    def worker(i: int) -> None:
        try:
            sid = create_session()["sessionId"]

            def fake(*, messages, model):
                return f"ok-{i}"

            post_message(sid, f"Hi vegan user {i}", chat_completions=fake)
            post_message(sid, "No allergies", chat_completions=fake)
            r = post_message(
                sid,
                "I want to build muscle, active",
                chat_completions=fake,
            )
            if "Day 1" not in r["reply"] and f"ok-{i}" not in r["reply"]:
                errors.append(f"bad reply for {i}")
            if SESSIONS[sid]["dietary_preference"] != "vegan":
                errors.append(f"diet leak for {i}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{i}: {exc}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(24)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    assert len(SESSIONS) == 24
    _clear_sessions()


def test_hard_safety_skips_llm() -> None:
    _clear_sessions()
    called = {"n": 0}

    def boom(*, messages, model):
        called["n"] += 1
        raise AssertionError("LLM must not be called for hard safety")

    sid = create_session()["sessionId"]
    # Pre-plan unsafe calorie request
    reply = post_message(
        sid,
        "Please make me an 800 calorie per day plan.",
        chat_completions=boom,
    )
    assert called["n"] == 0
    assert "calorie" in reply["reply"].lower() or "confirm" in reply["reply"].lower()
    _clear_sessions()


def main() -> int:
    test_llm_enabled_respects_flag_and_key()
    test_grounded_prompt_includes_plan_and_allergens()
    test_mock_llm_path_appends_plan_when_omitted()
    test_template_isolation_under_allergen_adapt()
    test_concurrent_sessions()
    test_hard_safety_skips_llm()
    print("PASS: LLM grounded hybrid tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
