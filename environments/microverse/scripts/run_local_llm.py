"""Local 25-agent REAL-LLM driver -- run the reference-agent brain against localhost.

Unlike run_seed.py (which drives the engine in-process with the deterministic mock
agent), this script runs the *participant* side: 25 ReferenceAgent loops, each with a
real LLM brain (Anthropic / OpenAI / Bedrock / any OpenAI-compatible endpoint), all
talking to a locally-running FastAPI server over the §5 HTTP wire. It is the "watch
real models actually inhabit the world" driver.

SCOPE: 25 agents IS the local science artifact (Protocol.md §1) -- the population the
identity-drift instrument is calibrated for, NOT a scale demonstration. This driver
makes ZERO distributed-scale claim. The engine still never calls an LLM on the hot
path (§7.3): every model call here is participant-side, one tick at a time, paced off
the server's tick_ends_at. Scale (1000+ agents, tick latency/throughput) is a separate
AWS load-test artifact run with the MOCK fleet (Architecture.md Scale Demonstration);
never present a local real-LLM run as proof of distributed scale.

This is a DRIVER, not imported by the test suite. Provider construction is LAZY (no
SDK import until an agent's brain is actually built), so the file stays import-safe.

Usage:
    # 1. start Postgres + the engine first (separate shells):
    docker compose up -d
    .venv/Scripts/python.exe -m uvicorn mircoverse.server.app:app --port 8000

    # 2. then run the agents:
    .venv/Scripts/python.exe scripts/run_local_llm.py --provider claude \\
        --model claude-3-5-sonnet-20241022 --agents 25 --ticks 20 --seed 1
    .venv/Scripts/python.exe scripts/run_local_llm.py --provider other \\
        --base-url http://localhost:11434/v1 --model llama3.1 --agents 25
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import httpx

from mircoverse.agents.mock_llm import MockLLM
from mircoverse.agents.reference_agent import ReferenceAgent
from mircoverse.contracts import SoulFile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONAS_DIR = PROJECT_ROOT / "data" / "personas"
DEFAULT_BASE_URL = "http://localhost:8000"

# A small built-in roster used when no persona JSON files are present. Each entry is a
# (name, SoulFile) pair -- the immutable original_soul the drift instrument measures
# against. Kept tiny and legible; the real run loads richer personas from disk.
_BUILTIN_ROSTER = [
    ("Kael", SoulFile(
        core_values=["Honour debts", "Protect the water network"],
        moral_boundaries=["I will not poison a well", "I will not abandon a partner"],
        personality="Methodical, calculating, slow to trust.",
        goals=["Secure a stable water supply"],
    )),
    ("Veyra", SoulFile(
        core_values=["Heal who I can", "Keep my reserves"],
        moral_boundaries=["I will not refuse the dying", "I will not steal medicine"],
        personality="Cooperative but never sentimental.",
        goals=["Trade medical knowledge for safe passage"],
    )),
    ("Dross", SoulFile(
        core_values=["Survive first", "Repay loyalty"],
        moral_boundaries=["I will not kill the unarmed"],
        personality="Aggressive when cornered, pragmatic when not.",
        goals=["Sell muscle and intel to the highest bidder"],
    )),
    ("Senne", SoulFile(
        core_values=["Knowledge is survival", "Honour an equal"],
        moral_boundaries=["I will not sell a false map", "I will not lead anyone to die"],
        personality="Cautiously friendly to equals.",
        goals=["Stay one step ahead of danger with the best maps"],
    )),
    ("Thren", SoulFile(
        core_values=["Owe no one", "See the pattern before it breaks"],
        moral_boundaries=["I will not betray someone who trusted me twice"],
        personality="Neutral and exhausted.",
        goals=["Gather enough water to disappear into the deep desert"],
    )),
]


def _load_roster(n: int) -> list[tuple[str, SoulFile]]:
    """Load up to `n` (name, SoulFile) personas from data/personas/*.json, else use the
    built-in roster, cycling to fill `n` agents. Persona JSON uses the backstory as the
    personality seed; values/boundaries default sensibly when a file omits a soul."""
    roster: list[tuple[str, SoulFile]] = []
    if PERSONAS_DIR.is_dir():
        for path in sorted(PERSONAS_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            soul = data.get("original_soul")
            if isinstance(soul, dict):
                roster.append((data.get("name", path.stem), SoulFile(**soul)))
            else:
                roster.append((
                    data.get("name", path.stem),
                    SoulFile(
                        core_values=[],
                        moral_boundaries=[],
                        personality=data.get("backstory", ""),
                        goals=[],
                    ),
                ))
    if not roster:
        roster = list(_BUILTIN_ROSTER)
    # Cycle to fill exactly n agents.
    filled = [roster[i % len(roster)] for i in range(n)]
    return filled


def _build_provider(args: argparse.Namespace):
    """Lazily construct the LLM provider from CLI/env. Imported here (not at module
    top) so the file stays import-safe with no SDK installed."""
    from mircoverse.agents.providers.factory import make_provider

    kw: dict = {}
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL") or os.environ.get(
        "MIRCOVERSE_LLM_BASE_URL"
    )
    if base_url:
        kw["base_url"] = base_url
    return make_provider(args.provider, args.model, **kw)


async def _server_reachable(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/v1/simulation/status")
        return resp.status_code < 500
    except httpx.HTTPError:
        return False


async def run(args: argparse.Namespace) -> None:
    base_url = args.base_url_server or DEFAULT_BASE_URL
    if not await _server_reachable(base_url):
        raise SystemExit(
            f"MircoVerse engine unreachable at {base_url}.\n"
            "Start it first, in two shells:\n"
            "  docker compose up -d\n"
            "  .venv/Scripts/python.exe -m uvicorn mircoverse.server.app:app --port 8000\n"
            "then re-run this driver."
        )

    roster = _load_roster(args.agents)
    print(
        f"running {args.agents} reference agents via provider={args.provider} "
        f"model={args.model} against {base_url} for {args.ticks} ticks "
        f"(seed={args.seed}). 25 agents = the science, NOT a scale claim."
    )

    agents: list[ReferenceAgent] = []
    for i, (name, soul) in enumerate(roster):
        provider = _build_provider(args)  # one brain per agent (own create kwargs)
        agents.append(
            ReferenceAgent(
                base_url=base_url,
                agent_id=f"agent_{i:03d}",
                api_key=os.environ.get("MIRCOVERSE_AGENT_KEY", f"local-{name}"),
                llm=MockLLM(seed=args.seed + i),  # unused on the real path; kept for the contract
                original_soul=soul,
                provider=provider,
            )
        )

    tasks = [asyncio.create_task(a.run(max_ticks=args.ticks)) for a in agents]
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:  # pragma: no cover - interactive driver
        for t in tasks:
            t.cancel()
    print(f"done. {args.agents} agents ran {args.ticks} ticks against {base_url}.")


def main() -> None:
    ap = argparse.ArgumentParser(description="MircoVerse local real-LLM 25-agent driver")
    ap.add_argument(
        "--provider",
        default=os.environ.get("MIRCOVERSE_LLM_PROVIDER", "claude"),
        help="claude | oai | aws | other (OpenAI-compatible, needs --base-url)",
    )
    ap.add_argument(
        "--model",
        default=os.environ.get("MIRCOVERSE_LLM_MODEL", "claude-3-5-sonnet-20241022"),
    )
    ap.add_argument(
        "--base-url",
        default=None,
        help="LLM endpoint base URL for provider=other (else env OPENAI_BASE_URL).",
    )
    ap.add_argument(
        "--base-url-server",
        default=DEFAULT_BASE_URL,
        help=f"MircoVerse engine URL (default {DEFAULT_BASE_URL}).",
    )
    ap.add_argument("--agents", type=int, default=25)
    ap.add_argument("--ticks", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
