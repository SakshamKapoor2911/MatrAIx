"""Unit tests for Sklansky preflop hand-tier classification."""
from direct_eval.hand_strength import classify_preflop


def test_premium_pairs_are_tier_1():
    assert classify_preflop(["Ah", "Ad"]) == 1
    assert classify_preflop(["Kh", "Kd"]) == 1
    assert classify_preflop(["Qh", "Qd"]) == 1


def test_ak_suited_is_tier_1():
    assert classify_preflop(["Ah", "Kh"]) == 1


def test_ak_offsuit_is_tier_2():
    assert classify_preflop(["Ad", "Kh"]) == 2


def test_kates_weak_hands():
    assert classify_preflop(["Kh", "5c"]) == 7  # K5o = Tier 7 (K-high, no pair, unsuited)
    assert classify_preflop(["Th", "6s"]) == 8  # T6o = Tier 8 (T-high rag)


def test_seven_two_offsuit_is_tier_8():
    assert classify_preflop(["7h", "2d"]) == 8


def test_jacks_are_tier_2():
    assert classify_preflop(["Jh", "Jd"]) == 2


def test_ace_ten_suited_is_tier_3():
    assert classify_preflop(["Ah", "Th"]) == 3


def test_jack_ten_offsuit_is_tier_5():
    assert classify_preflop(["Jh", "Td"]) == 5


def test_ace_jack_offsuit_is_tier_4():
    assert classify_preflop(["Ah", "Jd"]) == 4


def test_jack_nine_offsuit_is_tier_6():
    assert classify_preflop(["Jh", "9d"]) == 6


def test_king_nine_offsuit_is_tier_7():
    assert classify_preflop(["Kh", "9d"]) == 7


def test_queen_nine_offsuit_is_tier_8():
    assert classify_preflop(["Qh", "9d"]) == 8


def test_tier_8_default_for_rag_combinations():
    assert classify_preflop(["Qs", "8d"]) == 8
    assert classify_preflop(["Jh", "7c"]) == 8
    assert classify_preflop(["9h", "6s"]) == 8
