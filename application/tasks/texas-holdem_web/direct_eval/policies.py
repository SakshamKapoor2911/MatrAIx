"""Deterministic Persona Action Policies for poker direct engine evaluation."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .hand_strength import classify_preflop


class PersonaValueNormalizer:
    """Normalizes raw persona YAML dimension strings into categorical enums expected by strategy filters."""

    @staticmethod
    def normalize_risk(val: str) -> str:
        val = str(val).lower()
        if any(w in val for w in ["low", "averse", "cautious", "conservative"]):
            return "Low"
        if any(w in val for w in ["high", "seeking", "aggressive", "tolerant"]):
            return "High"
        return "Moderate"

    @staticmethod
    def normalize_trust(val: str) -> str:
        val = str(val).lower()
        if any(w in val for w in ["low", "skeptical", "distrust", "suspicious", "hostile"]):
            return "Low"
        if any(w in val for w in ["high", "trusting", "gullible"]):
            return "High"
        return "Moderate"

    @staticmethod
    def normalize_time_pressure(val: str) -> str:
        val = str(val).lower()
        if any(w in val for w in ["high", "urgent", "rushed", "tight", "emergency", "deadline"]):
            return "High"
        if any(w in val for w in ["moderate", "medium", "some"]):
            return "Moderate"
        return "None"

    @staticmethod
    def normalize_trait(val: str) -> str:
        val = str(val).lower()
        if any(w in val for w in ["competitive"]):
            return "Competitive"
        if any(w in val for w in ["analytical", "high conscientiousness"]):
            return "Analytical"
        if any(w in val for w in ["reserved", "low extraversion", "high neuroticism"]):
            return "Reserved"
        if any(w in val for w in ["creative", "high openness"]):
            return "Creative"
        return "Social"

    @staticmethod
    def normalize_domain(val: str) -> str:
        val = str(val).lower()
        if any(w in val for w in ["software", "ai", "tech", "computer"]):
            return "Technology"
        if any(w in val for w in ["finance", "economic", "bank", "invest"]):
            return "Finance"
        if any(w in val for w in ["game", "gaming", "esports"]):
            return "Gaming"
        return "General"

    @staticmethod
    def normalize_tech_savviness(val: str) -> str:
        val = str(val).lower()
        if any(w in val for w in ["low", "avoidant", "reluctant", "laggard"]):
            return "Low"
        if any(w in val for w in ["high", "native", "advanced", "expert"]):
            return "High"
        return "Medium"

    @staticmethod
    def normalize_socioeconomic(val: str) -> str:
        val = str(val).lower()
        if any(w in val for w in ["lower-middle", "low", "poor"]):
            return "Low income"
        if any(w in val for w in ["upper-middle", "high", "rich", "wealthy"]):
            return "High income"
        return "Middle"

    @staticmethod
    def normalize_decision_style(val: str) -> str:
        val = str(val).lower()
        if any(w in val for w in ["intuitive", "fast", "heuristic", "gut"]):
            return "Intuitive"
        if any(w in val for w in ["impulsive", "rash", "unpredictable"]):
            return "Impulsive"
        if any(w in val for w in ["cautious", "hesitant"]):
            return "Cautious"
        return "Analytical"

    @staticmethod
    def normalize_economic_motivation(val: str) -> str:
        val = str(val).lower()
        if any(w in val for w in ["status", "prestige", "win"]):
            return "Status-seeking"
        if any(w in val for w in ["loss", "risk-averse", "protect", "cost"]):
            return "Cost-sensitive"
        if any(w in val for w in ["premium"]):
            return "Premium-seeking"
        return "Value-driven"

    @classmethod
    def normalize_all(cls, dims: Dict[str, str]) -> Dict[str, str]:
        result = dict(dims)
        result["risk_tolerance"] = cls.normalize_risk(dims.get("risk_tolerance", ""))
        result["trust_level"] = cls.normalize_trust(dims.get("trust_level", ""))
        result["time_pressure"] = cls.normalize_time_pressure(dims.get("time_pressure", ""))
        result["dominant_trait"] = cls.normalize_trait(dims.get("dominant_trait", ""))
        result["domain"] = cls.normalize_domain(dims.get("domain", ""))
        result["tech_savviness"] = cls.normalize_tech_savviness(dims.get("tech_savviness", ""))
        result["socioeconomic_band"] = cls.normalize_socioeconomic(dims.get("socioeconomic_band", ""))
        result["decision_style"] = cls.normalize_decision_style(dims.get("decision_style", ""))
        result["economic_motivation"] = cls.normalize_economic_motivation(dims.get("economic_motivation", ""))
        return result


class PersonaActionPolicy(ABC):
    """Abstract base class mapping persona dimensions to poker actions and verifier fields."""

    @abstractmethod
    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        """Return 'fold' | 'check' | 'call' | 'raise' | None (to defer to next policy)."""

    @abstractmethod
    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        """Return dict of derived fields (e.g. risk_posture, exploration_style, strategy_basis)."""


class ComposedPolicy(PersonaActionPolicy):
    """Aggregates sub-policies with priority ordering."""

    def __init__(self, sub_policies: List[PersonaActionPolicy]):
        self.sub_policies = sub_policies

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> str:
        norm_dims = PersonaValueNormalizer.normalize_all(dims)
        for policy in self.sub_policies:
            action = policy.decide(state, norm_dims, rng)
            if action is not None:
                # Tech savviness UI error simulation wrapper
                tech = norm_dims.get("tech_savviness", "Medium")
                err_prob = 0.10 if tech == "Low" else 0.03 if tech == "Medium" else 0.0
                if err_prob > 0 and rng.random() < err_prob:
                    # Alternate action
                    alt_actions = [a for a in ["fold", "check", "call", "raise"] if a != action]
                    return rng.choice(alt_actions)
                return action
        return "check"  # Fallback safety

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        norm_dims = PersonaValueNormalizer.normalize_all(dims)
        result: Dict[str, Any] = {}
        for policy in self.sub_policies:
            fields = policy.derive_output_fields(norm_dims)
            if fields:
                for k, v in fields.items():
                    if k not in result or v is not None:
                        result.setdefault(k, v)
        return result



class TrustPolicy(PersonaActionPolicy):
    """Maps trust_level dimension to bot raise response behavior."""

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        trust = dims.get("trust_level", "Moderate")
        player_behind = state.player_bet < state.bot_bet
        if not player_behind:
            return None

        if trust == "Low":
            # Thinks bot is bluffing: 30% more likely to call instead of fold
            return "call" if rng.random() < 0.6 else None
        elif trust == "High":
            # Believes bot has a strong hand: 30% more likely to fold
            return "fold" if rng.random() < 0.4 else None
        return None

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        trust = dims.get("trust_level", "Moderate")
        return {"trust_posture": "skeptical" if trust == "Low" else "trusting" if trust == "High" else "neutral"}


class TimePressurePolicy(PersonaActionPolicy):
    """Maps time_pressure dimension to action complexity."""

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        pressure = dims.get("time_pressure", "None")
        player_behind = state.player_bet < state.bot_bet

        if pressure == "High":
            # Rushed: never raise, fold 80% when behind, otherwise check/call
            if player_behind:
                return "fold" if rng.random() < 0.8 else "call"
            return "check"
        elif pressure == "Moderate":
            # 50% chance to simplify to basic check/call
            if rng.random() < 0.5:
                return "call" if player_behind else "check"
        return None

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        pressure = dims.get("time_pressure", "None")
        return {"decision_pressure": pressure.lower()}


class DomainKnowledgePolicy(PersonaActionPolicy):
    """Maps domain knowledge to poker strategic awareness."""

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        domain = dims.get("domain", "General")
        player_behind = state.player_bet < state.bot_bet

        if domain == "Gaming":
            # High aggression, leverages fold equity
            if player_behind:
                return "raise" if rng.random() < 0.4 else None
            return "raise" if rng.random() < 0.5 else None
        elif domain == "Finance":
            # Pot odds mathematical evaluation
            to_call = state.bot_bet - state.player_bet
            if to_call > 0 and (state.pot + to_call) > 0:
                pot_odds = to_call / (state.pot + to_call)
                return "call" if pot_odds <= 0.35 else "fold"
        elif domain == "General":
            # Less optimal non-standard plays
            if rng.random() < 0.2:
                return rng.choice(["check", "call", "raise", "fold"])
        return None

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        domain = dims.get("domain", "General")
        return {"domain_awareness": domain.lower()}


class DominantTraitPolicy(PersonaActionPolicy):
    """Maps dominant_trait / Big Five table persona to table aggression."""

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        trait = dims.get("dominant_trait", "Social")
        player_behind = state.player_bet < state.bot_bet

        if trait == "Competitive":
            return "raise" if rng.random() < 0.5 else "call"
        elif trait == "Reserved":
            if player_behind:
                return "fold" if rng.random() < 0.5 else "call"
            return "check"
        elif trait == "Creative":
            if rng.random() < 0.3:
                return rng.choice(["raise", "call", "check"])
        elif trait == "Social":
            # Mirror bot's action
            return "call" if player_behind else "check"
        return None

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        trait = dims.get("dominant_trait", "Social")
        return {"trait_expression": trait.lower()}


class RiskPolicy(PersonaActionPolicy):
    """Maps risk_tolerance dimension to poker aggressiveness & risk_posture.

    Preflop decisions use Sklansky hand-tier thresholding to produce
    biologically plausible folding behavior. Post-flop decisions continue
    to use the bet-position heuristic. Modifiers apply for age & life_stage.
    """

    _RISK_POSTURE_MAP = {
        "Low": "risk_averse",
        "Moderate": "balanced",
        "High": "risk_seeking",
    }

    _FOLD_PREFLOP: dict[str, dict[int, float]] = {
        "Low":      {1: 0.00, 2: 0.00, 3: 0.05, 4: 0.15, 5: 0.30, 6: 0.50, 7: 0.70, 8: 0.85},
        "Moderate": {1: 0.00, 2: 0.00, 3: 0.02, 4: 0.08, 5: 0.15, 6: 0.30, 7: 0.50, 8: 0.65},
        "High":     {1: 0.00, 2: 0.00, 3: 0.00, 4: 0.02, 5: 0.05, 6: 0.10, 7: 0.20, 8: 0.35},
    }

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        rt = dims.get("risk_tolerance", "Moderate")
        age = dims.get("age_bracket", "")
        player_behind = state.player_bet < state.bot_bet

        # Apply age & life_stage risk modifiers
        mod = 0.0
        if "18-24" in age and rt == "High":
            mod = -0.15  # 15% lower fold rate (more aggressive)
        elif "55+" in age and rt == "High":
            mod = 0.10   # 10% higher fold rate

        if getattr(state, "street", "") == "preflop":
            if player_behind:
                tier = classify_preflop(state.hole_cards)
                base_fold = self._FOLD_PREFLOP.get(rt, {}).get(tier, 0.65)
                fold_pct = max(0.0, min(1.0, base_fold + mod))
                if rng.random() < fold_pct:
                    return "fold"
                if rt == "High":
                    return "raise" if rng.random() < 0.5 else "call"
                if rt == "Low":
                    return "call"
                return "call" if rng.random() < 0.7 else "raise"
            else:
                if rt == "High":
                    return "raise" if rng.random() < 0.4 else "check"
                return "check"

        if rt == "Low":
            if player_behind:
                return "fold" if rng.random() < (0.6 + mod) else "call"
            return "check"
        elif rt == "High":
            if player_behind:
                return "raise" if rng.random() < 0.5 else "call"
            return "raise" if rng.random() < 0.4 else "check"
        return None

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        rt = dims.get("risk_tolerance", "Moderate")
        return {"risk_posture": self._RISK_POSTURE_MAP.get(rt, "balanced")}


class DecisionStylePolicy(PersonaActionPolicy):
    """Maps decision_style to decision strategy & exploration_style."""

    _STYLE_MAP = {
        "Analytical": "deep_research",
        "Impulsive": "quick_pick",
        "Cautious": "hesitant",
        "Intuitive": "compared_multiple",
    }

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        ds = dims.get("decision_style", "Analytical")
        if ds == "Analytical":
            return self._pot_odds_decision(state)
        elif ds == "Impulsive":
            return rng.choice(["fold", "check", "call", "raise"])
        elif ds == "Cautious":
            if state.player_bet < state.bot_bet:
                return "call" if rng.random() < 0.7 else "fold"
            return "check"
        return None

    def _pot_odds_decision(self, state: Any) -> str:
        to_call = state.bot_bet - state.player_bet
        if to_call <= 0:
            return "check"
        pot_odds = to_call / (state.pot + to_call) if (state.pot + to_call) > 0 else 1.0
        return "call" if pot_odds <= 0.4 else "fold"

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        ds = dims.get("decision_style", "Analytical")
        return {"exploration_style": self._STYLE_MAP.get(ds, "deep_research")}


class EconomicMotivationPolicy(PersonaActionPolicy):
    """Maps economic_motivation to chip strategy & task_strategy_basis."""

    _STRATEGY_MAP = {
        "Cost-sensitive": "pot_control",
        "Value-driven": "hand_strength",
        "Premium-seeking": "bluff",
        "Status-seeking": "bluff",
        "Loss-averse": "pot_control",
    }

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> Optional[str]:
        eco = dims.get("economic_motivation", "Value-driven")
        socio = dims.get("socioeconomic_band", "Middle")

        # Socioeconomic modifier
        if socio == "Low income":
            if state.player_bet < state.bot_bet and rng.random() < 0.3:
                return "fold"

        if eco in ("Cost-sensitive", "Loss-averse"):
            if state.player_bet < state.bot_bet:
                return "fold"
            return "check"
        elif eco in ("Premium-seeking", "Status-seeking"):
            if state.player_bet >= state.bot_bet:
                return "raise" if rng.random() < 0.3 else "check"
            return "call"
        return None

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        eco = dims.get("economic_motivation", "Value-driven")
        return {"task_strategy_basis": self._STRATEGY_MAP.get(eco, "hand_strength")}


class _BasePolicy(PersonaActionPolicy):
    """Fallback base policy for default poker action decisions."""

    def decide(self, state: Any, dims: Dict[str, str], rng: random.Random) -> str:
        to_call = state.bot_bet - state.player_bet
        if to_call <= 0:
            return "check"
        return "call"

    def derive_output_fields(self, dims: Dict[str, str]) -> Dict[str, Any]:
        return {
            "risk_posture": "balanced",
            "exploration_style": "deep_research",
            "task_strategy_basis": "hand_strength",
        }

