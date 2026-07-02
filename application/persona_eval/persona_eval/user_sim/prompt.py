"""Assemble UserSim v2 system prompts (guidelines + persona + scenario)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from persona_eval.types import Persona
from persona_eval.user_sim.scenario import UserScenario

_GUIDELINES_PATH = Path(__file__).resolve().parent / "sim_guidelines.md"


def load_sim_guidelines() -> str:
    return _GUIDELINES_PATH.read_text(encoding="utf-8").strip()


def _persona_context(persona: Persona) -> str:
    if persona.context:
        return persona.context
    parts = [
        "Name: {}".format(persona.name),
        "Who you are: {}".format(persona.summary or "(a typical user)"),
        "What you want (preferences): {}".format(", ".join(persona.preferences) or "(open)"),
        "What you dislike: {}".format(", ".join(persona.dislikes) or "(none stated)"),
        "Your constraints: {}".format(", ".join(persona.constraints) or "(flexible)"),
        "Your goal: {}".format(persona.goal or "(find something suitable)"),
        "How you talk: {}".format(persona.communication_style or "natural and conversational"),
    ]
    return "\n".join(parts)


def render_persona_block(persona: Persona, *, persona_yaml_path: Optional[str] = None) -> str:
    if persona_yaml_path:
        try:
            from personabench.agents.persona.loader import load_persona
            from personabench.agents.persona.templating import (
                PERSONA_SYSTEM_TEMPLATE,
                render_persona_template,
                resolve_persona_template,
            )

            loaded = load_persona(persona_yaml_path)
            template = resolve_persona_template(loaded, None, PERSONA_SYSTEM_TEMPLATE)
            return render_persona_template(template, loaded).strip()
        except Exception:
            pass
    return _persona_context(persona)


def assemble_system_prompt(
    persona: Persona,
    scenario: UserScenario,
    *,
    persona_yaml_path: Optional[str] = None,
) -> str:
    blocks = [
        load_sim_guidelines(),
        "## Persona\n{}".format(render_persona_block(persona, persona_yaml_path=persona_yaml_path)),
        scenario.render_block(),
    ]
    return "\n\n".join(block for block in blocks if block.strip())


def prompt_bundle(
    persona: Persona,
    scenario: UserScenario,
    *,
    persona_yaml_path: Optional[str] = None,
    task_prompt: str = "",
) -> dict[str, str]:
    system = assemble_system_prompt(persona, scenario, persona_yaml_path=persona_yaml_path)
    return {
        "personaPrompt": system,
        "harborPrompt": system,
        "taskPrompt": task_prompt or scenario.goal or scenario.sut_context,
    }
