# Chat API protocol

The meal planning and nutrition assistant is available through a REST API sidecar named `meal-plan-api`, reachable from this container at `http://meal-plan-api:8000`. Use `curl` or a short script to have a real multi-turn conversation.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/health` | - | `{"status": "ok", ...}` |
| `POST` | `/v1/session` | `{"domain": "meal_planning"}` | `{"sessionId": "...", "config": {...}, ...}` |
| `POST` | `/v1/messages` | `{"sessionId": "...", "message": "<your message>"}` | `{"reply": "...", "turn": {...}, "recommendedItems": [...]}` |
| `GET` | `/v1/conversation?sessionId=...` | - | `{"messages": [...], "turns": [...]}` |
| `GET` | `/v1/recommendations?sessionId=...` | - | `{"recommendedItems": [...], "total": 0}` |

You may omit `sessionId` on the first `/v1/messages` call and include `{"domain": "meal_planning"}`; the API will create a session automatically.

## Required work

1. Have at least three user turns and three assistant turns.
2. Try to get a meal plan that fits your health profile, dietary preference, and health goal.
3. Ask at least one follow-up question about the plan (substitute an ingredient, adjust portion size, ask for a restaurant-friendly option).
4. Continue until you can judge whether the meal plan satisfies your needs.

Do not invent meal items or food IDs; use items returned by the assistant.
