#!/bin/bash
set -euo pipefail

curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

uv run --with mcp python3 <<'EOF'
import asyncio
import json
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = "http://support-bot:8000/mcp"
OUTPUT = Path("/app/output/transcript.json")


async def main() -> None:
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            await session.call_tool(
                "send_message",
                {
                    "message": (
                        "Hi, my order #4521 was supposed to arrive Tuesday "
                        "but still hasn't shown up. Can you help?"
                    )
                },
            )
            await session.call_tool(
                "send_message",
                {
                    "message": (
                        "Thanks. The shipping address should still be correct. "
                        "What does tracking show right now?"
                    )
                },
            )
            history = await session.call_tool("get_conversation_history", {})
            transcript = history.content[0].text

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(transcript)
    json.loads(transcript)


asyncio.run(main())
EOF
