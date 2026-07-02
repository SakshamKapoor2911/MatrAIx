"""User-side hidden scenario for UserSim v2 (separate from agent instruction)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

import yaml

from persona_eval.goal_contexts import GoalContext


@dataclass
class HiddenFact:
    """Task-specific fact the sim user may reveal later (disclosure policy is global)."""

    id: str
    text: str
    reveal_when: str = ""


@dataclass
class UserScenario:
    """Hidden user-side script for one task — not the global sim behavior."""

    identity: str = ""
    goal: str = ""
    domain: str = ""
    preferences: List[str] = field(default_factory=list)
    style: str = ""
    stop_when: str = "goal_satisfied"
    sut_context: str = ""
    hidden_facts: List[HiddenFact] = field(default_factory=list)

    def render_block(self) -> str:
        lines = ["## Your scenario (hidden from the application agent)"]
        if self.identity:
            lines.append("Identity: {}".format(self.identity))
        if self.goal:
            lines.append("Goal: {}".format(self.goal))
        if self.domain:
            lines.append("Domain / context: {}".format(self.domain))
        if self.preferences:
            lines.append("Task-specific preferences:")
            lines.extend("- {}".format(item) for item in self.preferences)
        if self.style:
            lines.append("How you talk in this task: {}".format(self.style))
        if self.stop_when:
            lines.append("Stop when: {}".format(self.stop_when))
        if self.sut_context:
            lines.append("")
            lines.append(self.sut_context.strip())
        if self.hidden_facts:
            lines.append("")
            lines.append(
                "Hidden facts (use reveal_fact when appropriate; follow global progressive disclosure):"
            )
            for fact in self.hidden_facts:
                when = " — reveal when: {}".format(fact.reveal_when) if fact.reveal_when else ""
                lines.append("- [{}] {}{}".format(fact.id, fact.text, when))
        return "\n".join(lines).strip()

    @classmethod
    def from_goal_context(
        cls,
        goal_context: GoalContext,
        *,
        domain: str,
        sut_description: str,
    ) -> "UserScenario":
        return cls(
            goal=goal_context.description,
            domain=domain,
            style="Brief and conversational (1-3 sentences).",
            sut_context=sut_description.strip(),
        )


def _load_hidden_facts(raw: dict[str, Any]) -> List[HiddenFact]:
    facts_raw = raw.get("hidden_facts")
    if facts_raw is None:
        disclosure = raw.get("disclosure") or {}
        if isinstance(disclosure, dict):
            facts_raw = disclosure.get("facts")
    facts: List[HiddenFact] = []
    if not isinstance(facts_raw, list):
        return facts
    for item in facts_raw:
        if not isinstance(item, dict):
            continue
        fact_id = str(item.get("id") or "").strip()
        if not fact_id:
            continue
        facts.append(
            HiddenFact(
                id=fact_id,
                text=str(item.get("text") or "").strip(),
                reveal_when=str(item.get("reveal_when") or "").strip(),
            )
        )
    return facts


def load_user_scenario(path: Path) -> UserScenario:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("user_scenario.yaml must be a mapping")
    prefs = raw.get("preferences") or []
    return UserScenario(
        identity=str(raw.get("identity") or "").strip(),
        goal=str(raw.get("goal") or "").strip(),
        domain=str(raw.get("domain") or "").strip(),
        preferences=[str(p).strip() for p in prefs if str(p).strip()],
        style=str(raw.get("style") or "").strip(),
        stop_when=str(raw.get("stop_when") or "goal_satisfied").strip(),
        sut_context=str(raw.get("sut_context") or raw.get("sutContext") or "").strip(),
        hidden_facts=_load_hidden_facts(raw),
    )


def resolve_user_scenario(
    *,
    task_path: Optional[str] = None,
    goal_context: GoalContext,
    domain: str,
    sut_description: str,
    repo_root: Optional[Path] = None,
) -> UserScenario:
    """Load ``user_scenario.yaml`` from a task dir, or fall back to goal context."""
    candidates: List[Path] = []
    if task_path:
        base = Path(task_path)
        if not base.is_absolute() and repo_root is not None:
            base = repo_root / base
        candidates.append(base / "user_scenario.yaml")
    for path in candidates:
        if path.is_file():
            scenario = load_user_scenario(path)
            if not scenario.domain:
                scenario = UserScenario(
                    identity=scenario.identity,
                    goal=scenario.goal,
                    domain=domain,
                    preferences=list(scenario.preferences),
                    style=scenario.style,
                    stop_when=scenario.stop_when,
                    sut_context=scenario.sut_context or sut_description,
                    hidden_facts=list(scenario.hidden_facts),
                )
            return scenario
    return UserScenario.from_goal_context(goal_context, domain=domain, sut_description=sut_description)
