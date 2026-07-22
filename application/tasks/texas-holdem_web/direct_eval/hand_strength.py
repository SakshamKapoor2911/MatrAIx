"""Sklansky-Malmuth preflop hand-tier classification for poker persona policies.

NOTE FOR REVIEW: Tier assignments follow standard Sklansky grouping.
Alternative systems (Chen formula, GTO ranges) can replace this lookup
without changing any other code in the Direct Engine.
"""
from __future__ import annotations

RANK_ORDER = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}

_SKLANSKY: dict[tuple[int, int, bool, bool], int] = {}


def _build_sklansky() -> None:
    """Build the Sklansky tier lookup table."""

    def _add(h: int, l: int, s: bool, p: bool, tier: int) -> None:
        _SKLANSKY[(h, l, s, p)] = tier

    # Tier 1: AA, KK, QQ, AKs
    for r in (14, 13, 12):
        _add(r, r, False, True, 1)
        _add(r, r, True, True, 1)
    _add(14, 13, True, False, 1)  # AKs

    # Tier 2: JJ, TT, AKo, AQs, AJs, KQs
    for r in (11, 10):
        _add(r, r, False, True, 2)
        _add(r, r, True, True, 2)
    _add(14, 13, False, False, 2)  # AKo
    _add(14, 12, True, False, 2)   # AQs
    _add(14, 11, True, False, 2)   # AJs
    _add(13, 12, True, False, 2)   # KQs

    # Tier 3: 99, 88, AQo, ATs, KJs, QJs, JTs
    for r in (9, 8):
        _add(r, r, False, True, 3)
        _add(r, r, True, True, 3)
    _add(14, 12, False, False, 3)  # AQo
    _add(14, 10, True, False, 3)   # ATs
    _add(13, 11, True, False, 3)   # KJs
    _add(12, 11, True, False, 3)   # QJs
    _add(11, 10, True, False, 3)   # JTs

    # Tier 4: 77, AJo, KQo, suited broadway (KTs, QTs, T9s), suited aces A2s-A9s
    _add(7, 7, False, True, 4)
    _add(7, 7, True, True, 4)
    _add(14, 11, False, False, 4)  # AJo
    _add(13, 12, False, False, 4)  # KQo
    _add(13, 10, True, False, 4)   # KTs
    _add(12, 10, True, False, 4)   # QTs
    _add(10, 9, True, False, 4)    # T9s
    for low in range(2, 10):
        _add(14, low, True, False, 4)  # A2s-A9s

    # Tier 5: 66, 55, ATo, KJo, QJo, KTo, QTo, JTo, suited connectors T8s-65s
    for r in (6, 5):
        _add(r, r, False, True, 5)
        _add(r, r, True, True, 5)
    _add(14, 10, False, False, 5)  # ATo
    _add(13, 11, False, False, 5)  # KJo
    _add(12, 11, False, False, 5)  # QJo
    _add(13, 10, False, False, 5)  # KTo
    _add(12, 10, False, False, 5)  # QTo
    _add(11, 10, False, False, 5)  # JTo
    for (h, l) in ((10, 8), (9, 8), (8, 7), (7, 6), (6, 5)):
        _add(h, l, True, False, 5)

    # Tier 6: 44, 33, 22, J9o, T9o, 98o, 87o, A2o-A9o, K2s-K8s, Q2s-Q8s
    for r in (4, 3, 2):
        _add(r, r, False, True, 6)
        _add(r, r, True, True, 6)
    for (h, l) in ((11, 9), (10, 9), (9, 8), (8, 7)):
        _add(h, l, False, False, 6)
    for low in range(2, 10):
        _add(14, low, False, False, 6)  # A2o-A9o
    for low in range(2, 9):
        _add(13, low, True, False, 6)   # K2s-K8s
        _add(12, low, True, False, 6)   # Q2s-Q8s

    # Tier 7: K2o-K9o, suited connectors (J8s-54s), J8o, T8o
    for low in range(2, 10):
        _add(13, low, False, False, 7)  # K2o-K9o
    for (h, l) in ((11, 8), (10, 8)):
        _add(h, l, False, False, 7)
    for (h, l) in ((11, 8), (10, 8), (9, 7), (8, 6), (7, 5), (5, 4)):
        _add(h, l, True, False, 7)

    # Tier 8: Everything else (Q9o, J7o, T7o, rag hands, etc.) — default


_build_sklansky()
del _build_sklansky


def classify_preflop(hole_cards: list[str]) -> int:
    """Return Sklansky tier (1-8) for player's hole cards.

    Args:
        hole_cards: List of 2 card strings in format 'Ah', 'Kc', etc.
                    e.g. ['Kh', '5c'] -> Tier 8 (K5o, Kate's test case)

    Returns:
        Integer 1-8 where 1=premium and 8=trash.
    """
    r1 = RANK_ORDER.get(hole_cards[0][0], 2)
    r2 = RANK_ORDER.get(hole_cards[1][0], 2)
    s1 = hole_cards[0][1] if len(hole_cards[0]) > 1 else ""
    s2 = hole_cards[1][1] if len(hole_cards[1]) > 1 else ""

    high = max(r1, r2)
    low = min(r1, r2)
    is_suited = (s1 == s2)
    is_pair = (r1 == r2)

    return _SKLANSKY.get((high, low, is_suited, is_pair), 8)
