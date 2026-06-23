"""Run ONE real RecAI turn against the in-repo engine. Exploratory smoke, not a unit test.

    DOMAIN=game INTERECAGENT_RANKER_MODE=native python scripts/smoke_real_turn.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

domain = os.environ.get("DOMAIN", "game")
os.environ["DOMAIN"] = domain
os.environ.setdefault("INTERECAGENT_DOMAIN", domain)
os.environ.setdefault("INTERECAGENT_RESOURCE_MODE", "recai_resources")
os.environ.setdefault("INTERECAGENT_RANKER_MODE", "native")
os.environ.setdefault("INTERECAGENT_ENGINE", "gpt-4o-mini")

from recbot.types import RecBotRequest
from recbot import interecagent_bridge

PROMPTS = {
    "game": "I want a fun co-op game to play with friends on PC, not too grindy.",
    "movie": "Recommend a slow-burn atmospheric horror movie without cheap jump scares.",
    "beauty_product": "I need a gentle fragrance-free moisturizer for sensitive skin on a budget.",
}

req = RecBotRequest(
    conversation_id="smoke",
    turn_id=0,
    messages=[{"role": "user", "content": PROMPTS.get(domain, PROMPTS["game"])}],
    metadata={"domain": domain},
)
result = interecagent_bridge.run_turn(req)
print("=== DOMAIN:", domain, "RANKER:", os.environ["INTERECAGENT_RANKER_MODE"])
print("ASSISTANT:", result.assistant_message)
print("RECOMMENDED IDS:", result.trace.recommended_item_ids)
assert result.assistant_message and result.assistant_message.strip(), "empty assistant message"
print("SMOKE OK")
