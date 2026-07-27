"""Unit tests for direct engine persona action policies."""
import random
from dataclasses import dataclass, field

from direct_eval.policies import (
    DecisionStylePolicy,
    DomainKnowledgePolicy,
    DominantTraitPolicy,
    EconomicMotivationPolicy,
    PersonaValueNormalizer,
    RiskPolicy,
    TimePressurePolicy,
    TrustPolicy,
)
from direct_eval.policy_registry import build_policy


@dataclass
class MockState:
    player_bet: int = 10
    bot_bet: int = 20
    pot: int = 30
    street: str = "flop"


@dataclass
class MockPreflopState:
    player_bet: int = 10
    bot_bet: int = 20
    pot: int = 30
    hole_cards: list = field(default_factory=lambda: ["Ah", "Ad"])
    street: str = "preflop"


def test_persona_value_normalizer():
    assert PersonaValueNormalizer.normalize_risk("risk-averse") == "Low"
    assert PersonaValueNormalizer.normalize_risk("risk-seeking") == "High"
    assert PersonaValueNormalizer.normalize_trust("hostile") == "Low"
    assert PersonaValueNormalizer.normalize_time_pressure("deadline") == "High"
    assert PersonaValueNormalizer.normalize_trait("High extraversion") == "Social"
    assert PersonaValueNormalizer.normalize_trait("Competitive player") == "Competitive"
    assert PersonaValueNormalizer.normalize_domain("Software & AI") == "Technology"
    assert PersonaValueNormalizer.normalize_tech_savviness("Digital native") == "High"
    assert PersonaValueNormalizer.normalize_socioeconomic("Upper-middle") == "High income"
    assert PersonaValueNormalizer.normalize_socioeconomic("Lower-middle") == "Low income"


def test_risk_policy_mapping():
    policy = RiskPolicy()
    assert policy.derive_output_fields({"risk_tolerance": "Low"})["risk_posture"] == "risk_averse"
    assert policy.derive_output_fields({"risk_tolerance": "High"})["risk_posture"] == "risk_seeking"
    assert policy.derive_output_fields({"risk_tolerance": "Moderate"})["risk_posture"] == "balanced"


def test_trust_policy():
    policy = TrustPolicy()
    state = MockState(player_bet=10, bot_bet=20)
    rng = random.Random(42)
    assert policy.derive_output_fields({"trust_level": "Low"})["trust_posture"] == "skeptical"
    assert policy.derive_output_fields({"trust_level": "High"})["trust_posture"] == "trusting"


def test_time_pressure_policy():
    policy = TimePressurePolicy()
    state = MockState(player_bet=10, bot_bet=20)
    rng = random.Random(42)
    assert policy.decide(state, {"time_pressure": "High"}, rng) in ("fold", "call")
    assert policy.derive_output_fields({"time_pressure": "High"})["decision_pressure"] == "high"


def test_domain_knowledge_policy():
    policy = DomainKnowledgePolicy()
    state = MockState(player_bet=10, bot_bet=20, pot=100)
    rng = random.Random(42)
    assert policy.derive_output_fields({"domain": "Gaming"})["domain_awareness"] == "gaming"


def test_dominant_trait_policy():
    policy = DominantTraitPolicy()
    state = MockState(player_bet=10, bot_bet=20)
    rng = random.Random(42)
    assert policy.derive_output_fields({"dominant_trait": "Social"})["trait_expression"] == "social"


def test_decision_style_policy_mapping():
    policy = DecisionStylePolicy()
    assert policy.derive_output_fields({"decision_style": "Analytical"})["exploration_style"] == "deep_research"
    assert policy.derive_output_fields({"decision_style": "Impulsive"})["exploration_style"] == "quick_pick"
    assert policy.derive_output_fields({"decision_style": "Cautious"})["exploration_style"] == "hesitant"


def test_economic_motivation_policy_mapping():
    policy = EconomicMotivationPolicy()
    assert policy.derive_output_fields({"economic_motivation": "Cost-sensitive"})["task_strategy_basis"] == "pot_control"
    assert policy.derive_output_fields({"economic_motivation": "Value-driven"})["task_strategy_basis"] == "hand_strength"


def test_composed_policy():
    dims = {
        "risk_tolerance": "risk-averse",
        "decision_style": "systematic",
        "economic_motivation": "loss-averse",
        "trust_level": "hostile",
        "time_pressure": "deadline",
    }
    policy = build_policy(dims)
    state = MockState(player_bet=10, bot_bet=20, pot=30)
    rng = random.Random(42)

    action = policy.decide(state, dims, rng)
    assert action in ("fold", "call", "check", "raise")

    derived = policy.derive_output_fields(dims)
    assert derived["risk_posture"] == "risk_averse"
    assert derived["exploration_style"] == "deep_research"
    assert derived["task_strategy_basis"] == "pot_control"


def test_risk_policy_preflop_folds_weak_hands():
    """Low risk_tolerance persona should frequently fold Tier 8 hands preflop."""
    policy = RiskPolicy()
    dims = {"risk_tolerance": "Low"}
    state = MockPreflopState(hole_cards=["Th", "6s"])  # Tier 8
    rng = random.Random(42)

    folds = sum(1 for _ in range(1000) if policy.decide(state, dims, rng) == "fold")
    fold_pct = folds / 1000
    assert fold_pct > 0.75, f"Expected >75% fold for Tier 8 + Low risk, got {fold_pct:.1%}"


def test_risk_policy_preflop_folds_tier_7():
    """Low risk should substantially fold Tier 7 hands preflop."""
    policy = RiskPolicy()
    dims = {"risk_tolerance": "Low"}
    state = MockPreflopState(hole_cards=["Kh", "5c"])  # Tier 7 (Kate's K5o)
    rng = random.Random(123)

    folds = sum(1 for _ in range(1000) if policy.decide(state, dims, rng) == "fold")
    fold_pct = folds / 1000
    assert fold_pct > 0.60, f"Expected >60% fold for Tier 7 + Low risk, got {fold_pct:.1%}"


def test_risk_policy_never_folds_premium_hands():
    """No persona should ever fold premium hands (AA, KK, QQ, AKs) preflop."""
    policy = RiskPolicy()
    premium_hands = [["Ah", "Ad"], ["Kh", "Kd"], ["Qh", "Qd"], ["Ah", "Kh"]]
    risk_levels = ["Low", "Moderate", "High"]

    for cards in premium_hands:
        for rt in risk_levels:
            dims = {"risk_tolerance": rt}
            state = MockPreflopState(hole_cards=cards)
            rng = random.Random(42)
            for _ in range(100):
                action = policy.decide(state, dims, rng)
                assert action != "fold", (
                    f"Premium hand {cards} should never fold, "
                    f"but got '{action}' with risk_tolerance={rt}"
                )


def test_risk_policy_high_risk_preflop_raises_or_calls():
    """High risk persona should prefer raise/call over fold on average hands."""
    policy = RiskPolicy()
    dims = {"risk_tolerance": "High"}
    state = MockPreflopState(hole_cards=["Jh", "Td"])  # Tier 5
    rng = random.Random(123)

    actions = [policy.decide(state, dims, rng) for _ in range(500)]
    fold_rate = actions.count("fold") / len(actions)
    raise_rate = actions.count("raise") / len(actions)
    assert fold_rate < 0.15, (
        f"Expected <15% fold on Tier 5 + High risk, got {fold_rate:.1%}"
    )
    assert raise_rate > 0.20, (
        f"Expected >20% raise on Tier 5 + High risk, got {raise_rate:.1%}"
    )


def test_risk_policy_postflop_unchanged():
    """Post-flop decisions should use the original bet-position heuristic."""
    policy = RiskPolicy()
    dims = {"risk_tolerance": "High"}
    state = MockState(player_bet=10, bot_bet=20, pot=30, street="flop")
    rng = random.Random(42)

    actions = [policy.decide(state, dims, rng) for _ in range(200)]
    assert "raise" in actions, "High risk should raise post-flop"
    assert actions.count("fold") == 0, "High risk should never fold post-flop"
