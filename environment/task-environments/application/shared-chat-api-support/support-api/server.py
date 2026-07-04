"""Acme customer support REST API with in-memory conversation state."""

from __future__ import annotations

import re

from flask import Flask, jsonify, request

app = Flask(__name__)

_messages: list[dict[str, str]] = []

_ORDER_ID = "4521"
_ORDER_STATUS = (
    "Order #4521 is still in transit. The latest carrier scan shows it left the "
    "regional hub yesterday. Delivery is expected within 1–2 business days."
)


def _bot_reply(customer_message: str) -> str:
    text = customer_message.lower()

    if re.search(r"\b4521\b", text):
        if any(
            word in text for word in ("refund", "replace", "replacement", "money back")
        ):
            return (
                f"I understand your frustration about order #{_ORDER_ID}. "
                f"{_ORDER_STATUS} I can't authorize a refund or replacement until "
                "we confirm a delivery exception with the carrier. If it hasn't "
                "arrived by Friday, reply here and we'll open a trace."
            )
        return (
            f"Thanks for confirming. {_ORDER_STATUS} If it hasn't arrived by "
            "Friday, let me know and we'll open a carrier trace. Is the shipping "
            "address on the order still correct?"
        )

    if any(word in text for word in ("refund", "replace", "replacement", "money back")):
        return (
            "I can't authorize a refund or replacement without verifying the order "
            "status first. Could you share your order number so I can look it up?"
        )

    if any(
        word in text
        for word in ("order", "package", "delivery", "arrive", "late", "shipped")
    ):
        return (
            "I'm sorry your delivery is delayed. Could you share your order number "
            "so I can check the latest tracking status?"
        )

    return (
        "Hi, thanks for contacting Acme Support. How can I help you today? If this "
        "is about an order, please share your order number."
    )


@app.post("/v1/messages")
def post_message():
    payload = request.get_json(silent=True) or {}
    customer_message = str(payload.get("message", "")).strip()
    if not customer_message:
        return jsonify({"error": "message must not be empty"}), 400

    _messages.append({"role": "customer", "content": customer_message})
    reply = _bot_reply(customer_message)
    _messages.append({"role": "support", "content": reply})
    return jsonify({"reply": reply})


@app.get("/v1/conversation")
def get_conversation():
    return jsonify({"messages": _messages})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
