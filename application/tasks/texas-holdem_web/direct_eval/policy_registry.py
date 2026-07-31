"""Policy registry for constructing composed persona policies."""
from __future__ import annotations

from typing import Dict

from .policies import (
    ComposedPolicy,
    DecisionStylePolicy,
    DomainKnowledgePolicy,
    DominantTraitPolicy,
    EconomicMotivationPolicy,
    PersonaActionPolicy,
    PersonaValueNormalizer,
    RiskPolicy,
    TimePressurePolicy,
    TrustPolicy,
    _BasePolicy,
)


def build_policy(dims: Dict[str, str]) -> PersonaActionPolicy:
    """Build a composed policy from persona dimensions."""
    norm_dims = PersonaValueNormalizer.normalize_all(dims)
    sub_policies = []

    if "time_pressure" in norm_dims:
        sub_policies.append(TimePressurePolicy())
    if "risk_tolerance" in norm_dims:
        sub_policies.append(RiskPolicy())
    if "trust_level" in norm_dims:
        sub_policies.append(TrustPolicy())
    if "decision_style" in norm_dims:
        sub_policies.append(DecisionStylePolicy())
    if "economic_motivation" in norm_dims:
        sub_policies.append(EconomicMotivationPolicy())
    if "domain" in norm_dims:
        sub_policies.append(DomainKnowledgePolicy())
    if "dominant_trait" in norm_dims:
        sub_policies.append(DominantTraitPolicy())

    sub_policies.append(_BasePolicy())

    return ComposedPolicy(sub_policies)
