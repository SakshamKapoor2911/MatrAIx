"""Texas Hold'em heads-up game logic."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from treys import Card, Evaluator

RANKS = "23456789TJQKA"
SUITS = "shdc"  # spades hearts diamonds clubs
RANK_NAMES = {
    "2": "Two", "3": "Three", "4": "Four", "5": "Five",
    "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine",
    "T": "Ten", "J": "Jack", "Q": "Queen", "K": "King", "A": "Ace",
}
SUIT_SYMBOLS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}

HAND_RANK_NAMES = {
    1: "straight_flush",
    2: "four_of_a_kind",
    3: "full_house",
    4: "flush",
    5: "straight",
    6: "three_of_a_kind",
    7: "two_pair",
    8: "pair",
    9: "high_card",
}

STARTING_STACK = 1000
SMALL_BLIND = 10
BIG_BLIND = 20
RAISE_SIZE = 60  # fixed raise size for simplicity


def _make_deck() -> List[str]:
    return [r + s for r in RANKS for s in SUITS]


def _card_display(c: str) -> str:
    """'Ah' -> 'A♥'"""
    return c[0] + SUIT_SYMBOLS[c[1]]


def _treys_card(c: str) -> int:
    """Convert 'Ah' to treys int (rank uppercase, suit lowercase)."""
    return Card.new(c)


@dataclass
class GameState:
    deck: List[str]
    hole_cards: List[str]      # player's 2 cards
    bot_cards: List[str]       # bot's 2 cards (hidden from UI)
    community_cards: List[str] # 0-5 revealed community cards
    pot: int
    player_stack: int
    bot_stack: int
    player_bet: int            # amount committed this street
    bot_bet: int
    street: str                # preflop | flop | turn | river | showdown
    street_actions: dict       # {"preflop": [...], "flop": [...], ...}
    status: str                # playing | finished
    winner: Optional[str]      # "player" | "opponent" | "tie" | None
    chip_delta: int            # player's net change from starting stack
    final_hand_rank: Optional[str]
    action_log: List[str]
    player_to_act: bool        # True = player acts next


def new_game() -> GameState:
    deck = _make_deck()
    random.shuffle(deck)
    hole = [deck.pop(), deck.pop()]
    bot = [deck.pop(), deck.pop()]
    # post blinds: player = small blind, bot = big blind (heads-up convention)
    state = GameState(
        deck=deck,
        hole_cards=hole,
        bot_cards=bot,
        community_cards=[],
        pot=SMALL_BLIND + BIG_BLIND,
        player_stack=STARTING_STACK - SMALL_BLIND,
        bot_stack=STARTING_STACK - BIG_BLIND,
        player_bet=SMALL_BLIND,
        bot_bet=BIG_BLIND,
        street="preflop",
        street_actions={"preflop": [], "flop": [], "turn": [], "river": []},
        status="playing",
        winner=None,
        chip_delta=0,
        final_hand_rank=None,
        action_log=[f"Blinds posted: player {SMALL_BLIND}, bot {BIG_BLIND}"],
        player_to_act=True,  # small blind acts first preflop
    )
    return state


def apply_action(state: GameState, action: str, raise_amount: int = RAISE_SIZE) -> GameState:
    """Apply player action, trigger bot response when needed, advance street when bets settle."""
    if state.status != "playing":
        return state

    actions = state.street_actions.setdefault(state.street, [])
    is_first_street_action = len(actions) == 0
    bot_needs_to_act = False

    if action == "fold":
        actions.append("fold")
        state.action_log.append("Player folds.")
        state.status = "finished"
        state.winner = "opponent"
        state.chip_delta = -(state.player_bet)
        return state

    elif action == "check":
        actions.append("check")
        state.action_log.append("Player checks.")
        bot_needs_to_act = True  # bot can check or bet in response

    elif action == "call":
        to_call = state.bot_bet - state.player_bet
        if to_call <= 0:
            actions.append("check")
            state.action_log.append("Player checks (nothing to call).")
            bot_needs_to_act = True
        else:
            to_call = min(to_call, state.player_stack)
            state.player_stack -= to_call
            state.player_bet += to_call
            state.pot += to_call
            actions.append("call")
            state.action_log.append(f"Player calls {to_call}.")
            # Preflop only: when SB calls BB as their very first action, BB gets option to raise
            if state.street == "preflop" and is_first_street_action:
                bot_needs_to_act = True
            # Otherwise a call closes the action — bot does not re-respond

    elif action == "raise":
        amount = min(raise_amount, state.player_stack)
        state.player_stack -= amount
        state.player_bet += amount
        state.pot += amount
        actions.append("raise")
        state.action_log.append(f"Player raises {amount}.")
        bot_needs_to_act = True  # bot must respond to any raise

    if bot_needs_to_act and state.status == "playing":
        _bot_action(state)

    if state.status == "playing":
        _maybe_advance_street(state)

    return state


def _bot_action(state: GameState) -> None:
    from bot import decide_bot_action
    bot_act = decide_bot_action(state)
    actions = state.street_actions.setdefault(state.street, [])

    if bot_act == "fold":
        actions.append("bot_fold")
        state.action_log.append("Bot folds.")
        state.status = "finished"
        state.winner = "player"
        state.chip_delta = state.pot - (STARTING_STACK - state.player_stack)
        return

    if bot_act == "check":
        actions.append("bot_check")
        state.action_log.append("Bot checks.")

    elif bot_act == "call":
        to_call = state.player_bet - state.bot_bet
        if to_call <= 0:
            # nothing to call — treat as check
            actions.append("bot_check")
            state.action_log.append("Bot checks.")
        else:
            to_call = min(to_call, state.bot_stack)
            state.bot_stack -= to_call
            state.bot_bet += to_call
            state.pot += to_call
            actions.append("bot_call")
            state.action_log.append(f"Bot calls {to_call}.")

    elif bot_act == "raise":
        amount = min(RAISE_SIZE, state.bot_stack)
        state.bot_stack -= amount
        state.bot_bet += amount
        state.pot += amount
        actions.append("bot_raise")
        state.action_log.append(f"Bot raises {amount}.")


def _maybe_advance_street(state: GameState) -> None:
    """Advance to next street when betting is settled."""
    if state.player_bet != state.bot_bet:
        return  # still betting

    order = ["preflop", "flop", "turn", "river", "showdown"]
    idx = order.index(state.street)
    if idx + 1 >= len(order):
        _resolve_showdown(state)
        return

    next_street = order[idx + 1]
    if next_street == "showdown":
        _resolve_showdown(state)
        return

    state.street = next_street
    state.player_bet = 0
    state.bot_bet = 0

    if next_street == "flop":
        state.community_cards = [state.deck.pop(), state.deck.pop(), state.deck.pop()]
        state.action_log.append(f"Flop: {' '.join(_card_display(c) for c in state.community_cards)}")
    elif next_street == "turn":
        state.community_cards.append(state.deck.pop())
        state.action_log.append(f"Turn: {_card_display(state.community_cards[3])}")
    elif next_street == "river":
        state.community_cards.append(state.deck.pop())
        state.action_log.append(f"River: {_card_display(state.community_cards[4])}")


def _resolve_showdown(state: GameState) -> None:
    evaluator = Evaluator()
    board = [_treys_card(c) for c in state.community_cards]
    player_hand = [_treys_card(c) for c in state.hole_cards]
    bot_hand = [_treys_card(c) for c in state.bot_cards]

    p_score = evaluator.evaluate(board, player_hand)
    b_score = evaluator.evaluate(board, bot_hand)
    p_class = evaluator.get_rank_class(p_score)
    state.final_hand_rank = HAND_RANK_NAMES.get(p_class, "high_card")

    state.street = "showdown"
    state.status = "finished"

    if p_score < b_score:  # lower = better in treys
        state.winner = "player"
        state.chip_delta = state.pot - (STARTING_STACK - state.player_stack)
        state.action_log.append(
            f"Showdown: player wins with {state.final_hand_rank}! "
            f"Bot had {' '.join(_card_display(c) for c in state.bot_cards)}"
        )
    elif b_score < p_score:
        state.winner = "opponent"
        state.chip_delta = -(STARTING_STACK - state.player_stack)
        bot_class = evaluator.get_rank_class(b_score)
        bot_rank = HAND_RANK_NAMES.get(bot_class, "high_card")
        state.action_log.append(
            f"Showdown: bot wins with {bot_rank}. "
            f"Bot had {' '.join(_card_display(c) for c in state.bot_cards)}"
        )
    else:
        state.winner = "tie"
        state.chip_delta = 0
        state.action_log.append("Showdown: tie! Pot split.")


def state_to_dict(state: GameState) -> dict:
    return {
        "game_id": "texas-holdem-heads-up-v1",
        "street": state.street,
        "status": state.status,
        "hole_cards": [_card_display(c) for c in state.hole_cards],
        "hole_cards_raw": state.hole_cards,
        "community_cards": [_card_display(c) for c in state.community_cards],
        "community_cards_raw": state.community_cards,
        "bot_cards": (
            [_card_display(c) for c in state.bot_cards]
            if state.status == "finished"
            else ["??", "??"]
        ),
        "pot": state.pot,
        "player_stack": state.player_stack,
        "bot_stack": state.bot_stack,
        "player_bet": state.player_bet,
        "bot_bet": state.bot_bet,
        "street_actions": state.street_actions,
        "winner": state.winner,
        "chip_delta": state.chip_delta,
        "final_hand_rank": state.final_hand_rank,
        "action_log": state.action_log,
        "call_amount": max(0, state.bot_bet - state.player_bet),
    }
