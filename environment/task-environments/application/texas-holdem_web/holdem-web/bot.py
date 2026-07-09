"""Simple rule-based bot for Texas Hold'em heads-up."""
from __future__ import annotations

from treys import Card, Evaluator

HIGH_RANKS = set("AKQJ")
PREMIUM_PAIRS = {"AA", "KK", "QQ", "JJ", "TT"}


def _hand_strength(state) -> int:
    """Return treys score for bot's best 5-card hand. Lower = stronger."""
    if len(state.community_cards) < 3:
        return 9999  # no board yet
    evaluator = Evaluator()
    board = [Card.new(c) for c in state.community_cards]
    hand = [Card.new(c) for c in state.bot_cards]
    return evaluator.evaluate(board, hand)


def decide_bot_action(state) -> str:
    """Return 'fold' | 'check' | 'call' | 'raise'."""
    street = state.street
    c1, c2 = state.bot_cards
    r1, r2 = c1[0], c2[0]
    suited = c1[1] == c2[1]
    is_pair = r1 == r2
    pair_key = r1 + r2 if r1 == r2 else None
    both_high = r1 in HIGH_RANKS and r2 in HIGH_RANKS
    player_raised = state.player_bet > state.bot_bet

    if street == "preflop":
        if is_pair and pair_key in PREMIUM_PAIRS:
            return "raise"
        if both_high:
            return "call" if player_raised else "raise"
        if is_pair or r1 in HIGH_RANKS or r2 in HIGH_RANKS:
            return "call"
        if suited and r1 in "89TJ" and r2 in "89TJ":
            return "call"
        # weak hand
        if player_raised:
            return "fold"
        return "check"

    # post-flop: use hand strength
    score = _hand_strength(state)
    if score <= 3000:   # very strong (flush+)
        return "raise"
    if score <= 5000:   # good hand (pair/two-pair/set)
        return "call" if player_raised else "raise"
    if score <= 7000:   # marginal
        return "call" if not player_raised else "fold"
    # weak
    if player_raised:
        return "fold"
    return "check"
