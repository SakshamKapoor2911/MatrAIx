"""Acme customer support MCP server with in-memory conversation state."""

from __future__ import annotations

import json
import re

from fastmcp import FastMCP

mcp = FastMCP("acme-support")

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


@mcp.tool()
def send_message(message: str) -> str:
    """Send a message to Acme customer support as the customer. Returns the support agent reply."""
    customer_message = message.strip()
    if not customer_message:
        raise ValueError("message must not be empty")

    _messages.append({"role": "customer", "content": customer_message})
    reply = _bot_reply(customer_message)
    _messages.append({"role": "support", "content": reply})
    return reply


@mcp.tool()
def get_conversation_history() -> str:
    """Return the full conversation transcript as JSON."""
    return json.dumps({"messages": _messages}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
