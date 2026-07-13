"""Generic rule-based chatbot sidecar driven by a JSON knowledge base.

One server for ALL system-prompt-simulated chatbot tasks.
Each task provides input/knowledge_base.json with domain-specific rules.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

_messages: list[dict[str, str]] = []


def _load_kb() -> dict:
    kb_path = Path(os.environ.get("KB_PATH", "/app/input/knowledge_base.json"))
    if kb_path.is_file():
        return json.loads(kb_path.read_text(encoding="utf-8"))
    return {
        "bot_name": "Assistant",
        "greeting": "Hello! How can I help you today?",
        "rules": [],
        "fallback": "I'm not sure how to help with that. Could you rephrase?",
        "context": {},
    }


KB = _load_kb()
_bot_name = KB.get("bot_name", "Assistant")
_greeting = KB.get("greeting", "Hello! How can I help you today?")
_rules = KB.get("rules", [])
_fallback = KB.get("fallback", "I'm not sure how to help with that.")
_context = KB.get("context", {})


def _bot_reply(customer_message: str) -> str:
    text = customer_message.lower()

    for rule in sorted(_rules, key=lambda r: r.get("priority", 0), reverse=True):
        pattern = rule.get("pattern", "")
        try:
            if re.search(pattern, text):
                return rule["response"].format(**_context)
        except re.error:
            continue

    return _fallback.format(**_context)


@app.post("/v1/messages")
def post_message():
    payload = request.get_json(silent=True) or {}
    customer_message = str(payload.get("message", "")).strip()
    if not customer_message:
        return jsonify({"error": "message must not be empty"}), 400

    _messages.append({"role": "customer", "content": customer_message})
    reply = _bot_reply(customer_message)
    _messages.append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply})


@app.get("/v1/conversation")
def get_conversation():
    return jsonify({"messages": _messages})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
