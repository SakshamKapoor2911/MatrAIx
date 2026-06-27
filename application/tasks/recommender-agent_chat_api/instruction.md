# Recommender Agent Chat Task

You are a simulated user of a recommendation system. Act according to your
assigned persona.

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

## Required Work

1. Have at least three user turns and three assistant turns.
2. Try to get recommendations that fit your product need, constraints, and
   personal preferences.
3. Save the exact conversation artifact to `/app/output/transcript.json`.
4. Save the recommendation artifact to `/app/output/recommendation_result.json`.
5. If possible, save your post-interaction questionnaire to
   `/app/output/user_feedback.json`.

## Output Schemas

`/app/output/transcript.json`:

```json
{
  "sessionId": "<string>",
  "domain": "movie",
  "messages": [
    {"role": "user", "content": "<string>"},
    {"role": "assistant", "content": "<string>"}
  ],
  "turns": []
}
```

`/app/output/recommendation_result.json`:

```json
{
  "sessionId": "<string>",
  "domain": "movie",
  "recommendedItems": [
    {"itemId": "<string>", "title": "<string>"}
  ],
  "turnsToRecommendation": 3
}
```

`/app/output/user_feedback.json`:

```json
{
  "productNeedConstraintSatisfaction": "yes|partially|no",
  "personalPreferenceSatisfaction": "yes|partially|no",
  "overallExperienceRating": 1,
  "reason": "<string>",
  "askedUsefulClarificationQuestions": true
}
```

Make sure the JSON files are valid JSON. Do not invent item ids; use item ids
returned by `/v1/recommendations` or `/v1/messages`.
