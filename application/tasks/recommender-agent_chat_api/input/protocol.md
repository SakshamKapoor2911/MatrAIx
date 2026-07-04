# Chat API protocol

The recommender application is available through a REST API sidecar named
`rec-agent-api`, reachable from this container at `http://rec-agent-api:8000`.
Use `curl` or a short script to have a real multi-turn conversation with the
recommender.

For this smoke task, use the `movie` domain unless the run configuration tells
you otherwise. Based on your persona, decide what kind of item you realistically
want, what constraints matter to you, and what personal preferences should guide
recommendations. Do not reveal everything at once. Interact naturally, answer
follow-up questions, provide feedback on recommendations, and continue until you
can judge whether the recommendations satisfy your need.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/health` | - | `{"status": "ok", ...}` |
| `POST` | `/v1/session` | `{"domain": "movie"}` | `{"sessionId": "...", "config": {...}, ...}` |
| `POST` | `/v1/messages` | `{"sessionId": "...", "message": "<your message>"}` | `{"reply": "...", "turn": {...}, "recommendedItems": [...]}` |
| `GET` | `/v1/conversation?sessionId=...` | - | `{"messages": [...], "turns": [...]}` |
| `GET` | `/v1/recommendations?sessionId=...` | - | `{"recommendedItems": [...], "total": 0}` |

You may omit `sessionId` on the first `/v1/messages` call and include
`{"domain": "movie"}`; the API will create a session automatically.

## Required work

1. Have at least three user turns and three assistant turns.
2. Try to get recommendations that fit your product need, constraints, and
   personal preferences.
3. Continue until you can judge whether the recommendations satisfy your need.

Do not invent item ids; use item ids returned by `/v1/recommendations` or
`/v1/messages`.
