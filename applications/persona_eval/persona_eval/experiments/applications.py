from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from persona_eval.goal_contexts import get_goal_context
from persona_eval.sut_descriptions import sut_description_for


@dataclass(frozen=True)
class ApplicationSpec:
    """One application target exposed through the experiment runner."""

    key: str
    application_type: str
    application_id: str
    application_context: str
    domain: str
    label: str
    system_label: str
    description_key: str
    concurrency_limit: int = 4
    min_turns: int = 3

    def to_dict(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "applicationType": self.application_type,
            "applicationId": self.application_id,
            "applicationContext": self.application_context,
            "domain": self.domain,
            "label": self.label,
            "systemLabel": self.system_label,
            "descriptionKey": self.description_key,
            "concurrencyLimit": self.concurrency_limit,
            "minTurns": self.min_turns,
        }


_REGISTRY: Dict[str, ApplicationSpec] = {
    "recai:movie": ApplicationSpec(
        key="recai:movie",
        application_type="chatbot",
        application_id="recai",
        application_context="movie",
        domain="movie",
        label="RecAI / InteRecAgent movie recommender",
        system_label="movie recommendation system",
        description_key="movie",
        concurrency_limit=1,
    ),
    "recai:beauty_product": ApplicationSpec(
        key="recai:beauty_product",
        application_type="chatbot",
        application_id="recai",
        application_context="beauty_product",
        domain="beauty_product",
        label="RecAI / InteRecAgent beauty recommender",
        system_label="beauty and personal-care recommendation system",
        description_key="beauty_product",
        concurrency_limit=1,
    ),
    "recai:game": ApplicationSpec(
        key="recai:game",
        application_type="chatbot",
        application_id="recai",
        application_context="game",
        domain="game",
        label="RecAI / InteRecAgent game recommender",
        system_label="game recommendation system",
        description_key="game",
        concurrency_limit=1,
    ),
    "finance_openbb:financial_research": ApplicationSpec(
        key="finance_openbb:financial_research",
        application_type="chatbot",
        application_id="finance_openbb",
        application_context="financial_research",
        domain="financial_research",
        label="FinAI / OpenBB financial research chatbot",
        system_label="financial research system",
        description_key="financial_research",
        concurrency_limit=8,
    ),
    "medical_assistant:medical_consultation": ApplicationSpec(
        key="medical_assistant:medical_consultation",
        application_type="chatbot",
        application_id="medical_assistant",
        application_context="medical_consultation",
        domain="medical_consultation",
        label="Medical assistant chatbot",
        system_label="medical assistant",
        description_key="medical_consultation",
        concurrency_limit=8,
    ),
}

_ALIASES = {
    "movie": "recai:movie",
    "beauty": "recai:beauty_product",
    "beauty_product": "recai:beauty_product",
    "game": "recai:game",
    "finance": "finance_openbb:financial_research",
    "finance_openbb": "finance_openbb:financial_research",
    "financial_research": "finance_openbb:financial_research",
    "medical": "medical_assistant:medical_consultation",
    "medical_assistant": "medical_assistant:medical_consultation",
    "medical_consultation": "medical_assistant:medical_consultation",
}


def list_application_specs() -> List[ApplicationSpec]:
    return list(_REGISTRY.values())


def parse_application_ref(ref: str) -> ApplicationSpec:
    normalized = str(ref or "").strip().replace("/", ":")
    key = _ALIASES.get(normalized, normalized)
    return get_application_spec(key)


def get_application_spec(key: str) -> ApplicationSpec:
    try:
        return _REGISTRY[key]
    except KeyError:
        raise KeyError("unknown application: {}".format(key))


def build_chatbot_task_prompt(
    spec: ApplicationSpec,
    *,
    goal_context_id: str = "scenario_default",
) -> str:
    goal_context = get_goal_context(goal_context_id)
    return """You are a user of a {system_label}.

{sut_description}

Context for this interaction: {goal_context_description}

Based on your assigned persona, silently decide what you realistically want from
this system and which constraints or preferences matter to you. Start the
conversation naturally. Do not reveal everything at once. Let the system ask
follow-up questions, answer in character, and give feedback when a response does
not fit. Continue until you can judge whether the system satisfied your need.
""".format(
        system_label=spec.system_label,
        sut_description=sut_description_for(spec.description_key),
        goal_context_description=goal_context.description,
    )
