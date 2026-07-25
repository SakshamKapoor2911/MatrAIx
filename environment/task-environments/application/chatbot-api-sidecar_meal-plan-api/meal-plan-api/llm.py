"""OpenAI-backed natural-language layer for meal-plan replies."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Callable

_LLM_SEM: threading.Semaphore | None = None
_LLM_SEM_LOCK = threading.Lock()


def _llm_semaphore() -> threading.Semaphore:
    global _LLM_SEM
    with _LLM_SEM_LOCK:
        if _LLM_SEM is None:
            raw = os.environ.get("MEAL_PLAN_LLM_CONCURRENCY", "32").strip()
            try:
                limit = max(1, int(raw))
            except ValueError:
                limit = 32
            _LLM_SEM = threading.Semaphore(limit)
        return _LLM_SEM


def llm_enabled() -> bool:
    """Return True when grounded LLM replies should be attempted."""
    flag = os.environ.get("MEAL_PLAN_LLM", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def model_name() -> str:
    return os.environ.get("MEAL_PLAN_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def _plan_summary(plan: list[dict[str, Any]] | None, *, max_days: int = 3) -> str:
    if not plan:
        return "(no plan materialized yet)"
    lines: list[str] = []
    for day in plan[:max_days]:
        lines.append(f"Day {day.get('day')}:")
        for meal in day.get("meals") or []:
            items = ", ".join(
                f"{item.get('id')} x{item.get('servings')}"
                for item in meal.get("items") or []
            )
            lines.append(
                f"  {meal.get('meal')}: {items} "
                f"({meal.get('total_calories', 0):.0f} kcal)"
            )
        totals = day.get("daily_totals") or {}
        lines.append(
            f"  totals: {totals.get('calories', 0):.0f} kcal, "
            f"{totals.get('protein_g', 0):.0f}g protein"
        )
    if len(plan) > max_days:
        lines.append(f"... ({len(plan) - max_days} more day(s) in full plan block)")
    return "\n".join(lines)


def _food_catalog_slice(
    *,
    allergens: list[str],
    diet: str | None,
    limit: int = 24,
) -> str:
    from nutrition_data import FOOD_DATABASE

    rows: list[str] = []
    for food in FOOD_DATABASE[:limit]:
        tags = ", ".join(food.get("tags") or [])
        rows.append(f"- {food['name']} [{food['id']}] tags={tags}")
    hint = ""
    if allergens:
        hint += f" User allergens: {', '.join(allergens)}."
    if diet:
        hint += f" Diet preference: {diet}."
    return "Known foods for substitutions (do not invent others):\n" + "\n".join(rows) + hint


def build_grounded_messages(
    *,
    session: dict[str, Any],
    user_message: str,
    action_notes: list[str],
    formatted_plan: str | None,
) -> list[dict[str, str]]:
    """Build chat messages with compact grounded product context."""
    profile = {
        "dietary_preference": session.get("dietary_preference"),
        "health_goal": session.get("health_goal"),
        "allergens": session.get("allergens") or [],
        "plan_generated": bool(session.get("plan_generated")),
        "profile_gathered": bool(session.get("profile_gathered")),
        "unsafe_request_flagged": bool(session.get("unsafe_request_flagged")),
        "clinical_boundary_flagged": bool(session.get("clinical_boundary_flagged")),
    }
    system = (
        "You are a friendly meal-planning and nutrition coach chatbot, not a "
        "clinician. Speak naturally in short paragraphs. Do NOT invent a new "
        "multi-day menu or calorie totals — the server already materializes "
        "plans from a fixed food database. When a formatted meal plan block is "
        "provided below, you may briefly introduce it but must not rewrite the "
        "menu items or macros. Never give medical diagnosis or treatment. "
        "If the user asks for unsafe very-low-calorie plans, the server already "
        "handled that; follow the action notes. Keep allergen safety front of mind."
    )
    context_parts = [
        "Session profile (JSON):\n" + json.dumps(profile, ensure_ascii=True),
        "Current plan summary (from templates):\n"
        + _plan_summary(session.get("current_plan")),
        _food_catalog_slice(
            allergens=list(session.get("allergens") or []),
            diet=session.get("dietary_preference"),
        ),
    ]
    if action_notes:
        context_parts.append(
            "Deterministic product actions already taken this turn:\n- "
            + "\n- ".join(action_notes)
        )
    if formatted_plan:
        context_parts.append(
            "Formatted meal plan block (include or introduce; do not alter items):\n"
            + formatted_plan
        )

    history: list[dict[str, str]] = []
    prior = session.get("messages") or []
    for msg in prior[-7:-1]:
        role = msg.get("role")
        content = str(msg.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            history.append({"role": role, "content": content[:1200]})

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    messages.append(
        {
            "role": "system",
            "content": "Grounded product context:\n\n" + "\n\n".join(context_parts),
        }
    )
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


def generate_llm_reply(
    *,
    session: dict[str, Any],
    user_message: str,
    action_notes: list[str],
    formatted_plan: str | None = None,
    chat_completions: Callable[..., Any] | None = None,
) -> str | None:
    """Call OpenAI chat completions; return None on disable/failure."""
    if chat_completions is None and not llm_enabled():
        return None
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if chat_completions is None and not api_key:
        return None

    messages = build_grounded_messages(
        session=session,
        user_message=user_message,
        action_notes=action_notes,
        formatted_plan=formatted_plan,
    )

    try:
        if chat_completions is not None:
            content = chat_completions(messages=messages, model=model_name())
            text = str(content or "").strip()
            return text or None

        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=60.0, max_retries=2)
        with _llm_semaphore():
            response = client.chat.completions.create(
                model=model_name(),
                messages=messages,
                temperature=0.7,
                max_tokens=900,
            )
        text = (response.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        return None
