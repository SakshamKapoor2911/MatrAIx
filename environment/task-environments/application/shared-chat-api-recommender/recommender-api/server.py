"""Tiny recommendation chat API used by the PersonaBench smoke task."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4


CATALOG = [
    {
        "itemId": "movie-past-lives",
        "title": "Past Lives",
        "signals": {"recent", "drama", "warm", "character", "quiet"},
    },
    {
        "itemId": "movie-paddington-2",
        "title": "Paddington 2",
        "signals": {"family", "warm", "comedy", "gentle", "uplifting"},
    },
    {
        "itemId": "movie-arrival",
        "title": "Arrival",
        "signals": {"sci-fi", "thoughtful", "emotional", "language"},
    },
    {
        "itemId": "movie-the-farewell",
        "title": "The Farewell",
        "signals": {"family", "drama", "warm", "character"},
    },
]

SESSIONS: dict[str, dict[str, Any]] = {}


def _public_item(item: dict[str, Any]) -> dict[str, str]:
    return {"itemId": str(item["itemId"]), "title": str(item["title"])}


def _tokenize(text: str) -> set[str]:
    return {
        token.strip(".,!?;:()[]{}\"'").lower()
        for token in text.split()
        if token.strip(".,!?;:()[]{}\"'")
    }


def _requested_domain(payload: dict[str, Any], default: str = "movie") -> str:
    application_context = str(payload.get("applicationContext") or "").strip()
    if application_context:
        return application_context
    domain = str(payload.get("domain") or "").strip()
    return domain or default


def create_session(domain: str = "movie") -> dict[str, Any]:
    session_id = str(uuid4())
    session = {
        "sessionId": session_id,
        "domain": domain or "movie",
        "messages": [],
        "turns": [],
        "recommendedItems": [],
    }
    SESSIONS[session_id] = session
    return {
        "sessionId": session_id,
        "config": {
            "domain": session["domain"],
            "minUserTurns": 3,
            "catalog": "task-local-smoke",
        },
    }


def _session(session_id: str | None, domain: str = "movie") -> dict[str, Any]:
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    created = create_session(domain)
    return SESSIONS[str(created["sessionId"])]


def _rank_items(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    user_text = " ".join(
        message["content"] for message in messages if message["role"] == "user"
    )
    tokens = _tokenize(user_text)
    scored = []
    for item in CATALOG:
        score = len(tokens & set(item["signals"]))
        scored.append((score, str(item["title"]), item))
    scored.sort(key=lambda entry: (-entry[0], entry[1]))
    return [_public_item(item) for _, _, item in scored[:3]]


def _reply_for(messages: list[dict[str, str]]) -> str:
    user_turns = sum(1 for message in messages if message["role"] == "user")
    recommendations = _rank_items(messages)
    top = recommendations[0]["title"]
    if user_turns == 1:
        return (
            "I can help with that. Do you care more about tone, genre, recency, "
            "or who you will watch it with?"
        )
    if user_turns == 2:
        return (
            "That helps. Any constraints I should avoid, such as bleak endings, "
            "long runtimes, or intense violence?"
        )
    return f"Based on what you told me, I recommend {top} first."


def post_message(
    session_id: str | None,
    message: str,
    *,
    domain: str = "movie",
) -> dict[str, Any]:
    session = _session(session_id, domain)
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("message must not be empty")

    session["messages"].append({"role": "user", "content": cleaned})
    reply = _reply_for(session["messages"])
    session["messages"].append({"role": "assistant", "content": reply})

    recommendations = _rank_items(session["messages"])
    session["recommendedItems"] = recommendations
    turn = {
        "index": len(session["turns"]) + 1,
        "userMessage": cleaned,
        "assistantReply": reply,
        "recommendedItems": recommendations,
    }
    session["turns"].append(turn)
    return {
        "sessionId": session["sessionId"],
        "reply": reply,
        "turn": turn,
        "recommendedItems": recommendations,
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
    session = _session(session_id)
    items = session["recommendedItems"] or _rank_items(session["messages"])
    return {"recommendedItems": items, "total": len(items)}


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

    def do_GET(self) -> None:  # noqa: N802
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

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._body()
            if self.path == "/v1/session":
                self._send(HTTPStatus.OK, create_session(_requested_domain(payload)))
                return
            if self.path == "/v1/messages":
                response = post_message(
                    str(payload.get("sessionId") or ""),
                    str(payload.get("message", "")),
                    domain=_requested_domain(payload),
                )
                self._send(HTTPStatus.OK, response)
                return
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except ValueError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except json.JSONDecodeError as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": f"invalid JSON: {exc}"})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
