"""Compatibility package for the legacy PersonaEval app-local modules.

The active core package lives in ``packages/persona-eval/src/persona_eval``.
Pytest may prepend ``application/persona_eval`` during backend test collection,
so this package must extend its search path instead of hiding the core modules.
"""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

_extended_path = list(extend_path(__path__, __name__))
_core_path = Path(__file__).resolve().parents[3] / "packages" / "persona-eval" / "src" / "persona_eval"

if _core_path.is_dir():
    core = str(_core_path)
    __path__ = [core, *[entry for entry in _extended_path if entry != core]]
else:
    __path__ = _extended_path
