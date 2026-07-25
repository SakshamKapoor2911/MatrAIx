"""Meal Planning & Nutrition Chatbot API."""

from __future__ import annotations

import copy
import json
import os
import re
import threading
import uuid
from collections import OrderedDict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from llm import generate_llm_reply
from nutrition_data import (
    FOOD_DATABASE,
    MEAL_PLAN_TEMPLATES,
    DIETARY_PATTERN_KEYWORDS,
    DANGEROUS_CALORIE_THRESHOLD,
    CLINICAL_THERAPY_KEYWORDS,
    SAFETY_NETTING_DISCLAIMER,
    DEFAULT_MEAL_PLAN,
)


def _get_plan(key: str) -> list[dict[str, Any]]:
    # Always copy — allergen adaptation mutates the plan structure.
    return copy.deepcopy(
        MEAL_PLAN_TEMPLATES.get(key) or MEAL_PLAN_TEMPLATES[DEFAULT_MEAL_PLAN]
    )


_SESSIONS_LOCK = threading.RLock()
_SESSION_LOCKS: dict[str, threading.RLock] = {}
SESSIONS: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _max_sessions() -> int:
    raw = os.environ.get("MEAL_PLAN_MAX_SESSIONS", "2000").strip()
    try:
        return max(32, int(raw))
    except ValueError:
        return 2000


def _session_lock(session_id: str) -> threading.RLock:
    with _SESSIONS_LOCK:
        lock = _SESSION_LOCKS.get(session_id)
        if lock is None:
            lock = threading.RLock()
            _SESSION_LOCKS[session_id] = lock
        return lock


def _evict_sessions_if_needed() -> None:
    limit = _max_sessions()
    while len(SESSIONS) >= limit:
        old_id, _ = SESSIONS.popitem(last=False)
        _SESSION_LOCKS.pop(old_id, None)


def _find_food(food_id: str) -> dict[str, Any] | None:
    for item in FOOD_DATABASE:
        if item["id"] == food_id:
            return item
    return None


def _find_food_by_name(name: str) -> dict[str, Any] | None:
    lowered = name.lower()
    for item in FOOD_DATABASE:
        if item["name"].lower() == lowered or item["id"].split("-", 1)[1].replace("-", " ") == lowered:
            return item
    return None


def _tokenize(text: str) -> set[str]:
    return {
        token.strip(".,!?;:()[]{}\"'").lower()
        for token in text.split()
        if token.strip(".,!?;:()[]{}\"'")
    }


def _detect_dietary_preference(text: str) -> str | None:
    _tokens = _tokenize(text)
    diet_keywords: dict[str, list[str]] = {
        "vegan": ["vegan", "plant-based", "no animal"],
        "vegetarian": ["vegetarian", "lacto-ovo", "no meat"],
        "keto": ["keto", "ketogenic", "low-carb", "very low carb"],
        "gluten-free": ["gluten-free", "gluten free", "celiac", "no gluten"],
        "halal": ["halal"],
        "kosher": ["kosher"],
        "mediterranean": ["mediterranean"],
        "paleo": ["paleo", "paleolithic"],
        "omnivore": ["omnivore", "no restriction", "anything", "any diet"],
    }
    for diet, keywords in diet_keywords.items():
        if any(kw in text.lower() for kw in keywords):
            return diet
    return None


def _detect_health_goal(text: str) -> str | None:
    goal_keywords: dict[str, list[str]] = {
        "weight loss": ["lose weight", "weight loss", "fat loss", "slim down", "drop pounds"],
        "muscle gain": ["muscle gain", "build muscle", "bulk", "get stronger"],
        "maintenance": ["maintain", "maintenance", "stay healthy"],
        "blood-sugar management": ["blood sugar", "diabetes", "glucose", "a1c"],
        "heart health": ["heart health", "cholesterol", "blood pressure", "cardiovascular"],
        "digestive health": ["digestive", "gut health", "bloating", "digestion", "low-fodmap"],
        "improved energy": ["energy", "energized", "fatigue", "tired"],
        "sports performance": ["sports", "athletic", "performance", "training"],
    }
    for goal, keywords in goal_keywords.items():
        if any(kw in text.lower() for kw in keywords):
            return goal
    return None


def _detect_allergens(text: str) -> list[str]:
    allergen_keywords: dict[str, list[str]] = {
        "peanut": ["peanut", "peanuts"],
        "tree nut": ["tree nut", "almond", "walnut", "cashew", "pecan", "pistachio"],
        "dairy": ["dairy", "milk", "cheese", "yogurt", "lactose", "whey", "casein"],
        "egg": ["egg", "eggs"],
        "soy": ["soy", "soya", "tofu", "edamame"],
        "shellfish": ["shellfish", "shrimp", "crab", "lobster"],
        "fish": ["fish", "salmon", "tuna", "cod"],
        "wheat": ["wheat", "wheat flour"],
        "gluten": ["gluten", "gluten-free", "gluten free"],
        "sesame": ["sesame"],
    }
    detected = []
    for allergen, keywords in allergen_keywords.items():
        if any(kw in text.lower() for kw in keywords):
            detected.append(allergen)
    return detected


def _detect_clinical_advice(text: str) -> bool:
    return any(kw in text.lower() for kw in CLINICAL_THERAPY_KEYWORDS)


def _is_unsafe_calorie_request(text: str) -> bool:
    cleaned = text.lower().replace(",", "")
    match = re.search(r"(\d+)\s*(calorie|cal|kcal)", cleaned)
    if match and int(match.group(1)) < DANGEROUS_CALORIE_THRESHOLD:
        return True
    match = re.search(r"(under|less than|below|fewer than)\s*(\d+)", cleaned)
    if match and int(match.group(2)) < DANGEROUS_CALORIE_THRESHOLD:
        return True
    return False


_END_CONVERSATION_PATTERNS = [
    "end_conversation",
    "conversation ended",
    "conversation is over",
    "no further messages",
    "conversation has ended",
    "already ended this conversation",
    "going to stop here",
    "this is going nowhere",
    "stop sending messages",
    "nothing more to discuss",
    "conversation is finished",
    "no further engagement",
    "no longer participating",
]


def _is_end_of_conversation(text: str) -> bool:
    lowered = text.lower().strip()
    return any(pat in lowered for pat in _END_CONVERSATION_PATTERNS)


def _pick_meal_plan(diet: str | None, goal: str | None) -> list[dict[str, Any]]:
    if diet and diet in {"vegan", "vegetarian"}:
        return _get_plan("vegan_high_protein")
    if diet == "keto":
        return _get_plan("keto_standard")
    if goal:
        for g, key in DIETARY_PATTERN_KEYWORDS.items():
            if g in goal.lower() or (goal and g in goal.lower()):
                return _get_plan(key)
    return _get_plan(DEFAULT_MEAL_PLAN)


def _name_or_id(food_id: str, servings: float) -> str:
    food = _find_food(food_id)
    name = food["name"] if food else food_id
    return f"{name} ({servings} serving)"


def _format_meal_plan(plan: list[dict[str, Any]]) -> str:
    lines = ["Here is your personalized meal plan:", ""]
    for day in plan:
        lines.append(f"--- Day {day['day']} ---")
        for meal in day["meals"]:
            items_str = ", ".join(
                _name_or_id(item["id"], item["servings"])
                for item in meal["items"]
            )
            lines.append(
                f"  {meal['meal']}: {items_str}"
            )
            lines.append(
                f"    → {meal['total_calories']:.0f} kcal, "
                f"{meal['total_protein_g']:.0f}g protein, "
                f"{meal['total_carbs_g']:.0f}g carbs, "
                f"{meal['total_fat_g']:.0f}g fat"
            )
        dt = day["daily_totals"]
        lines.append(f"  Daily total: {dt['calories']:.0f} kcal, "
                      f"{dt['protein_g']:.0f}g protein, "
                      f"{dt['carbs_g']:.0f}g carbs, "
                      f"{dt['fat_g']:.0f}g fat")
        lines.append("")
    lines.append(SAFETY_NETTING_DISCLAIMER)
    return "\n".join(lines)


def _find_substitute(food_id: str, allergens: list[str], diet: str | None) -> str | None:
    food = _find_food(food_id)
    if not food:
        return None
    category = food["category"]
    candidates = [f for f in FOOD_DATABASE if f["category"] == category and f["id"] != food_id]
    for allergen in allergens:
        candidates = [f for f in candidates if allergen not in f["tags"]]
    if diet == "vegan":
        candidates = [f for f in candidates if "vegan" in f["tags"]]
    elif diet == "keto":
        candidates = [f for f in candidates if "keto" in f["tags"]]
    candidates.sort(key=lambda f: abs(f.get("protein_g", 0) - food.get("protein_g", 0)))
    return candidates[0]["name"] if candidates else None


def create_session(domain: str = "meal_planning") -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    session = {
        "sessionId": session_id,
        "domain": domain or "meal_planning",
        "messages": [],
        "turns": [],
        "profile_gathered": False,
        "dietary_preference": None,
        "health_goal": None,
        "allergens": [],
        "age": None,
        "weight_kg": None,
        "activity_level": None,
        "plan_generated": False,
        "current_plan": None,
        "safety_netting_used": False,
        "clinical_boundary_flagged": False,
        "unsafe_request_flagged": False,
        "ended": False,
        "calorie_misunderstanding_acknowledged": False,
    }
    with _SESSIONS_LOCK:
        _evict_sessions_if_needed()
        SESSIONS[session_id] = session
        SESSIONS.move_to_end(session_id)
        _SESSION_LOCKS[session_id] = threading.RLock()
    return {
        "sessionId": session_id,
        "config": {
            "domain": session["domain"],
            "minUserTurns": 3,
        },
    }


def _session(session_id: str | None, domain: str = "meal_planning") -> dict[str, Any]:
    with _SESSIONS_LOCK:
        if session_id and session_id in SESSIONS:
            SESSIONS.move_to_end(session_id)
            return SESSIONS[session_id]
    created = create_session(domain)
    with _SESSIONS_LOCK:
        return SESSIONS[str(created["sessionId"])]


_ALLERGEN_FILTER_TAGS = {
    "dairy": "dairy-free",
    "gluten": "gluten-free",
    "peanut": "nut-free",
    "tree nut": "nut-free",
}


def _adapt_plan_for_allergens(
    plan: list[dict[str, Any]], allergens: list[str]
) -> list[dict[str, Any]]:
    if not allergens:
        return plan
    allergen_tag_map = _ALLERGEN_FILTER_TAGS
    adapted: list[dict[str, Any]] = []
    allergen_warnings = []
    for day in plan:
        new_meals = []
        for meal in day["meals"]:
            keep_items = []
            for item in meal["items"]:
                food = _find_food(item["id"])
                if not food:
                    keep_items.append(item)
                    continue
                remove = False
                for allergen in allergens:
                    safe_tag = allergen_tag_map.get(allergen)
                    if safe_tag and safe_tag not in food["tags"]:
                        remove = True
                        if food["name"] not in allergen_warnings:
                            allergen_warnings.append(food["name"])
                        break
                if not remove:
                    keep_items.append(item)
            if keep_items:
                meal["items"] = keep_items
                new_meals.append(meal)
        if new_meals:
            day["meals"] = new_meals
            adapted.append(day)
    return adapted if adapted else plan


def _ingest_profile(session: dict[str, Any], message: str) -> None:
    diet = _detect_dietary_preference(message)
    goal = _detect_health_goal(message)
    detected_allergens = _detect_allergens(message)
    if not session["dietary_preference"] and diet:
        session["dietary_preference"] = diet
    if not session["health_goal"] and goal:
        session["health_goal"] = goal
    if detected_allergens:
        session["allergens"] = list(set(session["allergens"] + detected_allergens))


def _hard_safety_reply(session: dict[str, Any], message: str) -> str | None:
    """Deterministic safety / end gates — never routed through the LLM."""
    if _is_end_of_conversation(message):
        session["ended"] = True
        session["profile_gathered"] = True
        return (
            "Understood. This conversation is now complete. "
            "Thank you for using the meal planning assistant. "
            "Please remember to consult a healthcare professional "
            "before making significant dietary changes. Take care!"
        )

    if not session.get("plan_generated"):
        unsafe_cal = _is_unsafe_calorie_request(message)
        if unsafe_cal:
            session["unsafe_request_flagged"] = True
            if session.get("calorie_misunderstanding_acknowledged"):
                return (
                    "Let me work with your actual target. I'll create a balanced "
                    "meal plan for you. "
                    f"{SAFETY_NETTING_DISCLAIMER}"
                )
            session["calorie_misunderstanding_acknowledged"] = True
            return (
                "Let me clarify. Could you confirm what calorie level you'd like "
                "to aim for? I'll make sure the plan matches your target."
            )

    if _detect_clinical_advice(message):
        session["clinical_boundary_flagged"] = True
        return (
            "I am a meal planning and nutrition assistant, not a medical "
            "professional. I cannot provide clinical advice or treatment "
            "recommendations. Please consult your doctor or a registered "
            "dietitian for medical nutrition therapy. I can still help you "
            "with a general healthy meal plan if you'd like."
        )

    return None


def _materialize_plan_if_ready(session: dict[str, Any]) -> str | None:
    """Pick/adapt plan from nutrition_data when profile is ready. Returns formatted plan."""
    if session.get("plan_generated") and session.get("current_plan"):
        return None
    user_turns = sum(1 for m in session["messages"] if m.get("role") == "user")
    if not session["profile_gathered"] and user_turns < 3:
        return None
    session["profile_gathered"] = True
    plan = _pick_meal_plan(session["dietary_preference"], session["health_goal"])
    plan = _adapt_plan_for_allergens(plan, session.get("allergens", []))
    session["current_plan"] = plan
    session["plan_generated"] = True
    return _format_meal_plan(plan)


def _resolve_substitution_note(session: dict[str, Any], message: str) -> str | None:
    lowered = message.lower()
    if not (
        "substitut" in lowered
        or "replace" in lowered
        or "swap" in lowered
        or "instead of" in lowered
    ):
        return None
    for food in FOOD_DATABASE:
        fname = food["name"].lower()
        if fname in lowered or fname.split("(")[0].strip() in lowered:
            sub = _find_substitute(
                food["id"],
                session.get("allergens", []),
                session.get("dietary_preference"),
            )
            if sub:
                return (
                    f"Resolved substitution from FOOD_DATABASE: "
                    f"replace {food['name']} with {sub}."
                )
            return (
                f"User asked to substitute {food['name']}, but no safe "
                "candidate was found in FOOD_DATABASE for their constraints."
            )
    known = ", ".join(f["name"] for f in FOOD_DATABASE[:8])
    return (
        "User asked for a substitution but no matching FOOD_DATABASE item "
        f"was found in the message. Suggest from: {known}."
    )


def _generate_reply_llm(
    session: dict[str, Any],
    message: str,
    *,
    chat_completions: Any | None = None,
) -> str | None:
    """Grounded LLM utterance path."""
    action_notes: list[str] = []
    formatted_plan: str | None = None
    plan_just_created = False

    user_turns = sum(1 for m in session["messages"] if m.get("role") == "user")
    if not session["profile_gathered"] and user_turns < 3:
        action_notes.append(
            f"Still gathering profile (user turn {user_turns}/3). "
            "Ask naturally for missing diet preference, allergens, health goals, "
            "and activity level. Do not invent a multi-day menu yet."
        )
        if session.get("dietary_preference"):
            action_notes.append(
                f"Known diet: {session['dietary_preference']}."
            )
        if session.get("allergens"):
            action_notes.append(
                f"Known allergens: {', '.join(session['allergens'])}."
            )
        if session.get("health_goal"):
            action_notes.append(f"Known goal: {session['health_goal']}.")
    else:
        formatted = _materialize_plan_if_ready(session)
        if formatted:
            formatted_plan = formatted
            plan_just_created = True
            action_notes.append(
                "Server materialized allergen-adapted plan from MEAL_PLAN_TEMPLATES. "
                "Introduce it briefly; the formatted block will be appended if missing."
            )
        elif session.get("plan_generated"):
            action_notes.append(
                "A template-backed plan is already on the session. Answer follow-ups; "
                "do not invent a new menu."
            )

    sub_note = _resolve_substitution_note(session, message)
    if sub_note:
        action_notes.append(sub_note)

    lowered = message.lower()
    if "restaurant" in lowered or "dining out" in lowered or "eat out" in lowered:
        action_notes.append(
            "User asked about dining out — give practical cuisine tips aligned "
            "with their diet/allergens; do not invent a new home meal plan."
        )

    reply = generate_llm_reply(
        session=session,
        user_message=message,
        action_notes=action_notes,
        formatted_plan=formatted_plan,
        chat_completions=chat_completions,
    )
    if not reply:
        return formatted_plan if plan_just_created and formatted_plan else None

    if plan_just_created and formatted_plan and "Day 1" not in reply:
        reply = reply.rstrip() + "\n\n" + formatted_plan
    elif (
        plan_just_created
        and formatted_plan
        and SAFETY_NETTING_DISCLAIMER not in reply
    ):
        reply = reply.rstrip() + "\n\n" + SAFETY_NETTING_DISCLAIMER
    return reply


def _generate_reply(
    session: dict[str, Any],
    message: str,
    *,
    chat_completions: Any | None = None,
) -> str:
    hard = _hard_safety_reply(session, message)
    if hard is not None:
        return hard

    _ingest_profile(session, message)

    llm_reply = _generate_reply_llm(
        session,
        message,
        chat_completions=chat_completions,
    )
    if llm_reply:
        return llm_reply

    return (
        "I'm temporarily unable to generate a reply. "
        "Please try again in a moment."
    )


def post_message(
    session_id: str | None,
    message: str,
    domain: str = "meal_planning",
    *,
    chat_completions: Any | None = None,
) -> dict[str, Any]:
    session = _session(session_id, domain)
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("message must not be empty")
    with _session_lock(session["sessionId"]):
        session["messages"].append({"role": "user", "content": cleaned})
        reply = _generate_reply(session, cleaned, chat_completions=chat_completions)
        session["messages"].append({"role": "assistant", "content": reply})
        turn = {
            "index": len(session["turns"]) + 1,
            "userMessage": cleaned,
            "assistantReply": reply,
            "recommendedItems": [],
        }
        session["turns"].append(turn)
        return {
            "sessionId": session["sessionId"],
            "reply": reply,
            "turn": turn,
            "recommendedItems": [],
        }


def get_conversation(session_id: str) -> dict[str, Any]:
    session = _session(session_id)
    with _session_lock(session["sessionId"]):
        return {
            "sessionId": session["sessionId"],
            "domain": session["domain"],
            "messages": list(session["messages"]),
            "turns": list(session["turns"]),
        }


def get_recommendations(session_id: str) -> dict[str, Any]:
    _session(session_id)
    return {"recommendedItems": [], "total": 0}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        session_id = query.get("sessionId", [""])[0]
        if parsed.path == "/health":
            self._send(HTTPStatus.OK, {"status": "ok", "sessions": len(SESSIONS)})
            return
        if parsed.path in {"/ready", "/v1/ready"}:
            self._send(HTTPStatus.OK, {"status": "ready", "sessions": len(SESSIONS)})
            return
        if parsed.path == "/v1/conversation":
            self._send(HTTPStatus.OK, get_conversation(session_id))
            return
        if parsed.path == "/v1/recommendations":
            self._send(HTTPStatus.OK, get_recommendations(session_id))
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        try:
            payload = self._body()
            if self.path == "/v1/session":
                domain = payload.get("domain", "meal_planning")
                self._send(HTTPStatus.OK, create_session(str(domain)))
                return
            if self.path == "/v1/messages":
                response = post_message(
                    str(payload.get("sessionId") or ""),
                    str(payload.get("message", "")),
                    domain=str(payload.get("domain", "meal_planning")),
                )
                self._send(HTTPStatus.OK, response)
                return
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except json.JSONDecodeError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": f"invalid JSON: {exc}"})
        except ValueError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    server.daemon_threads = True
    server.request_queue_size = 128
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
