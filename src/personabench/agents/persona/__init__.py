"""Persona-backed Harbor agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from personabench.agents.persona.browser_use import PersonaBrowserUse
    from personabench.agents.persona.claude_code import PersonaClaudeCode
    from personabench.agents.persona.cocoa import PersonaCocoa
    from personabench.agents.persona.codex import PersonaCodex
    from personabench.agents.persona.computer_1 import PersonaComputer1
    from personabench.agents.persona.gemini_cli import PersonaGeminiCli
    from personabench.agents.persona.loader import (
        Persona,
        load_persona,
        resolve_persona_path,
    )
    from personabench.agents.persona.openhands_sdk import PersonaOpenHandsSDK

_LAZY_IMPORTS = {
    "Persona": ("personabench.agents.persona.loader", "Persona"),
    "PersonaBrowserUse": (
        "personabench.agents.persona.browser_use",
        "PersonaBrowserUse",
    ),
    "PersonaClaudeCode": (
        "personabench.agents.persona.claude_code",
        "PersonaClaudeCode",
    ),
    "PersonaCocoa": ("personabench.agents.persona.cocoa", "PersonaCocoa"),
    "PersonaCodex": ("personabench.agents.persona.codex", "PersonaCodex"),
    "PersonaComputer1": (
        "personabench.agents.persona.computer_1",
        "PersonaComputer1",
    ),
    "PersonaGeminiCli": (
        "personabench.agents.persona.gemini_cli",
        "PersonaGeminiCli",
    ),
    "PersonaOpenHandsSDK": (
        "personabench.agents.persona.openhands_sdk",
        "PersonaOpenHandsSDK",
    ),
    "load_persona": ("personabench.agents.persona.loader", "load_persona"),
    "resolve_persona_path": (
        "personabench.agents.persona.loader",
        "resolve_persona_path",
    ),
}

__all__ = sorted(_LAZY_IMPORTS)


def __getattr__(name: str):
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_path, attr_name = _LAZY_IMPORTS[name]
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, attr_name)
