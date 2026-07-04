"""Tool-driven multi-turn simulated user."""

from __future__ import annotations


def run_persona_eval(*args, **kwargs):
    from persona_eval.user_sim.runner import run_persona_eval as _run_persona_eval

    return _run_persona_eval(*args, **kwargs)


async def run_persona_eval_async(*args, **kwargs):
    from persona_eval.user_sim.runner import (
        run_persona_eval_async as _run_persona_eval_async,
    )

    return await _run_persona_eval_async(*args, **kwargs)


__all__ = [
    "run_persona_eval",
    "run_persona_eval_async",
]
