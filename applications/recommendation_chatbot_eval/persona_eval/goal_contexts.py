from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

_SCENARIO_DEFAULT = """You are a real user of a {domain} recommendation system.

{sut_description}

Your assigned persona — stay in character at all times:
{persona_context}

Based on your assigned persona, first decide what kind of products/items you \
realistically want from this {domain} recommender and what constraints and \
preferences matter most to you. Then behave like a genuine human user:
- Do NOT reveal everything at once — share your needs gradually, as a real person \
would, and answer the agent's follow-up questions naturally.
- React to the agent's recommendations: if they fit your needs, say so; if not, \
push back or refine.
- Keep messages short and conversational (1-3 sentences)."""

_GRADUAL_REVEAL = """You are role-playing a real user of a {domain} recommendation system.

{sut_description}

Your persona — stay in character at all times:
{persona_context}

Behave like a realistic human user:
- Decide what you realistically want and which constraints matter most to you.
- Do NOT reveal everything at once — share preferences gradually, as a real person \
would, and answer the agent's follow-up questions naturally.
- React to the agent's recommendations: if they fit your needs, say so; if not, \
push back or refine.
- Keep messages short and conversational (1-3 sentences)."""


@dataclass
class GoalContext:
    id: str
    label: str
    description: str
    template: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "template": self.template,
        }


_REGISTRY: Dict[str, GoalContext] = {
    "scenario_default": GoalContext(
        id="scenario_default",
        label="Realistic scenario",
        description="Persona derives a realistic per-domain shopping intent and "
        "reveals it gradually.",
        template=_SCENARIO_DEFAULT,
    ),
    "gradual_reveal": GoalContext(
        id="gradual_reveal",
        label="Gradual reveal",
        description="Classic gradual-reveal user simulator prompt.",
        template=_GRADUAL_REVEAL,
    ),
}


def load_goal_contexts() -> List[GoalContext]:
    return list(_REGISTRY.values())


def get_goal_context(id: str) -> GoalContext:
    try:
        return _REGISTRY[id]
    except KeyError:
        raise KeyError("unknown goal context: {!r}".format(id))
