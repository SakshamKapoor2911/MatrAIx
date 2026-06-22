"""Unit tests for the pure spatial helpers (mircoverse.world.geometry).

One test per public function. No I/O, no DB — these never skip.
"""

from __future__ import annotations

from mircoverse.world.geometry import (
    DIRECTION_DELTAS,
    chebyshev,
    contention_key,
    contention_winner,
    fov_cells,
    is_adjacent,
    moore_neighbors,
    step_direction,
    step_toward,
)


def test_chebyshev() -> None:
    assert chebyshev((0, 0), (0, 0)) == 0
    assert chebyshev((0, 0), (3, 1)) == 3
    assert chebyshev((2, 2), (-1, 5)) == 3  # max(|dx|=3, |dy|=3)


def test_is_adjacent() -> None:
    assert is_adjacent((5, 5), (5, 6)) is True
    assert is_adjacent((5, 5), (6, 6)) is True   # diagonal Moore neighbour
    assert is_adjacent((5, 5), (5, 5)) is False  # same cell is NOT adjacent
    assert is_adjacent((5, 5), (5, 7)) is False  # two away


def test_moore_neighbors() -> None:
    nbrs = moore_neighbors((0, 0))
    assert len(nbrs) == 8
    assert (0, 0) not in nbrs
    # every neighbour is Chebyshev distance 1
    assert all(chebyshev((0, 0), n) == 1 for n in nbrs)


def test_step_toward() -> None:
    assert step_toward((0, 0), (5, 0)) == (1, 0)     # one step east
    assert step_toward((0, 0), (5, 5)) == (1, 1)     # diagonal approach
    assert step_toward((3, 3), (3, 3)) == (3, 3)     # already there
    assert step_toward((4, 4), (0, 7)) == (3, 5)     # mixed-sign one-cell step


def test_step_direction() -> None:
    assert step_direction((10, 10), "N") == (10, 11)
    assert step_direction((10, 10), "SW") == (9, 9)
    assert step_direction((10, 10), "E") == (11, 10)
    assert set(DIRECTION_DELTAS) == {"N", "NE", "E", "SE", "S", "SW", "W", "NW"}


def test_fov_cells() -> None:
    cells = fov_cells((5, 5), 2)
    assert len(cells) == 25          # 5x5 window
    assert (5, 5) in cells           # centre included
    assert all(chebyshev((5, 5), c) <= 2 for c in cells)
    assert (8, 5) not in cells       # distance 3 excluded


def test_contention_key_is_stable() -> None:
    # Stable across calls/processes (NOT Python's salted hash()).
    k1 = contention_key(42, "agent_07")
    k2 = contention_key(42, "agent_07")
    assert k1 == k2
    assert contention_key(42, "agent_07") != contention_key(43, "agent_07")


def test_contention_winner_deterministic() -> None:
    ids = ["agent_01", "agent_02", "agent_03"]
    w1 = contention_winner(7, ids)
    w2 = contention_winner(7, list(reversed(ids)))  # input order must not matter
    assert w1 == w2
    assert w1 in ids
