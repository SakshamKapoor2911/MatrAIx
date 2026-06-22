"""Mock load-test agent — Protocol.md §5/§7 (NORMATIVE wire only).

A deliberately dumb async HTTP loop: GET /world/observe -> pick a RANDOM but
contract-VALID action -> POST /action -> sleep until the server's tick_ends_at.

It exists to load-test the engine, not to think. There is no LLM, no memory
retrieval, no reflection. It only ever needs to obey the §4-5 wire contract, so
it is the cheapest possible "agent" the open arm could field. Parameterized so
1000+ instances can be spawned against one server.

Determinism: every stochastic choice flows through a seeded `random.Random`
instance passed in (one RNG per agent) — never the global `random` module and
never a time-based seed (BUILD_SPEC non-negotiable #3).
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Optional

import httpx

from mircoverse.contracts import (
    Action,
    ActionEnvelope,
    ActionType,
    AttackParams,
    ConsumeParams,
    MoveParams,
    Observation,
    SignalParams,
    TalkParams,
    TradeParams,
)
from mircoverse.contracts.actions import EmptyParams

# Blind directional moves are always valid (no known-cell requirement, §4.3).
_DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
_STANCES = ["friendly", "neutral", "aggressive"]
_RESOURCES = ["water", "food", "goods"]


def choose_action(obs: Observation, rng: random.Random) -> Action:
    """Pick a uniformly-random, contract-VALID action for this observation.

    Pure given (obs, rng): no I/O, no globals. The candidate set is built so that
    every option is guaranteed to satisfy the frozen Action validators —
    e.g. `move toward` only targets a cell actually present in the FOV (a known
    cell per §4.3), social actions only target an agent_id actually in the FOV,
    and `consume` only names a resource the self plausibly holds.

    Validity here means "the engine will accept the envelope shape", not
    "the action will succeed" — a mock agent is free to attempt a doomed trade.
    """
    visible_agent_ids = [a.agent_id for a in obs.fov.agents]
    # Cells we are allowed to goal-move toward: known == currently visible here
    # (the mock keeps no memory, so it only trusts what /observe shows it).
    known_cells = [tuple(c.pos) for c in obs.fov.cells if tuple(c.pos) != tuple(obs.self.pos)]

    builders: list = [
        lambda: Action(type=ActionType.WAIT, params=EmptyParams()),
        lambda: Action(type=ActionType.SCAVENGE, params=EmptyParams()),
        lambda: Action(
            type=ActionType.MOVE,
            params=MoveParams(direction=rng.choice(_DIRECTIONS)),
        ),
        lambda: Action(
            type=ActionType.SIGNAL,
            params=SignalParams(stance=rng.choice(_STANCES)),
        ),
    ]

    # consume is only worth offering for a resource the agent actually has > 0.
    affordable = [r for r in _RESOURCES if getattr(obs.self, r) > 0]
    if affordable:

        def _consume() -> Action:
            resource = rng.choice(affordable)
            held = getattr(obs.self, resource)
            return Action(
                type=ActionType.CONSUME,
                params=ConsumeParams(resource=resource, amount=rng.randint(1, held)),
            )

        builders.append(_consume)

    if known_cells:
        builders.append(
            lambda: Action(
                type=ActionType.MOVE,
                params=MoveParams(toward=rng.choice(known_cells)),
            )
        )

    if visible_agent_ids:
        builders.append(
            lambda: Action(
                type=ActionType.TALK,
                params=TalkParams(
                    target=rng.choice(visible_agent_ids),
                    message="(mock chatter)",
                ),
            )
        )
        builders.append(
            lambda: Action(
                type=ActionType.ATTACK,
                params=AttackParams(target=rng.choice(visible_agent_ids)),
            )
        )
        builders.append(
            lambda: Action(
                type=ActionType.TRADE,
                params=TradeParams(
                    target=rng.choice(visible_agent_ids),
                    offer={"goods": 1},
                    request={"water": 1},
                ),
            )
        )

    # broadcast talk needs no target; always available.
    builders.append(
        lambda: Action(
            type=ActionType.TALK,
            params=TalkParams(broadcast=True, message="(mock broadcast)"),
        )
    )

    return rng.choice(builders)()


def build_envelope(obs: Observation, rng: random.Random) -> ActionEnvelope:
    """Wrap a random valid action into a contract envelope for this tick.

    The mock never writes memory and never reflects, so it carries no
    memory_update and only a trivial rationale (logged but mechanically inert).
    """
    return ActionEnvelope(
        tick=obs.tick,
        action=choose_action(obs, rng),
        rationale="mock load-test agent",
    )


def _seconds_until(tick_ends_at: str, now: Optional[datetime] = None) -> float:
    """Seconds to sleep until the server-declared tick deadline (§5.3).

    Always derived from the server's `tick_ends_at`, never a locally computed
    deadline. Clamped to >= 0 so a stale/past deadline never sleeps negatively.
    """
    now = now or datetime.now(timezone.utc)
    try:
        deadline = datetime.fromisoformat(tick_ends_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return max(0.0, (deadline - now).total_seconds())


class MockAgent:
    """One dumb HTTP client. Spawn 1000+ of these (each with its own RNG) for load.

    Parameterized on base_url, agent_id, api_key and a seeded RNG so a fleet is
    fully reproducible: same seeds + same server ⇒ same action stream.
    """

    def __init__(
        self,
        base_url: str,
        agent_id: str,
        api_key: str,
        seed: int,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.api_key = api_key
        self.rng = random.Random(seed)
        self._client = client
        self._owns_client = client is None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def observe(self) -> Optional[Observation]:
        client = await self._ensure_client()
        resp = await client.get(
            f"{self.base_url}/api/v1/world/observe", headers=self._headers()
        )
        if resp.status_code != 200:
            return None
        return Observation.model_validate(resp.json())

    async def submit(self, envelope: ActionEnvelope) -> httpx.Response:
        client = await self._ensure_client()
        return await client.post(
            f"{self.base_url}/api/v1/agents/{self.agent_id}/action",
            headers=self._headers(),
            json=envelope.model_dump(mode="json", by_alias=True),
        )

    async def step(self) -> Optional[ActionEnvelope]:
        """One observe -> decide -> submit cycle. Returns the envelope sent (or None
        if there was nothing to observe). Does NOT sleep — `run` does that."""
        obs = await self.observe()
        if obs is None:
            return None
        envelope = build_envelope(obs, self.rng)
        await self.submit(envelope)
        return envelope

    async def run(self, *, max_ticks: Optional[int] = None) -> None:
        """The dumb loop: observe -> act -> sleep to tick_ends_at -> repeat.

        Runs forever unless `max_ticks` bounds it (useful for tests/load runs).
        """
        ticks = 0
        try:
            while max_ticks is None or ticks < max_ticks:
                obs = await self.observe()
                if obs is None:
                    await asyncio.sleep(1.0)
                    continue
                await self.submit(build_envelope(obs, self.rng))
                await asyncio.sleep(_seconds_until(obs.tick_ends_at))
                ticks += 1
        finally:
            if self._owns_client and self._client is not None:
                await self._client.aclose()
                self._client = None


async def spawn_fleet(
    base_url: str,
    agents: list[tuple[str, str]],
    *,
    base_seed: int,
    max_ticks: Optional[int] = None,
) -> None:
    """Spawn a fleet of MockAgents (one async task each) for load testing.

    `agents` is a list of (agent_id, api_key). Each gets a distinct, reproducible
    seed derived from `base_seed` so the whole fleet replays identically.
    """
    tasks = [
        asyncio.create_task(
            MockAgent(base_url, agent_id, api_key, base_seed + i).run(max_ticks=max_ticks)
        )
        for i, (agent_id, api_key) in enumerate(agents)
    ]
    await asyncio.gather(*tasks)
