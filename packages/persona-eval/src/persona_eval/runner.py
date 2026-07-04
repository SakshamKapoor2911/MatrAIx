from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from persona_eval.types import (
    Persona, PersonaEvalConfig, PersonaEvalResult,
)


def run_persona_eval(
    session: Any,
    persona: Persona,
    sut_description: str,
    config: PersonaEvalConfig,
    simulator: Any | None = None,
    *,
    created_at: str,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    task_path: Optional[str] = None,
    persona_yaml_path: Optional[str] = None,
    repo_root: Optional[Any] = None,
) -> PersonaEvalResult:
    del simulator
    from persona_eval.user_sim.runner import run_persona_eval as _run_user_sim

    return _run_user_sim(
        session,
        persona,
        sut_description,
        config,
        created_at=created_at,
        on_event=on_event,
        task_path=task_path,
        persona_yaml_path=persona_yaml_path,
        repo_root=repo_root,
    )
