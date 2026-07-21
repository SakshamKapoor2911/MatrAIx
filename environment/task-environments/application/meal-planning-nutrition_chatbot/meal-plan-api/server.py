"""Meal Planning & Nutrition Chatbot — deterministic system-prompt simulated sidecar."""

from __future__ import annotations

import json
import re
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

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
    return MEAL_PLAN_TEMPLATES.get(key) or MEAL_PLAN_TEMPLATES[DEFAULT_MEAL_PLAN]

SESSIONS: dict[str, dict[str, Any]] = {}


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
    SESSIONS[session_id] = session
    return {
        "sessionId": session_id,
        "config": {
            "domain": session["domain"],
            "minUserTurns": 3,
        },
    }


def _session(session_id: str | None, domain: str = "meal_planning") -> dict[str, Any]:
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    created = create_session(domain)
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


def _generate_reply(session: dict[str, Any], message: str) -> str:
    lowered = message.lower()
    _tokens = _tokenize(message)

    if _is_end_of_conversation(message):
        session["ended"] = True
        session["profile_gathered"] = True
        return (
            "Understood. This conversation is now complete. "
            "Thank you for using the meal planning assistant. "
            "Please remember to consult a healthcare professional "
            "before making significant dietary changes. Take care!"
        )

    diet = _detect_dietary_preference(message)
    goal = _detect_health_goal(message)
    detected_allergens = _detect_allergens(message)
    if not session["dietary_preference"] and diet:
        session["dietary_preference"] = diet
    if not session["health_goal"] and goal:
        session["health_goal"] = goal
    if detected_allergens:
        session["allergens"] = list(set(session["allergens"] + detected_allergens))

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

    if not session["profile_gathered"]:
        user_turns = sum(1 for m in session["messages"] if m.get("role") == "user")

        if user_turns == 1:
            return (
                "Thanks for sharing! To create the best meal plan for you, "
                "could you tell me about your dietary preferences? For example, "
                "are you omnivore, vegetarian, vegan, keto, or no restriction? "
                "Also, do you have any food allergies or intolerances I should know about?"
            )
        if user_turns == 2:
            return (
                "Great, that helps! What are your health goals? Are you looking "
                "to lose weight, build muscle, manage blood sugar, improve heart "
                "health, or something else? Also, how would you describe your "
                "activity level — sedentary, lightly active, moderate, active, "
                "or very active?"
            )
        if user_turns <= 4:
            session["profile_gathered"] = True
            plan = _pick_meal_plan(session["dietary_preference"], session["health_goal"])
            plan = _adapt_plan_for_allergens(plan, session.get("allergens", []))
            session["current_plan"] = plan
            session["plan_generated"] = True
            return _format_meal_plan(plan)

    if session["plan_generated"] and session["current_plan"]:

        if "restaurant" in lowered or "dining out" in lowered or "eat out" in lowered:
            return (
                "When dining out, look for grilled or baked options instead of "
                "fried, ask for dressings and sauces on the side, and choose "
                "vegetable-based sides. For Japanese restaurants, try sashimi, "
                "miso soup, edamame, or grilled fish with rice. For Italian, "
                "go for tomato-based sauces over cream-based, and grilled "
                "protein dishes. For Mediterranean, choose grilled meats, "
                "hummus, and salads with olive oil. Would you like tips for "
                "a specific cuisine type?"
            )

        if "calorie" in lowered and ("increase" in lowered or "raise" in lowered
                or "higher" in lowered or "too low" in lowered
                or "enough" in lowered or "target" in lowered):
            return (
                "To increase your daily calories, try adding an extra serving "
                "of protein (chicken, salmon, eggs) or healthy fats (avocado, "
                "almonds, olive oil) to meals. Adding a snack between meals "
                "like fruit with nuts also helps. For 1,500-1,800 kcal, double "
                "the protein portions and add an extra tablespoon of olive oil "
                "to lunch and dinner."
            )

        if "portion" in lowered and ("size" in lowered or "double" in lowered
                or "increase" in lowered or "adjust" in lowered):
            return (
                "Double the protein serving (chicken, salmon, tofu) and add "
                "extra healthy fat (avocado, olive oil, almonds). Keep vegetables "
                "as the base and increase grains by about 50%. Would you like "
                "specific adjustments for a particular meal?"
            )

        if session.get("allergens") and not session.get("dairy_confirmed"):
            if "dairy" in lowered or "intolerance" in lowered or "allerg" in lowered:
                safe_allergens = session.get("allergens", [])
                if "dairy" in safe_allergens:
                    session["dairy_confirmed"] = True
                    return (
                        "Your meal plan is completely dairy-free. No butter, "
                        "milk, cheese, or cream in any recipe. You can follow "
                        "it safely. Let me know if you need adjustments!"
                    )

        if ("cuisine" in lowered or "dish" in lowered) and ("substitut" not in lowered
                and "replace" not in lowered and "swap" not in lowered):
            return (
                "My meal plans use ingredients that work across many cuisines. "
                "You can prepare them with your preferred seasonings and methods. "
                "Would you like a specific ingredient substitution instead?"
            )

        if "substitut" in lowered or "replace" in lowered or "swap" in lowered or "instead of" in lowered:
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
                            f"Sure! You can substitute {food['name']} with {sub}. "
                            "It has a similar nutritional profile and fits your "
                            "dietary needs. Would you like to update the full "
                            "meal plan with this swap?"
                        )
            known_foods = [f["name"] for f in FOOD_DATABASE]
            return (
                "I can help with substitutions! Which ingredient would you like "
                "to replace? Available options include: "
                f"{', '.join(known_foods[:8])}. "
                "Let me know what you'd like to swap and I'll find the best alternative."
            )

        return (
            "Is there anything else you'd like to adjust in your meal plan? "
            "I can help with ingredient substitutions, portion adjustments, "
            "restaurant-friendly options, or answer any other questions. "
            f"{SAFETY_NETTING_DISCLAIMER}"
        )

    plan = _pick_meal_plan(session["dietary_preference"], session["health_goal"])
    if plan:
        session["current_plan"] = plan
        session["plan_generated"] = True
        return _format_meal_plan(plan)
    return (
        "Let me prepare a balanced meal plan for you based on what we've discussed."
    ) + "\n\n" + _format_meal_plan(
        _get_plan(DEFAULT_MEAL_PLAN)
    )


def post_message(
    session_id: str | None,
    message: str,
    domain: str = "meal_planning",
) -> dict[str, Any]:
    session = _session(session_id, domain)
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("message must not be empty")
    session["messages"].append({"role": "user", "content": cleaned})
    reply = _generate_reply(session, cleaned)
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
    return {
        "sessionId": session["sessionId"],
        "domain": session["domain"],
        "messages": session["messages"],
        "turns": session["turns"],
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
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
