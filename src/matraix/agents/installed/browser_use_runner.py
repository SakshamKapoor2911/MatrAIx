#!/usr/bin/env python3
"""Run browser-use inside a Harbor task container."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path


def _create_llm(model: str):
    provider, _, bare = model.partition("/")
    bare = bare or model

    if provider in ("anthropic", "") and (
        bare.startswith("claude") or provider == "anthropic"
    ):
        from browser_use import ChatAnthropic

        return ChatAnthropic(model=bare)

    from browser_use import ChatOpenAI

    return ChatOpenAI(model=bare)


async def _run(args: argparse.Namespace) -> int:
    from browser_use import Agent, Browser

    extend = os.environ.get("PERSONA_SYSTEM", "").strip() or None
    max_steps = int(os.environ.get("MAX_STEPS", "50"))

    llm = _create_llm(args.model)
    browser = Browser(headless=True)

    agent_kwargs: dict = {
        "task": args.instruction,
        "llm": llm,
        "browser": browser,
    }
    if extend:
        agent_kwargs["extend_system_message"] = extend

    agent = Agent(**agent_kwargs)
    history = await agent.run(max_steps=max_steps)

    trajectory = {
        "final_result": history.final_result() if history else None,
        "is_done": history.is_done() if history else False,
        "is_successful": history.is_successful() if history else False,
        "urls": history.urls() if history else [],
        "action_names": history.action_names() if history else [],
    }

    trajectory_path = Path(args.trajectory_path)
    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    trajectory_path.write_text(json.dumps(trajectory, indent=2) + "\n", encoding="utf-8")

    if history and not history.is_successful():
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--trajectory-path", required=True)
    args = parser.parse_args()

    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
