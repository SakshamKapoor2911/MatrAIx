#!/usr/bin/env python
"""External bridge responder for FileBridgeBrain (no API key required).

Polls ``ARENA_BRIDGE_DIR`` for ``request_<n>.json`` files and writes matching
``response_<n>.json`` decisions using ``MockArenaBrain``. Run this in a
separate terminal (or let ``run_arena_live.py --brain bridge`` spawn it) while
``run_arena.py`` / ``run_arena_live.py`` uses ``--brain bridge``.

Example:
    set ARENA_BRIDGE_DIR=C:\\tmp\\arena_bridge
    python bridge_responder.py --seed 42

    python run_arena.py --brain bridge ...   # in another terminal
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from typing import Set

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import brains  # noqa: E402


def _list_pending_requests(bridge_dir: str) -> list[int]:
    seqs: list[int] = []
    for path in glob.glob(os.path.join(bridge_dir, "request_*.json")):
        base = os.path.basename(path)
        try:
            seqs.append(int(base.replace("request_", "").replace(".json", "")))
        except ValueError:
            continue
    return sorted(seqs)


def _respond_once(bridge_dir: str, seq: int, brain: brains.MockArenaBrain) -> bool:
    request_path = os.path.join(bridge_dir, f"request_{seq}.json")
    response_path = os.path.join(bridge_dir, f"response_{seq}.json")
    if not os.path.isfile(request_path) or os.path.exists(response_path):
        return False

    with open(request_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    observation = payload.get("observation", {})
    decision = brain.decide(observation)

    tmp_path = response_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(decision, fh, indent=2)
    os.replace(tmp_path, response_path)

    persona_id = observation.get("self", {}).get("id", "?")
    action = decision.get("action", "?")
    print(f"[responder] response_{seq}.json -> persona {persona_id} action={action}", flush=True)
    return True


def run_loop(bridge_dir: str, seed: int, poll_interval_sec: float) -> None:
    os.makedirs(bridge_dir, exist_ok=True)
    brain = brains.MockArenaBrain(seed=seed)
    handled: Set[int] = set()
    print(f"[responder] watching {bridge_dir} (seed={seed})", flush=True)

    while True:
        for seq in _list_pending_requests(bridge_dir):
            if seq in handled:
                continue
            if _respond_once(bridge_dir, seq, brain):
                handled.add(seq)
        time.sleep(poll_interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(description="MockArenaBrain responder for FileBridgeBrain.")
    parser.add_argument(
        "--bridge-dir",
        default=os.environ.get("ARENA_BRIDGE_DIR"),
        help="Bridge directory (default: ARENA_BRIDGE_DIR env var)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--poll-interval", type=float, default=0.05)
    args = parser.parse_args()

    if not args.bridge_dir:
        print(
            "ERROR: set ARENA_BRIDGE_DIR or pass --bridge-dir",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        run_loop(args.bridge_dir, seed=args.seed, poll_interval_sec=args.poll_interval)
    except KeyboardInterrupt:
        print("\n[responder] stopped", flush=True)


if __name__ == "__main__":
    main()