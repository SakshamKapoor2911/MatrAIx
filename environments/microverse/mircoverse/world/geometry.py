"""Pure spatial helpers: Moore-8 adjacency, Chebyshev-radius FOV, deterministic contention.

No state, no I/O. Coordinates are integer ``(x, y)`` with ``0 ≤ x,y`` bounded by the grid
(Protocol.md §2.1). No teleport: movement is one cell/tick along one of the 8 compass directions.
"""

from __future__ import annotations

import hashlib

# 8 compass directions → (dx, dy). +y is "north" by convention; the engine never renders,
# so the only requirement is internal consistency and that all 8 Moore neighbours are reachable.
DIRECTION_DELTAS: dict[str, tuple[int, int]] = {
    "N": (0, 1),
    "NE": (1, 1),
    "E": (1, 0),
    "SE": (1, -1),
    "S": (0, -1),
    "SW": (-1, -1),
    "W": (-1, 0),
    "NW": (-1, 1),
}

# Chebyshev FOV radius (Protocol.md §2.1 seed-run value). Canonical HERE — the lowest-level
# spatial module — so "what a cell within view means" has ONE definition shared by the FOV
# computation (mircoverse.world.fov) and the movement gate (mircoverse.world.resolver). A
# `move toward` goal is legal if it is known OR within this radius; the two must never diverge.
FOV_RADIUS = 2


def chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Chebyshev (chessboard) distance — the metric for both adjacency and FOV."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def is_adjacent(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Moore-8 adjacency: distinct cells within Chebyshev distance 1 (Protocol.md §2.1)."""
    return a != b and chebyshev(a, b) <= 1


def moore_neighbors(pos: tuple[int, int]) -> list[tuple[int, int]]:
    """The 8 Moore neighbours of a cell (unbounded; caller filters to the grid)."""
    x, y = pos
    return [
        (x + dx, y + dy)
        for dx, dy in DIRECTION_DELTAS.values()
    ]


def step_toward(src: tuple[int, int], dst: tuple[int, int]) -> tuple[int, int]:
    """One Moore-8 step from ``src`` toward ``dst`` (no teleport).

    Moves at most one cell along each axis (sign of the delta), so a diagonal target is
    approached diagonally. Returns ``src`` unchanged if already at ``dst``.
    """
    sx, sy = src
    dx, dy = dst
    nx = sx + (0 if dx == sx else (1 if dx > sx else -1))
    ny = sy + (0 if dy == sy else (1 if dy > sy else -1))
    return (nx, ny)


def step_direction(src: tuple[int, int], direction: str) -> tuple[int, int]:
    """One blind step in a compass direction (Protocol.md §4.1 move-by-direction)."""
    dx, dy = DIRECTION_DELTAS[direction]
    return (src[0] + dx, src[1] + dy)


def fov_cells(center: tuple[int, int], radius: int) -> list[tuple[int, int]]:
    """All cells within Chebyshev ``radius`` of ``center`` (a (2r+1)×(2r+1) square),
    including the centre. Caller filters to the grid (Protocol.md §2.1, FOV radius 2 ⇒ 5×5)."""
    cx, cy = center
    return [
        (cx + dx, cy + dy)
        for dx in range(-radius, radius + 1)
        for dy in range(-radius, radius + 1)
    ]


def contention_key(tick_seed: int, agent_id: str) -> str:
    """Deterministic, reproducible priority for movement contention (Architecture.md §Conflict
    Resolution: ``winner = hash(tick_seed + agent_id)``).

    Uses a STABLE cryptographic digest, never Python's salted built-in ``hash()`` (which is
    randomised per-process and would break replay — World.md §11). Higher key wins; ties are
    impossible in practice but broken by ``agent_id`` lexicographically by the caller.
    """
    raw = f"{tick_seed}:{agent_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def contention_winner(tick_seed: int, agent_ids: list[str]) -> str:
    """Pick the single deterministic winner among agents contending for one cell.

    Winner = max ``contention_key``; ``agent_id`` breaks the (astronomically unlikely) digest tie
    so the result is total-ordered and replay-stable regardless of input list order.
    """
    return max(agent_ids, key=lambda aid: (contention_key(tick_seed, aid), aid))
