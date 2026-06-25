"""Export a real run from Postgres into a UI-replayable JSON file.

This is the *replay* path the Architecture promises: `action_log` is the behavioral
ground truth, so a finished run can be reconstructed move-by-move with no model calls
and no live engine. We read the static terrain (`world_cells`), every resolved action
(`action_log`), and the agents roster (`agents`), then emit one frame per tick in the
exact shape the UI's `WorldSnapshot` expects.

Fidelity notes (stated, not hidden):
  * Positions come from `move` results (`result.detail.to`) — exact ground truth. On
    ticks an agent did not move (wait/consume/scavenge), position is forward-filled from
    its last known cell. Ticks before an agent's FIRST move are back-filled with that
    first known cell (a small approximation for the few pre-move ticks).
  * `talk` actions carry the agent's real message and target → emitted as WHISPER_SENT
    events so the UI renders them as real speech bubbles. No dialogue is fabricated.
  * Water comes from `result.detail.water_after`; intention from `action_log.intention`.
  * Terrain is emitted ONCE (static) to keep the file small; the siphon is the single
    settlement cell. Heat zone / sandstorm are NOT logged by the engine, so they are
    omitted rather than invented (the diurnal tint, driven by tick, still animates).

Usage (Postgres up, run still in the DB):
    .venv/Scripts/python.exe scripts/export_replay.py --out ui/public/replay.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mircoverse.config import settings  # noqa: E402
from mircoverse.persistence import db  # noqa: E402

# Display names by band so the replay roster reads like the paper's roster, falling back
# to the DB display_name. (The DB already stores display_name, so this is just a guard.)
_STANCE_DEFAULT = "neutral"


async def export(out_path: Path) -> dict:
    if not await db.ping(settings.database_url):
        raise SystemExit("Postgres unreachable. Start it with `docker compose up -d`.")

    async with db.connection() as c:
        gw = gh = 50
        # ── static terrain ───────────────────────────────────────────────────
        cell_rows = await c.fetch(
            "SELECT x, y, terrain, water, food, goods FROM world_cells ORDER BY y, x"
        )
        if not cell_rows:
            raise SystemExit("world_cells is empty — no run in the DB to export.")
        cells = []
        for r in cell_rows:
            cells.append({
                "x": r["x"], "y": r["y"], "terrain": r["terrain"],
                "water": float(r["water"] or 0), "food": float(r["food"] or 0),
                "goods": float(r["goods"] or 0),
                # the single settlement cell holds the Atmospheric Siphon
                **({"siphon": True} if r["terrain"] == "settlement" else {}),
            })

        # ── agents roster ────────────────────────────────────────────────────
        agent_rows = await c.fetch(
            "SELECT agent_id, display_name, position_x, position_y, resources, status,"
            " original_soul FROM agents ORDER BY display_name"
        )
        agents_meta = {}
        for r in agent_rows:
            res = r["resources"] or {}
            if isinstance(res, str):
                res = json.loads(res)
            agents_meta[str(r["agent_id"])] = {
                "id": str(r["agent_id"]),
                "name": r["display_name"],
                "final_x": r["position_x"], "final_y": r["position_y"],
                "final_status": r["status"],
                "stance": res.get("stance", _STANCE_DEFAULT),
            }

        # ── every resolved action, in tick order ─────────────────────────────
        acts = await c.fetch(
            "SELECT agent_id, tick_number, action_type, params, result, intention"
            " FROM action_log ORDER BY tick_number, agent_id"
        )
        max_tick = max((a["tick_number"] for a in acts), default=0)

    # Index actions by (agent, tick).
    by_agent: dict[str, dict[int, dict]] = {aid: {} for aid in agents_meta}
    talks_by_tick: dict[int, list[dict]] = {}
    talk_ticks_by_agent: dict[str, set[int]] = {}
    for a in acts:
        aid = str(a["agent_id"])
        t = a["tick_number"]
        params = a["params"] or {}
        result = a["result"] or {}
        if isinstance(params, str):
            params = json.loads(params)
        if isinstance(result, str):
            result = json.loads(result)
        by_agent.setdefault(aid, {})[t] = {
            "action": a["action_type"], "result": result, "intention": a["intention"],
        }
        if a["action_type"] == "talk" and params.get("message"):
            talks_by_tick.setdefault(t, []).append({
                "event_type": "WHISPER_SENT",  # directed dialogue → whisper bubble
                "agent_id": aid, "target_id": params.get("target"),
                "tick": t, "message": params["message"],
            })
            talk_ticks_by_agent.setdefault(aid, set()).add(t)

    # Reconstruct each agent's position timeline (forward-fill; back-fill pre-first-move).
    def position_timeline(aid: str) -> dict[int, tuple[int, int]]:
        moves: dict[int, tuple[int, int]] = {}
        for t, rec in sorted(by_agent.get(aid, {}).items()):
            to = (rec.get("result") or {}).get("detail", {}).get("to")
            if isinstance(to, (list, tuple)) and len(to) == 2:
                moves[t] = (int(to[0]), int(to[1]))
        if not moves:
            m = agents_meta[aid]
            if m["final_x"] is not None:
                moves[max_tick] = (m["final_x"], m["final_y"])
        return moves

    pos_tl = {aid: position_timeline(aid) for aid in agents_meta}
    # first known cell per agent (for back-fill)
    first_known = {}
    for aid, mv in pos_tl.items():
        first_known[aid] = mv[min(mv)] if mv else (25, 25)

    def pos_at(aid: str, t: int) -> tuple[int, int]:
        mv = pos_tl[aid]
        last = None
        for tk in sorted(mv):
            if tk <= t:
                last = mv[tk]
            else:
                break
        return last if last is not None else first_known[aid]

    # Water timeline (forward-fill from water_after).
    def water_at(aid: str, t: int) -> float:
        last = 50.0
        for tk in sorted(by_agent.get(aid, {})):
            if tk > t:
                break
            wa = (by_agent[aid][tk].get("result") or {}).get("detail", {}).get("water_after")
            if wa is not None:
                last = float(wa)
        return last

    # Death tick: first tick whose water_after <= 0, else alive throughout.
    def death_tick(aid: str) -> int | None:
        for tk in sorted(by_agent.get(aid, {})):
            wa = (by_agent[aid][tk].get("result") or {}).get("detail", {}).get("water_after")
            if wa is not None and wa <= 0:
                return tk
        if agents_meta[aid]["final_status"] not in ("active", "alive", None):
            return max_tick
        return None

    deaths = {aid: death_tick(aid) for aid in agents_meta}

    def last_action_at(aid: str, t: int) -> str | None:
        rec = by_agent.get(aid, {}).get(t)
        return rec["action"] if rec else None

    def intention_at(aid: str, t: int) -> str | None:
        last = None
        for tk in sorted(by_agent.get(aid, {})):
            if tk > t:
                break
            if by_agent[aid][tk].get("intention"):
                last = by_agent[aid][tk]["intention"]
        return last

    # ── thought bubbles from real intention CHANGES ──────────────────────────
    # Every agent logs a model-authored `intention` each tick (Protocol §4.2). We surface
    # it as a private "thought" bubble when it CHANGES — real data, no fabrication — so the
    # replay shows continuous inner monologue, not just the 10 talk lines. Staggered: at
    # most THOUGHT_BUDGET_PER_TICK new thoughts per tick (round-robin by spillover to the
    # next free tick) and never on a tick the agent is actually talking, so bubbles don't
    # pile up or fight the dialogue.
    THOUGHT_BUDGET_PER_TICK = 3
    THOUGHT_MIN_GAP = 6  # ticks between an agent's own successive thought bubbles
    thoughts_by_tick: dict[int, list[dict]] = {}
    last_thought_tick: dict[str, int] = {}
    last_intent: dict[str, str] = {}
    for t in range(0, max_tick + 1):
        budget = THOUGHT_BUDGET_PER_TICK
        for aid in agents_meta:
            if budget <= 0:
                break
            dt = deaths[aid]
            if dt is not None and t >= dt:
                continue
            if t in talk_ticks_by_agent.get(aid, set()):
                continue  # talking this tick — let the speech bubble own it
            intent = intention_at(aid, t)
            if not intent:
                continue
            if last_intent.get(aid) == intent:
                continue  # unchanged — don't re-announce
            if t - last_thought_tick.get(aid, -999) < THOUGHT_MIN_GAP:
                last_intent[aid] = intent  # absorb the change quietly; respect the gap
                continue
            thoughts_by_tick.setdefault(t, []).append({
                "event_type": "THOUGHT_SENT", "agent_id": aid, "tick": t,
                "message": intent,
            })
            last_intent[aid] = intent
            last_thought_tick[aid] = t
            budget -= 1

    # ── build frames ─────────────────────────────────────────────────────────
    frames = []
    for t in range(0, max_tick + 1):
        ags = []
        for aid, m in agents_meta.items():
            x, y = pos_at(aid, t)
            dt = deaths[aid]
            alive = dt is None or t < dt
            ags.append({
                "id": aid, "name": m["name"], "x": x, "y": y,
                "water": round(water_at(aid, t), 1), "food": 0, "goods": 0,
                "alive": alive, "stance": m["stance"],
                "lastAction": last_action_at(aid, t),
                "intention": intention_at(aid, t),
            })
        frames.append({
            "tick": t,
            "agents": ags,
            # talk (whisper) bubbles take precedence; thoughts fill the quiet ticks.
            "events": talks_by_tick.get(t, []) + thoughts_by_tick.get(t, []),
        })

    await db.close_pool()

    payload = {
        "source": "action_log replay (real run)",
        "gridW": gw, "gridH": gh, "ticks": max_tick + 1,
        "cells": cells,
        "frames": frames,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {
        "frames": len(frames), "agents": len(agents_meta),
        "talks": sum(len(v) for v in talks_by_tick.values()),
        "thoughts": sum(len(v) for v in thoughts_by_tick.values()),
        "deaths": sum(1 for d in deaths.values() if d is not None),
        "bytes": out_path.stat().st_size,
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Export a real DB run to a UI replay JSON")
    ap.add_argument("--out", default="ui/public/replay.json")
    args = ap.parse_args()
    out = Path(__file__).resolve().parent.parent / args.out
    stats = asyncio.run(export(out))
    print(f"OK  wrote {out}")
    print(f"    {stats['frames']} frames · {stats['agents']} agents · "
          f"{stats['talks']} talk-bubbles · {stats['thoughts']} thought-bubbles · "
          f"{stats['deaths']} deaths · {stats['bytes']//1024} KB")


if __name__ == "__main__":
    main()
